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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create media directory
MEDIA_DIR = "media"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Alert history for priority determination
ALERT_HISTORY_FILE = "alert_history.json"

# Custom CSS for premium styling with forced dark theme
def inject_custom_css():
    st.markdown("""
        <style>
        /* Force dark theme and override all theme variables */
        :root {
            --primary-color: #ffffff !important;
            --background-color: #0e1117 !important;
            --secondary-background-color: #1a1d24 !important;
            --text-color: #ffffff !important;
            --font: "Source Sans Pro", sans-serif !important;
        }
        
        /* Completely override Streamlit's theme system */
        .stApp {
            background: #0e1117 !important;
            color: #ffffff !important;
        }
        
        /* Force all text elements to use white color */
        .main-header, .sub-header, h1, h2, h3, h4, h5, h6, p, div, span, label, li, ul, ol, td, th, tr, thead, tbody {
            color: #ffffff !important;
        }
        
        /* Fix Streamlit component text colors with !important */
        .stTextInput label, .stTextArea label, .stSelectbox label, .stFileUploader label,
        .stNumberInput label, .stDateInput label, .stTimeInput label, .stMultiSelect label {
            color: #ffffff !important;
        }
        
        /* Form inputs with dark background and white text */
        .stTextInput input, .stTextArea textarea, .stSelectbox select,
        .stNumberInput input, .stDateInput input, .stTimeInput input {
            background: #1a1d24 !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
        }
        
        .stTextInput input:focus, .stTextArea textarea:focus, .stSelectbox select:focus,
        .stNumberInput input:focus, .stDateInput input:focus, .stTimeInput input:focus {
            border-color: #667eea !important;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1) !important;
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
            color: white !important;
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
        
        /* Button styling - FIXED ALL BUTTONS */
        .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 2rem !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
        }
        
        /* Form submit buttons */
        .stFormSubmitButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem 2rem !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            width: 100% !important;
        }
        
        .stFormSubmitButton button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
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
        
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
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
        
        /* Sidebar button styling */
        [data-testid="stSidebar"] .stButton button {
            background: rgba(255,255,255,0.1) !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            padding: 0.75rem 1rem !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            text-align: left !important;
            width: 100% !important;
            margin: 0.25rem 0 !important;
        }
        
        [data-testid="stSidebar"] .stButton button:hover {
            background: rgba(255,255,255,0.2) !important;
            border-color: rgba(255,255,255,0.3) !important;
            transform: translateY(-1px) !important;
        }
        
        /* File uploader styling - COMPLETELY FIXED */
        .stFileUploader {
            border: 2px dashed #555 !important;
            border-radius: 12px !important;
            padding: 2rem !important;
            text-align: center !important;
            transition: border-color 0.3s ease !important;
            background: #1a1d24 !important;
        }
        
        .stFileUploader:hover {
            border-color: #667eea !important;
        }
        
        /* Fix file uploader text color - COMPREHENSIVE FIX */
        .stFileUploader section {
            background: #1a1d24 !important;
            border: none !important;
        }
        
        .stFileUploader section div {
            color: #ffffff !important;
        }
        
        .stFileUploader section p {
            color: #ffffff !important;
        }
        
        .stFileUploader section span {
            color: #ffffff !important;
        }
        
        .stFileUploader section small {
            color: #cccccc !important;
        }
        
        /* Fix the drag and drop text specifically */
        .stFileUploader section div[data-testid="stFileUploader"] {
            color: #ffffff !important;
        }
        
        /* Fix the browse files button */
        .stFileUploader section button {
            background: #667eea !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
        }
        
        .stFileUploader section button:hover {
            background: #764ba2 !important;
        }
        
        /* Fix the uploaded file name text */
        .stFileUploader section a {
            color: #ffffff !important;
        }
        
        /* Success/Error messages */
        .stAlert {
            border-radius: 8px;
            padding: 1rem;
            background: #1a1d24 !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
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
        
        /* Mic button styling */
        .mic-button {
            background: #dc2626;
            color: white !important;
            border: none;
            border-radius: 50%;
            width: 80px;
            height: 80px;
            font-size: 2rem;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
        }
        
        .mic-button:hover {
            background: #b91c1c;
            transform: scale(1.1);
        }
        
        .mic-button.recording {
            background: #ef4444;
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        /* Role-specific styling */
        .employee-view {
            border: 2px solid #667eea;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            background: rgba(102, 126, 234, 0.1);
        }
        
        .department-head-view {
            border: 2px solid #10b981;
            border-radius: 12px;
            padding: 1rem;
            margin: 1rem 0;
            background: rgba(16, 185, 129, 0.1);
        }
        
        .role-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            margin-left: 0.5rem;
        }
        
        .badge-employee {
            background: #667eea;
            color: white;
        }
        
        .badge-department-head {
            background: #10b981;
            color: white;
        }
        
        .badge-admin {
            background: #f59e0b;
            color: white;
        }
        
        /* Fix dataframe and table colors */
        .dataframe {
            background: #1a1d24 !important;
            color: #ffffff !important;
        }
        
        .dataframe th {
            background: #2d3748 !important;
            color: #ffffff !important;
        }
        
        .dataframe td {
            background: #1a1d24 !important;
            color: #ffffff !important;
            border-color: #444 !important;
        }
        
        /* Fix expander colors */
        .streamlit-expanderHeader {
            background: #1a1d24 !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
        }
        
        .streamlit-expanderContent {
            background: #1a1d24 !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
        }
        
        /* Fix checkbox colors */
        .stCheckbox label {
            color: #ffffff !important;
        }
        
        /* Fix radio button colors */
        .stRadio label {
            color: #ffffff !important;
        }
        
        /* Fix tab colors */
        .stTabs [data-baseweb="tab-list"] {
            background: #1a1d24 !important;
            gap: 2px;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: #2d3748 !important;
            color: #ffffff !important;
            border-radius: 4px 4px 0 0;
        }
        
        .stTabs [aria-selected="true"] {
            background: #667eea !important;
        }
        
        /* Additional overrides for complete theme control */
        .st-bb {
            background-color: #1a1d24 !important;
        }
        
        .st-at {
            background-color: #1a1d24 !important;
        }
        
        .st-bh, .st-bi, .st-bj, .st-bk, .st-bl, .st-bm, .st-bn, .st-bo, .st-bp, .st-bq, .st-br, .st-bs, .st-bt, .st-bu, .st-bv, .st-bw, .st-bx, .st-by, .st-bz {
            color: #ffffff !important;
        }
        
        /* Specific fix for file uploader dropzone text */
        div[data-testid="stFileUploader"] > div > section > div > div > div > span {
            color: #ffffff !important;
        }
        
        /* Fix the "Drag and drop file here" text */
        div[data-testid="stFileUploader"] > div > section > div > div > div {
            color: #ffffff !important;
        }
        
        /* Fix the file size limit text */
        div[data-testid="stFileUploader"] > div > section > div > div > small {
            color: #cccccc !important;
        }
        
        /* Fix sidebar collapse button */
        [data-testid="collapsedControl"] {
            color: #ffffff !important;
            background: #1a1d24 !important;
            border: 1px solid #444 !important;
        }
        
        [data-testid="collapsedControl"]:hover {
            background: #2d3748 !important;
        }
        
        /* Fix login form submit button */
        .stForm {
            border: none !important;
        }
        
        .stForm .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.75rem 2rem !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 1rem !important;
            width: 100% !important;
            margin-top: 1rem !important;
        }
        
        .stForm .stButton button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
        }
        
        /* Fix all other buttons in main content */
        div[data-testid="stVerticalBlock"] .stButton button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1.5rem !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
        }
        
        div[data-testid="stVerticalBlock"] .stButton button:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
        }
        
        /* Fix resolve buttons in alert cards */
        .alert-card .stButton button {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: white !important;
            border: none !important;
            padding: 0.5rem 1rem !important;
            border-radius: 6px !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
        }
        
        .alert-card .stButton button:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
            transform: translateY(-1px) !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4) !important;
        }
        
        /* Fix the sign out button */
        [data-testid="stSidebar"] .stButton button[kind="secondary"] {
            background: rgba(239, 68, 68, 0.8) !important;
            color: white !important;
            border: 1px solid rgba(239, 68, 68, 0.5) !important;
        }
        
        [data-testid="stSidebar"] .stButton button[kind="secondary"]:hover {
            background: rgba(239, 68, 68, 1) !important;
            border-color: rgba(239, 68, 68, 0.8) !important;
        }
        </style>
    """, unsafe_allow_html=True)

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
        ('admin', 'admin123', 'All', 'admin'),
        ('employee1', 'emp123', 'Fire', 'employee'),
        ('employee2', 'emp123', 'Health Care', 'employee'),
        ('employee3', 'emp123', 'Equipment Damage', 'employee'),
        ('employee4', 'emp123', 'Missing Items', 'employee')
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

