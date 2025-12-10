import streamlit as st
import folium
from streamlit_folium import st_folium
import base64
from datetime import datetime
import os

st.set_page_config(
    page_title="Drone Media Map",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if 'media_items' not in st.session_state:
    st.session_state.media_items = []

if 'viewing_story' not in st.session_state:
    st.session_state.viewing_story = False

if 'story_index' not in st.session_state:
    st.session_state.story_index = 0

if 'last_clicked_coords' not in st.session_state:
    st.session_state.last_clicked_coords = None

def save_uploaded_file(uploaded_file):
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    filepath = os.path.join(upload_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

def get_media_type(filename):
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv']
    
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in image_extensions:
        return 'image'
    elif ext in video_extensions:
        return 'video'
    return None

def get_base64_image(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode()

def get_base64_video(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode()

def create_map(media_items):
    if media_items:
        avg_lat = sum(item['lat'] for item in media_items) / len(media_items)
        avg_lon = sum(item['lon'] for item in media_items) / len(media_items)
        zoom_start = 10
    else:
        avg_lat = 37.7749
        avg_lon = -122.4194
        zoom_start = 4
    
    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=zoom_start,
        tiles='CartoDB positron'
    )
    
    for idx, item in enumerate(media_items):
        if item['type'] == 'image':
            icon_symbol = '📷'
            marker_color = 'green'
        else:
            icon_symbol = '🎬'
            marker_color = 'orange'
        
        popup_html = f"""
        <div style="width: 180px; text-align: center; font-family: 'Inter', sans-serif; padding: 8px;">
            <p style="font-weight: 600; margin: 0 0 8px 0; font-size: 14px;">{icon_symbol} {item['name'][:25]}</p>
            <p style="font-family: monospace; font-size: 11px; color: #666; margin: 0 0 4px 0;">
                📍 {item['lat']:.5f}, {item['lon']:.5f}
            </p>
            <p style="font-size: 11px; color: #888; margin: 0;">
                {item['timestamp']}
            </p>
            <p style="margin: 8px 0 0 0; font-size: 12px; color: #3498db; font-weight: 500;">
                Click marker to view story
            </p>
        </div>
        """
        
        folium.Marker(
            location=[item['lat'], item['lon']],
            popup=folium.Popup(popup_html, max_width=200),
            tooltip=f"Click to view {icon_symbol}",
            icon=folium.Icon(color=marker_color, icon='camera' if item['type'] == 'image' else 'play')
        ).add_to(m)
    
    return m

def render_snapchat_story():
    items = st.session_state.media_items
    current_idx = st.session_state.story_index
    current_item = items[current_idx]
    total_items = len(items)
    
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');
        
        .story-container {
            background: #000;
            min-height: 100vh;
            margin: -1rem;
            padding: 0;
        }
        
        .stApp {
            background: #000 !important;
        }
        
        .story-progress-wrapper {
            display: flex;
            gap: 4px;
            padding: 16px 16px 8px 16px;
            background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);
        }
        
        .story-bar {
            flex: 1;
            height: 3px;
            background: rgba(255,255,255,0.3);
            border-radius: 3px;
            overflow: hidden;
        }
        
        .story-bar-fill {
            height: 100%;
            background: #fff;
            border-radius: 3px;
        }
        
        .story-header-info {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 16px;
            color: white;
        }
        
        .story-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #FFFC00 0%, #FF5500 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        
        .story-user-name {
            font-weight: 600;
            font-size: 15px;
            font-family: 'Inter', sans-serif;
        }
        
        .story-time {
            font-size: 12px;
            color: rgba(255,255,255,0.7);
            font-family: 'Inter', sans-serif;
        }
        
        .story-media-container {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 8px;
            min-height: 400px;
        }
        
        .story-media-container img {
            max-width: 100%;
            max-height: 70vh;
            border-radius: 12px;
            object-fit: contain;
        }
        
        .story-media-container video {
            max-width: 100%;
            max-height: 70vh;
            border-radius: 12px;
        }
        
        .story-footer-info {
            background: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
            padding: 24px 16px;
            color: white;
            font-family: 'Inter', sans-serif;
        }
        
        .story-location-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        
        .story-coords-text {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            color: rgba(255,255,255,0.8);
        }
        
        .story-filename-text {
            font-size: 11px;
            color: rgba(255,255,255,0.5);
            margin-top: 4px;
        }
        
        .story-counter-badge {
            text-align: center;
            color: rgba(255,255,255,0.6);
            font-size: 12px;
            padding: 8px;
            font-family: 'Inter', sans-serif;
        }
        
        div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        
        section[data-testid="stMain"] > div {
            padding: 0 !important;
        }
        
        .stButton > button {
            background: rgba(255,255,255,0.15) !important;
            color: white !important;
            border: 1px solid rgba(255,255,255,0.3) !important;
            border-radius: 24px !important;
            font-weight: 500 !important;
            padding: 8px 20px !important;
        }
        
        .stButton > button:hover {
            background: rgba(255,255,255,0.25) !important;
            border-color: rgba(255,255,255,0.5) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    progress_bars_html = ""
    for i in range(total_items):
        fill_width = "100%" if i <= current_idx else "0%"
        progress_bars_html += f'<div class="story-bar"><div class="story-bar-fill" style="width: {fill_width};"></div></div>'
    
    st.markdown(f"""
    <div class="story-progress-wrapper">
        {progress_bars_html}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="story-header-info">
        <div class="story-avatar">🚁</div>
        <div>
            <div class="story-user-name">Drone Capture</div>
            <div class="story-time">{current_item['timestamp']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if current_item['type'] == 'image' and os.path.exists(current_item['path']):
        img_base64 = get_base64_image(current_item['path'])
        ext = os.path.splitext(current_item['path'])[1].lower()
        if ext in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif ext == '.png':
            mime_type = 'image/png'
        elif ext == '.gif':
            mime_type = 'image/gif'
        else:
            mime_type = 'image/webp'
        
        st.markdown(f"""
        <div class="story-media-container">
            <img src="data:{mime_type};base64,{img_base64}" alt="{current_item['name']}" />
        </div>
        """, unsafe_allow_html=True)
    elif current_item['type'] == 'video' and os.path.exists(current_item['path']):
        video_base64 = get_base64_video(current_item['path'])
        ext = os.path.splitext(current_item['path'])[1].lower()
        if ext == '.mp4':
            mime_type = 'video/mp4'
        elif ext == '.webm':
            mime_type = 'video/webm'
        elif ext == '.mov':
            mime_type = 'video/quicktime'
        else:
            mime_type = 'video/mp4'
        
        st.markdown(f"""
        <div class="story-media-container">
            <video controls autoplay muted playsinline>
                <source src="data:{mime_type};base64,{video_base64}" type="{mime_type}">
                Your browser does not support video playback.
            </video>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="story-media-container">
            <div style="color: white; text-align: center;">
                <div style="font-size: 48px; margin-bottom: 16px;">📁</div>
                <div>Media file not found</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="story-footer-info">
        <div class="story-location-row">
            <span>📍</span>
            <span>Drone Location</span>
        </div>
        <div class="story-coords-text">{current_item['lat']:.6f}, {current_item['lon']:.6f}</div>
        <div class="story-filename-text">{current_item['name']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="story-counter-badge">
        {current_idx + 1} / {total_items}
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    
    with col1:
        if current_idx > 0:
            if st.button("⬅️ Previous", key="prev_btn", use_container_width=True):
                st.session_state.story_index = current_idx - 1
                st.rerun()
        else:
            st.button("⬅️ Previous", key="prev_btn_disabled", disabled=True, use_container_width=True)
    
    with col2:
        if current_idx < total_items - 1:
            if st.button("➡️ Next", key="next_btn", use_container_width=True):
                st.session_state.story_index = current_idx + 1
                st.rerun()
        else:
            st.button("➡️ Next", key="next_btn_disabled", disabled=True, use_container_width=True)
    
    with col3:
        if st.button("🗺️ Back to Map", key="map_btn", use_container_width=True):
            st.session_state.viewing_story = False
            st.session_state.last_clicked_coords = None
            st.rerun()
    
    with col4:
        if st.button("❌ Close", key="close_btn", use_container_width=True):
            st.session_state.viewing_story = False
            st.session_state.last_clicked_coords = None
            st.rerun()

def render_main_app():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono&display=swap');
        
        .stApp {
            font-family: 'Inter', sans-serif;
        }
        
        .main-header {
            font-size: 32px;
            font-weight: 600;
            color: #1a1a2e;
            margin-bottom: 8px;
        }
        
        .sub-header {
            font-size: 16px;
            color: #666;
            margin-bottom: 24px;
        }
        
        .coord-display {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            color: #555;
            background: #f0f0f0;
            padding: 4px 8px;
            border-radius: 4px;
        }
        
        .media-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            margin-bottom: 16px;
        }
        
        .stats-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 16px;
        }
        
        .stats-number {
            font-size: 28px;
            font-weight: 600;
        }
        
        .stats-label {
            font-size: 14px;
            opacity: 0.9;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="main-header">🗺️ Drone Media Map</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Upload and visualize your drone footage on an interactive map</p>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📍 Map View", "📤 Upload Media", "📁 Media Gallery"])
    
    with tab2:
        st.markdown("### Upload Drone Media")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "Drop your drone media here",
                type=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'avi', 'webm'],
                help="Supported formats: Images (JPG, PNG, GIF, WEBP) and Videos (MP4, MOV, AVI, WEBM)"
            )
            
            if uploaded_file:
                media_type = get_media_type(uploaded_file.name)
                
                if media_type == 'image':
                    st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
                elif media_type == 'video':
                    st.video(uploaded_file)
        
        with col2:
            st.markdown("### 📍 GPS Coordinates")
            
            lat = st.number_input(
                "Latitude",
                min_value=-90.0,
                max_value=90.0,
                value=37.7749,
                step=0.0001,
                format="%.6f",
                help="Enter latitude (-90 to 90)"
            )
            
            lon = st.number_input(
                "Longitude",
                min_value=-180.0,
                max_value=180.0,
                value=-122.4194,
                step=0.0001,
                format="%.6f",
                help="Enter longitude (-180 to 180)"
            )
            
            st.markdown(f"""
            <div class="coord-display">
                📍 {lat:.6f}, {lon:.6f}
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("➕ Add to Map", type="primary", use_container_width=True):
                if uploaded_file:
                    media_type = get_media_type(uploaded_file.name)
                    
                    if media_type:
                        filepath = save_uploaded_file(uploaded_file)
                        
                        new_item = {
                            'id': len(st.session_state.media_items),
                            'name': uploaded_file.name,
                            'type': media_type,
                            'path': filepath,
                            'lat': lat,
                            'lon': lon,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        
                        st.session_state.media_items.append(new_item)
                        st.success(f"✅ Added {uploaded_file.name} to map!")
                        st.rerun()
                    else:
                        st.error("Unsupported file format")
                else:
                    st.warning("Please upload a file first")
    
    with tab1:
        col_map, col_stats = st.columns([3, 1])
        
        with col_stats:
            total_items = len(st.session_state.media_items)
            image_count = sum(1 for item in st.session_state.media_items if item['type'] == 'image')
            video_count = sum(1 for item in st.session_state.media_items if item['type'] == 'video')
            
            st.markdown(f"""
            <div class="stats-box">
                <div class="stats-number">{total_items}</div>
                <div class="stats-label">Total Media</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="stats-box" style="background: linear-gradient(135deg, #2ECC71 0%, #27AE60 100%);">
                <div class="stats-number">{image_count}</div>
                <div class="stats-label">📷 Photos</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="stats-box" style="background: linear-gradient(135deg, #E74C3C 0%, #C0392B 100%);">
                <div class="stats-number">{video_count}</div>
                <div class="stats-label">🎬 Videos</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown("**Legend**")
            st.markdown("🟢 **Green** - Photos")
            st.markdown("🟠 **Orange** - Videos")
            
            if st.session_state.media_items:
                st.markdown("---")
                if st.button("🎥 View All Stories", use_container_width=True, type="primary"):
                    st.session_state.viewing_story = True
                    st.session_state.story_index = 0
                    st.rerun()
        
        with col_map:
            if st.session_state.media_items:
                st.info("💡 **Click on any marker** to open that media in the Snapchat-style story viewer!")
                m = create_map(st.session_state.media_items)
                map_data = st_folium(m, width=None, height=500, key="main_map")
                
                if map_data and map_data.get('last_object_clicked'):
                    clicked_lat = map_data['last_object_clicked'].get('lat')
                    clicked_lng = map_data['last_object_clicked'].get('lng')
                    current_coords = (clicked_lat, clicked_lng)
                    
                    if clicked_lat and clicked_lng and current_coords != st.session_state.last_clicked_coords:
                        for idx, item in enumerate(st.session_state.media_items):
                            if abs(item['lat'] - clicked_lat) < 0.0001 and abs(item['lon'] - clicked_lng) < 0.0001:
                                st.session_state.last_clicked_coords = current_coords
                                st.session_state.story_index = idx
                                st.session_state.viewing_story = True
                                st.rerun()
                                break
            else:
                st.info("📍 No media uploaded yet. Go to the **Upload Media** tab to add drone footage to the map.")
                m = create_map([])
                st_folium(m, width=None, height=500, key="empty_map")
    
    with tab3:
        st.markdown("### 📁 Media Gallery")
        
        if st.session_state.media_items:
            col_filter, col_clear = st.columns([3, 1])
            
            with col_filter:
                filter_type = st.radio(
                    "Filter by type:",
                    ["All", "Photos Only", "Videos Only"],
                    horizontal=True
                )
            
            with col_clear:
                if st.button("🗑️ Clear All", type="secondary", use_container_width=True):
                    for item in st.session_state.media_items:
                        if os.path.exists(item['path']):
                            os.remove(item['path'])
                    st.session_state.media_items = []
                    st.session_state.viewing_story = False
                    st.rerun()
            
            if filter_type == "Photos Only":
                filtered_items = [item for item in st.session_state.media_items if item['type'] == 'image']
            elif filter_type == "Videos Only":
                filtered_items = [item for item in st.session_state.media_items if item['type'] == 'video']
            else:
                filtered_items = st.session_state.media_items
            
            if filtered_items:
                cols = st.columns(3)
                
                for idx, item in enumerate(filtered_items):
                    with cols[idx % 3]:
                        with st.container():
                            st.markdown(f"""
                            <div class="media-card">
                                <p style="font-weight: 600; margin-bottom: 4px;">
                                    {'📷' if item['type'] == 'image' else '🎬'} {item['name'][:20]}{'...' if len(item['name']) > 20 else ''}
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if os.path.exists(item['path']):
                                if item['type'] == 'image':
                                    st.image(item['path'], use_container_width=True)
                                else:
                                    st.video(item['path'])
                            
                            st.markdown(f"""
                            <div class="coord-display" style="margin-top: 8px;">
                                📍 {item['lat']:.4f}, {item['lon']:.4f}
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.caption(f"Added: {item['timestamp']}")
                            
                            col_view, col_remove = st.columns(2)
                            with col_view:
                                original_idx = st.session_state.media_items.index(item)
                                if st.button("👁️ View", key=f"view_{item['id']}", use_container_width=True):
                                    st.session_state.story_index = original_idx
                                    st.session_state.viewing_story = True
                                    st.rerun()
                            with col_remove:
                                if st.button("🗑️", key=f"remove_{item['id']}", use_container_width=True):
                                    if os.path.exists(item['path']):
                                        os.remove(item['path'])
                                    st.session_state.media_items = [
                                        m for m in st.session_state.media_items if m['id'] != item['id']
                                    ]
                                    st.rerun()
            else:
                st.info("No media matches the current filter.")
        else:
            st.info("📁 No media uploaded yet. Go to the **Upload Media** tab to add drone footage.")

if st.session_state.viewing_story and st.session_state.media_items:
    render_snapchat_story()
else:
    render_main_app()
