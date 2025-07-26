from flask import Flask, request, jsonify, Response
from airsim_controller import AirSimController
import sys
import os
import wave
import json
import time
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment

# --- Initialization ---

app = Flask(__name__)

MODEL_PATH = "model"
if not os.path.exists(MODEL_PATH):
    print(f"Vosk model not found at '{MODEL_PATH}'. Please download and place it there.", file=sys.stderr)
    sys.exit(1)
    
print("Loading speech recognition model...")
vosk_model = Model(MODEL_PATH)
print("Speech recognition model loaded.")

print("Initializing AirSim Controller...")
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
    while True:
        # Control the frame rate to avoid overwhelming the server or client.
        # 20 FPS is a good balance for monitoring.
        time.sleep(0.05)

        frame = drone_controller.get_camera_image()
        if frame is None:
            # If we fail to get a frame (e.g., simulator is lagging),
            # just skip it and try again in the next iteration.
            continue
        
        # Yield the frame in the multipart format. Each frame is a self-contained JPEG.
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# --- API Endpoints ---

@app.route('/video_feed')
def video_feed():
    """
    Endpoint for streaming the drone's camera feed.
    You can view this stream directly in a web browser.
    """
    if not drone_controller.is_connected:
        return "AirSim simulator not connected.", 503

    # Return a streaming response. The mimetype tells the browser how to handle it.
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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
    A simple health-check/info endpoint.
    """
    connection_status = "Connected" if drone_controller.is_connected else "Not Connected"
    return jsonify({
        "service": "AirSim Control API",
        "status": "running",
        "airsim_connection": connection_status,
        "endpoints": {
            "/command": "Accepts JSON POST requests for text commands.",
            "/audio_command": "Accepts multipart/form-data POST requests with an 'audio' file.",
            "/video_feed": "Provides a live MJPEG stream from the drone's camera."
        }
    })

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5000, debug=False)