def save_audio_file(audio_bytes: bytes) -> str:
    """Save audio bytes to file"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audio_{timestamp}.wav"
    filepath = os.path.join(MEDIA_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(audio_bytes)
    
    return filepath

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

def get_resolved_alerts(department: str, role: str) -> List[Dict]:
    conn = sqlite3.connect('emergency_alerts.db')
    c = conn.cursor()
    
    if role == 'admin':
        c.execute('''
            SELECT * FROM alerts 
            WHERE status = 'resolved' 
            ORDER BY resolved_at DESC
            LIMIT 50
        ''')
    else:
        c.execute('''
            SELECT * FROM alerts 
            WHERE department = ? AND status = 'resolved' 
            ORDER BY resolved_at DESC
            LIMIT 50
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

def display_audio_player(audio_path: str):
    """Display audio player for audio files"""
    st.markdown("**🎤 Audio Evidence:**")
    try:
        with open(audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
        
        # Display audio player
        st.audio(audio_bytes, format="audio/wav")
        
        # Show file info
        file_size = len(audio_bytes) / (1024 * 1024)  # Convert to MB
        file_name = os.path.basename(audio_path)
        st.caption(f"Audio file: `{file_name}` ({file_size:.2f} MB)")
        
    except Exception as e:
        st.error(f"Error loading audio: {e}")
        # Debug information
        st.write(f"Audio path: {audio_path}")
        st.write(f"File exists: {os.path.exists(audio_path)}")

def display_media(alert: Dict):
    """Display media evidence for an alert"""
    if alert.get('media_path'):
        # Split media paths by comma and handle each one
        media_files = alert['media_path'].split(',')
        
        # Debug information (can be commented out in production)
        # st.write(f"Media files found: {media_files}")
        
        # Create columns for better layout when both types exist
        has_photo = any('image:' in media_file for media_file in media_files)
        has_audio = any('audio:' in media_file for media_file in media_files)
        
        if has_photo and has_audio:
            col1, col2 = st.columns(2)
        else:
            # Use a single column layout
            col1 = st.container()
            col2 = None
        
        for media_file in media_files:
            # Clean the path by removing the type prefix
            if media_file.startswith('image:'):
                image_path = media_file.replace('image:', '')
                if os.path.exists(image_path):
                    if has_photo and has_audio:
                        with col1:
                            st.markdown("**📷 Photo Evidence:**")
                            try:
                                image = Image.open(image_path)
                                st.image(image, caption="Incident Photo", use_column_width=True)
                            except Exception as e:
                                st.error(f"Error loading image: {e}")
                    else:
                        st.markdown("**📷 Photo Evidence:**")
                        try:
                            image = Image.open(image_path)
                            st.image(image, caption="Incident Photo", use_column_width=True)
                        except Exception as e:
                            st.error(f"Error loading image: {e}")
                else:
                    st.warning(f"Photo file not found: {image_path}")
            
            elif media_file.startswith('audio:'):
                audio_path = media_file.replace('audio:', '')
                if os.path.exists(audio_path):
                    if has_photo and has_audio:
                        with col2:
                            display_audio_player(audio_path)
                    else:
                        display_audio_player(audio_path)
                else:
                    st.warning(f"Audio file not found: {audio_path}")
            
            # Handle case where media path doesn't have prefix (backward compatibility)
            elif os.path.exists(media_file):
                # Try to determine file type by extension
                if media_file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    st.markdown("**📷 Photo Evidence:**")
                    try:
                        image = Image.open(media_file)
                        st.image(image, caption="Incident Photo", use_column_width=True)
                    except Exception as e:
                        st.error(f"Error loading image: {e}")
                elif media_file.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg')):
                    display_audio_player(media_file)
                else:
                    st.warning(f"Unknown file type: {media_file}")

# HTML for audio recording
def audio_recorder_html():
    return """
    <div style="text-align: center; padding: 20px;">
        <button class="mic-button" id="startRecord">🎤</button>
        <div style="margin: 10px 0; color: white;" id="status">Click mic to start recording</div>
        <audio id="audioPlayback" controls style="margin: 10px 0; display: none;"></audio>
        <div id="timer" style="color: white; font-size: 1.2rem; margin: 10px 0;">00:00</div>
    </div>

    <script>
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let startTime;
    let timerInterval;

    const startRecordButton = document.getElementById('startRecord');
    const statusDiv = document.getElementById('status');
    const audioPlayback = document.getElementById('audioPlayback');
    const timerDiv = document.getElementById('timer');

    function updateTimer() {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const seconds = (elapsed % 60).toString().padStart(2, '0');
        timerDiv.textContent = `${minutes}:${seconds}`;
    }

    startRecordButton.addEventListener('click', async () => {
        if (!isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    audioPlayback.src = audioUrl;
                    audioPlayback.style.display = 'block';

                    // Convert blob to base64 for Streamlit
                    const reader = new FileReader();
                    reader.readAsDataURL(audioBlob);
                    reader.onloadend = () => {
                        const base64data = reader.result;
                        // Send to Streamlit
                        window.parent.postMessage({
                            type: 'audioRecorded',
                            audioData: base64data
                        }, '*');
                    };
                };

                mediaRecorder.start();
                isRecording = true;
                startRecordButton.classList.add('recording');
                startRecordButton.innerHTML = '⏹️';
                statusDiv.textContent = 'Recording... Click to stop';
                
                // Start timer
                startTime = Date.now();
                timerInterval = setInterval(updateTimer, 1000);

            } catch (err) {
                statusDiv.textContent = 'Error: Cannot access microphone';
                console.error('Error accessing microphone:', err);
            }
        } else {
            // Stop recording
            mediaRecorder.stop();
            isRecording = false;
            startRecordButton.classList.remove('recording');
            startRecordButton.innerHTML = '🎤';
            statusDiv.textContent = 'Recording complete';
            
            // Stop timer
            clearInterval(timerInterval);
            
            // Stop all tracks
            mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
    });
    </script>
    """

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
    if 'recorded_audio_path' not in st.session_state:
        st.session_state.recorded_audio_path = None
    if 'audio_recorded' not in st.session_state:
        st.session_state.audio_recorded = False
    if 'audio_data' not in st.session_state:
        st.session_state.audio_data = None
    
    # Handle audio recording messages from JavaScript
    if st.session_state.get('audio_recorded') and st.session_state.get('audio_data'):
        try:
            audio_data = st.session_state.audio_data
            # Convert base64 to bytes and save immediately
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
            media_path = save_audio_file(audio_bytes)
            st.session_state.recorded_audio_path = media_path
            st.session_state.audio_recorded = False
            st.rerun()
        except Exception as e:
            st.error(f"Error processing audio recording: {e}")
            logger.error(f"Audio processing error: {e}")
    
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
                submit = st.form_submit_button("🚪 Authenticate", use_container_width=True)
                
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
                **Department Heads**  
                `fire_head` / `fire123`  
                `health_head` / `health123`  
                `equipment_head` / `equipment123`  
                `missing_head` / `missing123`
                """)
            with cols[1]:
                st.info("""
                **Employees**  
                `employee1` / `emp123` (Fire)  
                `employee2` / `emp123` (Health)  
                `employee3` / `emp123` (Equipment)  
                `employee4` / `emp123` (Missing)
                
                **Administrator**  
                `admin` / `admin123`
                """)

