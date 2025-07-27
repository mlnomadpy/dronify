import airsim
import time
import sys
import os
import subprocess
from transformers import pipeline
import numpy as np
import cv2

class AirSimController:
    """
    A controller class to manage all interactions with the AirSim drone,
    including interpreting natural language commands and providing a camera feed.
    """
    def __init__(self, host_ip=None):
        """
        Initializes the connection to AirSim and loads the language model.
        
        Args:
            host_ip (str): IP address of the AirSim host. If None, will auto-detect for WSL.
        """
        # --- Determine AirSim Host IP ---
        if host_ip is None:
            host_ip = self._get_airsim_host_ip()
        
        print(f"Attempting to connect to AirSim at {host_ip}:41451")
        
        # --- AirSim Connection ---
        self.client = airsim.MultirotorClient(ip=host_ip)
        self.is_connected = False
        self.is_initialized = False
        self.host_ip = host_ip
        
        try:
            # Set a timeout for the connection attempt
            self.client.confirmConnection()
            # Test the connection with a simple call
            self.client.getMultirotorState()
            self.is_connected = True
            print(f"Successfully connected to AirSim simulator at {host_ip}.")
        except Exception as e:
            self.is_connected = False
            print(f"Could not connect to AirSim at {host_ip}. Error: {e}", file=sys.stderr)
            print("Make sure the AirSim simulator is running on the Windows host.", file=sys.stderr)
            if self._is_wsl():
                print("WSL detected. Ensure Windows Firewall allows connections on port 41451.", file=sys.stderr)
                print("You may need to run: New-NetFirewallRule -DisplayName 'AirSim' -Direction Inbound -Protocol TCP -LocalPort 41451 -Action Allow", file=sys.stderr)

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

    def _is_wsl(self):
        """
        Check if running in WSL (Windows Subsystem for Linux).
        """
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                return 'microsoft' in version_info or 'wsl' in version_info
        except:
            return False

    def _get_airsim_host_ip(self):
        """
        Auto-detect the AirSim host IP address.
        For WSL, this will be the Windows host IP.
        For native Linux, this will be localhost.
        """
        if self._is_wsl():
            return self._get_windows_host_ip()
        else:
            return "127.0.0.1"

    def _get_windows_host_ip(self):
        """
        Get the Windows host IP address from WSL.
        Tests multiple methods and returns the first working IP.
        """
        potential_ips = []
        
        try:
            # Method 1: Use /etc/resolv.conf (works in WSL2)
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        ip = line.split()[1]
                        potential_ips.append(('resolv.conf', ip))
                        break
        except:
            pass

        try:
            # Method 2: Use ip route (alternative method)
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'default via' in line:
                        ip = line.split('default via')[1].split()[0]
                        potential_ips.append(('ip route', ip))
                        break
        except:
            pass

        try:
            # Method 3: Use environment variable if set
            wsl_host = os.environ.get('WSL_HOST_IP') or os.environ.get('AIRSIM_HOST')
            if wsl_host:
                potential_ips.append(('environment variable', wsl_host))
        except:
            pass

        # Test each IP for connectivity to AirSim
        if potential_ips:
            print("📡 Testing potential Windows host IPs:")
            for method, ip in potential_ips:
                print(f"   {method}: {ip}")
                if self._test_connectivity(ip):
                    print(f"✅ Found working AirSim host: {ip}")
                    return ip
                else:
                    print(f"❌ {ip} not reachable")

        # Fallback to common WSL2 default and test it
        fallback_ips = ["172.21.176.1", "172.20.240.1", "172.18.0.1"]
        print("🔄 Trying fallback IPs:")
        for ip in fallback_ips:
            print(f"   Testing {ip}...")
            if self._test_connectivity(ip):
                print(f"✅ Found working fallback IP: {ip}")
                return ip
        
        # Ultimate fallback
        fallback_ip = "172.21.176.1"  # This worked in your test
        print(f"⚠️  Using default fallback IP: {fallback_ip}")
        return fallback_ip

    def _test_connectivity(self, ip, port=41451, timeout=2):
        """
        Test if AirSim is reachable at the given IP and port.
        """
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except:
            return False

    def reconnect(self, host_ip=None):
        """
        Attempt to reconnect to AirSim with a specific host IP.
        """
        if host_ip is None:
            host_ip = self._get_airsim_host_ip()
        
        print(f"Attempting to reconnect to AirSim at {host_ip}:41451")
        
        try:
            self.client = airsim.MultirotorClient(ip=host_ip)
            self.client.confirmConnection()
            self.client.getMultirotorState()
            self.is_connected = True
            self.host_ip = host_ip
            print(f"Successfully reconnected to AirSim at {host_ip}.")
            return True
        except Exception as e:
            self.is_connected = False
            print(f"Reconnection failed: {e}", file=sys.stderr)
            return False


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
            # print("Warning: Cannot get camera image - AirSim not connected", file=sys.stderr)
            return None
            
        try:
            # Use synchronous method to avoid IOLoop conflicts
            responses = self.client.simGetImages([airsim.ImageRequest(camera_name, airsim.ImageType.Scene, False, False)])
            
            if not responses:
                # print("Warning: No camera response received from AirSim", file=sys.stderr)
                return None
                
            response = responses[0]
            
            if not response.image_data_uint8:
                # print("Warning: Empty image data received from AirSim", file=sys.stderr)
                return None

            # Get image dimensions
            height = response.height
            width = response.width
            
            # Convert the raw image data to a NumPy array
            img1d = np.frombuffer(response.image_data_uint8, dtype=np.uint8)

            if len(img1d) == 0:
                # print("Warning: Empty image buffer from AirSim", file=sys.stderr)
                return None

            # Calculate expected size for RGBA (4 channels)
            expected_size = height * width * 4
            actual_size = len(img1d)
            
            # Check if the size matches RGBA format
            if actual_size == expected_size:
                # Standard RGBA format
                img_rgba = img1d.reshape(height, width, 4)
                img_bgr = cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)
            elif actual_size == height * width * 3:
                # RGB format (3 channels)
                img_rgb = img1d.reshape(height, width, 3)
                img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
            elif actual_size == height * width:
                # Grayscale format (1 channel)
                img_gray = img1d.reshape(height, width)
                img_bgr = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2BGR)
            else:
                # print(f"Error: Unexpected image size. Expected: {expected_size} (RGBA), got: {actual_size}", file=sys.stderr)
                # print(f"Image dimensions: {width}x{height}", file=sys.stderr)
                return None

            # Encode the BGR image to a JPEG format in memory
            ret, buffer = cv2.imencode('.jpg', img_bgr)
            if not ret:
                # print("Error: Failed to encode image to JPEG", file=sys.stderr)
                return None
            
            # Return the JPEG image as a byte string
            return buffer.tobytes()
        except Exception as e:
            # Reduce spam in logs - only print occasionally
            if hasattr(self, '_camera_error_count'):
                self._camera_error_count += 1
                if self._camera_error_count % 10 == 0:  # Print every 10th error
                    print(f"Camera error (#{self._camera_error_count}): {e}", file=sys.stderr)
            else:
                self._camera_error_count = 1
                print(f"Camera error: {e}", file=sys.stderr)
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
        try:
            self.client.takeoffAsync().join()
            print("Takeoff complete.")
            return {"status": "success", "message": "Takeoff completed successfully."}
        except Exception as e:
            if "IOLoop is already running" in str(e):
                print("Using alternative takeoff method due to IOLoop conflict...")
                try:
                    # Use moveToPositionAsync to takeoff
                    current_pose = self.client.simGetVehiclePose()
                    takeoff_z = current_pose.position.z_val - 5  # Go up 5 meters
                    self.client.moveToPositionAsync(
                        current_pose.position.x_val, 
                        current_pose.position.y_val, 
                        takeoff_z, 
                        2
                    ).join()
                    print("Alternative takeoff complete.")
                    return {"status": "success", "message": "Takeoff completed successfully."}
                except Exception as e2:
                    print(f"Takeoff failed: {e2}")
                    return {"status": "error", "message": f"Takeoff failed: {e2}"}
            else:
                print(f"Takeoff failed: {e}")
                return {"status": "error", "message": f"Takeoff failed: {e}"}
        
        return {"status": "success", "message": "Takeoff completed successfully."}

    def land(self):
        print("Landing...")
        try:
            self.client.landAsync().join()
            self.client.armDisarm(False)
            self.is_initialized = False
            print("Landing complete. Drone disarmed.")
        except Exception as e:
            if "IOLoop is already running" in str(e):
                # Handle IOLoop conflict by using synchronous method
                print("Using alternative landing method due to IOLoop conflict...")
                try:
                    # Use moveToPositionAsync to land at current X,Y but lower Z
                    current_pose = self.client.simGetVehiclePose()
                    land_z = current_pose.position.z_val + 10  # Land 10 meters down
                    self.client.moveToPositionAsync(
                        current_pose.position.x_val, 
                        current_pose.position.y_val, 
                        land_z, 
                        1
                    ).join()
                    time.sleep(2)
                    self.client.armDisarm(False)
                    self.is_initialized = False
                    print("Alternative landing complete. Drone disarmed.")
                except Exception as e2:
                    print(f"Landing failed: {e2}")
                    return {"status": "error", "message": f"Landing failed: {e2}"}
            else:
                print(f"Landing failed: {e}")
                return {"status": "error", "message": f"Landing failed: {e}"}
        
        return {"status": "success", "message": "Landing completed successfully."}

    def move_at_velocity(self, vx=0, vy=0, vz=0, duration=1):
        print(f"Moving with velocity (vx={vx}, vy={vy}, vz={vz}) for {duration}s.")
        try:
            self.client.moveByVelocityAsync(vx, vy, vz, duration, airsim.DrivetrainType.MaxDegreeOfFreedom, airsim.YawMode(False, 0)).join()
            time.sleep(0.5)
            self.hover()
            return {"status": "success", "message": f"Movement completed successfully."}
        except Exception as e:
            if "IOLoop is already running" in str(e):
                print("Using alternative movement method due to IOLoop conflict...")
                try:
                    # Calculate target position based on current position and velocity
                    current_pose = self.client.simGetVehiclePose()
                    target_x = current_pose.position.x_val + (vx * duration)
                    target_y = current_pose.position.y_val + (vy * duration)
                    target_z = current_pose.position.z_val + (vz * duration)
                    
                    self.client.moveToPositionAsync(target_x, target_y, target_z, 5).join()
                    time.sleep(0.5)
                    self.hover()
                    return {"status": "success", "message": f"Movement completed successfully."}
                except Exception as e2:
                    print(f"Movement failed: {e2}")
                    return {"status": "error", "message": f"Movement failed: {e2}"}
            else:
                print(f"Movement failed: {e}")
                return {"status": "error", "message": f"Movement failed: {e}"}
                print(f"Movement failed: {e}")
                return {"status": "error", "message": f"Movement failed: {e}"}
        
        return {"status": "success", "message": "Movement completed successfully."}

    def rotate_at_rate(self, yaw_rate=20, duration=1):
        print(f"Rotating at {yaw_rate} deg/s for {duration}s.")
        try:
            self.client.rotateByYawRateAsync(yaw_rate, duration).join()
            time.sleep(0.5)
            self.hover()
        except Exception as e:
            if "IOLoop is already running" in str(e):
                print("Using alternative rotation method due to IOLoop conflict...")
                try:
                    # Calculate target yaw based on current yaw and rate
                    current_pose = self.client.simGetVehiclePose()
                    current_yaw = airsim.to_eularian_angles(current_pose.orientation)[2]
                    target_yaw = current_yaw + (yaw_rate * duration * 3.14159 / 180)  # Convert to radians
                    
                    self.client.rotateToYawAsync(target_yaw * 180 / 3.14159, 5).join()  # Convert back to degrees
                    time.sleep(0.5)
                    self.hover()
                except Exception as e2:
                    print(f"Rotation failed: {e2}")
                    return {"status": "error", "message": f"Rotation failed: {e2}"}
            else:
                print(f"Rotation failed: {e}")
                return {"status": "error", "message": f"Rotation failed: {e}"}
        
        return {"status": "success", "message": "Rotation completed successfully."}

    def hover(self):
        print("Hovering.")
        try:
            self.client.hoverAsync().join()
        except Exception as e:
            if "IOLoop is already running" in str(e):
                print("Using alternative hover method due to IOLoop conflict...")
                try:
                    # Hover by staying at current position
                    current_pose = self.client.simGetVehiclePose()
                    self.client.moveToPositionAsync(
                        current_pose.position.x_val,
                        current_pose.position.y_val,
                        current_pose.position.z_val,
                        1
                    ).join()
                except Exception as e2:
                    print(f"Hover failed: {e2}")
            else:
                print(f"Hover failed: {e}")

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
