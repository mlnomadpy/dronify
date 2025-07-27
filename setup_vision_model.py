#!/usr/bin/env python3
"""
Setup script for downloading and testing the vision-language model.
This script helps ensure the LLaVA model is properly downloaded and cached
before running the main application.
"""

import torch
import os
from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
import psutil
import time

def check_system_requirements():
    """Check if system meets minimum requirements for vision model."""
    print("🔍 Checking system requirements...")
    
    # Check RAM
    ram_gb = psutil.virtual_memory().total / (1024**3)
    print(f"   RAM: {ram_gb:.1f} GB")
    
    if ram_gb < 8:
        print("   ⚠️  Warning: Less than 8GB RAM detected. Model may run slowly.")
    
    # Check GPU
    if torch.cuda.is_available():
        gpu_count = torch.cuda.device_count()
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            gpu_memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            print(f"   GPU {i}: {gpu_name} ({gpu_memory:.1f} GB)")
        
        if gpu_memory < 6:
            print("   ⚠️  Warning: GPU has less than 6GB VRAM. Consider using CPU mode.")
    else:
        print("   CPU: CUDA not available, will use CPU mode")
    
    return True

def download_and_test_model():
    """Download and test the vision-language model."""
    print("\n📥 Downloading LLaVA-1.5-7B model...")
    print("   This may take several minutes on first run...")
    
    start_time = time.time()
    
    try:
        # Determine device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"   Using device: {device}")
        
        # Load model
        model_id = "llava-hf/llava-1.5-7b-hf"
        print(f"   Loading processor from {model_id}...")
        processor = LlavaNextProcessor.from_pretrained(model_id)
        
        print(f"   Loading model from {model_id}...")
        model = LlavaNextForConditionalGeneration.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
            device_map="auto" if torch.cuda.is_available() else None
        )
        
        if not torch.cuda.is_available():
            model.to(device)
        
        download_time = time.time() - start_time
        print(f"   ✅ Model loaded successfully in {download_time:.1f}s")
        
        # Test with a simple prompt
        print("\n🧪 Testing model with sample prompt...")
        
        # Create a simple test image (solid color)
        from PIL import Image
        import numpy as np
        
        test_image = Image.fromarray(
            np.full((224, 224, 3), 128, dtype=np.uint8)
        )
        
        prompt = """<image>
USER: What do you see in this image? Respond briefly.

A: """
        
        inputs = processor(prompt, test_image, return_tensors="pt").to(device)
        
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=True,
                temperature=0.3,
                pad_token_id=processor.tokenizer.eos_token_id
            )
        
        response = processor.decode(output[0], skip_special_tokens=True)
        print(f"   Model response: {response[-100:]}")  # Show last 100 chars
        
        print("   ✅ Model test completed successfully!")
        
        # Memory usage
        if torch.cuda.is_available():
            memory_used = torch.cuda.memory_allocated(device) / (1024**3)
            print(f"   GPU memory used: {memory_used:.1f} GB")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error loading model: {e}")
        print("\n💡 Troubleshooting tips:")
        print("   - Ensure you have stable internet connection")
        print("   - Try running: pip install --upgrade transformers torch")
        print("   - For GPU issues, check CUDA installation")
        return False

def main():
    """Main setup function."""
    print("🚁 Dronify Vision-Language Model Setup")
    print("=" * 45)
    
    # Check requirements
    if not check_system_requirements():
        print("❌ System requirements not met")
        return False
    
    # Download and test model
    if not download_and_test_model():
        print("❌ Model setup failed")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start AirSim simulator")
    print("2. Run: python app.py")
    print("3. Open http://localhost:5000 in your browser")
    print("4. Try vision-guided commands like:")
    print("   - 'Navigate to the building'")
    print("   - 'Avoid obstacles and move forward'")
    print("   - 'Search for people'")
    
    return True

if __name__ == "__main__":
    main()
