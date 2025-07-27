# Vision-Language Integration Guide

## Overview

The Dronify system now includes advanced vision-language capabilities that allow the drone to analyze its camera feed and plan intelligent actions based on both visual input and natural language commands.

## Model Architecture

- **Vision-Language Model**: LLaVA-1.5-7B (Large Language and Vision Assistant)
- **Text Classification**: BART-large-mnli for simple command mapping
- **Speech Recognition**: SpeechRecognition library with Google/Sphinx backends

## Key Features

### 🎯 Vision-Guided Navigation
- Analyze camera feed to identify landmarks, obstacles, and targets
- Plan safe navigation paths based on visual information
- Execute multi-step actions automatically

### 🧠 Intelligent Action Planning  
- Understand complex commands like "navigate to the red building"
- Break down high-level tasks into executable drone actions
- Provide reasoning for planned actions

### 👁️ Real-time Scene Analysis
- Process live camera feed for decision making
- Identify objects, obstacles, and safe areas
- Adapt flight patterns based on environment

## New Command Types

### Vision-Guided Commands
These commands analyze the current camera feed to plan actions:

- `navigate to [target]` - Navigate towards visible targets
- `avoid obstacles and move [direction]` - Safe movement with obstacle avoidance  
- `search for [object]` - Rotate and move to locate objects
- `follow [object]` - Track moving objects while maintaining distance
- `inspect [area]` - Examine areas from multiple angles
- `land in the safest spot visible` - Find optimal landing location

### Enhanced Movement Commands
Traditional commands now support parameters:

- `move forward [distance] [duration]` - Parameterized movement
- `rotate left [angle] [duration]` - Precise rotation control

## API Endpoints

### Vision Command Endpoints

#### POST `/vision_command`
Execute vision-guided text commands.

**Request:**
```json
{
    "command": "navigate to the red building",
    "use_current_image": true
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Vision-guided command executed",
    "original_command": "navigate to the red building", 
    "reasoning": "I can see a red building to the right. I'll move forward and right to approach it safely.",
    "planned_actions": [
        {"action": "move forward", "parameters": {"distance": 3, "duration": 2}},
        {"action": "move right", "parameters": {"distance": 2, "duration": 1}},
        {"action": "hover", "parameters": {}}
    ],
    "execution_results": [...],
    "confidence": 0.85
}
```

#### POST `/audio_vision_command`
Execute vision-guided voice commands.

**Request:** Multipart form with `audio` file
**Response:** Same as `/vision_command` plus `transcribed_text`

## Web Interface Updates

### Vision Command Panel
- Text input for vision commands
- Quick action buttons for common vision tasks
- Real-time status indicators

### Vision Voice Recording
- Separate button for vision-guided voice commands
- Visual indicators for recording state
- Integration with camera feed analysis

## System Requirements

### Minimum Requirements
- **RAM**: 8GB (16GB recommended)
- **Storage**: 15GB free space for model cache
- **CPU**: Multi-core processor (Intel i5 or AMD equivalent)

### Recommended for Best Performance
- **GPU**: NVIDIA GPU with 6GB+ VRAM (RTX 3060 or better)
- **CUDA**: Version 11.8 or higher
- **RAM**: 16GB or more

## Installation and Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Download and Test Vision Model
```bash
python setup_vision_model.py
```

This script will:
- Check system requirements
- Download LLaVA-1.5-7B model (~13GB)
- Test model functionality
- Provide performance recommendations

### 3. Start the Application
```bash
python app.py
```

The vision model will load automatically on startup.

## Performance Optimization

### GPU Mode (Recommended)
- Automatic if CUDA available
- ~2-3 second response time
- Better accuracy and reasoning

### CPU Mode (Fallback)
- Used when no GPU available
- ~10-15 second response time
- Still functional but slower

### Memory Management
- Model uses ~6-8GB VRAM (GPU) or ~8-12GB RAM (CPU)
- Automatic memory optimization
- Graceful fallback to text-only mode if model fails

## Usage Examples

### Web Interface
1. Navigate to the vision command panel
2. Enter command: "navigate to the building and inspect the area"
3. Click "Send Vision Command"
4. Watch as the drone analyzes the scene and executes planned actions

### API Usage
```python
import requests

# Send vision command
response = requests.post('http://localhost:5000/vision_command', 
    json={'command': 'search for people and maintain safe distance'})

result = response.json()
print(f"Reasoning: {result['reasoning']}")
print(f"Actions planned: {len(result['planned_actions'])}")
```

### Voice Commands
1. Click "Vision Voice" button
2. Speak: "Fly towards the red car but avoid hitting anything"
3. System will transcribe speech and analyze camera feed
4. Drone executes intelligent action sequence

## Safety Features

### Obstacle Avoidance
- Visual obstacle detection and avoidance
- Safety distance maintenance
- Automatic hover on safety concerns

### Confidence Scoring
- Each vision analysis includes confidence score
- Low confidence commands require confirmation
- Fallback to manual control when needed

### Error Handling
- Graceful degradation to text-only mode
- Automatic retry on network issues
- Clear error messages and recovery suggestions

## Troubleshooting

### Model Won't Load
- Check available RAM/VRAM
- Ensure stable internet for initial download
- Try CPU mode: set `CUDA_VISIBLE_DEVICES=""`

### Slow Performance
- Use GPU if available
- Close other applications to free memory
- Consider using smaller batch sizes

### Vision Analysis Errors
- Ensure camera feed is working
- Check lighting conditions
- Verify AirSim connection

## Advanced Configuration

### Custom Prompts
Modify vision prompts in `airsim_controller.py`:

```python
def analyze_scene_and_plan(self, text_command, image_data=None):
    prompt = f"""<image>
    USER: Custom system prompt here...
    Command: {text_command}
    
    A: """
```

### Model Parameters
Adjust generation parameters for different behavior:

```python
output = self.vl_model.generate(
    **inputs,
    max_new_tokens=512,        # Longer responses
    temperature=0.1,           # More deterministic  
    do_sample=True,           # Enable sampling
)
```

## Future Enhancements

- [ ] Object tracking and following
- [ ] Multiple drone coordination
- [ ] Custom object detection training
- [ ] Integration with mapping systems
- [ ] Advanced path planning algorithms

## Contributing

To contribute to vision-language features:

1. Test with different environments
2. Report edge cases and failures  
3. Suggest new command types
4. Optimize prompts for better accuracy
5. Add safety checks and validations

## Support

For vision-related issues:
- Check GPU drivers and CUDA installation
- Monitor memory usage during operation
- Test with simpler commands first
- Review logs for detailed error messages
