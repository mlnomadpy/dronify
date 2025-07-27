#!/usr/bin/env python3
"""
Simple test script to check if the camera is working with AirSim.
Run this to diagnose camera issues.
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from airsim_controller import AirSimController

def test_camera():
    print("🎥 Testing AirSim Camera Functionality")
    print("=" * 50)
    
    # Initialize controller
    print("1. Initializing AirSim Controller...")
    controller = AirSimController()
    
    if not controller.is_connected:
        print("❌ AirSim is not connected!")
        print("Make sure AirSim simulator is running.")
        return False
    
    print(f"✅ Connected to AirSim at {controller.host_ip}")
    
    # Test basic connection
    print("\n2. Testing basic AirSim connection...")
    try:
        state = controller.client.getMultirotorState()
        print(f"✅ Drone state retrieved successfully")
        print(f"   - Landed State: {state.landed_state}")
        position = state.kinematics_estimated.position
        print(f"   - Position: ({position.x_val:.2f}, {position.y_val:.2f}, {position.z_val:.2f})")
    except Exception as e:
        print(f"❌ Failed to get drone state: {e}")
        return False
    
    # Test camera
    print("\n3. Testing Camera...")
    try:
        print("   Requesting camera image...")
        frame = controller.get_camera_image()
        
        if frame is None:
            print("❌ Camera returned None (no image)")
            print("   Possible causes:")
            print("   - Drone not initialized (try 'initialize' command)")
            print("   - AirSim world not loaded properly")
            print("   - Camera not available in current environment")
            return False
        
        print(f"✅ Camera is working!")
        print(f"   - Frame size: {len(frame)} bytes")
        
        # Save test image
        test_image_path = "test_camera_frame.jpg"
        with open(test_image_path, 'wb') as f:
            f.write(frame)
        print(f"   - Test frame saved as: {test_image_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def main():
    success = test_camera()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 Camera test PASSED! Video feed should work.")
        print("\nNext steps:")
        print("1. Start the Flask app: python app.py")
        print("2. Open browser to: http://localhost:5000")
        print("3. The live video feed should now work!")
    else:
        print("💥 Camera test FAILED!")
        print("\nTroubleshooting:")
        print("1. Make sure AirSim simulator is running")
        print("2. Try initializing the drone first:")
        print("   curl -X POST http://localhost:5000/command -H 'Content-Type: application/json' -d '{\"command\": \"initialize\"}'")
        print("3. Check AirSim settings.json for camera configuration")
        print("4. Restart AirSim simulator")
    
    print("\nFor more debugging, check the debug endpoint: http://localhost:5000/debug/camera")

if __name__ == "__main__":
    main()
