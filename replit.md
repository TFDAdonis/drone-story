# Drone Media Mapping App

## Overview

A Streamlit-based web application for mapping and visualizing drone media (images and videos) on an interactive map. The application allows users to upload drone footage with GPS metadata and display it on a Snapchat Snap Map-inspired interface. The focus is on creating a clean, visual-rich experience for drone operators to showcase and organize their aerial media geographically.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Framework
- **Technology**: Streamlit with custom CSS styling
- **Rationale**: Streamlit provides rapid prototyping for Python-based data applications with built-in UI components. Custom CSS is injected to achieve the Snapchat-inspired aesthetic with Inter and JetBrains Mono fonts.
- **Map Integration**: Uses Folium for interactive maps with streamlit-folium bridge for Streamlit compatibility

### Design System
- **Visual Style**: Snapchat Snap Map-inspired with permanent markers and clean, minimal interface
- **Color Scheme**: Light/dark mode support with vibrant accent colors (emerald green for images, orange-red for videos)
- **Typography**: Inter for UI text, JetBrains Mono for coordinates and metadata
- **Layout**: Tailwind-inspired spacing system with tight, standard, and generous spacing units

### Application Structure
- **Entry Point**: `app.py` serves as the main Streamlit application
- **Page Layout**: Wide layout with collapsed sidebar, focusing attention on the map and media content
- **Media Handling**: Base64 encoding for media display, datetime for timestamp management

## External Dependencies

### Python Packages
- **streamlit**: Core web application framework
- **folium**: Interactive map generation library
- **streamlit-folium**: Bridge component for embedding Folium maps in Streamlit

### External Services
- **Google Fonts**: Inter and JetBrains Mono font families loaded via CSS import

### Future Considerations
- GPS/EXIF metadata extraction from drone media files
- User authentication system (referenced in design guidelines with purple accent color)
- Media storage solution for uploaded drone footage