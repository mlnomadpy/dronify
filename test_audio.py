#!/usr/bin/env python3
"""
Simple test script to debug audio transcription issues.
"""

import sys
import os
import json
from vosk import Model, KaldiRecognizer
from pydub import AudioSegment

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = "/home/skywolfmo/github/dronify/model/vosk-model-small-en-us-0.15"

def test_audio_file(audio_path):
    print(f"🎤 Testing Audio Transcription")
    print("=" * 50)
    
    # Check if model exists
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Vosk model not found at '{MODEL_PATH}'")
        return False
    
    print("✅ Loading Vosk model...")
    vosk_model = Model(MODEL_PATH)
    print("✅ Model loaded successfully")
    
    # Check if audio file exists
    if not os.path.exists(audio_path):
        print(f"❌ Audio file not found: {audio_path}")
        return False
    
    try:
        # Load audio
        print(f"\n📁 Loading audio file: {audio_path}")
        sound = AudioSegment.from_file(audio_path)
        print(f"   Original: {len(sound)}ms, {sound.frame_rate}Hz, {sound.channels} channels")
        
        # Process audio
        sound = sound.set_channels(1)
        sound = sound.set_frame_rate(16000)
        sound = sound.normalize()
        
        # Add some basic noise reduction
        if len(sound) > 0:
            sound = sound.high_pass_filter(80)
        
        print(f"   Processed: {len(sound)}ms, {sound.frame_rate}Hz, {sound.channels} channels")
        
        # Check audio length
        if len(sound) < 200:
            print("⚠️  Audio is very short (< 200ms)")
        
        # Create recognizer
        rec = KaldiRecognizer(vosk_model, sound.frame_rate)
        rec.SetWords(True)
        
        # Convert to raw data
        audio_data = sound.raw_data
        print(f"   Audio data: {len(audio_data)} bytes")
        
        # Test different transcription approaches
        print("\n🔄 Testing chunked transcription...")
        chunk_size = 4000
        recognized_text = ""
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            if len(chunk) > 0:
                if rec.AcceptWaveform(chunk):
                    result = json.loads(rec.Result())
                    chunk_text = result.get('text', '').strip()
                    if chunk_text:
                        recognized_text += chunk_text + " "
                        print(f"   Chunk {i//chunk_size + 1}: '{chunk_text}'")
        
        # Get final result
        final_result = json.loads(rec.FinalResult())
        final_text = final_result.get('text', '').strip()
        if final_text:
            recognized_text += final_text
            print(f"   Final chunk: '{final_text}'")
        
        recognized_text = recognized_text.strip()
        
        print(f"\n✅ Chunked result: '{recognized_text}'")
        
        # Try single-pass if chunked failed
        if not recognized_text:
            print("\n🔄 Trying single-pass transcription...")
            rec2 = KaldiRecognizer(vosk_model, sound.frame_rate)
            rec2.SetWords(True)
            rec2.AcceptWaveform(audio_data)
            result = json.loads(rec2.FinalResult())
            single_pass_text = result.get('text', '').strip()
            print(f"✅ Single-pass result: '{single_pass_text}'")
            
            if single_pass_text:
                recognized_text = single_pass_text
        
        # Final result
        print("\n" + "=" * 50)
        if recognized_text:
            print(f"🎉 SUCCESS! Transcribed text: '{recognized_text}'")
            return True
        else:
            print("💥 FAILED! No text was transcribed")
            print("\nPossible causes:")
            print("1. Audio contains no speech")
            print("2. Audio quality is too low")
            print("3. Background noise is too high")
            print("4. Speech is too quiet or unclear")
            print("5. Language model doesn't recognize the words")
            return False
            
    except Exception as e:
        print(f"❌ Error during transcription: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_audio.py <audio_file>")
        print("\nExample:")
        print("  python3 test_audio.py temp_audio_command")
        print("  python3 test_audio.py test.wav")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    success = test_audio_file(audio_path)
    
    if success:
        print("\n✅ Audio transcription is working!")
    else:
        print("\n❌ Audio transcription failed!")
        print("\nTips for better results:")
        print("- Speak clearly and loudly")
        print("- Reduce background noise")
        print("- Record in a quiet environment")
        print("- Use simple, common words")

if __name__ == "__main__":
    main()
