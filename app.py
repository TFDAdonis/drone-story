import streamlit as st
import folium
from streamlit_folium import st_folium
import base64
from datetime import datetime
import os
import json
import uuid
import pandas as pd
from PIL import Image
import io
import shutil

st.set_page_config(
    page_title="GeoCollect - Drone Media Manager",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
DATA_DIR = "geo_collect_data"
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
MEDIA_DIR = "media"
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")

# Initialize session state
session_defaults = {
    'media_items': [],
    'viewing_story': False,
    'story_index': 0,
    'map_center': [0, 0],
    'zoom_level': 2,
    'projects': {},
    'active_project': None,
    'organizations': {},
    'active_organization': None,
    'selected_marker': None
}

for key, default_value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

def init_data_directories():
    """Initialize data directories"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)
    
    # Load existing data
    load_saved_data()

def load_saved_data():
    """Load saved data from disk"""
    # Load metadata
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                data = json.load(f)
                st.session_state.media_items = data.get('media_items', [])
                st.session_state.projects = data.get('projects', {})
                st.session_state.organizations = data.get('organizations', {})
        except:
            pass
    
    # Ensure default organization exists
    if not st.session_state.organizations:
        st.session_state.organizations = {
            "default": {
                "name": "Default Organization",
                "description": "Main organization for drone media collection",
                "created": datetime.now().isoformat(),
                "projects": []
            }
        }
        st.session_state.active_organization = "default"
    
    # Ensure default project exists
    if not st.session_state.projects:
        st.session_state.projects = {
            "default": {
                "name": "Default Project",
                "description": "Main project for drone media",
                "organization": "default",
                "created": datetime.now().isoformat(),
                "media_items": []
            }
        }
        st.session_state.active_project = "default"
    
    save_all_data()

def save_all_data():
    """Save all data to disk"""
    data = {
        'media_items': st.session_state.media_items,
        'projects': st.session_state.projects,
        'organizations': st.session_state.organizations,
        'last_updated': datetime.now().isoformat()
    }
    
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return its path"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    safe_name = "".join(c for c in uploaded_file.name if c.isalnum() or c in (' ', '.', '_', '-')).rstrip()
    filename = f"{timestamp}_{unique_id}_{safe_name}"
    filepath = os.path.join(MEDIA_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath, filename

def get_media_type(filename):
    """Determine if file is image or video"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv']
    
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in image_extensions:
        return 'image'
    elif ext in video_extensions:
        return 'video'
    return None

def create_thumbnail(image_path, size=(100, 100)):
    """Create thumbnail for image"""
    try:
        img = Image.open(image_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        buffered = io.BytesIO()
        
        # Preserve transparency for PNG
        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
            img.save(buffered, format="PNG")
        else:
            img.save(buffered, format="JPEG")
            
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        return None

def get_video_preview(video_path):
    """Get video preview (first frame if possible, otherwise placeholder)"""
    return None  # Could implement with moviepy or similar

def create_collect_earth_style_map():
    """Create a Collect Earth Online style map"""
    items = [item for item in st.session_state.media_items 
             if item.get('project') == st.session_state.active_project]
    
    # Set initial view
    if items:
        avg_lat = sum(item['lat'] for item in items) / len(items)
        avg_lon = sum(item['lon'] for item in items) / len(items)
        center = [avg_lat, avg_lon]
        zoom = 10
    else:
        center = [0, 0]
        zoom = 2
    
    # Create base map
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,
        control_scale=True,
        zoom_control=True
    )
    
    # Add multiple tile layers like Collect Earth Online
    tile_layers = {
        'Google Satellite': folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
            attr='Google',
            name='Google Satellite',
            overlay=False,
            control=True
        ),
        'OpenStreetMap': folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='OpenStreetMap',
            name='OpenStreetMap',
            overlay=False,
            control=True
        ),
        'ESRI World Imagery': folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='ESRI',
            name='ESRI Imagery',
            overlay=False,
            control=True
        ),
        'CartoDB Dark': folium.TileLayer(
            tiles='CartoDB dark_matter',
            attr='CartoDB',
            name='Dark Mode',
            overlay=False,
            control=True
        )
    }
    
    # Add all tile layers
    for name, layer in tile_layers.items():
        layer.add_to(m)
    
    # Default to Google Satellite
    tile_layers['Google Satellite'].add_to(m)
    
    # Add markers with organization/project info
    for idx, item in enumerate(items):
        # Create marker icon based on media type
        if item['type'] == 'image':
            icon_color = 'green'
            icon_name = 'camera'
        else:
            icon_color = 'blue'
            icon_name = 'play'
        
        # Create custom icon
        icon = folium.Icon(
            color=icon_color,
            icon=icon_name,
            prefix='fa'
        )
        
        # Create popup content
        project_name = st.session_state.projects.get(item.get('project', 'default'), {}).get('name', 'Default Project')
        org_name = st.session_state.organizations.get(
            st.session_state.projects.get(item.get('project', 'default'), {}).get('organization', 'default'),
            {}
        ).get('name', 'Default Organization')
        
        popup_content = f"""
        <div style="font-family: Arial, sans-serif; width: 250px;">
            <div style="background: #f8f9fa; padding: 10px; border-radius: 8px 8px 0 0;">
                <strong style="color: #2c3e50;">{org_name}</strong><br>
                <small style="color: #7f8c8d;">Project: {project_name}</small>
            </div>
            <div style="padding: 10px;">
                <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <span style="font-size: 24px; margin-right: 10px;">
                        {'📷' if item['type'] == 'image' else '🎬'}
                    </span>
                    <div>
                        <strong>{item['name'][:20]}{'...' if len(item['name']) > 20 else ''}</strong><br>
                        <small>{item['timestamp']}</small>
                    </div>
                </div>
                <div style="background: #e8f4fd; padding: 8px; border-radius: 4px; margin: 8px 0;">
                    <strong>📍 Coordinates:</strong><br>
                    <code>Lat: {item['lat']:.6f}</code><br>
                    <code>Lon: {item['lon']:.6f}</code>
                </div>
                <button onclick="window.parent.document.getElementById('view-story-{item['id']}').click()"
                        style="background: #3498db; color: white; border: none; padding: 8px 16px; 
                               border-radius: 4px; cursor: pointer; width: 100%; margin-top: 8px;">
                    👁️ View Media
                </button>
            </div>
        </div>
        """
        
        iframe = folium.IFrame(popup_content, width=270, height=220)
        popup = folium.Popup(iframe, max_width=270)
        
        # Add marker to map
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=popup,
            tooltip=f"{project_name}: {item['name'][:15]}",
            icon=icon
        ).add_to(m)
        
        # Add hidden button for story viewing
        st.markdown(f"""
        <div id="view-story-{item['id']}" style="display: none;"></div>
        <script>
            document.getElementById('view-story-{item['id']}').onclick = function() {{
                window.parent.postMessage({{
                    type: 'view_story',
                    index: {idx}
                }}, '*');
            }};
        </script>
        """, unsafe_allow_html=True)
    
    # Add drawing tools like Collect Earth Online
    folium.plugins.Draw(
        export=True,
        position='topleft',
        draw_options={
            'polyline': False,
            'rectangle': True,
            'polygon': True,
            'circle': True,
            'marker': True,
            'circlemarker': False
        }
    ).add_to(m)
    
    # Add measure control
    folium.plugins.MeasureControl(
        position='topleft',
        primary_length_unit='meters',
        primary_area_unit='sqmeters'
    ).add_to(m)
    
    # Add fullscreen
    folium.plugins.Fullscreen().add_to(m)
    
    # Add mouse position
    folium.plugins.MousePosition().add_to(m)
    
    # Add layer control
    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    
    return m

