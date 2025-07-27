#!/usr/bin/env python3
"""
Test script for the vision-language integration.
This script tests the vision capabilities without requiring AirSim.
"""

import sys
import os
import io
from PIL import Image
import numpy as np
import requests
import json

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_test_image():
    """Create a simple test image with some geometric shapes."""
    # Create a 640x480 RGB image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add a blue sky
    img[:240, :] = [135, 206, 235]  # Sky blue
    
    # Add green ground
    img[240:, :] = [34, 139, 34]   # Forest green
    
    # Add a red rectangle (building)
    img[180:320, 400:550] = [220, 20, 60]  # Crimson red
    
    # Add a yellow circle (sun)
    center = (150, 100)
    radius = 40
    y, x = np.ogrid[:480, :640]
    mask = (x - center[0])**2 + (y - center[1])**2 <= radius**2
    img[mask] = [255, 255, 0]  # Yellow
    
    return Image.fromarray(img)

def test_vision_analysis():
    """Test the vision analysis without AirSim."""
    print("🧪 Testing Vision-Language Analysis")
    print("=" * 40)
    
    try:
        # Import the controller
        from airsim_controller import AirSimController
        
        # Create controller instance (will fail AirSim connection but that's OK)
        print("Creating controller instance...")
        controller = AirSimController()
        
        if not controller.vl_model_available:
            print("❌ Vision-language model not available")
            print("   Run 'python setup_vision_model.py' first")
            return False
        
        print("✅ Vision-language model loaded successfully")
        
        # Create test image
        print("\n🖼️ Creating test image...")
        test_image = create_test_image()
        
        # Convert to bytes (JPEG format)
        img_byte_arr = io.BytesIO()
        test_image.save(img_byte_arr, format='JPEG')
        image_data = img_byte_arr.getvalue()
        
        print(f"   Test image created: {len(image_data)} bytes")
        
        # Test different commands
        test_commands = [
            "Describe what you see in this image",
            "Navigate to the red building",
            "Find a safe place to land",
            "What obstacles should I avoid?"
        ]
        
        print("\n🎯 Testing vision analysis commands...")
        
        for i, command in enumerate(test_commands, 1):
            print(f"\n{i}. Command: '{command}'")
            
            try:
                result = controller.analyze_scene_and_plan(command, image_data)
                
                print(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}...")
                print(f"   Actions planned: {len(result.get('actions', []))}")
                print(f"   Confidence: {result.get('confidence', 0):.2f}")
                
                if result.get('safety_concerns'):
                    print(f"   Safety: {result['safety_concerns'][:50]}...")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        print("\n✅ Vision analysis test completed!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Make sure all dependencies are installed")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints (requires running server)."""
    print("\n🌐 Testing API Endpoints")
    print("=" * 25)
    
    base_url = "http://localhost:5000"
    
    # Test status endpoint
    try:
        print("Testing /api/status...")
        response = requests.get(f"{base_url}/api/status", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ API Status: {data.get('status')}")
            print(f"   AirSim: {data.get('airsim_connection')}")
            print(f"   Vision AI: {'✅' if data.get('vision_language_model') else '❌'}")
        else:
            print(f"   ❌ API Error: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️  Server not running. Start with: python app.py")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test vision command endpoint
    try:
        print("\nTesting /vision_command...")
        test_payload = {
            "command": "Describe what you see",
            "use_current_image": True
        }
        
        response = requests.post(
            f"{base_url}/vision_command", 
            json=test_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Vision command successful")
            print(f"   Message: {result.get('message', 'N/A')}")
        else:
            print(f"   ❌ Vision command failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return True

def main():
    """Main test function."""
    print("🚁 Dronify Vision-Language Test Suite")
    print("=" * 42)
    
    # Test 1: Vision Analysis
    if not test_vision_analysis():
        print("\n❌ Vision analysis test failed")
        return False
    
    # Test 2: API Endpoints (optional)
    print("\n" + "="*50)
    user_input = input("Test API endpoints? (requires server running) [y/N]: ").lower()
    
    if user_input in ['y', 'yes']:
        test_api_endpoints()
    
    print("\n🎉 Test suite completed!")
    print("\nNext steps:")
    print("1. Start AirSim simulator")
    print("2. Run: python app.py") 
    print("3. Open: http://localhost:5000")
    print("4. Try vision commands in the web interface")
    
    return True

if __name__ == "__main__":
    main()
