# Dronify Web Interface

This directory contains the web interface for the Dronify drone control system.

## Files:
- `index.html` - Main web interface
- `style.css` - Styling for the web interface  
- `script.js` - JavaScript functionality for API interactions

## Features:
- Live camera feed from the drone
- Text command input with quick command buttons
- Voice command recording and processing
- Real-time command log with status indicators
- Connection status monitoring

## Usage:
1. Start the Flask server: `python app.py`
2. Open your browser and navigate to `http://localhost:5000`
3. Use the interface to control your drone via text or voice commands

## Commands Available:
- initialize, take off, land, hover
- move forward/back/left/right/up/down
- rotate left/right
- get status, reset

Make sure the AirSim simulator is running before using the interface.
