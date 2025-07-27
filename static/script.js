// Global variables
let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let videoRetryCount = 0;
let maxVideoRetries = 3;
let videoFeedCheckInterval;

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', function() {
    checkConnectionStatus();
    setupEventListeners();
    initializeVideoFeed();
    
    // Check connection status every 30 seconds
    setInterval(checkConnectionStatus, 30000);
    
    // Monitor video feed health every 10 seconds
    videoFeedCheckInterval = setInterval(checkVideoFeedHealth, 10000);
});

// Initialize video feed monitoring
function initializeVideoFeed() {
    const videoFeed = document.getElementById('video-feed');
    let lastLoadTime = Date.now();
    
    // Update video resolution info when image loads
    videoFeed.onload = function() {
        hideVideoError();
        updateVideoInfo(this.naturalWidth, this.naturalHeight);
        updateFeedStatus('LIVE', false);
        videoRetryCount = 0; // Reset retry count on successful load
        lastLoadTime = Date.now(); // Update last successful load time
    };
    
    // Handle video feed errors
    videoFeed.onerror = function() {
        showVideoError();
        updateFeedStatus('ERROR', true);
        
        // Auto-retry after delay
        if (videoRetryCount < maxVideoRetries) {
            setTimeout(() => {
                videoRetryCount++;
                addLogEntry('info', 'Video Feed', `Auto-retry attempt ${videoRetryCount}/${maxVideoRetries}`);
                refreshVideoFeed();
            }, 3000 + (videoRetryCount * 2000)); // Increasing delay
        } else {
            addLogEntry('error', 'Video Feed', 'Maximum retry attempts reached. Use manual refresh.');
        }
    };
    
    // Monitor for stalled video feed (when image doesn't refresh)
    setInterval(() => {
        const timeSinceLastLoad = Date.now() - lastLoadTime;
        
        // If no new frame for more than 15 seconds, consider it stalled
        if (timeSinceLastLoad > 15000 && videoRetryCount < maxVideoRetries) {
            addLogEntry('warning', 'Video Feed', 'Feed appears stalled, attempting refresh...');
            refreshVideoFeed();
            lastLoadTime = Date.now(); // Prevent multiple rapid refreshes
        }
    }, 10000); // Check every 10 seconds
}

// Set up event listeners
function setupEventListeners() {
    // Enter key for text command input
    document.getElementById('text-command').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendTextCommand();
        }
    });
    
    // Enter key for vision command input
    document.getElementById('vision-command').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendVisionCommand();
        }
    });
    
    // Enter key for host IP input
    document.getElementById('host-ip-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            reconnectAirSim();
        }
    });
}

// Check API connection status
async function checkConnectionStatus() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const data = await response.json();
            const isConnected = data.airsim_connection === 'Connected';
            const hasVisionModel = data.vision_language_model || false;
            updateConnectionStatus(isConnected, data.airsim_connection, data.airsim_host, hasVisionModel);
        } else {
            updateConnectionStatus(false, 'API Error', 'Unknown', false);
        }
    } catch (error) {
        updateConnectionStatus(false, 'Connection Failed', 'Unknown', false);
    }
}

// Update connection status display
function updateConnectionStatus(isConnected, statusText, hostIp, hasVisionModel) {
    const statusElement = document.getElementById('connection-status');
    const statusContainer = document.getElementById('status');
    const hostInfo = document.getElementById('host-info');
    const airSimHost = document.getElementById('airsim-host');
    
    // Update main status
    statusElement.textContent = statusText;
    
    // Update host info
    if (hostIp && hostIp !== 'Unknown') {
        let hostText = hostIp;
        if (hasVisionModel) {
            hostText += ' | Vision-AI: ✅';
        } else {
            hostText += ' | Vision-AI: ❌';
        }
        airSimHost.textContent = hostText;
        hostInfo.style.display = 'block';
    } else {
        hostInfo.style.display = 'none';
    }
    
    // Update connection styling
    if (isConnected) {
        statusContainer.className = 'status connected';
    } else {
        statusContainer.className = 'status disconnected';
    }
    
    // Enable/disable vision features based on model availability
    updateVisionFeatureAvailability(hasVisionModel);
}

