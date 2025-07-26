import airsim
import time
import sys
from transformers import pipeline
import numpy as np
import cv2

class AirSimController:
    """
    A controller class to manage all interactions with the AirSim drone,
    including interpreting natural language commands and providing a camera feed.
    """
    def __init__(self):
        """
        Initializes the connection to AirSim and loads the language model.
        """
        # --- AirSim Connection ---
        self.client = airsim.MultirotorClient()
        self.is_connected = False
        self.is_initialized = False
        try:
            self.client.confirmConnection()
            self.is_connected = True
            print("Successfully connected to AirSim simulator.")
        except:
            self.is_connected = False
            print("Could not connect to AirSim. Make sure the simulator is running.", file=sys.stderr)

        # --- Command and Model Setup ---
        self.command_map = {
            "initialize": self.initialize_drone,
            "take off": self.take_off,
            "land": self.land,
            "move forward": lambda: self.move_at_velocity(vx=5, duration=2),
            "move back": lambda: self.move_at_velocity(vx=-5, duration=2),
            "move left": lambda: self.move_at_velocity(vy=-5, duration=2),
            "move right": lambda: self.move_at_velocity(vy=5, duration=2),
            "move up": lambda: self.move_at_velocity(vz=-3, duration=2),
            "move down": lambda: self.move_at_velocity(vz=3, duration=2),
            "rotate left": lambda: self.rotate_at_rate(yaw_rate=-30, duration=2),
            "rotate right": lambda: self.rotate_at_rate(yaw_rate=30, duration=2),
            "hover": self.hover,
            "get status": self.get_status,
            "reset": self.reset_drone,
        }
        
        self.candidate_labels = list(self.command_map.keys())

        print("Loading language model for command interpretation...")
        try:
            self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
            print("Language model loaded successfully.")
        except Exception as e:
            print(f"Failed to load language model: {e}", file=sys.stderr)
            self.classifier = None


    def interpret_text_command(self, text):
        """
        Uses the zero-shot classification model to map transcribed text to a drone command.
        """
        if not self.classifier:
            print("Cannot interpret command: language model is not available.", file=sys.stderr)
            return None
            
        print(f"Interpreting text: '{text}'")
        result = self.classifier(text, self.candidate_labels)
        
        best_match = result['labels'][0]
        confidence = result['scores'][0]
        
        print(f"Interpretation result: '{best_match}' with confidence {confidence:.2f}")

        if confidence > 0.70:
            return best_match
        else:
            print("Interpretation confidence too low, command ignored.")
            return None

    def execute_command(self, command):
        """
        Executes a command by looking it up in the command map.
        """
        command = command.lower().strip()
        if not self.is_connected:
            return {"status": "error", "message": "AirSim simulator not connected."}

        action = self.command_map.get(command)

        if not action:
            return {"status": "error", "message": f"Command '{command}' not recognized."}
        
        if not self.is_initialized and command not in ["initialize", "get status", "reset"]:
             return {"status": "error", "message": "Drone is not initialized. Send the 'initialize' command first."}

        try:
            result = action()
            if result is None:
                return {"status": "success", "message": f"Command '{command}' executed successfully."}
            return result
        except Exception as e:
            error_message = f"An error occurred while executing '{command}': {str(e)}"
            print(error_message, file=sys.stderr)
            return {"status": "error", "message": error_message}

    # --- New Method for Camera Feed ---
    
    def get_camera_image(self, camera_name="0"):
        """
        Gets a single image frame from a specified camera and encodes it as JPEG.

        Args:
            camera_name (str): The name of the camera. "0" is the front-center camera.

        Returns:
            bytes: A JPEG-encoded image as a byte string, or None on failure.
        """
        if not self.is_connected:
            return None
            
        try:
            # Request an uncompressed RGBA image from the simulation
            responses = self.client.simGetImages([airsim.ImageRequest(camera_name, airsim.ImageType.Scene, False, False)])
            response = responses[0]

            # Convert the raw image data to a NumPy array
            img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

            # Reshape the array to a 4-channel image (RGBA) and then convert to 3-channel (BGR) for OpenCV
            img_rgba = img1d.reshape(response.height, response.width, 4)
            img_bgr = cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)

            # Encode the BGR image to a JPEG format in memory
            ret, buffer = cv2.imencode('.jpg', img_bgr)
            if not ret:
                print("Failed to encode image to JPEG.", file=sys.stderr)
                return None
            
            # Return the JPEG image as a byte string
            return buffer.tobytes()
        except Exception as e:
            # This can happen if the simulator is not keeping up.
            # print(f"Error getting camera image: {e}", file=sys.stderr)
            return None


    # --- Drone Action Methods (unchanged) ---

    def initialize_drone(self):
        self.client.enableApiControl(True)
        self.client.armDisarm(True)
        self.is_initialized = True
        print("Drone initialized: API control enabled and armed.")
        return {"status": "success", "message": "Drone initialized and ready for flight."}

    def take_off(self):
        print("Taking off...")
        self.client.takeoffAsync().join()
        print("Takeoff complete.")

    def land(self):
        print("Landing...")
        self.client.landAsync().join()
        self.client.armDisarm(False)
        self.is_initialized = False
        print("Landing complete. Drone disarmed.")

    def move_at_velocity(self, vx=0, vy=0, vz=0, duration=1):
        print(f"Moving with velocity (vx={vx}, vy={vy}, vz={vz}) for {duration}s.")
        self.client.moveByVelocityAsync(vx, vy, vz, duration, airsim.DrivetrainType.MaxDegreeOfFreedom, airsim.YawMode(False, 0)).join()
        time.sleep(0.5)
        self.hover()

    def rotate_at_rate(self, yaw_rate=20, duration=1):
        print(f"Rotating at {yaw_rate} deg/s for {duration}s.")
        self.client.rotateByYawRateAsync(yaw_rate, duration).join()
        time.sleep(0.5)
        self.hover()

    def hover(self):
        print("Hovering.")
        self.client.hoverAsync().join()

    def get_status(self):
        state = self.client.getMultirotorState()
        pos = state.kinematics_estimated.position
        orientation = state.kinematics_estimated.orientation
        pitch, roll, yaw = airsim.to_eularian_angles(orientation)
        status = {
            "status": "success",
            "message": "Drone status retrieved.",
            "data": {
                "position": {"x": pos.x_val, "y": pos.y_val, "z": pos.z_val},
                "orientation_degrees": {"pitch": pitch * 180/3.14, "roll": roll* 180/3.14, "yaw": yaw* 180/3.14},
                "is_initialized": self.is_initialized,
                "is_connected": self.is_connected
            }
        }
        print(status)
        return status
        
    def reset_drone(self):
        print("Resetting drone...")
        self.client.armDisarm(False)
        self.client.reset()
        self.client.enableApiControl(False)
        self.is_initialized = False
        print("Drone has been reset.")
        return {"status": "success", "message": "Drone has been reset."}
