#!/usr/bin/env python3
"""
Day 24: Agent Persona Demo Script
Quick demo of persona switching functionality
"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"
DEMO_SESSION = "demo-session-day24"

def demo_persona_switch():
    """Demo switching between different personas"""
    print("🎭 Day 24: Agent Persona System Demo")
    print("=" * 50)
    
    # Get all personas
    response = requests.get(f"{BASE_URL}/api/personas")
    personas = response.json()['personas']
    
    print(f"Available Personas ({len(personas)}):")
    for pid, persona in personas.items():
        print(f"  {persona['avatar']} {persona['name']} - {persona['description']}")
    
    print("\n🔄 Demonstrating persona switching...")
    print("-" * 50)
    
    # Demo each persona
    demo_personas = ['pirate', 'cowboy', 'robot', 'wizard', 'detective', 'chef']
    
    for persona_id in demo_personas:
        if persona_id in personas:
            persona = personas[persona_id]
            
            # Switch to persona
            requests.post(f"{BASE_URL}/api/personas/{DEMO_SESSION}/{persona_id}")
            
            # Verify switch
            current = requests.get(f"{BASE_URL}/api/personas/{DEMO_SESSION}").json()
            
            print(f"{persona['avatar']} Switched to: {persona['name']}")
            print(f"   Voice: {persona['voice_id']}")
            print(f"   Character: {persona['description']}")
            
            # Show a sample of the system prompt
            prompt_preview = persona['system_prompt'][:100] + "..."
            print(f"   Personality: {prompt_preview}")
            print()
            
            time.sleep(1)
    
    print("✅ All persona switches completed successfully!")
    print("\n🌐 Open http://localhost:8000 to test with voice!")
    print("🎥 Ready for LinkedIn demo recording!")

if __name__ == "__main__":
    try:
        demo_persona_switch()
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("Make sure the server is running: python -m uvicorn main:app --reload")