// Update vision feature availability in UI
function updateVisionFeatureAvailability(hasVisionModel) {
    const visionPanel = document.querySelector('.control-panel:has(#vision-command)');
    const visionRecordBtn = document.getElementById('vision-record-btn');
    const visionCommandInput = document.getElementById('vision-command');
    
    if (visionPanel) {
        if (hasVisionModel) {
            visionPanel.style.opacity = '1';
            visionPanel.style.pointerEvents = 'auto';
            if (visionRecordBtn) visionRecordBtn.disabled = false;
            if (visionCommandInput) visionCommandInput.disabled = false;
        } else {
            visionPanel.style.opacity = '0.5';
            visionPanel.style.pointerEvents = 'none';
            if (visionRecordBtn) visionRecordBtn.disabled = true;
            if (visionCommandInput) visionCommandInput.disabled = true;
        }
    }
}

// Reconnect to AirSim
async function reconnectAirSim() {
    const hostInput = document.getElementById('host-ip-input');
    const hostIp = hostInput.value.trim();
    
    addLogEntry('info', 'Reconnecting', 'Attempting to reconnect to AirSim...');
    
    try {
        const response = await fetch('/reconnect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ host_ip: hostIp || null })
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            addLogEntry('success', 'Reconnection', `Successfully connected to AirSim at ${result.host_ip}`);
            // Clear the input field on successful connection
            hostInput.value = '';
            // Refresh connection status
            checkConnectionStatus();
        } else {
            addLogEntry('error', 'Reconnection', result.message || 'Failed to reconnect to AirSim');
        }
    } catch (error) {
        addLogEntry('error', 'Reconnection', `Network error: ${error.message}`);
    }
}

// Show video error message
function showVideoError() {
    document.getElementById('video-feed').style.display = 'none';
    document.getElementById('video-error').style.display = 'flex';
}

// Hide video error message
function hideVideoError() {
    document.getElementById('video-feed').style.display = 'block';
    document.getElementById('video-error').style.display = 'none';
}

// Refresh video feed
function refreshVideoFeed() {
    const videoFeed = document.getElementById('video-feed');
    const timestamp = new Date().getTime();
    
    // Add timestamp to prevent caching issues
    videoFeed.src = `/video_feed?t=${timestamp}`;
    
    updateFeedStatus('CONNECTING...', false);
    addLogEntry('info', 'Video Feed', 'Refreshing camera feed...');
}

// Refresh camera connection
async function refreshCamera() {
    updateFeedStatus('REFRESHING...', false);
    addLogEntry('info', 'Camera', 'Refreshing camera connection...');
    
    try {
        const response = await fetch('/refresh_camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            addLogEntry('success', 'Camera', 'Camera connection refreshed successfully');
            // Refresh the video feed after successful camera refresh
            setTimeout(() => {
                refreshVideoFeed();
            }, 1000);
        } else {
            addLogEntry('error', 'Camera', result.message || 'Failed to refresh camera');
            updateFeedStatus('ERROR', true);
        }
    } catch (error) {
        addLogEntry('error', 'Camera', `Network error: ${error.message}`);
        updateFeedStatus('ERROR', true);
    }
}

// Update video feed status
function updateFeedStatus(statusText, isError) {
    const statusTextElement = document.getElementById('feed-status-text');
    const indicator = document.getElementById('feed-indicator');
    
    statusTextElement.textContent = statusText;
    
    if (isError) {
        indicator.classList.add('error');
    } else {
        indicator.classList.remove('error');
    }
}

// Update video information
function updateVideoInfo(width, height) {
    const videoResolution = document.getElementById('video-resolution');
    videoResolution.textContent = `${width} × ${height}`;
}

// Check video feed health
function checkVideoFeedHealth() {
    const videoFeed = document.getElementById('video-feed');
    const videoError = document.getElementById('video-error');
    
    // If error is showing and we haven't exceeded retry limit, try refreshing
    if (videoError.style.display !== 'none' && videoRetryCount < maxVideoRetries) {
        refreshVideoFeed();
    }
}

