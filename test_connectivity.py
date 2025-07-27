#!/usr/bin/env python3

"""
Quick diagnostic script to test AirSim connectivity with different IPs
"""

import socket
import time

def test_connection(ip, port=41451, timeout=3):
    """Test socket connection to given IP and port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start_time = time.time()
        result = sock.connect_ex((ip, port))
        end_time = time.time()
        sock.close()
        
        if result == 0:
            print(f"✅ {ip}:{port} - SUCCESS ({end_time-start_time:.2f}s)")
            return True
        else:
            print(f"❌ {ip}:{port} - FAILED (Error code: {result})")
            return False
    except Exception as e:
        print(f"❌ {ip}:{port} - EXCEPTION: {e}")
        return False

def main():
    print("🔍 Testing AirSim Connectivity")
    print("=" * 40)
    
    # Test the detected IPs
    test_ips = [
        "10.255.255.254",  # From resolv.conf
        "172.21.176.1",   # From ip route
        "127.0.0.1",      # Localhost (if running locally)
        "192.168.1.1",    # Common router IP
        "192.168.0.1",    # Common router IP
    ]
    
    successful_ips = []
    
    for ip in test_ips:
        if test_connection(ip):
            successful_ips.append(ip)
    
    print("\n📋 Results:")
    print("=" * 40)
    
    if successful_ips:
        print(f"✅ Found {len(successful_ips)} working IP(s):")
        for ip in successful_ips:
            print(f"   {ip}")
        print(f"\n💡 Recommended: Use 'export AIRSIM_HOST=\"{successful_ips[0]}\"'")
    else:
        print("❌ No working IPs found!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Make sure AirSim simulator is running on Windows")
        print("2. Run this PowerShell command as Administrator on Windows:")
        print("   New-NetFirewallRule -DisplayName 'AirSim' -Direction Inbound -Protocol TCP -LocalPort 41451 -Action Allow")
        print("3. Check Windows Defender Firewall settings")
        print("4. Find your Windows IP manually:")
        print("   - Open Command Prompt on Windows")
        print("   - Run: ipconfig")
        print("   - Look for your network adapter's IPv4 address")

if __name__ == "__main__":
    main()
