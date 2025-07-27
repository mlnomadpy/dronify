from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from airsim_controller import AirSimController
import sys
import os
import wave
import json
import time
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment

# --- Initialization ---

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

MODEL_PATH = "/home/skywolfmo/github/dronify/model/vosk-model-small-en-us-0.15"
if not os.path.exists(MODEL_PATH):
    print(f"Vosk model not found at '{MODEL_PATH}'. Please download and place it there.", file=sys.stderr)
    sys.exit(1)
    
print("Loading speech recognition model...")
vosk_model = Model(MODEL_PATH)
print("Speech recognition model loaded.")

print("Initializing AirSim Controller...")
# Check if user wants to specify a custom AirSim host IP
airsim_host = os.environ.get('AIRSIM_HOST', None)
if airsim_host:
    print(f"Using custom AirSim host from environment: {airsim_host}")
    drone_controller = AirSimController(host_ip=airsim_host)
else:
    drone_controller = AirSimController()

# --- Helper Functions ---

def transcribe_audio(audio_path):
    """
    Transcribes an audio file to text using the Vosk model.
    """
    try:
        sound = AudioSegment.from_file(audio_path)
        sound = sound.set_channels(1)
        sound = sound.set_frame_rate(16000)
        
        rec = KaldiRecognizer(vosk_model, sound.frame_rate)
        rec.SetWords(True)
        rec.AcceptWaveform(sound.raw_data)
        result = rec.FinalResult()
        text = json.loads(result).get("text", "")
        return text
    except Exception as e:
        print(f"Error during transcription: {e}", file=sys.stderr)
        return None

def generate_frames():
    """
    A generator function that continuously yields camera frames from AirSim
    in a format suitable for HTTP streaming.
    """
    consecutive_failures = 0
    max_consecutive_failures = 10
    
    while True:
        # Control the frame rate to avoid overwhelming the server or client.
        # 20 FPS is a good balance for monitoring.
        time.sleep(0.05)

        try:
            frame = drone_controller.get_camera_image()
            if frame is None:
                consecutive_failures += 1
                print(f"Warning: Failed to get camera frame (attempt {consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    print("Error: Too many consecutive camera failures, breaking stream")
                    break
                    
                # If we fail to get a frame, continue to next iteration
                continue
            else:
                # Reset failure counter on successful frame
                consecutive_failures = 0
            
            # Yield the frame in the multipart format. Each frame is a self-contained JPEG.
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                   
        except Exception as e:
            print(f"Error in generate_frames: {e}")
            consecutive_failures += 1
            
            if consecutive_failures >= max_consecutive_failures:
                print("Error: Too many consecutive errors, breaking stream")
                break
            
            continue

# --- API Endpoints ---

@app.route('/video_feed')
def video_feed():
    """
    Endpoint for streaming the drone's camera feed.
    You can view this stream directly in a web browser.
    """
    if not drone_controller.is_connected:
        print("Error: AirSim simulator not connected for video feed")
        return "AirSim simulator not connected.", 503

    # Test if we can get at least one frame before starting the stream
    test_frame = drone_controller.get_camera_image()
    if test_frame is None:
        print("Error: Cannot get camera image from AirSim")
        return "Camera not available. Make sure the drone is initialized and AirSim is running.", 503

    print("Starting video stream...")
    # Return a streaming response. The mimetype tells the browser how to handle it.
    try:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    except Exception as e:
        print(f"Error starting video stream: {e}")
        return f"Video stream error: {e}", 500

@app.route('/video_status')
def video_status():
    """
    Endpoint to check video feed status.
    """
    if not drone_controller.is_connected:
        return jsonify({
            "status": "error",
            "message": "AirSim simulator not connected",
            "connected": False
        }), 503
    
    # Try to get a single frame to test the video feed
    test_frame = drone_controller.get_camera_image()
    
    if test_frame is None:
        return jsonify({
            "status": "error",
            "message": "Camera feed unavailable",
            "connected": True,
            "camera_working": False
        }), 503
    
    return jsonify({
        "status": "success",
        "message": "Video feed is working",
        "connected": True,
        "camera_working": True,
        "frame_size": len(test_frame)
    })

@app.route('/debug/camera')
def debug_camera():
    """
    Debug endpoint to test camera functionality.
    """
    debug_info = {
        "airsim_connected": drone_controller.is_connected,
        "airsim_host": getattr(drone_controller, 'host_ip', 'Unknown'),
        "camera_test": None,
        "error": None
    }
    
    if not drone_controller.is_connected:
        debug_info["error"] = "AirSim not connected"
        return jsonify(debug_info)
    
    try:
        # Test basic connection
        state = drone_controller.client.getMultirotorState()
        debug_info["drone_state"] = {
            "armed": state.armed,
            "landed_state": str(state.landed_state),
            "position": {
                "x": state.kinematics_estimated.position.x_val,
                "y": state.kinematics_estimated.position.y_val,
                "z": state.kinematics_estimated.position.z_val
            }
        }
        
        # Test camera
        test_frame = drone_controller.get_camera_image()
        if test_frame:
            debug_info["camera_test"] = {
                "working": True,
                "frame_size": len(test_frame)
            }
        else:
            debug_info["camera_test"] = {
                "working": False,
                "message": "Failed to get camera frame"
            }
            
    except Exception as e:
        debug_info["error"] = str(e)
    
    return jsonify(debug_info)

@app.route('/audio_command', methods=['POST'])
def handle_audio_command():
    """
    Endpoint to handle audio file uploads for commands.
    """
    if not drone_controller.is_connected:
        return jsonify({"status": "error", "message": "Cannot process command, AirSim simulator is not connected."}), 503

    if 'audio' not in request.files:
        return jsonify({"status": "error", "message": "No audio file found in the request."}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"status": "error", "message": "No selected file."}), 400

    temp_path = "temp_audio_command"
    audio_file.save(temp_path)

    transcribed_text = transcribe_audio(temp_path)
    os.remove(temp_path)

    if not transcribed_text:
        return jsonify({"status": "error", "message": "Could not understand audio or audio was empty."}), 400

    command = drone_controller.interpret_text_command(transcribed_text)

    if not command:
        return jsonify({
            "status": "error",
            "message": "Failed to map your speech to a known command.",
            "transcribed_text": transcribed_text
        }), 400

    response = drone_controller.execute_command(command)
    response['transcribed_text'] = transcribed_text
    response['interpreted_command'] = command
    
    status_code = 200 if response.get('status') == 'success' else 500
    return jsonify(response), status_code

