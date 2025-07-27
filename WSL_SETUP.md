# WSL Setup Guide for Dronify

This guide explains how to set up Dronify to work with AirSim running on Windows while your Python code runs in WSL (Windows Subsystem for Linux).

## Architecture Overview

```
┌─────────────────┐    Network     ┌─────────────────┐
│                 │   Connection   │                 │
│   WSL Ubuntu    │◄─────────────►│  Windows Host   │
│                 │   Port 41451   │                 │
│  • Python Code │                │  • AirSim       │
│  • Flask API    │                │  • Simulator    │
│  • Web Interface│                │                 │
└─────────────────┘                └─────────────────┘
```

## Prerequisites

1. **Windows 10/11** with WSL2 installed
2. **AirSim** installed and running on Windows
3. **Python 3.7+** installed in WSL
4. **Required Python packages** (see requirements.txt)

## Quick Setup

### 1. Automatic Setup (Recommended)

Use the provided startup script:

```bash
./start_dronify.sh
```

This script will:
- Auto-detect your WSL environment
- Find the Windows host IP address
- Test connectivity to AirSim
- Set environment variables
- Start the Dronify server

### 2. Manual Setup

If you prefer manual configuration:

#### Step 2.1: Find Windows Host IP

In WSL, run:
```bash
# Method 1: Check resolv.conf (WSL2)
grep nameserver /etc/resolv.conf

# Method 2: Check default route
ip route show default
```

#### Step 2.2: Set Environment Variable

```bash
export AIRSIM_HOST="YOUR_WINDOWS_IP_HERE"
# Example: export AIRSIM_HOST="172.20.240.1"
```

#### Step 2.3: Test Connectivity

First, test which IP works with AirSim:

```bash
# Run the connectivity test script
python3 test_connectivity.py
```

This will test multiple IP addresses and show you which one works. Then use the working IP:

```bash
# Test if AirSim port is reachable with the working IP
export AIRSIM_HOST="172.21.176.1"  # Use the IP that worked in the test
timeout 5 bash -c "</dev/tcp/$AIRSIM_HOST/41451"
```

#### Step 2.4: Start Dronify

```bash
python3 app.py
```

## Troubleshooting

### Problem: "Cannot connect to AirSim"

#### Solution 1: Check AirSim is Running
- Make sure AirSim simulator is running on Windows
- Verify it's using the default port (41451)

#### Solution 2: Configure Windows Firewall
Run this command in **PowerShell as Administrator** on Windows:

```powershell
New-NetFirewallRule -DisplayName "AirSim" -Direction Inbound -Protocol TCP -LocalPort 41451 -Action Allow
```

#### Solution 3: Check Network Configuration
In WSL, verify network connectivity:

```bash
# Ping Windows host
ping $AIRSIM_HOST

# Check if port is reachable
telnet $AIRSIM_HOST 41451
```

#### Solution 4: Multiple IP Detection Issue
If auto-detection finds multiple IPs but selects the wrong one:

1. **Run the connectivity test**:
   ```bash
   python3 test_connectivity.py
   ```

2. **Use the working IP from the test results**:
   ```bash
   export AIRSIM_HOST="172.21.176.1"  # Use the IP that showed SUCCESS
   ```

3. **Make it permanent** by adding to your `~/.bashrc`:
   ```bash
   echo 'export AIRSIM_HOST="172.21.176.1"' >> ~/.bashrc
   source ~/.bashrc
   ```

#### Solution 5: Manual IP Configuration
If auto-detection fails, manually set the IP:

1. Find Windows IP address:
   ```cmd
   # In Windows Command Prompt
   ipconfig
   ```

2. Set in WSL:
   ```bash
   export AIRSIM_HOST="192.168.1.100"  # Replace with your IP
   ```

### Problem: "Connection Lost During Operation"

#### Solution: Use Web Interface Reconnect
1. Open web interface at `http://localhost:5000`
2. Enter the correct IP in the "AirSim Host IP" field
3. Click "Reconnect"

### Problem: "Video Feed Not Working"

#### Possible Causes:
- AirSim simulator not running
- Network connectivity issues
- Camera not configured in AirSim

#### Solution:
1. Restart AirSim simulator
2. Check AirSim settings.json for camera configuration
3. Verify network connection using the reconnect feature

## Advanced Configuration

### Persistent Environment Variables

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
# Auto-detect and set AirSim host for WSL
if grep -qE "(Microsoft|WSL)" /proc/version 2>/dev/null; then
    export AIRSIM_HOST=$(grep nameserver /etc/resolv.conf | awk '{print $2}' | head -1)
    echo "AirSim host set to: $AIRSIM_HOST"
fi
```

### Custom AirSim Configuration

Create or modify `~/Documents/AirSim/settings.json` on Windows:

```json
{
    "SeeDocsAt": "https://github.com/Microsoft/AirSim/blob/master/docs/settings.md",
    "SettingsVersion": 1.2,
    "ApiServerPort": 41451,
    "SimMode": "Multirotor",
    "Vehicles": {
        "SimpleFlight": {
            "VehicleType": "SimpleFlight",
            "DefaultVehicleState": "Armed",
            "EnableCollisionPassthrogh": false,
            "EnableCollisions": true,
            "AllowAPIAlways": true,
            "Cameras": {
                "0": {
                    "CameraName": "0",
                    "ImageType": 0,
                    "MotionBlurAmount": 0
                }
            }
        }
    }
}
```

## Using the Web Interface

1. **Start the server**: Run `./start_dronify.sh` or `python3 app.py`
2. **Open browser**: Navigate to `http://localhost:5000`
3. **Check connection**: Status indicator shows AirSim connection state
4. **Control drone**: Use text commands or voice commands
5. **Monitor feed**: Live camera feed from drone
6. **Reconnect if needed**: Use the reconnect feature with custom IP

## API Endpoints

- `GET /` - Web interface
- `GET /api/status` - Connection status and host info
- `POST /command` - Send text commands
- `POST /audio_command` - Send voice commands
- `GET /video_feed` - Live camera stream
- `POST /reconnect` - Reconnect to AirSim with optional host IP

## Network Security Notes

- AirSim API runs on port 41451 (unencrypted)
- Only allow connections from trusted networks
- Consider using VPN for remote access
- The web interface is served on all interfaces (0.0.0.0)

## Performance Tips

1. **Reduce video quality** if network is slow:
   - Modify frame rate in `generate_frames()` function
   - Adjust camera resolution in AirSim settings

2. **Use wired connection** for better stability

3. **Close unnecessary applications** on Windows to reduce resource usage

## Debugging

Enable debug mode by setting environment variable:

```bash
export FLASK_DEBUG=1
python3 app.py
```

Check logs for detailed error messages and connection attempts.