def render_story_viewer():
    """Render the story viewer with Collect Earth style"""
    items = [item for item in st.session_state.media_items 
             if item.get('project') == st.session_state.active_project]
    
    if not items:
        st.error("No media items in current project")
        st.session_state.viewing_story = False
        return
    
    current_idx = st.session_state.story_index % len(items)
    current_item = items[current_idx]
    total_items = len(items)
    
    # Get project and org info
    project_name = st.session_state.projects.get(
        current_item.get('project', 'default'), 
        {}
    ).get('name', 'Default Project')
    
    org_name = st.session_state.organizations.get(
        st.session_state.projects.get(current_item.get('project', 'default'), {}).get('organization', 'default'),
        {}
    ).get('name', 'Default Organization')
    
    # Custom CSS for story viewer
    st.markdown("""
    <style>
        /* Story container */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        }
        
        .story-viewer-container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Header */
        .story-header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px 20px 0 0;
            padding: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .header-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .org-badge {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .project-badge {
            background: #2ecc71;
            color: white;
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .media-counter {
            text-align: right;
        }
        
        .counter-number {
            font-size: 32px;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Media container */
        .media-display-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            padding: 30px;
            min-height: 500px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0 0 20px 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        
        .media-content {
            max-width: 100%;
            max-height: 70vh;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }
        
        /* Info panel */
        .info-panel {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .coordinates-display {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
        }
        
        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .metadata-item {
            background: #f8f9fa;
            padding: 10px;
            border-radius: 8px;
        }
        
        /* Navigation */
        .nav-container {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .nav-button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .nav-button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
        }
        
        .nav-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .close-button {
            background: #e74c3c;
            color: white;
        }
        
        /* Progress bar */
        .progress-container {
            margin: 20px 0;
        }
        
        .progress-bar {
            height: 6px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: white;
            border-radius: 3px;
            transition: width 0.3s ease;
        }
        
        .progress-labels {
            display: flex;
            justify-content: space-between;
            margin-top: 5px;
            color: white;
            font-size: 12px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main container
    st.markdown(f"""
    <div class="story-viewer-container">
        <!-- Progress bar -->
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" style="width: {((current_idx + 1) / total_items) * 100}%"></div>
            </div>
            <div class="progress-labels">
                <span>Item {current_idx + 1} of {total_items}</span>
                <span>{int(((current_idx + 1) / total_items) * 100)}% complete</span>
            </div>
        </div>
        
        <!-- Header -->
        <div class="story-header">
            <div class="header-left">
                <div class="org-badge">🏢 {org_name}</div>
                <div class="project-badge">📋 {project_name}</div>
                <div>
                    <h3 style="margin: 0; color: #2c3e50;">{current_item['name']}</h3>
                    <p style="margin: 5px 0 0 0; color: #7f8c8d; font-size: 14px;">
                        🕒 {current_item['timestamp']} | 📍 Drone Media
                    </p>
                </div>
            </div>
            <div class="media-counter">
                <div class="counter-number">{current_idx + 1}/{total_items}</div>
                <p style="margin: 5px 0 0 0; color: #7f8c8d; font-size: 12px;">Story Viewer</p>
            </div>
        </div>
        
        <!-- Media display -->
        <div class="media-display-container">
    """, unsafe_allow_html=True)
    
    # Display media
    if os.path.exists(current_item['path']):
        if current_item['type'] == 'image':
            st.image(current_item['path'], use_container_width=True, output_format="auto")
        else:
            # For videos, display with controls
            video_bytes = open(current_item['path'], 'rb').read()
            st.video(video_bytes, format=f"video/{current_item['path'].split('.')[-1]}")
    else:
        st.error("⚠️ Media file not found")
        st.markdown(f"""
        <div style="text-align: center; padding: 40px;">
            <div style="font-size: 64px; margin-bottom: 20px;">📁</div>
            <h3>Media File Not Found</h3>
            <p>The media file appears to have been moved or deleted.</p>
            <p><strong>Original path:</strong> {current_item['path']}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("""
        </div>
        
        <!-- Information panel -->
        <div class="info-panel">
            <h4 style="color: #2c3e50; margin-bottom: 15px;">📊 Media Information</h4>
            
            <div class="coordinates-display">
                <strong>📍 GPS Coordinates:</strong><br>
                <div style="display: flex; justify-content: space-between; margin-top: 5px;">
                    <div>
                        <small>Latitude</small><br>
                        <strong>{:.6f}</strong>
                    </div>
                    <div>
                        <small>Longitude</small><br>
                        <strong>{:.6f}</strong>
                    </div>
                </div>
            </div>
            
            <div class="metadata-grid">
                <div class="metadata-item">
                    <small>Media Type</small><br>
                    <strong>{}</strong>
                </div>
                <div class="metadata-item">
                    <small>File Size</small><br>
                    <strong>{}</strong>
                </div>
                <div class="metadata-item">
                    <small>Uploaded</small><br>
                    <strong>{}</strong>
                </div>
            </div>
        </div>
        
        <!-- Navigation buttons -->
        <div class="nav-container">
    """.format(
        current_item['lat'],
        current_item['lon'],
        '📷 Image' if current_item['type'] == 'image' else '🎬 Video',
        f"{os.path.getsize(current_item['path']) / (1024*1024):.2f} MB" if os.path.exists(current_item['path']) else 'Unknown',
        current_item['timestamp']
    ), unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⏮️ Previous", use_container_width=True, disabled=current_idx == 0):
            st.session_state.story_index = (current_idx - 1) % len(items)
            st.rerun()
    
    with col2:
        if st.button("⏭️ Next", use_container_width=True, disabled=current_idx == len(items) - 1):
            st.session_state.story_index = (current_idx + 1) % len(items)
            st.rerun()
    
    with col3:
        if st.button("🗺️ Back to Map", use_container_width=True):
            st.session_state.viewing_story = False
            st.rerun()
    
    with col4:
        if st.button("❌ Close Viewer", use_container_width=True, type="primary"):
            st.session_state.viewing_story = False
            st.rerun()

def render_main_interface():
    """Render the main Collect Earth Online style interface"""
    
    # Initialize data
    init_data_directories()
    
    # Custom CSS
    st.markdown("""
    <style>
        /* Main app styling */
        .stApp {
            background: #f8f9fa;
        }
        
        /* Header */
        .main-header {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            padding: 1.5rem 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
        }
        
        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .logo-section {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo {
            font-size: 2.5rem;
            background: rgba(255, 255, 255, 0.2);
            padding: 10px;
            border-radius: 12px;
        }
        
        .title-section h1 {
            margin: 0;
            font-size: 1.8rem;
            font-weight: 700;
        }
        
        .title-section p {
            margin: 5px 0 0 0;
            opacity: 0.9;
            font-size: 0.9rem;
        }
        
        .header-actions {
            display: flex;
            gap: 10px;
        }
        
        /* Stats cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
        }
        
        .stat-icon {
            font-size: 2rem;
            margin-bottom: 10px;
        }
        
        .stat-number {
            font-size: 1.8rem;
            font-weight: 700;
            color: #1a2980;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Sidebar */
        .sidebar-section {
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
        }
        
        .section-title {
            color: #1a2980;
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Organizations list */
        .org-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .org-item {
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .org-item:hover {
            background: #f8f9fa;
        }
        
        .org-item.active {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
        }
        
        .org-name {
            font-weight: 600;
            color: #2c3e50;
        }
        
        .org-meta {
            font-size: 0.8rem;
            color: #7f8c8d;
            margin-top: 3px;
        }
        
        /* Projects list */
        .project-item {
            padding: 10px;
            border-radius: 8px;
            background: #f8f9fa;
            margin-bottom: 8px;
            border: 1px solid #e9ecef;
        }
        
        .project-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }
        
        .project-name {
            font-weight: 600;
            color: #2c3e50;
        }
        
        .project-stats {
            font-size: 0.8rem;
            color: #6c757d;
            background: white;
            padding: 2px 8px;
            border-radius: 12px;
        }
        
        /* Upload area */
        .upload-container {
            border: 2px dashed #1a2980;
            border-radius: 12px;
            padding: 30px;
            text-align: center;
            background: rgba(26, 41, 128, 0.03);
            margin: 20px 0;
        }
        
        .upload-icon {
            font-size: 3rem;
            color: #1a2980;
            margin-bottom: 15px;
        }
        
        /* Media gallery */
        .media-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .media-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 3px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
        }
        
        .media-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);
        }
        
        .media-preview {
            height: 150px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 3rem;
        }
        
        .media-info {
            padding: 15px;
        }
        
        .media-title {
            font-weight: 600;
            margin-bottom: 5px;
            color: #2c3e50;
        }
        
        .media-meta {
            font-size: 0.8rem;
            color: #7f8c8d;
            margin-bottom: 10px;
        }
        
        .media-actions {
            display: flex;
            gap: 5px;
        }
        
        /* Map container */
        .map-wrapper {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }
        
        /* Button styling */
        .stButton > button {
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.3s ease !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo">🌍</div>
                <div class="title-section">
                    <h1>GeoCollect - Drone Media Manager</h1>
                    <p>Professional Geographic Data Collection & Visualization Platform</p>
                </div>
            </div>
            <div class="header-actions">
                <button onclick="window.location.reload()" style="background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.3); padding: 8px 16px; border-radius: 6px; cursor: pointer;">
                    🔄 Refresh
                </button>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Calculate statistics
    active_project_items = [item for item in st.session_state.media_items 
                           if item.get('project') == st.session_state.active_project]
    
    total_media = len(st.session_state.media_items)
    project_media = len(active_project_items)
    images_count = sum(1 for item in st.session_state.media_items if item['type'] == 'image')
    videos_count = sum(1 for item in st.session_state.media_items if item['type'] == 'video')
    unique_locations = len(set((item['lat'], item['lon']) for item in st.session_state.media_items))
    
    # Statistics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">📊</div>
            <div class="stat-number">{total_media}</div>
            <div class="stat-label">Total Media</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">📷</div>
            <div class="stat-number">{images_count}</div>
            <div class="stat-label">Images</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">🎬</div>
            <div class="stat-number">{videos_count}</div>
            <div class="stat-label">Videos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">📍</div>
            <div class="stat-number">{unique_locations}</div>
            <div class="stat-label">Locations</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">🏢</div>
            <div class="stat-number">{len(st.session_state.organizations)}</div>
            <div class="stat-label">Organizations</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main layout
    col_sidebar, col_main = st.columns([1, 3])
    
    with col_sidebar:
        # Organizations
        st.markdown("""
        <div class="sidebar-section">
            <div class="section-title">🏢 Organizations</div>
            <div class="org-list">
        """, unsafe_allow_html=True)
        
        for org_id, org_data in st.session_state.organizations.items():
            is_active = org_id == st.session_state.active_organization
            active_class = "active" if is_active else ""
            
            # Count projects in this organization
            org_projects = [p for p in st.session_state.projects.values() 
                           if p.get('organization') == org_id]
            
            st.markdown(f"""
            <div class="org-item {active_class}" onclick="window.parent.document.getElementById('select-org-{org_id}').click()">
                <div class="org-name">{org_data['name']}</div>
                <div class="org-meta">
                    {len(org_projects)} projects • Created {org_data.get('created', '')[:10]}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("Select", key=f"select-org-{org_id}", use_container_width=True, 
                        type="primary" if is_active else "secondary"):
                st.session_state.active_organization = org_id
                st.rerun()
        
        st.markdown("""
            </div>
            <div style="margin-top: 15px;">
                <button onclick="window.parent.document.getElementById('new-org-btn').click()" 
                        style="width: 100%; background: #1a2980; color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer;">
                    + New Organization
                </button>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # New Organization Button
        if st.button("+ New Organization", key="new-org-btn", use_container_width=True):
            with st.form("new_organization"):
                org_name = st.text_input("Organization Name")
                org_desc = st.text_area("Description")
                
                if st.form_submit_button("Create Organization"):
                    if org_name:
                        org_id = org_name.lower().replace(" ", "_")
                        st.session_state.organizations[org_id] = {
                            "name": org_name,
                            "description": org_desc,
                            "created": datetime.now().isoformat(),
                            "projects": []
                        }
                        st.session_state.active_organization = org_id
                        save_all_data()
                        st.rerun()
        
        # Current Project
        st.markdown("""
        <div class="sidebar-section">
            <div class="section-title">📋 Current Project</div>
        """, unsafe_allow_html=True)
        
        if st.session_state.active_project and st.session_state.active_project in st.session_state.projects:
            project = st.session_state.projects[st.session_state.active_project]
            project_items = [item for item in st.session_state.media_items 
                           if item.get('project') == st.session_state.active_project]
            
            st.markdown(f"""
            <div style="padding: 15px; background: #e3f2fd; border-radius: 8px; margin-bottom: 15px;">
                <div style="font-weight: 600; font-size: 1.1rem; color: #1a2980; margin-bottom: 5px;">
                    {project['name']}
                </div>
                <div style="font-size: 0.9rem; color: #5d6d7e; margin-bottom: 10px;">
                    {project.get('description', 'No description')}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                    <span>📁 {len(project_items)} media</span>
                    <span>📅 {project.get('created', '')[:10]}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("No project selected")
        
        # Projects list for current organization
        org_projects = [p for p_id, p in st.session_state.projects.items() 
                       if p.get('organization') == st.session_state.active_organization]
        
        if org_projects:
            st.markdown('<div class="section-title" style="margin-top: 20px;">📁 Organization Projects</div>', unsafe_allow_html=True)
            
            for project in org_projects[:5]:  # Show first 5
                proj_items = [item for item in st.session_state.media_items 
                            if item.get('project') == project['name'].lower().replace(" ", "_")]
                
                st.markdown(f"""
                <div class="project-item">
                    <div class="project-header">
                        <div class="project-name">{project['name']}</div>
                        <div class="project-stats">{len(proj_items)} items</div>
                    </div>
                    <div style="font-size: 0.8rem; color: #7f8c8d;">
                        {project.get('description', '')[:50]}...
                    </div>
                    <button onclick="window.parent.document.getElementById('select-proj-{project['name'].lower().replace(' ', '_')}').click()"
                            style="margin-top: 8px; width: 100%; padding: 5px; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                        Select Project
                    </button>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Select", key=f"select-proj-{project['name'].lower().replace(' ', '_')}", 
                            use_container_width=True, type="primary" if project['name'].lower().replace(" ", "_") == st.session_state.active_project else "secondary"):
                    st.session_state.active_project = project['name'].lower().replace(" ", "_")
                    st.rerun()
        
        # New Project Button
        if st.button("+ New Project", key="new-project-btn", use_container_width=True):
            with st.form("new_project"):
                proj_name = st.text_input("Project Name")
                proj_desc = st.text_area("Project Description")
                
                if st.form_submit_button("Create Project"):
                    if proj_name:
                        proj_id = proj_name.lower().replace(" ", "_")
                        st.session_state.projects[proj_id] = {
                            "name": proj_name,
                            "description": proj_desc,
                            "organization": st.session_state.active_organization,
                            "created": datetime.now().isoformat(),
                            "media_items": []
                        }
                        st.session_state.active_project = proj_id
                        save_all_data()
                        st.rerun()
        
        # Quick Actions
        st.markdown("""
        <div class="sidebar-section">
            <div class="section-title">⚡ Quick Actions</div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
        """, unsafe_allow_html=True)
        
        if st.button("📤 Upload Media", key="upload-btn-side", use_container_width=True, type="primary"):
            st.session_state.show_upload = True
        
        if project_media > 0:
            if st.button("🎥 View Project Stories", key="stories-btn-side", use_container_width=True):
                st.session_state.viewing_story = True
                st.session_state.story_index = 0
                st.rerun()
        
        if st.button("📊 Export Data", key="export-btn-side", use_container_width=True):
            if st.session_state.media_items:
                export_data = {
                    'organizations': st.session_state.organizations,
                    'projects': st.session_state.projects,
                    'media_items': st.session_state.media_items,
                    'export_date': datetime.now().isoformat()
                }
                
                st.download_button(
                    label="Download JSON Export",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"geocollect_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
        
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_main:
        # Upload section (if triggered)
        if st.session_state.get('show_upload', False):
            st.markdown("### 📤 Upload Media to Project")
            
            with st.form("upload_form"):
                col_upload, col_coords = st.columns([2, 1])
                
                with col_upload:
                    uploaded_files = st.file_uploader(
                        "Select drone media files",
                        type=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'],
                        accept_multiple_files=True,
                        help="You can select multiple files at once"
                    )
                
                with col_coords:
                    st.markdown("**📍 GPS Coordinates**")
                    lat = st.number_input("Latitude", min_value=-90.0, max_value=90.0, 
                                         value=0.0, step=0.0001, format="%.6f")
                    lon = st.number_input("Longitude", min_value=-180.0, max_value=180.0, 
                                         value=0.0, step=0.0001, format="%.6f")
                    
                    st.markdown(f"""
                    <div style="background: #f0f2f6; padding: 10px; border-radius: 6px; margin-top: 10px;">
                        <small>Selected Coordinates:</small><br>
                        <code>{lat:.6f}, {lon:.6f}</code>
                    </div>
                    """, unsafe_allow_html=True)
                
                col_project, col_submit = st.columns([2, 1])
                with col_project:
                    project_options = {pid: p['name'] for pid, p in st.session_state.projects.items() 
                                     if p.get('organization') == st.session_state.active_organization}
                    selected_project = st.selectbox(
                        "Assign to Project",
                        options=list(project_options.keys()),
                        format_func=lambda x: project_options[x],
                        index=list(project_options.keys()).index(st.session_state.active_project) 
                        if st.session_state.active_project in project_options else 0
                    )
                
                with col_submit:
                    st.markdown("<br>", unsafe_allow_html=True)
                    submit_upload = st.form_submit_button("Upload Files", type="primary", use_container_width=True)
                
                if submit_upload and uploaded_files:
                    success_count = 0
                    for uploaded_file in uploaded_files:
                        media_type = get_media_type(uploaded_file.name)
                        
                        if media_type:
                            filepath, filename = save_uploaded_file(uploaded_file)
                            
                            new_item = {
                                'id': str(uuid.uuid4()),
                                'name': uploaded_file.name,
                                'type': media_type,
                                'path': filepath,
                                'filename': filename,
                                'lat': lat,
                                'lon': lon,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'project': selected_project,
                                'organization': st.session_state.active_organization
                            }
                            
                            st.session_state.media_items.append(new_item)
                            success_count += 1
                    
                    if success_count > 0:
                        save_all_data()
                        st.success(f"✅ Successfully uploaded {success_count} file(s)!")
                        st.session_state.show_upload = False
                        st.rerun()
                    else:
                        st.error("No valid files were uploaded")
            
            if st.button("Cancel Upload", use_container_width=True):
                st.session_state.show_upload = False
                st.rerun()
        
        else:
            # Map View
            st.markdown("### 🗺️ Interactive Map Viewer")
            
            # Map controls
            col_view, col_actions = st.columns([2, 1])
            
            with col_view:
                view_mode = st.selectbox(
                    "Map View",
                    ["Satellite", "Street", "Terrain", "Dark"],
                    help="Choose your preferred map style"
                )
            
            with col_actions:
                if st.button("🗺️ Reset View", use_container_width=True):
                    st.session_state.map_center = [0, 0]
                    st.session_state.zoom_level = 2
                    st.rerun()
            
            # Create and display map
            with st.container():
                m = create_collect_earth_style_map()
                map_data = st_folium(
                    m,
                    width=900,
                    height=600,
                    key="main_map",
                    returned_objects=["last_object_clicked", "center", "zoom", "bounds"]
                )
                
                # Update map state
                if map_data:
                    if map_data.get('center'):
                        st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]
                    if map_data.get('zoom'):
                        st.session_state.zoom_level = map_data['zoom']
                    
                    # Handle marker clicks
                    if map_data.get('last_object_clicked'):
                        clicked_lat = map_data['last_object_clicked'].get('lat')
                        clicked_lng = map_data['last_object_clicked'].get('lng')
                        
                        if clicked_lat and clicked_lng:
                            # Find item
                            active_items = [item for item in st.session_state.media_items 
                                          if item.get('project') == st.session_state.active_project]
                            
                            for idx, item in enumerate(active_items):
                                if (abs(item['lat'] - clicked_lat) < 0.001 and 
                                    abs(item['lon'] - clicked_lng) < 0.001):
                                    st.session_state.story_index = idx
                                    st.session_state.viewing_story = True
                                    st.rerun()
                                    break
            
            # Project Media Gallery
            if project_media > 0:
                st.markdown(f"### 📁 Project Media ({project_media} items)")
                
                # Filter options
                col_filter, col_sort, col_view = st.columns([2, 2, 1])
                
                with col_filter:
                    media_filter = st.selectbox(
                        "Filter by type",
                        ["All Media", "Images Only", "Videos Only"]
                    )
                
                with col_sort:
                    sort_by = st.selectbox(
                        "Sort by",
                        ["Newest First", "Oldest First", "Name A-Z", "Name Z-A"]
                    )
                
                with col_view:
                    if st.button("Grid View", use_container_width=True):
                        st.session_state.view_mode = "grid"
                
                # Filter items
                filtered_items = active_project_items.copy()
                
                if media_filter == "Images Only":
                    filtered_items = [item for item in filtered_items if item['type'] == 'image']
                elif media_filter == "Videos Only":
                    filtered_items = [item for item in filtered_items if item['type'] == 'video']
                
                # Sort items
                if sort_by == "Newest First":
                    filtered_items.sort(key=lambda x: x['timestamp'], reverse=True)
                elif sort_by == "Oldest First":
                    filtered_items.sort(key=lambda x: x['timestamp'])
                elif sort_by == "Name A-Z":
                    filtered_items.sort(key=lambda x: x['name'].lower())
                elif sort_by == "Name Z-A":
                    filtered_items.sort(key=lambda x: x['name'].lower(), reverse=True)
                
                # Display as grid
                cols = st.columns(3)
                for idx, item in enumerate(filtered_items[:12]):  # Show first 12
                    with cols[idx % 3]:
                        with st.container():
                            st.markdown(f"""
                            <div class="media-card">
                                <div class="media-preview">
                                    {'📷' if item['type'] == 'image' else '🎬'}
                                </div>
                                <div class="media-info">
                                    <div class="media-title">{item['name'][:25]}{'...' if len(item['name']) > 25 else ''}</div>
                                    <div class="media-meta">
                                        📍 {item['lat']:.4f}, {item['lon']:.4f}<br>
                                        🕒 {item['timestamp']}
                                    </div>
                                    <div class="media-actions">
                                        <button onclick="window.parent.document.getElementById('view-item-{item['id']}').click()"
                                                style="flex: 1; background: #3498db; color: white; border: none; padding: 6px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                            View
                                        </button>
                                        <button onclick="window.parent.document.getElementById('delete-item-{item['id']}').click()"
                                                style="background: #e74c3c; color: white; border: none; padding: 6px; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Hidden buttons for actions
                            col_view, col_del = st.columns(2)
                            with col_view:
                                if st.button("👁️ View", key=f"view-item-{item['id']}", use_container_width=True):
                                    st.session_state.story_index = idx
                                    st.session_state.viewing_story = True
                                    st.rerun()
                            
                            with col_del:
                                if st.button("🗑️", key=f"delete-item-{item['id']}", use_container_width=True):
                                    if os.path.exists(item['path']):
                                        os.remove(item['path'])
                                    st.session_state.media_items = [
                                        m for m in st.session_state.media_items 
                                        if m['id'] != item['id']
                                    ]
                                    save_all_data()
                                    st.rerun()
                
                if len(filtered_items) > 12:
                    st.info(f"Showing 12 of {len(filtered_items)} items. Use filters to find specific media.")
            else:
                st.info("No media in current project. Upload some files to get started!")

# JavaScript message handler
st.markdown("""
<script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'view_story') {
            // Trigger Streamlit rerun with story index
            window.parent.postMessage({
                isStreamlitMessage: true,
                type: 'streamlit:setComponentValue',
                value: {index: event.data.index}
            }, '*');
        }
    });
</script>
""", unsafe_allow_html=True)

# Main app flow
if st.session_state.viewing_story:
    render_story_viewer()
else:
    render_main_interface()
