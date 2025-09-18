import streamlit as st
import sqlite3
import hashlib
import torch
from PIL import Image
import io
import re
from gtts import gTTS
import requests
import json
import av
import warnings
warnings.filterwarnings('ignore')

# Try to import transformers for local image processing
try:
    from transformers import BlipProcessor, BlipForConditionalGeneration
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    st.warning("Transformers library not available. Using fallback mode.")

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

def compress_image(image, max_size=(512, 512), quality=85):
    """Compress/resize image to reduce file size"""
    # Resize image if it's too large
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Convert to JPEG format to reduce size
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Save to buffer with reduced quality
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG", quality=quality, optimize=True)
    buffered.seek(0)
    
    return Image.open(buffered)

# Initialize BLIP model for local image captioning
@st.cache_resource
def load_blip_model():
    """Load BLIP model for local image captioning"""
    if not TRANSFORMERS_AVAILABLE:
        return None, None
    
    try:
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        return processor, model
    except Exception as e:
        st.error(f"Error loading BLIP model: {e}")
        return None, None

def local_image_captioning(image):
    """Use local BLIP model for image captioning"""
    if not TRANSFORMERS_AVAILABLE:
        return None
    
    try:
        processor, model = load_blip_model()
        if processor is None or model is None:
            return None
        
        # Preprocess the image
        inputs = processor(image, return_tensors="pt")
        
        # Generate caption
        with torch.no_grad():
            out = model.generate(**inputs, max_length=50, num_beams=5)
        
        caption = processor.decode(out[0], skip_special_tokens=True)
        return caption
        
    except Exception as e:
        st.error(f"Error in local image captioning: {e}")
        return None

