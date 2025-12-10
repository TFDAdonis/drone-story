import streamlit as st
import folium
from streamlit_folium import st_folium
import base64
from datetime import datetime
import os
import json
import uuid
from PIL import Image
import io

st.set_page_config(
    page_title="GeoDrone Visualizer",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Constants
DATA_DIR = "geo_drone_data"
MEDIA_DIR = os.path.join(DATA_DIR, "media")
METADATA_FILE = os.path.join(DATA_DIR, "metadata.json")

# Initialize session state
if 'media_items' not in st.session_state:
    st.session_state.media_items = []

if 'viewing_story' not in st.session_state:
    st.session_state.viewing_story = False

if 'story_index' not in st.session_state:
    st.session_state.story_index = 0

if 'map_center' not in st.session_state:
    st.session_state.map_center = [37.7749, -122.4194]

if 'zoom_level' not in st.session_state:
    st.session_state.zoom_level = 4

def init_data_directories():
    """Initialize data directories"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MEDIA_DIR, exist_ok=True)

def load_media_items():
    """Load media items from disk"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            data = json.load(f)
            return data.get('media_items', [])
    return []

def save_media_items():
    """Save media items to disk"""
    data = {
        'media_items': st.session_state.media_items,
        'last_updated': datetime.now().isoformat()
    }
    with open(METADATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return its path"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{uploaded_file.name}"
    filepath = os.path.join(MEDIA_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath, filename

def get_media_type(filename):
    """Determine if file is image or video"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
    
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
        img.thumbnail(size)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        return None

def get_video_thumbnail(video_path):
    """Placeholder for video thumbnail extraction"""
    return None

def get_marker_html(item, thumbnail_base64=None):
    """Generate HTML for marker popup with media preview"""
    if thumbnail_base64 and item['type'] == 'image':
        media_preview = f'<img src="data:image/png;base64,{thumbnail_base64}" style="width:100px;height:100px;object-fit:cover;border-radius:8px;margin:5px 0;">'
    else:
        icon = '📷' if item['type'] == 'image' else '🎬'
        media_preview = f'<div style="text-align:center;font-size:48px;margin:10px 0;">{icon}</div>'
    
    return f"""
    <div style="width:200px;font-family:Arial,sans-serif;">
        <div style="font-weight:bold;margin-bottom:5px;">{item['name'][:20]}{'...' if len(item['name']) > 20 else ''}</div>
        {media_preview}
        <div style="font-size:11px;color:#666;margin:5px 0;">
            📍 {item['lat']:.5f}, {item['lon']:.5f}
        </div>
        <div style="font-size:10px;color:#888;">{item['timestamp']}</div>
        <button onclick="window.parent.document.getElementById('view-btn-{item['id']}').click()" 
                style="background:#3498db;color:white;border:none;padding:5px 10px;border-radius:4px;cursor:pointer;margin-top:5px;width:100%;">
            👁️ View Story
        </button>
    </div>
    """

def create_map():
    """Create the main map with media markers"""
    items = st.session_state.media_items
    
    # Use last map view or calculate center
    if items and st.session_state.map_center == [37.7749, -122.4194]:
        avg_lat = sum(item['lat'] for item in items) / len(items)
        avg_lon = sum(item['lon'] for item in items) / len(items)
        center = [avg_lat, avg_lon]
        zoom = 10
    else:
        center = st.session_state.map_center
        zoom = st.session_state.zoom_level
    
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles='CartoDB positron',
        control_scale=True
    )
    
    # Add tile layer options
    folium.TileLayer(
        'OpenStreetMap',
        name='Open Street Map'
    ).add_to(m)
    
    folium.TileLayer(
        'CartoDB dark_matter',
        name='Dark Mode'
    ).add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Add markers
    for idx, item in enumerate(items):
        # Create thumbnail
        thumbnail = None
        if item['type'] == 'image' and os.path.exists(item['path']):
            thumbnail = create_thumbnail(item['path'])
        
        # Generate popup HTML
        popup_html = get_marker_html(item, thumbnail)
        
        # Create marker
        iframe = folium.IFrame(popup_html, width=220, height=200)
        popup = folium.Popup(iframe, max_width=220)
        
        # Use custom icon for better visual
        icon_color = 'green' if item['type'] == 'image' else 'blue'
        icon = folium.Icon(
            color=icon_color,
            icon='camera' if item['type'] == 'image' else 'play',
            prefix='fa'
        )
        
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=popup,
            tooltip=f"{'📷' if item['type'] == 'image' else '🎬'} {item['name'][:15]}",
            icon=icon
        ).add_to(m)
        
        # Add JavaScript trigger button (hidden)
        st.markdown(f"""
        <div id="view-btn-{item['id']}" style="display:none;"></div>
        <script>
            document.getElementById('view-btn-{item['id']}').onclick = function() {{
                window.parent.postMessage({{
                    type: 'view_story',
                    index: {idx}
                }}, '*');
            }};
        </script>
        """, unsafe_allow_html=True)
    
    # Add fullscreen button
    folium.plugins.Fullscreen().add_to(m)
    
    # Add measure control
    folium.plugins.MeasureControl(position='topleft').add_to(m)
    
    return m

def render_snapchat_story():
    """Render the story viewer interface"""
    items = st.session_state.media_items
    current_idx = st.session_state.story_index
    current_item = items[current_idx]
    total_items = len(items)
    
    st.markdown("""
    <style>
        .story-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: white;
        }
        
        .story-progress {
            display: flex;
            gap: 4px;
            margin-bottom: 20px;
        }
        
        .progress-bar {
            flex: 1;
            height: 3px;
            background: rgba(255,255,255,0.3);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: white;
            transition: width 0.3s ease;
        }
        
        .story-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        
        .story-user {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .user-avatar {
            width: 50px;
            height: 50px;
            background: linear-gradient(45deg, #FF5F6D, #FFC371);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        
        .story-media-container {
            background: white;
            border-radius: 20px;
            padding: 20px;
            min-height: 400px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        
        .story-media-container img,
        .story-media-container video {
            max-width: 100%;
            max-height: 60vh;
            border-radius: 10px;
            object-fit: contain;
        }
        
        .story-info {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 15px;
            margin-top: 20px;
        }
        
        .coordinate-display {
            font-family: 'Courier New', monospace;
            background: rgba(0,0,0,0.2);
            padding: 8px 12px;
            border-radius: 8px;
            margin: 10px 0;
        }
        
        .nav-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        
        .nav-buttons button {
            flex: 1;
            padding: 12px;
            border: none;
            border-radius: 10px;
            background: rgba(255,255,255,0.2);
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .nav-buttons button:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        
        .close-btn {
            background: #e74c3c !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Progress bars
    progress_bars = ""
    for i in range(total_items):
        is_active = i <= current_idx
        progress_bars += f'<div class="progress-bar"><div class="progress-fill" style="width: {100 if is_active else 0}%"></div></div>'
    
    st.markdown(f"""
    <div class="story-container">
        <div class="story-progress">
            {progress_bars}
        </div>
        
        <div class="story-header">
            <div class="story-user">
                <div class="user-avatar">🚁</div>
                <div>
                    <h3 style="margin:0;">Drone Capture #{current_idx + 1}</h3>
                    <p style="margin:0;opacity:0.8;font-size:14px;">{current_item['timestamp']}</p>
                </div>
            </div>
            <div style="text-align:right;">
                <h2 style="margin:0;">{current_idx + 1}/{total_items}</h2>
                <p style="margin:0;opacity:0.8;font-size:14px;">Story Viewer</p>
            </div>
        </div>
        
        <div class="story-media-container">
    """, unsafe_allow_html=True)
    
    # Display media
    if os.path.exists(current_item['path']):
        if current_item['type'] == 'image':
            st.image(current_item['path'], use_container_width=True)
        else:
            st.video(current_item['path'])
    else:
        st.error("Media file not found")
    
    st.markdown(f"""
        </div>
        
        <div class="story-info">
            <h4>📍 Location Information</h4>
            <div class="coordinate-display">
                Latitude: {current_item['lat']:.6f}<br>
                Longitude: {current_item['lon']:.6f}
            </div>
            <p><strong>Filename:</strong> {current_item['name']}</p>
            <p><strong>Type:</strong> {'📷 Photo' if current_item['type'] == 'image' else '🎬 Video'}</p>
        </div>
        
        <div class="nav-buttons">
    """, unsafe_allow_html=True)
    
    # Navigation buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("⬅️ Previous", use_container_width=True, disabled=current_idx == 0):
            st.session_state.story_index = max(0, current_idx - 1)
            st.rerun()
    
    with col2:
        if st.button("Next ➡️", use_container_width=True, disabled=current_idx == total_items - 1):
            st.session_state.story_index = min(total_items - 1, current_idx + 1)
            st.rerun()
    
    with col3:
        if st.button("🗺️ Back to Map", use_container_width=True):
            st.session_state.viewing_story = False
            st.rerun()
    
    with col4:
        if st.button("❌ Close", use_container_width=True, type="primary"):
            st.session_state.viewing_story = False
            st.rerun()

def render_main_app():
    """Render the main application interface"""
    # Custom CSS
    st.markdown("""
    <style>
        /* Import fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* Main styles */
        .stApp {
            font-family: 'Inter', sans-serif;
        }
        
        /* Header */
        .main-header {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            padding: 2rem;
            border-radius: 0 0 20px 20px;
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .header-title {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .header-subtitle {
            font-size: 1rem;
            opacity: 0.9;
            font-weight: 300;
        }
        
        /* Stats cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: #1a2980;
            margin-bottom: 0.5rem;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Sidebar */
        .sidebar-section {
            background: white;
            padding: 1.5rem;
            border-radius: 15px;
            margin-bottom: 1rem;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
        }
        
        .sidebar-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #1a2980;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #1a2980 0%, #26d0ce 100%);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(26, 41, 128, 0.2);
        }
        
        /* Map container */
        .map-container {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        /* Upload area */
        .upload-area {
            border: 2px dashed #1a2980;
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
            background: rgba(26, 41, 128, 0.05);
            margin-bottom: 1rem;
        }
        
        /* Media card */
        .media-card {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .media-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0,0,0,0.1);
        }
        
        .media-preview {
            height: 150px;
            background: #f5f5f5;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
        }
        
        .media-info {
            padding: 1rem;
        }
        
        /* Institution list */
        .institution-list {
            max-height: 300px;
            overflow-y: auto;
        }
        
        .institution-item {
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .institution-item:last-child {
            border-bottom: none;
        }
        
        .institution-name {
            font-weight: 500;
            color: #333;
        }
        
        .visit-btn {
            background: #1a2980;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 5px 15px;
            font-size: 0.8rem;
            cursor: pointer;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <div class="header-title">🌍 GeoDrone Visualizer</div>
        <div class="header-subtitle">Professional Geographic Data Visualization & Drone Media Management</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize data
    init_data_directories()
    
    # Load saved data on first run
    if not st.session_state.media_items:
        st.session_state.media_items = load_media_items()
    
    # Stats
    total_items = len(st.session_state.media_items)
    image_count = sum(1 for item in st.session_state.media_items if item['type'] == 'image')
    video_count = sum(1 for item in st.session_state.media_items if item['type'] == 'video')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{total_items}</div>
            <div class="stat-label">Total Media</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{image_count}</div>
            <div class="stat-label">Photographs</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{video_count}</div>
            <div class="stat-label">Videos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{len(set((item['lat'], item['lon']) for item in st.session_state.media_items))}</div>
            <div class="stat-label">Locations</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Main layout
    col_main, col_sidebar = st.columns([3, 1])
    
    with col_sidebar:
        # Institutions sidebar
        st.markdown("""
        <div class="sidebar-section">
            <div class="sidebar-title">📍 Institutions</div>
            <div class="institution-list">
                <div class="institution-item">
                    <div class="institution-name">Aerial Research Center</div>
                    <button class="visit-btn">VISIT</button>
                </div>
                <div class="institution-item">
                    <div class="institution-name">Geospatial Lab</div>
                    <button class="visit-btn">VISIT</button>
                </div>
                <div class="institution-item">
                    <div class="institution-name">Drone Analytics HQ</div>
                    <button class="visit-btn">VISIT</button>
                </div>
                <div class="institution-item">
                    <div class="institution-name">Mapping Institute</div>
                    <button class="visit-btn">VISIT</button>
                </div>
                <div class="institution-item">
                    <div class="institution-name">Remote Sensing Dept</div>
                    <button class="visit-btn">VISIT</button>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Upload section
        with st.container():
            st.markdown('<div class="sidebar-title">📤 Upload Media</div>', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader(
                "Drop your drone media here",
                type=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'],
                label_visibility="collapsed",
                help="Upload images or videos from your drone"
            )
            
            if uploaded_file:
                col_lat, col_lon = st.columns(2)
                with col_lat:
                    lat = st.number_input(
                        "Latitude",
                        min_value=-90.0,
                        max_value=90.0,
                        value=37.7749,
                        step=0.0001,
                        format="%.6f",
                        key="upload_lat"
                    )
                
                with col_lon:
                    lon = st.number_input(
                        "Longitude",
                        min_value=-180.0,
                        max_value=180.0,
                        value=-122.4194,
                        step=0.0001,
                        format="%.6f",
                        key="upload_lon"
                    )
                
                if st.button("➕ Add to Map", use_container_width=True):
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
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        st.session_state.media_items.append(new_item)
                        save_media_items()
                        st.success(f"✅ Added {uploaded_file.name} to map!")
                        st.rerun()
                    else:
                        st.error("Unsupported file format")
        
        # Quick actions
        st.markdown('<div class="sidebar-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
        
        if st.button("🎥 View All Stories", use_container_width=True):
            if st.session_state.media_items:
                st.session_state.viewing_story = True
                st.session_state.story_index = 0
                st.rerun()
            else:
                st.warning("No media to view")
        
        if st.button("🗑️ Clear All", use_container_width=True, type="secondary"):
            if st.session_state.media_items:
                if st.checkbox("Confirm deletion of all media"):
                    for item in st.session_state.media_items:
                        if os.path.exists(item['path']):
                            os.remove(item['path'])
                    st.session_state.media_items = []
                    save_media_items()
                    st.rerun()
        
        # Export button
        if st.button("📤 Export Data", use_container_width=True):
            if st.session_state.media_items:
                # Create export data
                export_data = {
                    'metadata': {
                        'export_date': datetime.now().isoformat(),
                        'total_items': len(st.session_state.media_items)
                    },
                    'media_items': st.session_state.media_items
                }
                
                # Convert to JSON for download
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"geodrone_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    with col_main:
        # Map view
        st.markdown("### 🗺️ Interactive Map")
        
        if st.session_state.media_items:
            st.info("💡 Click on any marker to preview media. Click 'View Story' in popup to open full viewer.")
            
            # Create and display map
            with st.container():
                m = create_map()
                map_data = st_folium(
                    m,
                    width=800,
                    height=600,
                    key="main_map",
                    returned_objects=["last_object_clicked", "center", "zoom"]
                )
                
                # Update map view state
                if map_data:
                    if map_data.get('center'):
                        st.session_state.map_center = [map_data['center']['lat'], map_data['center']['lng']]
                    if map_data.get('zoom'):
                        st.session_state.zoom_level = map_data['zoom']
                    
                    # Check for marker clicks
                    if map_data.get('last_object_clicked'):
                        clicked_lat = map_data['last_object_clicked'].get('lat')
                        clicked_lng = map_data['last_object_clicked'].get('lng')
                        
                        if clicked_lat and clicked_lng:
                            # Find closest item
                            closest_idx = None
                            closest_dist = float('inf')
                            
                            for idx, item in enumerate(st.session_state.media_items):
                                dist = ((item['lat'] - clicked_lat)**2 + (item['lon'] - clicked_lng)**2)**0.5
                                if dist < closest_dist and dist < 0.01:  # Threshold for click detection
                                    closest_dist = dist
                                    closest_idx = idx
                            
                            if closest_idx is not None:
                                st.session_state.story_index = closest_idx
                                st.session_state.viewing_story = True
                                st.rerun()
        else:
            st.info("📍 No media uploaded yet. Use the sidebar to upload drone footage.")
            m = create_map()
            st_folium(m, width=800, height=600, key="empty_map")
        
        # Media gallery
        st.markdown("### 📁 Media Gallery")
        
        if st.session_state.media_items:
            # Filter options
            col_filter, col_sort = st.columns(2)
            with col_filter:
                filter_type = st.selectbox(
                    "Filter by type:",
                    ["All", "Photos Only", "Videos Only"]
                )
            
            with col_sort:
                sort_by = st.selectbox(
                    "Sort by:",
                    ["Newest First", "Oldest First", "Location"]
                )
            
            # Apply filters
            if filter_type == "Photos Only":
                filtered_items = [item for item in st.session_state.media_items if item['type'] == 'image']
            elif filter_type == "Videos Only":
                filtered_items = [item for item in st.session_state.media_items if item['type'] == 'video']
            else:
                filtered_items = st.session_state.media_items
            
            # Apply sorting
            if sort_by == "Newest First":
                filtered_items.sort(key=lambda x: x['timestamp'], reverse=True)
            elif sort_by == "Oldest First":
                filtered_items.sort(key=lambda x: x['timestamp'])
            elif sort_by == "Location":
                filtered_items.sort(key=lambda x: (x['lat'], x['lon']))
            
            # Display gallery
            cols = st.columns(3)
            for idx, item in enumerate(filtered_items):
                with cols[idx % 3]:
                    st.markdown(f"""
                    <div class="media-card">
                        <div class="media-preview">
                            {'📷' if item['type'] == 'image' else '🎬'}
                        </div>
                        <div class="media-info">
                            <strong>{item['name'][:20]}{'...' if len(item['name']) > 20 else ''}</strong>
                            <p style="font-size:0.8rem;color:#666;margin:5px 0;">
                                📍 {item['lat']:.4f}, {item['lon']:.4f}
                            </p>
                            <p style="font-size:0.7rem;color:#888;">{item['timestamp']}</p>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_view, col_del = st.columns(2)
                    with col_view:
                        if st.button("👁️ View", key=f"gallery_view_{item['id']}", use_container_width=True):
                            original_idx = st.session_state.media_items.index(item)
                            st.session_state.story_index = original_idx
                            st.session_state.viewing_story = True
                            st.rerun()
                    
                    with col_del:
                        if st.button("🗑️", key=f"gallery_del_{item['id']}", use_container_width=True):
                            if os.path.exists(item['path']):
                                os.remove(item['path'])
                            st.session_state.media_items = [
                                m for m in st.session_state.media_items if m['id'] != item['id']
                            ]
                            save_media_items()
                            st.rerun()
        else:
            st.info("No media available. Upload some drone footage to get started!")

# JavaScript for handling marker clicks
st.markdown("""
<script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'view_story') {
            // This will be handled by Streamlit's rerun
            window.location.href = window.location.href.split('?')[0] + '?view_story=' + event.data.index;
        }
    });
</script>
""", unsafe_allow_html=True)

# Main app flow
if st.session_state.viewing_story and st.session_state.media_items:
    render_snapchat_story()
else:
    render_main_app()
