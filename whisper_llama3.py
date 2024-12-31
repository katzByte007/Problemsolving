#streamlit.py
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
import streamlit as st
import sqlite3
import hashlib
import base64
import numpy as np
from PIL import Image
import io
import requests
from gtts import gTTS
import json

# Database Initialization
def init_database():
    """Initialize SQLite database for users and alerts"""
    conn = sqlite3.connect('user1_database.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT,
        department TEXT
    )''')
    
    # Create alerts table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        department TEXT,
        priority INTEGER,
        description TEXT,
        status TEXT DEFAULT 'UNREAD'
    )''')
    
    # Add default users
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
    conn = sqlite3.connect('user1_database.db')
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
def create_alert(department, priority, description):
    """Create an alert in the database"""
    conn = sqlite3.connect('user1_database.db')
    cursor = conn.cursor()
    
    try:
        # Debug print to verify alert creation
        print(f"Creating alert - Department: {department}, Priority: {priority}, Description: {description}")
        
        cursor.execute("""
            INSERT INTO alerts (department, priority, description, status) 
            VALUES (?, ?, ?, 'UNREAD')
        """, (department, priority, description))
        
        conn.commit()
        
        # Debug print to confirm insertion
        print("Alert created successfully")
    
    except Exception as e:
        print(f"Error creating alert: {e}")
        conn.rollback()
    
    finally:
        conn.close()
def img2txt(input_text, input_image):
    try:
        buffered = io.BytesIO()
        input_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-base"
        headers = {"Authorization": f"Bearer {st.secrets['HUGGINGFACE_TOKEN']}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": {"image": img_str}})
        
        if response.status_code != 200:
            st.error(f"API Error: {response.text}")
            return "Error: Unable to process image"

        image_description = response.json()[0]['generated_text']

        # Determine department and priority based on description
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
            if keyword in (image_description + input_text).lower():
                department_match = (dept, pri)
                break

        description = f"{image_description} {input_text}".strip()[:200]
        create_alert(department_match[0], department_match[1], description)
        
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
    """Retrieve and format alerts ONLY for the specific user's department"""
    conn = sqlite3.connect('user1_database.db')
    cursor = conn.cursor()

    try:
        # Get user's department
        cursor.execute("SELECT department FROM users WHERE username = ?", (username,))
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return "Error: User department not found."

        user_department = user_result[0]

        # Fetch ONLY alerts for THIS specific department
        cursor.execute("""
            SELECT id, timestamp, description, priority, status
            FROM alerts
            WHERE department = ?
            ORDER BY timestamp DESC
        """, (user_department,))

        alerts = cursor.fetchall()
        conn.close()

        if not alerts:
            return f"No alerts found for {user_department}."

        # Separate recent and historical alerts
        recent_alerts = [alert for alert in alerts if alert[4] == 'UNREAD']
        historical_alerts = [alert for alert in alerts if alert[4] == 'READ']

        # Format the output with improved readability
        output = f"🚨 {user_department.upper()} ALERTS 🚨\n\n"
        
        if recent_alerts:
            output += "🔴 URGENT ALERTS:\n"
            for _, timestamp, description, priority, status in recent_alerts:
                output += f"• {timestamp}\n  {description}\n\n"
        
        if historical_alerts:
            output += "🔵 HISTORICAL ALERTS:\n"
            for _, timestamp, description, priority, status in historical_alerts:
                output += f"• {timestamp}\n  {description}\n\n"

        return output

    except Exception as e:
        return f"Error retrieving alerts: {str(e)}"
def clear_department_alerts(username):
    """Completely clear all alerts for a specific department"""
    conn = sqlite3.connect('user1_database.db')
    cursor = conn.cursor()

    # Get user's department
    cursor.execute("SELECT department FROM users WHERE username = ?", (username,))
    department = cursor.fetchone()[0]

    # Completely remove all alerts for the department
    cursor.execute("DELETE FROM alerts WHERE department = ?", (department,))
    
    conn.commit()
    rows_deleted = cursor.rowcount
    conn.close()

    return rows_deleted, department
# Main Streamlit App
def main():
    # Initialize session state variables
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'department' not in st.session_state:
        st.session_state['department'] = None

    # Store Hugging Face token in streamlit secrets
    if 'HUGGINGFACE_TOKEN' not in st.secrets:
        st.secrets['HUGGINGFACE_TOKEN'] = "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"

    
    # Initialize database
    init_database()

    # Page title
    st.title("Multimodal Alert System")

    # Session state for login
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None

    # Login Section
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
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")

    # Main Interface after Login
    if st.session_state.logged_in:
        st.sidebar.success(f"Logged in as: {st.session_state.username}")
        
        # Logout button
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.experimental_rerun()

        # Tabs for different functionalities
        tab1, tab2 = st.tabs(["Alert Generation", "Check Alerts"])

        with tab1:
            st.subheader("Generate Alert")
            
            # Audio Input
            audio_file = st.file_uploader("Upload Audio", type=['wav', 'mp3'])
            
            # Image Input
            image_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
            
            if st.button("Process Inputs"):
                # Process audio if uploaded
                speech_text = ""
                if audio_file:
                    speech_text = transcribe_audio(audio_file.read())
                    st.write("Speech to Text:", speech_text)
                
                # Process image if uploaded
                if image_file:
                    image = Image.open(image_file)
                    
                    # Generate description and alert
                    alert_description = img2txt(speech_text, image)
                    st.write("Alert Description:", alert_description)
                    
                    # Text to Speech
                    audio_output = text_to_speech(alert_description)
                    if audio_output:
                        st.audio(audio_output)

        with tab2:
            st.subheader("Department Alerts")
            
            # Style the alerts container
            st.markdown("""
            <style>
                .alert-container {
                    background-color: #000000; /* Black background */
                    color: #ffffff; /* White text */
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 20px;
                }
                .urgent-alerts {
                    color: #ff4b4b; /* Red color for urgent alerts */
                    font-weight: bold;
                }
                .historical-alerts {
                    color: #4b69ff; /* Blue color for historical alerts */
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Alerts container
            alerts_container = st.container()
            
            # Retrieve Alerts Button
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Retrieve Alerts", key="retrieve_alerts"):
                    alerts = check_alerts(st.session_state.username)
                    with alerts_container:
                        st.markdown(f'<div class="alert-container">{alerts}</div>', unsafe_allow_html=True)
            
            # Clear Alerts Button
            with col2:
                clear_confirmation = st.checkbox("Confirm Alert Deletion", key="clear_confirm")
                
                if clear_confirmation:
                    if st.button("Clear All Department Alerts", type="primary", key="clear_alerts"):
                        try:
                            # Perform deletion
                            rows_deleted, department = clear_department_alerts(st.session_state.username)
                            
                            # Immediate feedback
                            st.success(f"Successfully cleared {rows_deleted} alerts for {department}.")
                            
                            # Update alerts view
                            alerts = check_alerts(st.session_state.username)
                            with alerts_container:
                                st.markdown(f'<div class="alert-container">{alerts}</div>', unsafe_allow_html=True)
                        
                        except Exception as e:
                            st.error(f"Error clearing alerts: {str(e)}")
# Run the app
if __name__ == "__main__":
    main()