def try_image_captioning_models(image_bytes, image_pil):
    """Try multiple approaches for image captioning"""
    # First try local model
    local_caption = local_image_captioning(image_pil)
    if local_caption:
        return local_caption
    
    # If local model fails, try Hugging Face API with multiple models
    HUGGINGFACE_TOKEN = "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"
    
    models_to_try = [
        "Salesforce/blip-image-captioning-base",
        "Salesforce/blip-image-captioning-large",
        "nlpconnect/vit-gpt2-image-captioning",
    ]
    
    for model_name in models_to_try:
        try:
            API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
            headers = {
                "Authorization": f"Bearer {HUGGINGFACE_TOKEN}"
            }
            
            st.info(f"Trying API model: {model_name}")
            
            response = requests.post(API_URL, headers=headers, data=image_bytes, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'generated_text' in result[0]:
                        return result[0]['generated_text']
                    else:
                        return str(result[0])
            
            elif response.status_code == 503:
                st.warning(f"Model {model_name} is loading, trying next model...")
                continue
                
        except Exception as e:
            st.warning(f"Error with API model {model_name}: {str(e)}")
            continue
    
    return None

def img2txt(input_text, input_image, audio_data=None, additional_context=""):
    try:
        # Compress the image before processing
        compressed_image = compress_image(input_image)
        
        # Convert compressed image to bytes for storage
        buffered = io.BytesIO()
        compressed_image.save(buffered, format="JPEG")
        img_data = buffered.getvalue()
        
        # Convert image to bytes for API
        buffered.seek(0)
        image_bytes = buffered.getvalue()

        # Try multiple image captioning approaches
        image_description = try_image_captioning_models(image_bytes, compressed_image)
        
        if image_description is None:
            st.warning("All image captioning methods failed. Using fallback description.")
            return fallback_image_processing(input_text, additional_context, img_data, audio_data)

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
        return fallback_image_processing(input_text, additional_context, img_data, audio_data)

def fallback_image_processing(input_text, additional_context, img_data=None, audio_data=None):
    """Fallback method when image processing fails"""
    # Create a simple description based on available text
    combined_text = f"Image analysis unavailable. {input_text} {additional_context}".strip()
    
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

def transcribe_audio(audio_bytes):
    """Transcribe audio using Hugging Face's Whisper API"""
    try:
        HUGGINGFACE_TOKEN = "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"
        
        # Try multiple Whisper models
        whisper_models = [
            "openai/whisper-large-v3",
            "openai/whisper-large-v2",
            "openai/whisper-base"
        ]
        
        for model_name in whisper_models:
            try:
                API_URL = f"https://api-inference.huggingface.co/models/{model_name}"
                headers = {
                    "Authorization": f"Bearer {HUGGINGFACE_TOKEN}"
                }

                response = requests.post(API_URL, headers=headers, data=audio_bytes, timeout=15)

                if response.status_code == 200:
                    result = response.json()
                    return result.get('text', 'No transcription available')
                
                elif response.status_code == 503:
                    st.warning(f"Whisper model {model_name} is loading, trying next...")
                    continue
                    
            except Exception as e:
                st.warning(f"Error with Whisper model {model_name}: {str(e)}")
                continue
        
        return "Error: All audio transcription models failed"

    except Exception as e:
        return f"Error transcribing audio: {str(e)}"

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
    conn = sqlite3.connect('user4_database.db')
    cursor = conn.cursor()

    try:
        # Get user's department
        cursor.execute("SELECT department FROM users WHERE username = ?", (username,))
        user_result = cursor.fetchone()
        
        if not user_result:
            conn.close()
            return 0, None
            
        department = user_result[0]

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
    # Initialize session state and database
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'department' not in st.session_state:
        st.session_state['department'] = None

    init_database()

    st.title("Multimodal Alert System")
    
    # Show installation instructions if transformers is not available
    if not TRANSFORMERS_AVAILABLE:
        st.warning("""
        **For better image processing, please install the transformers library:**
        ```bash
        pip install transformers torch torchvision
        ```
        This will enable local image captioning without relying on external APIs.
        """)

    # Login section
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
                    st.image(image, caption="Uploaded Image", use_container_width=True)
                    
                    alert_description = img2txt(
                        speech_text, 
                        image,
                        audio_data,
                        additional_context
                    )
                    st.write("Alert Description:", alert_description)
                    
                    if audio_data:
                        st.audio(audio_data)
                elif speech_text or additional_context:
                    # Handle case where only text/audio is provided without image
                    description = f"{speech_text} {additional_context}".strip()
                    if description:
                        # Determine department based on text content
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
                            if keyword in description.lower():
                                department_match = (dept, pri)
                                break
                        
                        create_alert(department_match[0], department_match[1], description, None, audio_data)
                        st.write("Alert created based on text/audio input")

        with tab2:
            st.subheader("Department Alerts")
            
            col1, col2 = st.columns(2)
            
            with col1:
                retrieve_button = st.button("Retrieve Alerts", key="retrieve_alerts")
            
            with col2:
                clear_confirmation = st.checkbox("Confirm Alert Deletion", key="clear_confirm")
                if clear_confirmation:
                    if st.button("Clear All Department Alerts", type="primary", key="clear_alerts"):
                        rows_deleted, department = clear_department_alerts(st.session_state.username)
                        if rows_deleted > 0:
                            st.success(f"Successfully cleared {rows_deleted} alerts for {department}.")
                        else:
                            st.info(f"No alerts to clear for {department}.")
                        st.rerun()

            if retrieve_button:
                alerts_text, formatted_alerts = check_alerts(st.session_state.username)
                
                if not formatted_alerts:
                    st.info("No alerts found for your department.")
                else:
                    for alert in formatted_alerts:
                        st.markdown(f"### Alert {alert['id']} - {alert['timestamp']}")
                        st.write(alert['description'])
                        
                        if alert['image_data']:
                            try:
                                image = Image.open(io.BytesIO(alert['image_data']))
                                st.image(image, caption=f"Alert {alert['id']} Image", use_container_width=True)
                            except Exception as e:
                                st.error(f"Error displaying image: {e}")
                        
                        if alert['audio_data']:
                            try:
                                st.audio(alert['audio_data'])
                            except Exception as e:
                                st.error(f"Error playing audio: {e}")
                        
                        st.markdown("---")

# Run the app
if __name__ == "__main__":
    main()
