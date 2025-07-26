// Global variables
let isRecording = false;
let mediaRecorder;
let audioChunks = [];

// Initialize the app when the page loads
document.addEventListener('DOMContentLoaded', function() {
    checkConnectionStatus();
    setupEventListeners();
    
    // Check connection status every 30 seconds
    setInterval(checkConnectionStatus, 30000);
});

// Set up event listeners
function setupEventListeners() {
    // Enter key for text command input
    document.getElementById('text-command').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendTextCommand();
        }
    });
}

// Check API connection status
async function checkConnectionStatus() {
    try {
        const response = await fetch('/api/status');
        if (response.ok) {
            const data = await response.json();
            updateConnectionStatus(data.airsim_connection === 'Connected', data.airsim_connection);
        } else {
            updateConnectionStatus(false, 'API Error');
        }
    } catch (error) {
        updateConnectionStatus(false, 'Connection Failed');
    }
}

// Update connection status display
function updateConnectionStatus(isConnected, statusText) {
    const statusElement = document.getElementById('connection-status');
    const statusContainer = document.getElementById('status');
    
    statusElement.textContent = statusText;
    
    if (isConnected) {
        statusContainer.className = 'status connected';
    } else {
        statusContainer.className = 'status disconnected';
    }
}

// Show video error message
function showVideoError() {
    document.getElementById('video-feed').style.display = 'none';
    document.getElementById('video-error').style.display = 'block';
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
