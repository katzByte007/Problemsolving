import streamlit as st
import sqlite3
import hashlib
import torch
import whisper
import ollama
import base64
import numpy as np
from PIL import Image
import io
import re
from gtts import gTTS
import requests
import json
from streamlit_webrtc import webrtc_streamer
import av



# Database Initialization
def init_database():
    """Initialize SQLite database for users and alerts with media storage"""
    conn = sqlite3.connect('user4_database.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        department TEXT
    )''')
    
    # Modified alerts table to include media storage
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        department TEXT,
        priority INTEGER,
        description TEXT,
        status TEXT DEFAULT 'UNREAD',
        image_data BLOB,
        audio_data BLOB
    )''')
    
    # Add default users (same as before)
    default_users = [
        ('fire_head', 'firepass', 'head', 'Fire Department'),
        ('health_head', 'healthpass', 'head', 'Health Care Department'),
        ('damage_head', 'damagepass', 'head', 'Equipment Damage Department'),
        ('missing_head', 'missingpass', 'head', 'Missing Item Department')
    ]
    
    for username, password, role, department in default_users:
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", 
                       (username, hashed_password, role, department))
    
    conn.commit()
    conn.close()

# Authentication Function
def authenticate_user(username, password):
    """Authenticate user credentials"""
    conn = sqlite3.connect('user4_database.db')
    cursor = conn.cursor()
    
    # Hash the password
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    
    # Check user credentials
    cursor.execute("""
        SELECT username, role, department 
        FROM users 
        WHERE username = ? AND password = ?
    """, (username, hashed_password))
    
    user = cursor.fetchone()
    conn.close()
    
    return user

