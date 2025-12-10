import streamlit as st
import folium
from streamlit_folium import st_folium
import base64
from datetime import datetime
import os
import json

# Page config
st.set_page_config(
    page_title="Drone Media Map",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'media_items' not in st.session_state:
    st.session_state.media_items = []

if 'viewing_story' not in st.session_state:
    st.session_state.viewing_story = False

if 'story_index' not in st.session_state:
    st.session_state.story_index = 0

if 'selected_item' not in st.session_state:
    st.session_state.selected_item = None

# Data file
DATA_FILE = "media_data.json"

def load_data():
    """Load media data from file"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                # Ensure all items have the required fields
                for item in data:
                    if 'id' not in item:
                        item['id'] = f"{item['timestamp']}_{item['name']}"
                return data
        except:
            return []
    return []

def save_data():
    """Save media data to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(st.session_state.media_items, f, indent=2)

# Load data on startup
if not st.session_state.media_items:
    st.session_state.media_items = load_data()

def save_uploaded_file(uploaded_file):
    """Save uploaded file and return its path"""
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Create unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    filepath = os.path.join(upload_dir, filename)
    
    # Save file
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

def get_media_type(filename):
    """Check if file is image or video"""
    image_ext = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    video_ext = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    
    ext = os.path.splitext(filename)[1].lower()
    if ext in image_ext:
        return 'image'
    elif ext in video_ext:
        return 'video'
    return None

def create_simple_map():
    """Create a simple map with media markers"""
    # Create base map
    m = folium.Map(location=[20, 0], zoom_start=2)
    
    # Add markers for each media item
    for idx, item in enumerate(st.session_state.media_items):
        # Choose icon based on media type
        if item['type'] == 'image':
            icon_color = 'green'
            icon_type = 'camera'
        else:
            icon_color = 'red'
            icon_type = 'play'
        
        # Create popup with preview
        popup_html = f"""
        <div style="width: 200px; padding: 10px;">
            <div style="font-weight: bold; margin-bottom: 5px;">
                {item['name']}
            </div>
            <div style="color: #666; font-size: 12px; margin-bottom: 8px;">
                📍 {item['lat']:.4f}, {item['lon']:.4f}<br>
                📅 {item['timestamp']}
            </div>
            <div style="text-align: center;">
                <button onclick="
                    window.parent.postMessage({{
                        type: 'view_media',
                        index: {idx}
                    }}, '*');
                " style="
                    background: #3498db;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                    cursor: pointer;
                ">
                    👁️ View Media
                </button>
            </div>
        </div>
        """
        
        # Add marker to map
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"Click to view {item['name']}",
            icon=folium.Icon(color=icon_color, icon=icon_type, prefix='fa')
        ).add_to(m)
    
    return m