// Refresh camera connection
async function refreshCamera() {
    updateFeedStatus('REFRESHING...', false);
    addLogEntry('info', 'Camera Refresh', 'Refreshing camera connection...');
    
    try {
        const response = await fetch('/refresh_camera', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            addLogEntry('success', 'Camera Refresh', result.message);
            // Reset retry count and refresh video feed
            videoRetryCount = 0;
            setTimeout(() => {
                refreshVideoFeed();
            }, 1000);
        } else {
            addLogEntry('error', 'Camera Refresh', result.message || 'Failed to refresh camera');
            updateFeedStatus('ERROR', true);
        }
    } catch (error) {
        addLogEntry('error', 'Camera Refresh', `Network error: ${error.message}`);
        updateFeedStatus('ERROR', true);
    }
}

// Send text command
async function sendTextCommand() {
    const commandInput = document.getElementById('text-command');
    const command = commandInput.value.trim();
    
    if (!command) {
        addLogEntry('error', 'Empty Command', 'Please enter a command');
        return;
    }
    
    commandInput.value = '';
    addLogEntry('info', `Command: ${command}`, 'Sending...');
    
    try {
        const response = await fetch('/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command })
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            addLogEntry('success', `Command: ${command}`, result.message || 'Command executed successfully');
        } else {
            addLogEntry('error', `Command: ${command}`, result.message || 'Command failed');
        }
    } catch (error) {
        addLogEntry('error', `Command: ${command}`, `Network error: ${error.message}`);
    }
}

// Send quick command
function sendQuickCommand(command) {
    document.getElementById('text-command').value = command;
    sendTextCommand();
}

// Send vision-guided text command
async function sendVisionCommand() {
    const commandInput = document.getElementById('vision-command');
    const command = commandInput.value.trim();
    
    if (!command) {
        addLogEntry('error', 'Vision Command', 'Please enter a vision command');
        return;
    }
    
    addLogEntry('info', 'Vision Command', `Analyzing scene and executing: "${command}"`);
    
    try {
        const response = await fetch('/vision_command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command: command, use_current_image: true })
        });
        
        const result = await response.json();
        
        if (result.status === 'success' || result.status === 'partial') {
            let message = result.message;
            if (result.reasoning) {
                message += `\nReasoning: ${result.reasoning}`;
            }
            if (result.planned_actions && result.planned_actions.length > 0) {
                message += `\nActions executed: ${result.planned_actions.length}`;
            }
            addLogEntry('success', 'Vision Command', message);
        } else {
            addLogEntry('error', 'Vision Command', result.message || 'Command failed');
        }
        
        commandInput.value = '';
        
    } catch (error) {
        addLogEntry('error', 'Vision Command', 'Network error: ' + error.message);
    }
}

// Send quick vision command
function sendQuickVisionCommand(command) {
    document.getElementById('vision-command').value = command;
    sendVisionCommand();
}

// Vision recording variables
let isVisionRecording = false;
let visionMediaRecorder;
let visionAudioChunks = [];

// Toggle vision voice recording
async function toggleVisionRecording() {
    if (!isVisionRecording) {
        await startVisionRecording();
    } else {
        await stopVisionRecording();
    }
}

// Start vision voice recording
async function startVisionRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        visionMediaRecorder = new MediaRecorder(stream);
        visionAudioChunks = [];
        
        visionMediaRecorder.ondataavailable = event => {
            visionAudioChunks.push(event.data);
        };
        
        visionMediaRecorder.onstop = () => {
            const audioBlob = new Blob(visionAudioChunks, { type: 'audio/wav' });
            sendVisionAudioCommand(audioBlob);
        };
        
        visionMediaRecorder.start();
        isVisionRecording = true;
        
        // Update UI
        document.getElementById('vision-record-btn').textContent = '🛑 Stop Vision Recording';
        document.getElementById('vision-recording-status').style.display = 'block';
        document.getElementById('recording-status').style.display = 'none'; // Hide regular recording
        
        addLogEntry('info', 'Vision Voice', 'Recording started for vision analysis...');
        
    } catch (error) {
        addLogEntry('error', 'Vision Voice', 'Could not access microphone: ' + error.message);
    }
}