@app.route('/command', methods=['POST'])
def handle_command():
    """
    The original endpoint for text-based commands.
    """
    if not drone_controller.is_connected:
        return jsonify({"status": "error", "message": "Cannot process command, AirSim simulator is not connected."}), 503

    if not request.is_json:
        return jsonify({"status": "error", "message": "Invalid request: Content-Type must be application/json."}), 400

    data = request.get_json()
    command = data.get('command', None)

    if not command:
        return jsonify({"status": "error", "message": "Invalid JSON payload: Missing 'command' key."}), 400

    print(f"Received text command: '{command}'")
    response = drone_controller.execute_command(command)
    status_code = 200 if response.get('status') == 'success' else 500
    return jsonify(response), status_code

@app.route('/', methods=['GET'])
def index():
    """
    Serve the web interface if accessed via browser, otherwise return API info.
    """
    # Check if the request is from a browser (looking for HTML)
    if 'text/html' in request.headers.get('Accept', ''):
        return render_template('index.html')
    
    # Otherwise, return API info as JSON
    connection_status = "Connected" if drone_controller.is_connected else "Not Connected"
    return jsonify({
        "service": "AirSim Control API",
        "status": "running",
        "airsim_connection": connection_status,
        "endpoints": {
            "/command": "Accepts JSON POST requests for text commands.",
            "/audio_command": "Accepts multipart/form-data POST requests with an 'audio' file.",
            "/video_feed": "Provides a live MJPEG stream from the drone's camera.",
            "/web": "Web interface for drone control."
        }
    })

@app.route('/web')
def web_interface():
    """
    Explicitly serve the web interface.
    """
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """
    API endpoint specifically for status information.
    """
    connection_status = "Connected" if drone_controller.is_connected else "Not Connected"
    host_ip = getattr(drone_controller, 'host_ip', 'Unknown')
    
    # Test video feed availability
    video_working = False
    if drone_controller.is_connected:
        test_frame = drone_controller.get_camera_image()
        video_working = test_frame is not None
    
    return jsonify({
        "service": "AirSim Control API",
        "status": "running",
        "airsim_connection": connection_status,
        "airsim_host": host_ip,
        "video_feed_working": video_working,
        "endpoints": {
            "/command": "Accepts JSON POST requests for text commands.",
            "/audio_command": "Accepts multipart/form-data POST requests with an 'audio' file.",
            "/video_feed": "Provides a live MJPEG stream from the drone's camera.",
            "/video_status": "Check video feed status.",
            "/reconnect": "POST endpoint to reconnect to AirSim with optional host IP."
        }
    })

@app.route('/reconnect', methods=['POST'])
def reconnect_airsim():
    """
    Endpoint to reconnect to AirSim, optionally with a new host IP.
    """
    data = request.get_json() if request.is_json else {}
    host_ip = data.get('host_ip', None)
    
    if drone_controller.reconnect(host_ip):
        return jsonify({
            "status": "success",
            "message": f"Successfully reconnected to AirSim at {drone_controller.host_ip}",
            "host_ip": drone_controller.host_ip
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Failed to reconnect to AirSim",
            "host_ip": host_ip or "auto-detected"
        }), 503

@app.route('/static/<path:filename>')
def serve_static(filename):
    """
    Explicitly serve static files.
    """
    return send_from_directory('static', filename)

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