def display_media_fullscreen(item):
    """Display media in fullscreen story mode"""
    st.markdown("""
    <style>
        .story-container {
            background: black;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 9999;
        }
        .media-display {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .media-display img, .media-display video {
            max-width: 100%;
            max-height: 100vh;
            object-fit: contain;
        }
        .close-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if os.path.exists(item['path']):
            if item['type'] == 'image':
                st.image(item['path'], use_container_width=True)
            else:
                st.video(item['path'])
        else:
            st.error("File not found")
        
        # Display info
        st.markdown(f"""
        <div style="color: white; text-align: center; padding: 20px;">
            <h3>{item['name']}</h3>
            <p>📍 {item['lat']:.6f}, {item['lon']:.6f}</p>
            <p>📅 {item['timestamp']}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Close", type="primary"):
            st.session_state.viewing_story = False
            st.rerun()

# Main app
st.title("🌍 Drone Media Map")
st.markdown("Upload and view your drone media on an interactive map")

# Sidebar for upload
with st.sidebar:
    st.header("📤 Upload Media")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'mkv']
    )
    
    if uploaded_file:
        # Show preview
        media_type = get_media_type(uploaded_file.name)
        if media_type == 'image':
            st.image(uploaded_file, caption="Preview", use_container_width=True)
        elif media_type == 'video':
            st.video(uploaded_file)
        
        # Get coordinates
        st.subheader("📍 Set Location")
        col1, col2 = st.columns(2)
        with col1:
            lat = st.number_input("Latitude", 
                                 min_value=-90.0, 
                                 max_value=90.0, 
                                 value=37.7749,
                                 format="%.6f")
        with col2:
            lon = st.number_input("Longitude",
                                 min_value=-180.0,
                                 max_value=180.0,
                                 value=-122.4194,
                                 format="%.6f")
        
        if st.button("Add to Map", type="primary"):
            if media_type:
                # Save file
                filepath = save_uploaded_file(uploaded_file)
                
                # Create media item
                new_item = {
                    'id': f"{datetime.now().timestamp()}_{uploaded_file.name}",
                    'name': uploaded_file.name,
                    'type': media_type,
                    'path': filepath,
                    'lat': lat,
                    'lon': lon,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                # Add to list
                st.session_state.media_items.append(new_item)
                save_data()
                st.success(f"✅ Added {uploaded_file.name} to map!")
                st.rerun()
            else:
                st.error("Unsupported file type")

# Main content area
tab1, tab2 = st.tabs(["🗺️ Map View", "📁 Media List"])

with tab1:
    # Stats
    total = len(st.session_state.media_items)
    images = sum(1 for item in st.session_state.media_items if item['type'] == 'image')
    videos = sum(1 for item in st.session_state.media_items if item['type'] == 'video')
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Media", total)
    with col2:
        st.metric("Images", images)
    with col3:
        st.metric("Videos", videos)
    with col4:
        st.metric("Locations", len(set((item['lat'], item['lon']) for item in st.session_state.media_items)))
    
    # Create and display map
    m = create_simple_map()
    
    # Display map
    map_data = st_folium(m, width=800, height=500, key="main_map")
    
    # Handle map clicks
    if map_data and map_data.get('last_object_clicked'):
        clicked_lat = map_data['last_object_clicked'].get('lat')
        clicked_lng = map_data['last_object_clicked'].get('lng')
        
        # Find closest media item
        closest_item = None
        min_distance = float('inf')
        
        for idx, item in enumerate(st.session_state.media_items):
            dist = abs(item['lat'] - clicked_lat) + abs(item['lon'] - clicked_lng)
            if dist < min_distance and dist < 0.1:  # 0.1 degree threshold
                min_distance = dist
                closest_item = idx
        
        if closest_item is not None:
            st.session_state.story_index = closest_item
            st.session_state.viewing_story = True
            st.rerun()
    
    # Add JavaScript for button clicks
    st.markdown("""
    <script>
    window.addEventListener('message', function(event) {
        if (event.data.type === 'view_media') {
            // This triggers a Streamlit rerun
            window.location.href = window.location.href.split('#')[0] + '?view=' + event.data.index;
        }
    });
    </script>
    """, unsafe_allow_html=True)

with tab2:
    st.header("Media Library")
    
    if st.session_state.media_items:
        # Search and filter
        search = st.text_input("🔍 Search media")
        
        # Filter by type
        filter_type = st.selectbox("Filter by type", ["All", "Images", "Videos"])
        
        # Apply filters
        filtered_items = st.session_state.media_items
        if search:
            filtered_items = [item for item in filtered_items if search.lower() in item['name'].lower()]
        if filter_type == "Images":
            filtered_items = [item for item in filtered_items if item['type'] == 'image']
        elif filter_type == "Videos":
            filtered_items = [item for item in filtered_items if item['type'] == 'video']
        
        # Display media grid
        cols = st.columns(3)
        for idx, item in enumerate(filtered_items):
            with cols[idx % 3]:
                with st.container():
                    st.markdown(f"""
                    <div style="border: 1px solid #ddd; border-radius: 10px; padding: 10px; margin: 5px;">
                        <div style="font-weight: bold;">{item['name'][:30]}{'...' if len(item['name']) > 30 else ''}</div>
                        <div style="font-size: 12px; color: #666;">
                            📍 {item['lat']:.4f}, {item['lon']:.4f}<br>
                            📅 {item['timestamp']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show preview or icon
                    if os.path.exists(item['path']):
                        if item['type'] == 'image':
                            st.image(item['path'], use_container_width=True)
                        else:
                            st.video(item['path'])
                    else:
                        st.markdown(f"""
                        <div style="text-align: center; padding: 20px; background: #f0f0f0; border-radius: 5px;">
                            <div style="font-size: 48px;">{'📷' if item['type'] == 'image' else '🎬'}</div>
                            <div>File not found</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("View", key=f"view_{item['id']}", use_container_width=True):
                            item_index = st.session_state.media_items.index(item)
                            st.session_state.story_index = item_index
                            st.session_state.viewing_story = True
                            st.rerun()
                    with col2:
                        if st.button("Delete", key=f"delete_{item['id']}", use_container_width=True):
                            # Remove file
                            if os.path.exists(item['path']):
                                os.remove(item['path'])
                            # Remove from list
                            st.session_state.media_items = [i for i in st.session_state.media_items if i['id'] != item['id']]
                            save_data()
                            st.rerun()
    else:
        st.info("No media uploaded yet. Use the sidebar to upload files.")

# Handle story viewing
if st.session_state.viewing_story and st.session_state.media_items:
    current_item = st.session_state.media_items[st.session_state.story_index]
    total_items = len(st.session_state.media_items)
    
    # Create story viewer
    st.markdown("""
    <style>
        .story-viewer {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: black;
            z-index: 10000;
            display: flex;
            flex-direction: column;
        }
        .story-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
        }
        .story-media {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .story-media img, .story-media video {
            max-width: 100%;
            max-height: 80vh;
            object-fit: contain;
        }
        .story-controls {
            padding: 20px;
            background: rgba(0,0,0,0.8);
            display: flex;
            gap: 10px;
            justify-content: center;
        }
        .story-controls button {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Progress bar
    progress = (st.session_state.story_index + 1) / total_items
    st.progress(progress)
    
    # Header
    col1, col2, col3 = st.columns([2, 3, 2])
    with col1:
        st.markdown(f"### {current_item['name']}")
    with col2:
        st.markdown(f"#### 📍 {current_item['lat']:.6f}, {current_item['lon']:.6f}")
    with col3:
        st.markdown(f"#### Item {st.session_state.story_index + 1} of {total_items}")
    
    # Media display
    if os.path.exists(current_item['path']):
        if current_item['type'] == 'image':
            st.image(current_item['path'], use_container_width=True)
        else:
            st.video(current_item['path'])
    else:
        st.error("Media file not found")
        st.markdown(f"""
        <div style="text-align: center; padding: 50px;">
            <div style="font-size: 64px;">📁</div>
            <h3>File Not Found</h3>
            <p>The file may have been moved or deleted.</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Navigation controls
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.story_index > 0:
            if st.button("⬅️ Previous", use_container_width=True):
                st.session_state.story_index -= 1
                st.rerun()
        else:
            st.button("⬅️ Previous", disabled=True, use_container_width=True)
    
    with col2:
        if st.session_state.story_index < total_items - 1:
            if st.button("➡️ Next", use_container_width=True):
                st.session_state.story_index += 1
                st.rerun()
        else:
            st.button("➡️ Next", disabled=True, use_container_width=True)
    
    with col3:
        if st.button("🗺️ Back to Map", use_container_width=True):
            st.session_state.viewing_story = False
            st.rerun()
    
    with col4:
        if st.button("❌ Close", type="primary", use_container_width=True):
            st.session_state.viewing_story = False
            st.rerun()
    
    # Display additional info
    with st.expander("📋 Media Information"):
        st.write(f"**Filename:** {current_item['name']}")
        st.write(f"**Type:** {'Image' if current_item['type'] == 'image' else 'Video'}")
        st.write(f"**Uploaded:** {current_item['timestamp']}")
        st.write(f"**Coordinates:** {current_item['lat']:.6f}, {current_item['lon']:.6f}")
        if os.path.exists(current_item['path']):
            file_size = os.path.getsize(current_item['path']) / (1024*1024)  # MB
            st.write(f"**File size:** {file_size:.2f} MB")

# Clear all button (in sidebar)
with st.sidebar:
    st.markdown("---")
    if st.button("🗑️ Clear All Media", type="secondary"):
        if st.session_state.media_items:
            # Remove all files
            for item in st.session_state.media_items:
                if os.path.exists(item['path']):
                    try:
                        os.remove(item['path'])
                    except:
                        pass
            
            # Clear data
            st.session_state.media_items = []
            save_data()
            st.success("All media cleared!")
            st.rerun()
        else:
            st.info("No media to clear")
    
    # Info
    st.markdown("---")
    st.markdown("### ℹ️ How to use:")
    st.markdown("""
    1. Upload media using the uploader
    2. Set coordinates for the media
    3. Click "Add to Map"
    4. Click markers on map to view media
    5. Use Media List tab to browse all items
    """)