def render_main_application():
    user_info = st.session_state.user_info
    
    with st.sidebar:
        st.markdown('<div class="sidebar-header">Emergency Response System</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="user-info">', unsafe_allow_html=True)
        st.markdown(f"**{user_info['username']}**")
        
        # Display role badge
        role_badge_class = f"badge-{user_info['role'].replace('_', '-')}"
        role_display = user_info['role'].replace('_', ' ').title()
        st.markdown(f'<span class="role-badge {role_badge_class}">{role_display}</span>', unsafe_allow_html=True)
        
        st.markdown(f"*{user_info['department']} Department*")
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
    
    # Role-specific welcome message
    if user_info['role'] == 'employee':
        st.markdown('<div class="employee-view">', unsafe_allow_html=True)
        st.markdown("### 👤 Employee Dashboard")
        st.markdown("You can report incidents and view active alerts in your department.")
        st.markdown('</div>', unsafe_allow_html=True)
    elif user_info['role'] == 'department_head':
        st.markdown('<div class="department-head-view">', unsafe_allow_html=True)
        st.markdown("### 👨‍💼 Department Head Dashboard")
        st.markdown("You have authority to view, manage, and resolve incidents in your department.")
        st.markdown('</div>', unsafe_allow_html=True)
    elif user_info['role'] == 'admin':
        st.markdown("### 👑 Administrator Dashboard")
        st.markdown("You have full system access across all departments.")
    
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
            
            # Add expandable evidence section in dashboard too
            with st.expander("View Evidence"):
                display_media(alert)
        
        with col2:
            # Only show resolve button for department heads and admin
            if user_info['role'] in ['department_head', 'admin']:
                if st.button("✅ Resolve", key=f"resolve_{alert['id']}", use_container_width=True):
                    if resolve_alert(alert['id'], user_info['username']):
                        st.success("Incident resolved")
                        st.rerun()
            else:
                st.info("🔒 Department Head Only")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_report_emergency():
    st.markdown('<div class="main-header">Report Emergency</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Submit incident report with multimedia evidence</div>', unsafe_allow_html=True)
    
    user_info = st.session_state.user_info
    
    # Role-specific styling for report page
    if user_info['role'] == 'employee':
        st.markdown('<div class="employee-view">', unsafe_allow_html=True)
        st.markdown("### 👤 Employee Incident Reporting")
        st.markdown("As an employee, you can report incidents to any department based on the incident type.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="department-head-view">', unsafe_allow_html=True)
        st.markdown("### 👨‍💼 Department Head Incident Reporting")
        st.markdown("As a department head, you can report incidents to any relevant department.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Initialize session state for audio recording
    if 'audio_recorded' not in st.session_state:
        st.session_state.audio_recorded = False
    if 'recorded_audio_path' not in st.session_state:
        st.session_state.recorded_audio_path = None
    
    # Two-column layout for media upload
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Visual Evidence")
        uploaded_image = st.file_uploader("Upload incident photo", 
                                        type=['jpg', 'jpeg', 'png'],
                                        help="Upload clear photos of the incident scene")
    
    with col2:
        st.markdown("### Audio Evidence")
        
        # Audio recording section
        st.markdown("#### Record Live Audio")
        st.components.v1.html(audio_recorder_html(), height=300)
        
        # Handle recorded audio from JavaScript
        if st.session_state.get('audio_recorded'):
            audio_data = st.session_state.audio_data
            # Convert base64 to bytes and save immediately
            audio_bytes = base64.b64decode(audio_data.split(',')[1])
            media_path = save_audio_file(audio_bytes)
            st.session_state.recorded_audio_path = media_path
            st.session_state.audio_recorded = False
            st.success("Audio recording saved successfully!")
        
        # Display and manage recorded audio
        if st.session_state.get('recorded_audio_path'):
            st.markdown("#### Current Recording")
            with open(st.session_state.recorded_audio_path, 'rb') as audio_file:
                audio_bytes = audio_file.read()
            st.audio(audio_bytes, format="audio/wav")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Use This Recording", key="use_recording"):
                    st.success("Recording will be used in report")
            with col_b:
                if st.button("🗑️ Delete Recording", key="delete_recording"):
                    try:
                        os.remove(st.session_state.recorded_audio_path)
                        del st.session_state.recorded_audio_path
                        st.rerun()
                    except:
                        st.error("Error deleting recording")
        
        st.markdown("#### Or Upload Audio File")
        uploaded_audio = st.file_uploader("Upload audio file", 
                                        type=['wav', 'mp3', 'm4a'],
                                        help="Upload pre-recorded audio file")
    
    # Preview section
    if uploaded_image or st.session_state.get('recorded_audio_path') or uploaded_audio:
        st.markdown("### Evidence Preview")
        preview_col1, preview_col2 = st.columns(2)
        
        with preview_col1:
            if uploaded_image:
                image = Image.open(uploaded_image)
                st.image(image, caption="Incident Photo", use_column_width=True)
        
        with preview_col2:
            if st.session_state.get('recorded_audio_path'):
                with open(st.session_state.recorded_audio_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                st.audio(audio_bytes, format="audio/wav")
                st.markdown("*Live Recording Preview*")
            elif uploaded_audio:
                st.audio(uploaded_audio, format="audio/wav")
                st.markdown("*Uploaded Audio Preview*")
    
    # Incident Report Form
    st.markdown("### Incident Details")
    
    with st.form("emergency_alert_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Changed from "Incident Title" to "Incident Location"
            location = st.text_input("Incident Location*", 
                                   placeholder="Enter exact location of incident")
        
        with col2:
            # ALL users (employees and department heads) can select any department
            departments = ["Fire", "Health Care", "Equipment Damage", "Missing Items", "General"]
            
            # Show user's department as default but allow selection of any department
            user_department = user_info['department']
            default_index = departments.index(user_department) if user_department in departments else 0
            
            department = st.selectbox(
                "Responsible Department*",
                departments,
                index=default_index,
                help="Select the department responsible for handling this incident"
            )
        
        description = st.text_area("Incident Description*",
                                 placeholder="Provide detailed description of the incident including what happened, people involved, and immediate risks",
                                 height=100)
        
        submitted = st.form_submit_button("🚨 Submit Incident Report", use_container_width=True)
        
        if submitted:
            if location and department and description:
                has_media = uploaded_image or st.session_state.get('recorded_audio_path') or uploaded_audio
                if not has_media:
                    st.error("Please provide at least one piece of evidence (photo or audio)")
                else:
                    with st.spinner("Processing incident report..."):
                        # Determine media type
                        media_types = []
                        if uploaded_image:
                            media_types.append("photo")
                        if st.session_state.get('recorded_audio_path') or uploaded_audio:
                            media_types.append("audio")
                        
                        alert_type = " + ".join(media_types) if len(media_types) > 1 else media_types[0] if media_types else "media"
                        
                        # Save media files
                        media_paths = []
                        
                        if uploaded_image:
                            image_path = save_uploaded_file(uploaded_image, "image")
                            media_paths.append(f"image:{image_path}")
                        
                        # Priority: Use recorded audio first, then uploaded audio
                        if st.session_state.get('recorded_audio_path'):
                            media_paths.append(f"audio:{st.session_state.recorded_audio_path}")
                        elif uploaded_audio:
                            audio_path = save_uploaded_file(uploaded_audio, "audio")
                            media_paths.append(f"audio:{audio_path}")
                        
                        media_path = ",".join(media_paths) if media_paths else None
                        
                        alert_data = {
                            'title': f"Incident at {location}",  # Use location as title
                            'description': description,
                            'department': department,
                            'priority': "high",
                            'alert_type': alert_type,
                            'media_path': media_path,
                            'created_by': user_info['username']
                        }
                        
                        if create_alert(alert_data):
                            st.success("Incident report submitted successfully")
                            st.balloons()
                            # Clear recorded audio after successful submission
                            if 'recorded_audio_path' in st.session_state:
                                del st.session_state.recorded_audio_path
                            if 'audio_recorded' in st.session_state:
                                del st.session_state.audio_recorded
                            if 'audio_data' in st.session_state:
                                del st.session_state.audio_data
                        else:
                            st.error("Error submitting incident report")
            else:
                st.error("Please complete all required fields")

def render_view_alerts():
    st.markdown('<div class="main-header">Incident Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Manage and monitor emergency situations</div>', unsafe_allow_html=True)
    
    user_info = st.session_state.user_info
    
    # Role-specific header
    if user_info['role'] == 'employee':
        st.markdown('<div class="employee-view">', unsafe_allow_html=True)
        st.markdown("### 👤 Employee View - Active Incidents")
        st.markdown("You can view all active incidents in your department. Department heads will resolve them.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="department-head-view">', unsafe_allow_html=True)
        st.markdown("### 👨‍💼 Department Head View - Incident Management")
        st.markdown("You have authority to view and resolve incidents in your department.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Create tabs for Active and Resolved incidents
    tab1, tab2 = st.tabs(["🚨 Active Incidents", "📋 Resolved Cases"])
    
    with tab1:
        st.markdown("### Active Incidents")
        active_alerts = get_alerts(user_info['department'], user_info['role'])
        
        if not active_alerts:
            st.info("No active incidents in your department.")
        else:
            for alert in active_alerts:
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
                    
                    # Expandable media section
                    with st.expander("View Evidence Details"):
                        # Temporary debug info (can be removed in production)
                        if st.checkbox("Show debug info", key=f"debug_{alert['id']}"):
                            st.write(f"Media path: {alert.get('media_path')}")
                            st.write(f"Media files: {alert.get('media_path', '').split(',') if alert.get('media_path') else []}")
                        
                        display_media(alert)
                
                with col2:
                    # Only show resolve button for department heads and admin
                    if user_info['role'] in ['department_head', 'admin']:
                        if st.button("✅ Resolve Incident", key=f"resolve_{alert['id']}", use_container_width=True):
                            if resolve_alert(alert['id'], user_info['username']):
                                st.success("Incident resolved")
                                st.rerun()
                    else:
                        st.info("⏳ Pending Resolution")
                        st.caption("Department Head Action Required")
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown("### Previously Resolved Cases")
        resolved_alerts = get_resolved_alerts(user_info['department'], user_info['role'])
        
        if not resolved_alerts:
            st.info("No resolved incidents found.")
        else:
            # Add filter options for resolved cases
            col1, col2, col3 = st.columns(3)
            with col1:
                department_filter = st.selectbox(
                    "Filter by Department",
                    ["All"] + list(set([alert['department'] for alert in resolved_alerts])),
                    key="resolved_dept_filter"
                )
            with col2:
                priority_filter = st.selectbox(
                    "Filter by Priority",
                    ["All", "high", "medium", "low"],
                    key="resolved_priority_filter"
                )
            with col3:
                date_sort = st.selectbox(
                    "Sort by Date",
                    ["Newest First", "Oldest First"],
                    key="resolved_date_sort"
                )
            
            # Apply filters
            filtered_alerts = resolved_alerts
            
            if department_filter != "All":
                filtered_alerts = [alert for alert in filtered_alerts if alert['department'] == department_filter]
            
            if priority_filter != "All":
                filtered_alerts = [alert for alert in filtered_alerts if alert['priority'] == priority_filter]
            
            if date_sort == "Oldest First":
                filtered_alerts = sorted(filtered_alerts, key=lambda x: x['resolved_at'] or x['created_at'])
            else:
                filtered_alerts = sorted(filtered_alerts, key=lambda x: x['resolved_at'] or x['created_at'], reverse=True)
            
            for alert in filtered_alerts:
                priority_class = f"card-{alert['priority']}"
                priority_icons = {'high': '🔴 Critical', 'medium': '🟡 Urgent', 'low': '🟢 Routine'}
                
                st.markdown(f'<div class="alert-card {priority_class}">', unsafe_allow_html=True)
                
                st.markdown(f"#### {alert['title']}")
                st.markdown(f"**{priority_icons[alert['priority']]}** • **Department:** {alert['department']}")
                st.markdown(f"**Description:** {alert['description']}")
                st.markdown(f"**Evidence Type:** {alert['alert_type'].title()}")
                st.markdown(f"*Reported by {alert['created_by']} • {alert['created_at'][:16]}*")
                st.markdown(f"**Resolved by {alert['resolved_by']} • {alert['resolved_at'][:16] if alert['resolved_at'] else 'Unknown'}**")
                
                # Expandable media section for resolved cases too
                with st.expander("View Evidence Details"):
                    display_media(alert)
                
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
