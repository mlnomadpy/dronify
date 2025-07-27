#!/usr/bin/env python3

"""
Test script to verify Dronify WSL configuration and AirSim connectivity.
Run this before starting the main application to diagnose issues.
"""

import sys
import os
import subprocess
import socket

def test_wsl_detection():
    """Test if WSL environment is detected correctly."""
    print("🔍 Testing WSL Detection...")
    
    try:
        with open('/proc/version', 'r') as f:
            version_info = f.read().lower()
            is_wsl = 'microsoft' in version_info or 'wsl' in version_info
            
        if is_wsl:
            print("✅ WSL environment detected")
            print(f"   Version info: {version_info.strip()}")
            return True
        else:
            print("🐧 Native Linux environment detected")
            return False
    except Exception as e:
        print(f"❌ Error checking WSL: {e}")
        return False

def get_windows_host_ip():
    """Get the Windows host IP address."""
    print("\n🔍 Finding Windows Host IP...")
    
    methods = []
    
    # Method 1: /etc/resolv.conf
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                if line.startswith('nameserver'):
                    ip = line.split()[1]
                    methods.append(('resolv.conf', ip))
                    break
    except:
        pass
    
    # Method 2: ip route
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'default via' in line:
                    ip = line.split('default via')[1].split()[0]
                    methods.append(('ip route', ip))
                    break
    except:
        pass
    
    # Method 3: Environment variable
    wsl_host = os.environ.get('WSL_HOST_IP')
    if wsl_host:
        methods.append(('WSL_HOST_IP env var', wsl_host))
    
    if methods:
        print("📡 Found potential host IPs:")
        for method, ip in methods:
            print(f"   {method}: {ip}")
        return methods[0][1]  # Return first found IP
    else:
        fallback_ip = "172.20.240.1"
        print(f"⚠️  Using fallback IP: {fallback_ip}")
        return fallback_ip

def test_connectivity(host_ip, port=41451):
    """Test connectivity to AirSim port."""
    print(f"\n🔍 Testing connectivity to {host_ip}:{port}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)  # 5 second timeout
        result = sock.connect_ex((host_ip, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Successfully connected to {host_ip}:{port}")
            return True
        else:
            print(f"❌ Cannot connect to {host_ip}:{port}")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_airsim_import():
    """Test if AirSim Python package can be imported."""
    print("\n🔍 Testing AirSim Python package...")
    
    try:
        import airsim
        print("✅ AirSim package imported successfully")
        print(f"   Version: {getattr(airsim, '__version__', 'Unknown')}")
        return True
    except ImportError as e:
        print(f"❌ Cannot import AirSim: {e}")
        print("   Install with: pip install airsim")
        return False
    except Exception as e:
        print(f"❌ Error importing AirSim: {e}")
        return False

def test_requirements():
    """Test if required packages are available."""
    print("\n🔍 Testing required packages...")
    
    required_packages = [
        ('flask', 'Flask'),
        ('transformers', 'Transformers'),
        ('vosk', 'Vosk'),
        ('pydub', 'PyDub'),
        ('numpy', 'NumPy'),
        ('cv2', 'OpenCV')
    ]
    
    all_ok = True
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} - Install with: pip install {package}")
            all_ok = False
        except Exception as e:
            print(f"⚠️  {name} - Warning: {e}")
    
    return all_ok

def main():
    """Main test function."""
    print("🚁 Dronify Environment Test")
    print("=" * 40)
    
    # Test WSL detection
    is_wsl = test_wsl_detection()
    
    # Test package imports
    packages_ok = test_requirements()
    airsim_ok = test_airsim_import()
    
    # Test network connectivity if in WSL
    connectivity_ok = True
    if is_wsl:
        host_ip = get_windows_host_ip()
        connectivity_ok = test_connectivity(host_ip)
        
        if not connectivity_ok:
            print("\n🔧 Troubleshooting Tips:")
            print("1. Make sure AirSim is running on Windows")
            print("2. Run this PowerShell command as Administrator on Windows:")
            print("   New-NetFirewallRule -DisplayName 'AirSim' -Direction Inbound -Protocol TCP -LocalPort 41451 -Action Allow")
            print("3. Check your Windows Defender Firewall settings")
            print("4. Try setting a custom IP: export AIRSIM_HOST='your.ip.here'")
    
    # Summary
    print("\n📋 Test Summary:")
    print("=" * 40)
    print(f"WSL Detection: {'✅' if is_wsl else '🐧 Native Linux'}")
    print(f"Required Packages: {'✅' if packages_ok else '❌'}")
    print(f"AirSim Package: {'✅' if airsim_ok else '❌'}")
    print(f"Network Connectivity: {'✅' if connectivity_ok else '❌'}")
    
    if packages_ok and airsim_ok and connectivity_ok:
        print("\n🎉 All tests passed! You're ready to run Dronify.")
        print("   Start with: ./start_dronify.sh or python3 app.py")
    else:
        print("\n⚠️  Some tests failed. Please address the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
