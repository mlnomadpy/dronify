#!/bin/bash

# Dronify Startup Script for WSL Environment
# This script helps set up the environment for running Dronify in WSL with AirSim on Windows

echo "🚁 Dronify WSL Setup and Startup Script"
echo "======================================"

# Function to detect WSL
is_wsl() {
    if grep -qE "(Microsoft|WSL)" /proc/version &>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to get Windows host IP
get_windows_host_ip() {
    # Try to get IP from /etc/resolv.conf (WSL2)
    if [ -f /etc/resolv.conf ]; then
        HOST_IP=$(grep nameserver /etc/resolv.conf | awk '{print $2}' | head -1)
        if [ ! -z "$HOST_IP" ]; then
            echo "$HOST_IP"
            return 0
        fi
    fi
    
    # Try to get IP from ip route
    HOST_IP=$(ip route show default | awk '/default/ {print $3}' | head -1)
    if [ ! -z "$HOST_IP" ]; then
        echo "$HOST_IP"
        return 0
    fi
    
    # Fallback
    echo "172.20.240.1"
}

# Check if running in WSL
if is_wsl; then
    echo "✅ WSL environment detected"
    
    # Get Windows host IP
    WINDOWS_HOST_IP=$(get_windows_host_ip)
    echo "🖥️  Windows host IP detected: $WINDOWS_HOST_IP"
    
    # Export environment variable
    export AIRSIM_HOST="$WINDOWS_HOST_IP"
    echo "🔧 Set AIRSIM_HOST environment variable to: $AIRSIM_HOST"
    
    # Test connectivity to AirSim port
    echo "🔍 Testing connectivity to AirSim..."
    if timeout 5 bash -c "</dev/tcp/$WINDOWS_HOST_IP/41451" 2>/dev/null; then
        echo "✅ AirSim is reachable at $WINDOWS_HOST_IP:41451"
    else
        echo "❌ Cannot reach AirSim at $WINDOWS_HOST_IP:41451"
        echo ""
        echo "Troubleshooting steps:"
        echo "1. Make sure AirSim is running on Windows"
        echo "2. Check Windows Firewall settings"
        echo "3. Run this PowerShell command as Administrator on Windows:"
        echo "   New-NetFirewallRule -DisplayName 'AirSim' -Direction Inbound -Protocol TCP -LocalPort 41451 -Action Allow"
        echo "4. If using a different IP, set it manually:"
        echo "   export AIRSIM_HOST='your.custom.ip.here'"
        echo ""
    fi
else
    echo "🐧 Native Linux environment detected"
    echo "💡 AirSim should be running locally on 127.0.0.1"
fi

echo ""
echo "🚀 Starting Dronify server..."
echo "📱 Web interface will be available at: http://localhost:5000"
echo "🔗 API endpoints available at: http://localhost:5000/api/status"
echo ""

# Start the Flask application
python3 app.py
