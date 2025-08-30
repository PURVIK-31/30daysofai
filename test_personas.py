#!/usr/bin/env python3
"""
Test script for Day 24: Agent Persona System
Tests all personas and their functionality
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
TEST_SESSION_ID = "test-session-123"

def test_health():
    """Test if server is running"""
    print("🔍 Testing server health...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy: {data['message']}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_day_info():
    """Test day info endpoint"""
    print("\n📅 Testing day info...")
    try:
        response = requests.get(f"{BASE_URL}/api/day")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Day {data['day']}: {data['title']}")
            print(f"   Description: {data['description']}")
            return True
        else:
            print(f"❌ Day info failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Day info error: {e}")
        return False

def test_personas_list():
    """Test personas listing"""
    print("\n🎭 Testing personas list...")
    try:
        response = requests.get(f"{BASE_URL}/api/personas")
        if response.status_code == 200:
            data = response.json()
            personas = data.get('personas', {})
            print(f"✅ Found {len(personas)} personas:")
            
            for persona_id, persona in personas.items():
                print(f"   {persona['avatar']} {persona['name']} ({persona_id})")
                print(f"      Voice: {persona['voice_id']}")
                print(f"      Description: {persona['description']}")
                print()
            
            return personas
        else:
            print(f"❌ Personas list failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Personas list error: {e}")
        return None

def test_persona_selection(persona_id, persona_name):
    """Test selecting a specific persona"""
    print(f"🎯 Testing persona selection: {persona_name}")
    try:
        response = requests.post(f"{BASE_URL}/api/personas/{TEST_SESSION_ID}/{persona_id}")
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ Successfully selected {persona_name}")
                return True
            else:
                print(f"❌ Selection failed: {data}")
                return False
        else:
            print(f"❌ Selection request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Persona selection error: {e}")
        return False

def test_get_current_persona():
    """Test getting current persona for session"""
    print(f"📋 Testing current persona retrieval...")
    try:
        response = requests.get(f"{BASE_URL}/api/personas/{TEST_SESSION_ID}")
        if response.status_code == 200:
            data = response.json()
            current = data.get('persona', {})
            print(f"✅ Current persona: {current.get('name')} ({data.get('persona_id')})")
            return data
        else:
            print(f"❌ Current persona request failed: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Current persona error: {e}")
        return None

def test_chat_history():
    """Test chat history endpoint"""
    print(f"💬 Testing chat history...")
    try:
        response = requests.get(f"{BASE_URL}/agent/chat/{TEST_SESSION_ID}/history")
        if response.status_code == 200:
            data = response.json()
            messages = data.get('messages', [])
            print(f"✅ Chat history loaded: {len(messages)} messages")
            return True
        else:
            print(f"❌ Chat history request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Chat history error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Day 24 Persona System Tests\n")
    print("=" * 50)
    
    # Test 1: Health check
    if not test_health():
        print("❌ Server is not running. Please start it first.")
        return
    
    # Test 2: Day info
    test_day_info()
    
    # Test 3: List personas
    personas = test_personas_list()
    if not personas:
        print("❌ Cannot continue without personas data")
        return
    
    # Test 4: Test each persona selection
    print("\n🎭 Testing individual persona selections...")
    print("=" * 50)
    
    success_count = 0
    for persona_id, persona_data in personas.items():
        persona_name = persona_data['name']
        if test_persona_selection(persona_id, persona_name):
            success_count += 1
            
            # Test getting current persona
            current = test_get_current_persona()
            if current and current.get('persona_id') == persona_id:
                print(f"✅ Persona persistence verified for {persona_name}")
            else:
                print(f"⚠️  Persona persistence issue for {persona_name}")
        
        print("-" * 30)
        time.sleep(0.5)  # Small delay between tests
    
    # Test 5: Chat history
    test_chat_history()
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 50)
    print(f"✅ Successfully tested {success_count}/{len(personas)} personas")
    
    if success_count == len(personas):
        print("🎉 All persona tests passed! System is ready for demo.")
    else:
        print("⚠️  Some persona tests failed. Check the logs above.")
    
    print("\n🌐 Open http://localhost:8000 in your browser to test the UI!")

if __name__ == "__main__":
    main()
