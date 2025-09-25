import streamlit as st
import sqlite3
import os
import hashlib
import datetime
from PIL import Image
import io
import base64
import tempfile
from typing import Dict, List, Optional, Tuple
import logging
import json
import av
import numpy as np
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import queue
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create media directory
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Alert history for priority determination
ALERT_HISTORY_FILE = "alert_history.json"

# WebRTC configuration for voice recording
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

# Audio recording queue
audio_queue = queue.Queue()

# Custom CSS for premium styling with dark theme fix and mobile optimization
def inject_custom_css():
    st.markdown("""
        <style>
        /* Force dark theme and fix all text visibility */
        .stApp {
            background: #0e1117 !important;
            color: #ffffff !important;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .main-header {
                font-size: 2rem !important;
            }
            .sub-header {
                font-size: 1rem !important;
            }
            .metric-value {
                font-size: 1.8rem !important;
            }
            .stButton button {
                padding: 0.75rem 1rem !important;
                font-size: 1rem !important;
            }
        }
        
        /* Fix all text colors to be visible on dark background */
        .main-header, .sub-header, h1, h2, h3, h4, h5, h6, p, div, span, label {
            color: #ffffff !important;
        }
        
        /* Fix Streamlit component text colors */
        .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label {
            color: #ffffff !important;
            font-size: 1.1rem !important;
        }
        
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            background: #1a1d24 !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
            font-size: 1rem !important;
            padding: 1rem !important;
        }
        
        .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1) !important;
        }
        
        /* Mobile-friendly file uploader */
        .stFileUploader {
            min-height: 120px !important;
            padding: 1.5rem !important;
        }
        
        .stFileUploader section {
            padding: 1rem !important;
        }
        
        /* Voice recording button styling */
        .voice-recorder {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%) !important;
            border: none;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            color: white;
            font-size: 2rem;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 1rem auto;
        }
        
        .voice-recorder:hover {
            transform: scale(1.1);
            box-shadow: 0 0 20px rgba(255, 107, 107, 0.5);
        }
        
        .voice-recorder.recording {
            background: linear-gradient(135deg, #ff3838 0%, #c23616 100%) !important;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        /* Main styling */
        .main-header {
            font-size: 2.5rem;
            font-weight: 300;
            color: #ffffff !important;
            margin-bottom: 0.5rem;
        }
        
        .sub-header {
            font-size: 1.1rem;
            color: #cccccc !important;
            font-weight: 300;
            margin-bottom: 2rem;
        }
        
        /* Card styling */
        .alert-card {
            background: #1a1d24;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1rem 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.3);
            border-left: 4px solid;
            transition: transform 0.2s ease;
            color: #ffffff !important;
        }
        
        .alert-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        }
        
        .card-high { border-left-color: #dc2626; }
        .card-medium { border-left-color: #f59e0b; }
        .card-low { border-left-color: #10b981; }
        
        /* Metric cards */
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 1.5rem;
            color: white;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2.5rem;
            font-weight: 300;
            margin: 0.5rem 0;
            color: white !important;
        }
        
        .metric-label {
            font-size: 0.9rem;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: white !important;
        }
        
        /* Button styling */
        .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.5rem 2rem;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
            font-size: 1rem;
        }
        
        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        /* Form styling */
        .stTextInput input, .stTextArea textarea, .stSelectbox select {
            border: 1px solid #444;
            border-radius: 8px;
            padding: 0.75rem;
            font-size: 0.95rem;
            background: #1a1d24 !important;
            color: #ffffff !important;
        }
        
        .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
        }
        
        /* Sidebar styling - Force dark background */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1d24 0%, #2d3748 100%) !important;
        }
        
        .sidebar-header {
            color: #ffffff !important;
            font-size: 1.3rem;
            font-weight: 300;
            margin-bottom: 1rem;
        }
        
        .user-info {
            background: rgba(255,255,255,0.1);
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            color: #ffffff !important;
        }
        
        /* File uploader styling */
        .stFileUploader {
            border: 2px dashed #555;
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            transition: border-color 0.3s ease;
            background: #1a1d24;
        }
        
        .stFileUploader:hover {
            border-color: #667eea;
        }
        
        /* Fix file uploader text color */
        .stFileUploader section {
            color: #ffffff !important;
        }
        
        .stFileUploader section div {
            color: #ffffff !important;
        }
        
        /* Success/Error messages */
        .stAlert {
            border-radius: 8px;
            padding: 1rem;
            background: #1a1d24 !important;
        }
        
        /* Navigation */
        .nav-section {
            margin: 2rem 0;
        }
        
        .nav-item {
            padding: 0.75rem 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
            color: #ffffff !important;
            text-decoration: none;
            display: block;
            transition: background 0.3s ease;
        }
        
        .nav-item:hover {
            background: rgba(255,255,255,0.1);
        }
        
        /* Fix all text in info boxes */
        .stInfo, .stSuccess, .stError, .stWarning {
            background: #1a1d24 !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
        }
        
        /* Fix text in form labels and placeholders */
        .stTextInput input::placeholder {
            color: #888 !important;
        }
        
        .stTextArea textarea::placeholder {
            color: #888 !important;
        }
        
        /* Fix select box options */
        .stSelectbox option {
            background: #1a1d24 !important;
            color: #ffffff !important;
        }
        
        /* Ensure all text in the app is visible */
        * {
            color: #ffffff !important;
        }
        
        /* Specific fix for markdown text */
        .stMarkdown {
            color: #ffffff !important;
        }
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            color: #ffffff !important;
        }
        
        .stMarkdown p {
            color: #ffffff !important;
        }
        
        /* Mobile-specific optimizations */
        @media (max-width: 480px) {
            .stFileUploader {
                padding: 1rem !important;
                min-height: 100px !important;
            }
            .voice-recorder {
                width: 70px !important;
                height: 70px !important;
                font-size: 1.5rem !important;
            }
            .alert-card {
                padding: 1rem !important;
                margin: 0.5rem 0 !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

# Audio recording callback
def audio_callback(frame):
    audio_queue.put(frame.to_ndarray())
    return frame

# Save audio from queue to file
def save_audio_from_queue(filename, duration=10):
    frames = []
    start_time = datetime.datetime.now()
    
    while (datetime.datetime.now() - start_time).seconds < duration:
        try:
            frame = audio_queue.get(timeout=1)
            frames.append(frame)
        except queue.Empty:
            break
    
    if frames:
        # Convert frames to audio file (simplified - in production use proper audio processing)
        audio_path = os.path.join(MEDIA_DIR, filename)
        # For demo purposes, we'll create a simple WAV file
        # In production, you'd use proper audio processing libraries
        with open(audio_path, 'wb') as f:
            f.write(b"Audio recording placeholder - would be actual audio data in production")
        return audio_path
    return None

# Initialize database with migration support
def init_db():
    conn = sqlite3.connect('emergency_alerts.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            department TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Alerts table - simplified version
    c.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            department TEXT NOT NULL,
            priority TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            media_path TEXT,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            resolved_at TIMESTAMP,
            resolved_by TEXT
        )
    ''')
    
    # Insert default users
    default_users = [
        ('fire_head', 'fire123', 'Fire', 'department_head'),
        ('health_head', 'health123', 'Health Care', 'department_head'),
        ('equipment_head', 'equipment123', 'Equipment Damage', 'department_head'),
        ('missing_head', 'missing123', 'Missing Items', 'department_head'),
        ('admin', 'admin123', 'All', 'admin')
    ]
    
    for username, password, department, role in default_users:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        try:
            c.execute(
                'INSERT OR IGNORE INTO users (username, password_hash, department, role) VALUES (?, ?, ?, ?)',
                (username, password_hash, department, role)
            )
        except:
            pass
    
    conn.commit()
    conn.close()

# Hash password
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Authentication functions
def authenticate_user(username: str, password: str) -> Optional[Dict]:
    conn = sqlite3.connect('emergency_alerts.db')
    c = conn.cursor()
    
    password_hash = hash_password(password)
    c.execute(
        'SELECT username, department, role FROM users WHERE username = ? AND password_hash = ?',
        (username, password_hash)
    )
    
    result = c.fetchone()
    conn.close()
    
    if result:
        return {
            'username': result[0],
            'department': result[1],
            'role': result[2]
        }
    return None

# Media handling functions
def save_uploaded_file(uploaded_file, file_type: str) -> str:
    """Save uploaded file and return path"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = uploaded_file.name.split('.')[-1]
    filename = f"{file_type}_{timestamp}.{file_extension}"
    filepath = os.path.join(MEDIA_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

# Simple audio transcription using text input as fallback
def transcribe_audio(audio_file) -> Dict:
    """Simple audio transcription - returns text input as fallback"""
    try:
        return {
            'transcription': 'Emergency audio recording - details would be transcribed here',
            'success': True
        }
    except Exception as e:
        return {
            'transcription': f'Error processing audio: {str(e)}',
            'success': False
        }

# Load alert history for priority determination
def load_alert_history() -> List[Dict]:
    """Load previous alerts to help with priority determination"""
    try:
        if os.path.exists(ALERT_HISTORY_FILE):
            with open(ALERT_HISTORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_alert_history(history: List[Dict]):
    """Save alert history"""
    try:
        with open(ALERT_HISTORY_FILE, 'w') as f:
            json.dump(history[-100:], f)
    except Exception as e:
        logger.error(f"Error saving alert history: {e}")

# Database operations for alerts
def create_alert(alert_data: Dict) -> bool:
    try:
        conn = sqlite3.connect('emergency_alerts.db')
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO alerts 
            (title, description, department, priority, alert_type, media_path, created_by, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert_data['title'],
            alert_data['description'],
            alert_data['department'],
            alert_data['priority'],
            alert_data['alert_type'],
            alert_data.get('media_path'),
            alert_data['created_by'],
            'active'
        ))
        
        history = load_alert_history()
        history.append({
            'title': alert_data['title'],
            'department': alert_data['department'],
            'priority': alert_data['priority'],
            'timestamp': datetime.datetime.now().isoformat()
        })
        save_alert_history(history)
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        return False

def get_alerts(department: str, role: str) -> List[Dict]:
    conn = sqlite3.connect('emergency_alerts.db')
    c = conn.cursor()
    
    if role == 'admin':
        c.execute('''
            SELECT * FROM alerts 
            WHERE status = 'active' 
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at DESC
        ''')
    else:
        c.execute('''
            SELECT * FROM alerts 
            WHERE department = ? AND status = 'active' 
            ORDER BY 
                CASE priority 
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                END,
                created_at DESC
        ''', (department,))
    
    alerts = []
    for row in c.fetchall():
        alerts.append({
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'department': row[3],
            'priority': row[4],
            'alert_type': row[5],
            'media_path': row[6],
            'created_by': row[7],
            'created_at': row[8],
            'status': row[9],
            'resolved_at': row[10],
            'resolved_by': row[11]
        })
    
    conn.close()
    return alerts

def resolve_alert(alert_id: int, resolved_by: str) -> bool:
    try:
        conn = sqlite3.connect('emergency_alerts.db')
        c = conn.cursor()
        
        c.execute('''
            UPDATE alerts 
            SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP, resolved_by = ?
            WHERE id = ?
        ''', (resolved_by, alert_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return False

# Streamlit application
def main():
    st.set_page_config(
        page_title="Emergency Alert System",
        page_icon="🚨",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    inject_custom_css()
    init_db()
    
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'login'
    if 'recording' not in st.session_state:
        st.session_state.recording = False
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None
    
    if not st.session_state.authenticated:
        render_login_page()
        return
    
    render_main_application()

def render_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="main-header">Emergency Response System</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Enterprise Incident Management Platform</div>', unsafe_allow_html=True)
        
        with st.container():
            st.markdown("### Secure Access")
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("Authenticate", use_container_width=True)
                
                if submit:
                    if username and password:
                        user_info = authenticate_user(username, password)
                        if user_info:
                            st.session_state.authenticated = True
                            st.session_state.user_info = user_info
                            st.session_state.current_page = 'dashboard'
                            st.rerun()
                        else:
                            st.error("Invalid credentials")
                    else:
                        st.error("Please enter both username and password")
            
            st.markdown("---")
            st.markdown("**Default Access Credentials**")
            cols = st.columns(2)
            with cols[0]:
                st.info("""
                **Fire Department**  
                `fire_head` / `fire123`
                
                **Health Care**  
                `health_head` / `health123`
                """)
            with cols[1]:
                st.info("""
                **Equipment Damage**  
                `equipment_head` / `equipment123`
                
                **Missing Items**  
                `missing_head` / `missing123`
                """)
            st.info("**Administrator:** `admin` / `admin123`")

def render_main_application():
    user_info = st.session_state.user_info
    
    with st.sidebar:
        st.markdown('<div class="sidebar-header">Emergency Response System</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="user-info">', unsafe_allow_html=True)
        st.markdown(f"**{user_info['username']}**")
        st.markdown(f"*{user_info['department']} Department*")
        st.markdown(f"Role: {user_info['role'].title()}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="nav-section">', unsafe_allow_html=True)
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.current_page = 'dashboard'
        if st.button("🚨 Report Incident", use_container_width=True):
            st.session_state.current_page = 'report_emergency'
        if st.button("📋 Active Alerts", use_container_width=True):
            st.session_state.current_page = 'view_alerts'
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.rerun()
    
    if st.session_state.current_page == 'dashboard':
        render_dashboard()
    elif st.session_state.current_page == 'report_emergency':
        render_report_emergency()
    elif st.session_state.current_page == 'view_alerts':
        render_view_alerts()

def render_dashboard():
    st.markdown('<div class="main-header">Incident Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Real-time emergency monitoring and management</div>', unsafe_allow_html=True)
    
    user_info = st.session_state.user_info
    alerts = get_alerts(user_info['department'], user_info['role'])
    
    # Statistics Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Total Active</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{len(alerts)}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        high_priority = len([a for a in alerts if a['priority'] == 'high'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Critical</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{high_priority}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        medium_priority = len([a for a in alerts if a['priority'] == 'medium'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Urgent</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{medium_priority}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        low_priority = len([a for a in alerts if a['priority'] == 'low'])
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Routine</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{low_priority}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Active Alerts Section
    st.markdown("### Active Incidents")
    
    if not alerts:
        st.info("No active incidents reported.")
        return
    
    for alert in alerts:
        priority_class = f"card-{alert['priority']}"
        priority_icons = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
        
        st.markdown(f'<div class="alert-card {priority_class}">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"#### {priority_icons[alert['priority']]} {alert['title']}")
            st.markdown(f"**Description:** {alert['description']}")
            st.markdown(f"**Department:** {alert['department']} • **Type:** {alert['alert_type'].title()}")
            st.markdown(f"*Reported by {alert['created_by']} at {alert['created_at'][:16]}*")
        
        with col2:
            if st.button("Resolve", key=f"resolve_{alert['id']}", use_container_width=True):
                if resolve_alert(alert['id'], user_info['username']):
                    st.success("Incident resolved")
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_report_emergency():
    st.markdown('<div class="main-header">Report Emergency</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Submit incident report with multimedia evidence</div>', unsafe_allow_html=True)
    
    user_info = st.session_state.user_info
    
    # Two-column layout for media upload
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📸 Visual Evidence")
        st.markdown("**Upload incident photos from your device**")
        uploaded_image = st.file_uploader("Choose image file", 
                                        type=['jpg', 'jpeg', 'png'],
                                        help="Take or select photos from your camera roll",
                                        accept_multiple_files=False,
                                        key="image_upload")
        
        if uploaded_image:
            st.success(f"✅ Image ready: {uploaded_image.name}")
            image = Image.open(uploaded_image)
            st.image(image, caption="Uploaded Incident Photo", use_column_width=True)
    
    with col2:
        st.markdown("### 🎤 Audio Evidence")
        
        # Option 1: Upload existing audio file
        st.markdown("**Upload existing audio file**")
        uploaded_audio = st.file_uploader("Choose audio file", 
                                        type=['wav', 'mp3', 'm4a', 'ogg'],
                                        help="Select audio recording from your device",
                                        key="audio_upload")
        
        if uploaded_audio:
            st.success(f"✅ Audio ready: {uploaded_audio.name}")
            st.audio(uploaded_audio)
        
        st.markdown("---")
        st.markdown("**Or record live audio**")
        
        # Option 2: Live voice recording
        if not st.session_state.recording:
            if st.button("🎤 Start Live Recording", use_container_width=True):
                st.session_state.recording = True
                st.rerun()
        else:
            st.warning("🔴 Recording in progress...")
            st.info("Please allow microphone access when prompted")
            
            # Simple recording simulation (in production, use proper WebRTC)
            recording_duration = st.slider("Recording duration (seconds)", 5, 60, 10)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("⏹️ Stop & Save Recording", use_container_width=True):
                    # Simulate saving recording
                    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                    audio_filename = f"live_recording_{timestamp}.wav"
                    audio_path = os.path.join(MEDIA_DIR, audio_filename)
                    
                    # Create a placeholder audio file
                    with open(audio_path, 'wb') as f:
                        f.write(b"Live recording placeholder")
                    
                    st.session_state.audio_file = audio_path
                    st.session_state.recording = False
                    st.success(f"✅ Recording saved: {audio_filename}")
                    st.rerun()
            
            with col2:
                if st.button("❌ Cancel Recording", use_container_width=True):
                    st.session_state.recording = False
                    st.rerun()
        
        # Show saved recording
        if st.session_state.audio_file and os.path.exists(st.session_state.audio_file):
            st.markdown("**Saved recording:**")
            st.audio(st.session_state.audio_file)
            if st.button("🗑️ Remove Recording", key="remove_audio"):
                st.session_state.audio_file = None
                st.rerun()
    
    # Incident Report Form
    st.markdown("---")
    st.markdown("### Incident Details")
    
    with st.form("emergency_alert_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            title = st.text_input("Incident Title*", 
                                placeholder="Brief descriptive title")
        
        with col2:
            departments = ["Fire", "Health Care", "Equipment Damage", "Missing Items", "General"]
            selected_department = st.selectbox(
                "Responsible Department*",
                departments
            )
        
        submitted = st.form_submit_button("Submit Incident Report", use_container_width=True)
        
        if submitted:
            if title and selected_department:
                # Check if at least one media file is provided
                has_media = uploaded_image or uploaded_audio or st.session_state.audio_file
                
                if not has_media:
                    st.error("Please provide at least one piece of evidence (photo or audio)")
                else:
                    with st.spinner("Processing incident report..."):
                        # Determine alert type and description
                        media_types = []
                        if uploaded_image:
                            media_types.append("photo")
                        if uploaded_audio:
                            media_types.append("audio file")
                        if st.session_state.audio_file:
                            media_types.append("live recording")
                        
                        alert_type = " + ".join(media_types) if media_types else "multimedia"
                        description = f"Incident reported with {', '.join(media_types)} evidence"
                        
                        # Save media files and prepare media_path
                        media_paths = []
                        
                        if uploaded_image:
                            image_path = save_uploaded_file(uploaded_image, "image")
                            media_paths.append(f"image:{image_path}")
                        
                        if uploaded_audio:
                            audio_path = save_uploaded_file(uploaded_audio, "audio")
                            media_paths.append(f"audio:{audio_path}")
                        
                        if st.session_state.audio_file:
                            media_paths.append(f"live_audio:{st.session_state.audio_file}")
                        
                        media_path = ",".join(media_paths) if media_paths else None
                        
                        alert_data = {
                            'title': title,
                            'description': description,
                            'department': selected_department,
                            'priority': "high",
                            'alert_type': alert_type,
                            'media_path': media_path,
                            'created_by': user_info['username']
                        }
                        
                        if create_alert(alert_data):
                            st.success("Incident report submitted successfully")
                            st.balloons()
                            # Reset form state
                            st.session_state.audio_file = None
                            st.rerun()
                        else:
                            st.error("Error submitting incident report")
            else:
                st.error("Please complete all required fields")

def render_view_alerts():
    st.markdown('<div class="main-header">Active Incidents</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage and monitor current emergency situations</div>', unsafe_allow_html=True)
    
    user_info = st.session_state.user_info
    alerts = get_alerts(user_info['department'], user_info['role'])
    
    if not alerts:
        st.info("No active incidents in your department.")
        return
    
    for alert in alerts:
        priority_class = f"card-{alert['priority']}"
        priority_icons = {'high': '🔴 Critical', 'medium': '🟡 Urgent', 'low': '🟢 Routine'}
        
        st.markdown(f'<div class="alert-card {priority_class}">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.markdown(f"#### {alert['title']}")
            st.markdown(f"**{priority_icons[alert['priority']]}** • **Department:** {alert['department']}")
            st.markdown(f"**Description:** {alert['description']}")
            st.markdown(f"**Evidence Type:** {alert['alert_type'].title()}")
            st.markdown(f"*Reported by {alert['created_by']} • {alert['created_at'][:16]}*")
            
            if alert['media_path']:
                media_files = alert['media_path'].split(',')
                for media_file in media_files:
                    if media_file.startswith('image:'):
                        image_path = media_file.replace('image:', '')
                        if os.path.exists(image_path):
                            try:
                                image = Image.open(image_path)
                                st.image(image, caption="Attached Photo", width=300)
                            except:
                                st.markdown("📷 **Photo evidence available**")
                    elif media_file.startswith('audio:') or media_file.startswith('live_audio:'):
                        audio_path = media_file.split(':')[1]
                        if os.path.exists(audio_path):
                            st.audio(audio_path, format="audio/wav")
                            st.markdown("🎤 **Audio recording available**")
        
        with col2:
            if st.button("Resolve Incident", key=f"resolve_{alert['id']}", use_container_width=True):
                if resolve_alert(alert['id'], user_info['username']):
                    st.success("Incident resolved")
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
