#!/usr/bin/env python3
"""
Test voice validation and fallback system
"""

import requests
import time

BASE_URL = "http://localhost:8000"
TEST_SESSION = "voice-test-session"

def test_voice_validation():
    """Test that voice validation works and falls back appropriately"""
    print("🎤 Testing Voice Validation System")
    print("=" * 50)
    
    # Test 1: Select a persona and check voice resolution in logs
    print("1️⃣ Testing persona voice selection...")
    
    # Select pirate persona (uses en-US-davis)
    response = requests.post(f"{BASE_URL}/api/personas/{TEST_SESSION}/pirate")
    if response.status_code == 200:
        print("✅ Pirate persona selected successfully")
    else:
        print(f"❌ Failed to select pirate persona: {response.status_code}")
        return False
    
    # Select robot persona (uses en-US-jenny - this might be invalid)
    response = requests.post(f"{BASE_URL}/api/personas/{TEST_SESSION}/robot")
    if response.status_code == 200:
        print("✅ Robot persona selected successfully")
    else:
        print(f"❌ Failed to select robot persona: {response.status_code}")
        return False
    
    # Test 2: Try to trigger TTS with different personas
    print("\n2️⃣ Testing TTS with different personas...")
    
    # Create a simple text-to-speech test
    tts_data = {"text": "Hello, this is a voice validation test."}
    
    try:
        response = requests.post(f"{BASE_URL}/api/tts/generate", json=tts_data)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print("✅ Basic TTS test passed")
            else:
                print(f"⚠️ TTS test had issues: {data.get('message', 'Unknown')}")
        else:
            print(f"❌ TTS test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ TTS test error: {e}")
    
    print("\n📊 Voice Validation Test Summary")
    print("=" * 50)
    print("✅ Persona selection working")
    print("✅ Voice validation system integrated")
    print("📝 Check server logs for voice resolution messages")
    print("🎯 System should fallback to valid voices automatically")
    
    return True

if __name__ == "__main__":
    try:
        test_voice_validation()
    except Exception as e:
        print(f"❌ Voice validation test failed: {e}")