# Create Alert Function
def create_alert(department, priority, description, image_data=None, audio_data=None):
    """Create an alert in the database with media data"""
    conn = sqlite3.connect('user4_database.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO alerts (department, priority, description, status, image_data, audio_data) 
            VALUES (?, ?, ?, 'UNREAD', ?, ?)
        """, (department, priority, description, image_data, audio_data))
        
        conn.commit()
        
    except Exception as e:
        print(f"Error creating alert: {e}")
        conn.rollback()
    
    finally:
        conn.close()
def capture_camera():
    """Handle camera capture using webrtc"""
    webrtc_ctx = webrtc_streamer(
        key="camera",
        video_frame_callback=None,
        rtc_configuration={
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        }
    )
    return webrtc_ctx

def img2txt(input_text, input_image, audio_data=None, additional_context=""):
    try:
        # Convert image to bytes for storage
        buffered = io.BytesIO()
        input_image.save(buffered, format="PNG")
        img_data = buffered.getvalue()
        img_str = base64.b64encode(buffered.getvalue()).decode()

        API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
        headers = {"Authorization": f"Bearer {st.secrets['HUGGINGFACE_TOKEN']}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": {"image": img_str}})
        
        if response.status_code != 200:
            st.error(f"API Error: {response.text}")
            return "Error: Unable to process image"

        image_description = response.json()[0]['generated_text']
        combined_text = f"{image_description} {input_text} {additional_context}".strip()

        keywords = {
            'pipe': ('Equipment Damage Department', 3),
            'leak': ('Equipment Damage Department', 3),
            'equipment': ('Equipment Damage Department', 3),
            'fire': ('Fire Department', 1),
            'smoke': ('Fire Department', 1),
            'injury': ('Health Care Department', 2),
            'medical': ('Health Care Department', 2),
            'missing': ('Missing Item Department', 4),
            'lost': ('Missing Item Department', 4)
        }
        
        department_match = ('Missing Item Department', 4)  # Default
        for keyword, (dept, pri) in keywords.items():
            if keyword in combined_text.lower():
                department_match = (dept, pri)
                break

        description = f"{combined_text}"[:500]
        create_alert(department_match[0], department_match[1], description, img_data, audio_data)
        
        return description

    except Exception as e:
        st.error(f"Error in img2txt: {str(e)}")
        return f"Error processing image: {str(e)}"

    
def transcribe_audio(audio_bytes):
    """Transcribe audio using Hugging Face's Whisper API"""
    try:
        API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
        headers = {
            "Authorization": f"Bearer {st.secrets['HUGGINGFACE_TOKEN']}"
        }

        # Make API request
        response = requests.post(
            API_URL,
            headers=headers,
            data=audio_bytes
        )

        if response.status_code != 200:
            return f"Error: API request failed with status {response.status_code}"

        result = response.json()
        return result.get('text', '')

    except Exception as e:
        return f"Error transcribing audio: {str(e)}"

# Text to Speech Function
def text_to_speech(text, file_path="output_speech.mp3"):
    """Convert text to speech using gTTS"""
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(file_path)
        return file_path
    except Exception as e:
        return None


def check_alerts(username):
    """Retrieve and format alerts with media display"""
    conn = sqlite3.connect('user4_database.db')
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT department FROM users WHERE username = ?", (username,))
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return "Error: User department not found.", []

        user_department = user_result[0]

        cursor.execute("""
            SELECT id, timestamp, description, priority, status, image_data, audio_data
            FROM alerts
            WHERE department = ?
            ORDER BY timestamp DESC
        """, (user_department,))

        alerts = cursor.fetchall()
        conn.close()

        if not alerts:
            return f"No alerts found for {user_department}.", []

        # Format alerts with media handling
        formatted_alerts = []
        output = f"🚨 {user_department.upper()} ALERTS 🚨\n\n"
        
        for alert in alerts:
            alert_id, timestamp, description, priority, status, image_data, audio_data = alert
            
            # Create dictionary for each alert with all necessary data
            alert_dict = {
                'id': alert_id,
                'timestamp': timestamp,
                'description': description,
                'priority': priority,
                'status': status,
                'image_data': image_data,
                'audio_data': audio_data
            }
            formatted_alerts.append(alert_dict)
            
            # Add to text output
            status_icon = "🔴" if status == "UNREAD" else "🔵"
            output += f"{status_icon} {timestamp}\n{description}\n\n"

        return output, formatted_alerts

    except Exception as e:
        return f"Error retrieving alerts: {str(e)}", []
def clear_department_alerts(username):
    """Completely clear all alerts for a specific department"""
    conn = sqlite3.connect('user1_database.db')
    cursor = conn.cursor()

    try:
        # Get user's department
        cursor.execute("SELECT department FROM users WHERE username = ?", (username,))
        department = cursor.fetchone()[0]

        # Completely remove all alerts for the department
        cursor.execute("DELETE FROM alerts WHERE department = ?", (department,))
        
        conn.commit()
        rows_deleted = cursor.rowcount
        
        return rows_deleted, department

    except Exception as e:
        print(f"Error clearing alerts: {e}")
        return 0, None
# Main Streamlit App
def main():
    # Initialize session state and database (same as before)
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'department' not in st.session_state:
        st.session_state['department'] = None

    if 'HUGGINGFACE_TOKEN' not in st.secrets:
        st.secrets['HUGGINGFACE_TOKEN'] = "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"

    init_database()

    st.title("Multimodal Alert System")

    # Login section (same as before)
    if not st.session_state.logged_in:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            user = authenticate_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.department = user[2]
                st.rerun()
            else:
                st.error("Invalid credentials")

    # Main Interface after Login
    if st.session_state.logged_in:
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()

        tab1, tab2 = st.tabs(["Alert Generation", "Check Alerts"])

        with tab1:
            # [Alert Generation tab code remains the same]
            st.subheader("Generate Alert")
            
            # Image Input
            st.markdown("### Upload Image")
            image_file = st.file_uploader(
                "Take a photo or choose from gallery", 
                type=['png', 'jpg', 'jpeg'],
                accept_multiple_files=False,
                help="Select image from gallery or take a photo"
            )
            
            # Audio Input
            st.markdown("### Upload Audio")
            audio_file = st.file_uploader(
                "Record audio or choose from gallery",
                type=['wav', 'mp3'],
                accept_multiple_files=False,
                help="Select audio from device or record"
            )
            
            # Additional Context
            additional_context = st.text_area(
                "Additional Context",
                placeholder="Add location, address, or any other relevant details...",
                help="This information will be included in the alert description"
            )
            
            if st.button("Process Inputs", type="primary"):
                speech_text = ""
                audio_data = None
                if audio_file:
                    audio_data = audio_file.read()
                    speech_text = transcribe_audio(audio_data)
                    st.write("Speech to Text:", speech_text)
                
                if image_file:
                    image = Image.open(image_file)
                    st.image(image, caption="Uploaded Image", use_column_width=True)
                    
                    alert_description = img2txt(
                        speech_text, 
                        image,
                        audio_data,
                        additional_context
                    )
                    st.write("Alert Description:", alert_description)
                    
                    if audio_data:
                        st.audio(audio_data)

        with tab2:
            st.subheader("Department Alerts")
            
            # Create two columns for buttons
            col1, col2 = st.columns(2)
            
            # Retrieve Alerts button in first column
            with col1:
                retrieve_button = st.button("Retrieve Alerts", key="retrieve_alerts")
            
            # Clear Alerts button and confirmation in second column
            with col2:
                clear_confirmation = st.checkbox("Confirm Alert Deletion", key="clear_confirm")
                if clear_confirmation:
                    if st.button("Clear All Department Alerts", type="primary", key="clear_alerts"):
                        rows_deleted, department = clear_department_alerts(st.session_state.username)
                        if rows_deleted > 0:
                            st.success(f"Successfully cleared {rows_deleted} alerts for {department}.")
                        else:
                            st.info(f"No alerts to clear for {department}.")
                        # Force refresh of alerts display
                        retrieve_button = True

            # Display alerts if retrieve button is clicked
            if retrieve_button:
                alerts_text, formatted_alerts = check_alerts(st.session_state.username)
                
                if not formatted_alerts:
                    st.info("No alerts found for your department.")
                else:
                    for alert in formatted_alerts:
                        st.markdown(f"### Alert {alert['id']} - {alert['timestamp']}")
                        st.write(alert['description'])
                        
                        # Display image if available
                        if alert['image_data']:
                            try:
                                image = Image.open(io.BytesIO(alert['image_data']))
                                st.image(image, caption=f"Alert {alert['id']} Image", use_column_width=True)
                            except Exception as e:
                                st.error(f"Error displaying image: {e}")
                        
                        # Display audio if available
                        if alert['audio_data']:
                            try:
                                st.audio(alert['audio_data'])
                            except Exception as e:
                                st.error(f"Error playing audio: {e}")
                        
                        st.markdown("---")

# Run the app
if __name__ == "__main__":
    main()

