#!/usr/bin/env python3
"""
Final verification script for Day 24: Agent Persona System
Comprehensive test of all components
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"
TEST_SESSION = "final-verification-session"

def test_component(name, test_func):
    """Helper to run and report test results"""
    print(f"🧪 Testing {name}...")
    try:
        result = test_func()
        if result:
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED")
        return result
    except Exception as e:
        print(f"❌ {name} - ERROR: {e}")
        return False

def test_server_health():
    """Test server health endpoint"""
    response = requests.get(f"{BASE_URL}/api/health")
    return response.status_code == 200 and response.json().get("status") == "healthy"

def test_day_info():
    """Test day info endpoint"""
    response = requests.get(f"{BASE_URL}/api/day")
    data = response.json()
    return (response.status_code == 200 and 
            data.get("day") == 24 and 
            "Persona" in data.get("title", ""))

def test_personas_api():
    """Test personas API endpoints"""
    # Test getting all personas
    response = requests.get(f"{BASE_URL}/api/personas")
    if response.status_code != 200:
        return False
    
    personas = response.json().get("personas", {})
    if len(personas) != 6:
        return False
    
    # Test setting a persona
    response = requests.post(f"{BASE_URL}/api/personas/{TEST_SESSION}/pirate")
    if response.status_code != 200:
        return False
    
    # Test getting current persona
    response = requests.get(f"{BASE_URL}/api/personas/{TEST_SESSION}")
    data = response.json()
    return (response.status_code == 200 and 
            data.get("persona_id") == "pirate" and
            data.get("persona", {}).get("name") == "Captain Blackbeard")

def test_chat_history():
    """Test chat history endpoint"""
    response = requests.get(f"{BASE_URL}/agent/chat/{TEST_SESSION}/history")
    return response.status_code == 200 and "messages" in response.json()

def test_tts_basic():
    """Test basic TTS functionality"""
    data = {"text": "Hello from the persona system!"}
    response = requests.post(f"{BASE_URL}/api/tts/generate", json=data)
    return response.status_code == 200 and response.json().get("success")

def test_persona_switching():
    """Test switching between different personas"""
    personas = ["pirate", "cowboy", "robot", "wizard", "detective", "chef"]
    
    for persona_id in personas:
        response = requests.post(f"{BASE_URL}/api/personas/{TEST_SESSION}/{persona_id}")
        if response.status_code != 200:
            return False
        
        # Verify the switch worked
        response = requests.get(f"{BASE_URL}/api/personas/{TEST_SESSION}")
        if response.json().get("persona_id") != persona_id:
            return False
    
    return True

def test_ui_assets():
    """Test that UI assets are accessible"""
    # Test main page
    response = requests.get(f"{BASE_URL}/")
    if response.status_code != 200:
        return False
    
    # Test CSS
    response = requests.get(f"{BASE_URL}/static/css/style.css")
    if response.status_code != 200:
        return False
    
    # Test JS
    response = requests.get(f"{BASE_URL}/static/js/app.js")
    if response.status_code != 200:
        return False
    
    return True

def main():
    """Run all verification tests"""
    print("🎭 Day 24: Agent Persona System - Final Verification")
    print("=" * 60)
    print()
    
    tests = [
        ("Server Health", test_server_health),
        ("Day Info API", test_day_info),
        ("Personas API", test_personas_api),
        ("Chat History API", test_chat_history),
        ("Basic TTS", test_tts_basic),
        ("Persona Switching", test_persona_switching),
        ("UI Assets", test_ui_assets),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        if test_component(test_name, test_func):
            passed += 1
        print()
    
    print("📊 Final Verification Results")
    print("=" * 60)
    print(f"✅ Passed: {passed}/{total} tests")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! System is ready for LinkedIn demo!")
        print()
        print("🚀 Demo Instructions:")
        print("1. Open http://localhost:8000 in your browser")
        print("2. Select different personas by clicking on the character cards")
        print("3. Use the voice recorder to speak with each persona")
        print("4. Show how each character responds with unique personality and voice")
        print()
        print("📹 Ready for your Day 24 LinkedIn video!")
    else:
        failed = total - passed
        print(f"⚠️  {failed} test(s) failed. Please review the issues above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