// Stop vision voice recording
async function stopVisionRecording() {
    if (visionMediaRecorder && isVisionRecording) {
        visionMediaRecorder.stop();
        isVisionRecording = false;
        
        // Update UI
        document.getElementById('vision-record-btn').textContent = '🎤👁️ Vision Voice';
        document.getElementById('vision-recording-status').style.display = 'none';
        
        // Stop all audio tracks
        visionMediaRecorder.stream.getTracks().forEach(track => track.stop());
        
        addLogEntry('info', 'Vision Voice', 'Recording stopped, processing with vision analysis...');
    }
}

// Send vision audio command
async function sendVisionAudioCommand(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'vision_command.wav');
    
    addLogEntry('info', 'Vision Voice', 'Analyzing audio and camera feed...');
    
    try {
        const response = await fetch('/audio_vision_command', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success' || result.status === 'partial') {
            let message = `Transcribed: "${result.transcribed_text}"`;
            if (result.reasoning) {
                message += `\nReasoning: ${result.reasoning}`;
            }
            if (result.planned_actions && result.planned_actions.length > 0) {
                message += `\nActions executed: ${result.planned_actions.length}`;
            }
            addLogEntry('success', 'Vision Voice', message);
        } else {
            let errorMsg = result.message || 'Command failed';
            if (result.transcribed_text) {
                errorMsg = `Transcribed: "${result.transcribed_text}" - ${errorMsg}`;
            }
            addLogEntry('error', 'Vision Voice', errorMsg);
        }
        
    } catch (error) {
        addLogEntry('error', 'Vision Voice', 'Network error: ' + error.message);
    }
}

// Toggle voice recording
async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

// Start voice recording
async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await sendAudioCommand(audioBlob);
            
            // Stop all tracks to release the microphone
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        isRecording = true;
        
        updateRecordingUI(true);
        addLogEntry('info', 'Voice Recording', 'Recording started... Speak your command');
        
    } catch (error) {
        addLogEntry('error', 'Voice Recording', `Microphone access denied: ${error.message}`);
        console.error('Error accessing microphone:', error);
    }
}

// Stop voice recording
async function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        updateRecordingUI(false);
        addLogEntry('info', 'Voice Recording', 'Processing audio command...');
    }
}

// Update recording UI
function updateRecordingUI(recording) {
    const recordBtn = document.getElementById('record-btn');
    const recordingStatus = document.getElementById('recording-status');
    
    if (recording) {
        recordBtn.textContent = '⏹️ Stop Recording';
        recordBtn.classList.add('recording');
        recordingStatus.style.display = 'block';
    } else {
        recordBtn.textContent = '🎤 Start Recording';
        recordBtn.classList.remove('recording');
        recordingStatus.style.display = 'none';
    }
}

// Send audio command
async function sendAudioCommand(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'command.wav');
    
    try {
        const response = await fetch('/audio_command', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            const transcribed = result.transcribed_text || 'Unknown';
            const command = result.interpreted_command || 'Unknown';
            
            addLogEntry('success', 
                `Voice Command: "${transcribed}" → ${command}`, 
                result.message || 'Command executed successfully'
            );
        } else {
            const transcribed = result.transcribed_text || 'Could not transcribe';
            addLogEntry('error', 
                `Voice Command: "${transcribed}"`, 
                result.message || 'Command failed'
            );
        }
    } catch (error) {
        addLogEntry('error', 'Voice Command', `Network error: ${error.message}`);
    }
}

// Add entry to the log
function addLogEntry(type, command, response) {
    const logContainer = document.getElementById('log-container');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    
    entry.innerHTML = `
        <div class="log-time">${timeString}</div>
        <div class="log-content">
            <div class="log-command">${command}</div>
            <div class="log-response">${response}</div>
        </div>
    `;
    
    // Remove welcome message if it's the first real entry
    const welcomeEntry = logContainer.querySelector('.log-entry.welcome');
    if (welcomeEntry && logContainer.children.length === 1) {
        welcomeEntry.remove();
    }
    
    logContainer.appendChild(entry);
    
    // Auto-scroll to bottom
    logContainer.scrollTop = logContainer.scrollHeight;
    
    // Limit log entries to prevent memory issues
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// Utility function to format JSON responses nicely
function formatResponse(response) {
    if (typeof response === 'object') {
        return JSON.stringify(response, null, 2);
    }
    return response;
}
