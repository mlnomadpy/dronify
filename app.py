from flask import Flask, request, jsonify, Response, render_template, send_from_directory
from airsim_controller import AirSimController
import sys
import os
import wave
import json
import time
import speech_recognition as sr
from pydub import AudioSegment

# --- Initialization ---

app = Flask(__name__, static_folder='static', static_url_path='/static', template_folder='templates')

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
    Transcribes an audio file to text using the SpeechRecognition library.
    """
    try:
        print(f"Transcribing audio file: {audio_path}")
        
        # Check if file exists
        if not os.path.exists(audio_path):
            print(f"Error: Audio file {audio_path} does not exist")
            return None
            
        # Initialize recognizer
        recognizer = sr.Recognizer()
        
        # Load and process audio
        sound = AudioSegment.from_file(audio_path)
        print(f"Original audio: {len(sound)}ms, {sound.frame_rate}Hz, {sound.channels} channels")
        
        # Convert to mono and normalize
        sound = sound.set_channels(1)
        sound = sound.normalize()
        
        # Apply some noise reduction (simple high-pass filter)
        if len(sound) > 0:
            sound = sound.high_pass_filter(80)  # Remove very low frequencies
        
        print(f"Processed audio: {len(sound)}ms, {sound.frame_rate}Hz, {sound.channels} channels")
        
        # Check if audio is too short
        if len(sound) < 200:  # Less than 200ms
            print("Error: Audio too short for transcription")
            return None
        
        # Convert to WAV format for SpeechRecognition
        wav_path = audio_path + "_temp.wav"
        sound.export(wav_path, format="wav")
        
        # Use SpeechRecognition to transcribe
        with sr.AudioFile(wav_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            audio_data = recognizer.record(source)
        
        # Clean up temporary file
        os.remove(wav_path)
        
        # Try multiple recognition engines for better accuracy
        recognized_text = None
        
        # Try Google Web Speech API first (most accurate but requires internet)
        try:
            print("Attempting Google Web Speech API...")
            recognized_text = recognizer.recognize_google(audio_data)
            print(f"Google result: '{recognized_text}'")
        except sr.UnknownValueError:
            print("Google Web Speech API could not understand audio")
        except sr.RequestError as e:
            print(f"Google Web Speech API error: {e}")
        
        # If Google fails, try offline Sphinx as fallback
        if not recognized_text:
            try:
                print("Attempting offline Sphinx recognition...")
                recognized_text = recognizer.recognize_sphinx(audio_data)
                print(f"Sphinx result: '{recognized_text}'")
            except sr.UnknownValueError:
                print("Sphinx could not understand audio")
            except sr.RequestError as e:
                print(f"Sphinx error: {e}")
        
        # Clean up the recognized text
        if recognized_text:
            recognized_text = recognized_text.strip()
            print(f"Final transcription: '{recognized_text}'")
        else:
            print("No transcription could be generated")
        
        return recognized_text if recognized_text else None
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_frames():
    """
    A generator function that continuously yields camera frames from AirSim
    in a format suitable for HTTP streaming.
    """
    consecutive_failures = 0
    max_consecutive_failures = 10
    last_successful_time = time.time()
    
    while True:
        # Control the frame rate to avoid overwhelming the server or client.
        # 20 FPS is a good balance for monitoring.
        time.sleep(0.05)

        try:
            frame = drone_controller.get_camera_image()
            if frame is None:
                consecutive_failures += 1
                # print(f"Warning: Failed to get camera frame (attempt {consecutive_failures})")
                
                # If it's been too long since last successful frame, check connection
                if time.time() - last_successful_time > 30:  # 30 seconds
                    try:
                        # Try to refresh the AirSim connection
                        drone_controller.client.confirmConnection()
                        print("Refreshed AirSim connection for camera feed")
                        last_successful_time = time.time()
                    except:
                        pass
                
                if consecutive_failures >= max_consecutive_failures:
                    print("Error: Too many consecutive camera failures, breaking stream")
                    break
                    
                # If we fail to get a frame, continue to next iteration
                continue
            else:
                # Reset failure counter on successful frame
                consecutive_failures = 0
                last_successful_time = time.time()
            
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

@app.route('/refresh_camera', methods=['POST'])
def refresh_camera():
    """
    Endpoint to refresh the camera connection.
    """
    if not drone_controller.is_connected:
        return jsonify({
            "status": "error",
            "message": "AirSim simulator not connected"
        }), 503
    
    try:
        # Reset camera error count
        if hasattr(drone_controller, '_camera_error_count'):
            drone_controller._camera_error_count = 0
        
        # Try to refresh the connection
        drone_controller.client.confirmConnection()
        
        # Test camera immediately
        test_frame = drone_controller.get_camera_image()
        
        if test_frame:
            return jsonify({
                "status": "success",
                "message": "Camera connection refreshed successfully",
                "frame_size": len(test_frame)
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Camera refresh failed - no image received"
            }), 503
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Failed to refresh camera: {e}"
        }), 500

@app.route('/debug/audio', methods=['POST'])
def debug_audio():
    """
    Debug endpoint to test audio transcription without command interpretation.
    """
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    audio_file = request.files['audio']
    if audio_file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Save temporary file
    temp_path = "debug_audio_temp"
    try:
        audio_file.save(temp_path)
        
        # Get file info
        file_size = os.path.getsize(temp_path)
        
        # Load audio for analysis
        sound = AudioSegment.from_file(temp_path)
        
        # Transcribe
        transcribed_text = transcribe_audio(temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        debug_info = {
            "file_info": {
                "filename": audio_file.filename,
                "size_bytes": file_size,
                "duration_ms": len(sound),
                "sample_rate": sound.frame_rate,
                "channels": sound.channels
            },
            "transcription": {
                "success": transcribed_text is not None,
                "text": transcribed_text or "",
                "length": len(transcribed_text) if transcribed_text else 0
            }
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"error": f"Debug failed: {str(e)}"}), 500

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
        print("Error: No audio file in request")
        return jsonify({"status": "error", "message": "No audio file found in the request."}), 400

    audio_file = request.files['audio']
    if audio_file.filename == '':
        print("Error: Empty audio filename")
        return jsonify({"status": "error", "message": "No selected file."}), 400

    print(f"Received audio file: {audio_file.filename}, size: {len(audio_file.read())} bytes")
    audio_file.seek(0)  # Reset file pointer after reading

    temp_path = "temp_audio_command"
    try:
        audio_file.save(temp_path)
        print(f"Audio file saved to {temp_path}")
        
        # Check if file was saved properly
        if not os.path.exists(temp_path):
            print("Error: Failed to save audio file")
            return jsonify({"status": "error", "message": "Failed to save audio file."}), 500
            
        file_size = os.path.getsize(temp_path)
        print(f"Saved audio file size: {file_size} bytes")
        
        if file_size == 0:
            print("Error: Saved audio file is empty")
            os.remove(temp_path)
            return jsonify({"status": "error", "message": "Audio file is empty."}), 400

        transcribed_text = transcribe_audio(temp_path)
        os.remove(temp_path)
        
        print(f"Transcription result: '{transcribed_text}'")

        if not transcribed_text or transcribed_text.strip() == "":
            print("Error: Transcription returned empty or None")
            return jsonify({"status": "error", "message": "Could not understand audio or audio was empty."}), 400

        command = drone_controller.interpret_text_command(transcribed_text)
        print(f"Interpreted command: '{command}'")

        if not command:
            print("Error: Failed to interpret command")
            return jsonify({
                "status": "error",
                "message": "Failed to map your speech to a known command.",
                "transcribed_text": transcribed_text
            }), 400

        response = drone_controller.execute_command(command)
        response['transcribed_text'] = transcribed_text
        response['interpreted_command'] = command
        
        print(f"Command execution result: {response}")
        
        status_code = 200 if response.get('status') == 'success' else 500
        return jsonify(response), status_code
        
    except Exception as e:
        print(f"Error processing audio command: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({"status": "error", "message": f"Error processing audio: {str(e)}"}), 500

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
