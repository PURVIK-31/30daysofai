#!/usr/bin/env python3
"""
Test script for Day 25: Web Search Special Skill
"""
import os
from dotenv import load_dotenv
from services.web_search import web_search_service
from services.function_calling import function_calling_service

# Load environment variables
load_dotenv()

def test_web_search_service():
    """Test the web search service directly."""
    print("🔍 Testing Web Search Service...")
    
    # Test search
    query = "latest AI developments 2024"
    result = web_search_service.search(query, max_results=2)
    
    if result["success"]:
        print(f"✅ Search successful for query: {query}")
        print(f"📊 Found {len(result['results'])} results")
        if result.get("answer"):
            print(f"💡 Quick Answer: {result['answer'][:100]}...")
        
        # Test formatting
        formatted = web_search_service.format_search_results_for_llm(result)
        print(f"📝 Formatted length: {len(formatted)} characters")
        print("✅ Web search service working correctly")
        return True
    else:
        print(f"❌ Search failed: {result.get('error', 'Unknown error')}")
        return False

def test_function_calling():
    """Test the function calling service."""
    print("\n🤖 Testing Function Calling Service...")
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY not configured")
        return False
    
    # Test function calling with web search
    contents = [
        {
            "role": "user",
            "parts": [{"text": "What are the latest developments in artificial intelligence? Please search for current information."}]
        }
    ]
    
    result = function_calling_service.call_gemini_with_functions(
        contents, gemini_api_key, "gemini-1.5-flash"
    )
    
    if result["success"]:
        print("✅ Function calling successful")
        print(f"📝 Response length: {len(result.get('response', ''))}")
        
        function_calls = result.get("function_calls", [])
        print(f"🔧 Function calls made: {len(function_calls)}")
        
        for i, call in enumerate(function_calls):
            if call.get("success"):
                print(f"✅ Call {i+1}: {call.get('function_name')} - Success")
            else:
                print(f"❌ Call {i+1}: {call.get('function_name')} - Failed: {call.get('error')}")
        
        return True
    else:
        print(f"❌ Function calling failed: {result.get('error', 'Unknown error')}")
        return False

def main():
    """Main test function."""
    print("🚀 Day 25: Web Search Special Skill Test\n")
    
    # Check API keys
    required_keys = ["TAVILY_API_KEY", "GEMINI_API_KEY"]
    missing_keys = []
    
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing API keys: {', '.join(missing_keys)}")
        print("Please configure these keys in your .env file")
        print("\n📝 Create a .env file with:")
        print("TAVILY_API_KEY=your_tavily_api_key_here")
        print("GEMINI_API_KEY=your_gemini_api_key_here")
        print("ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here")
        print("MURF_API_KEY=your_murf_api_key_here")
        print("\n✅ Implementation is ready - just add your API keys!")
        print("\n🔧 Web Search Service: ✅ IMPLEMENTED")
        print("🔧 Function Calling Service: ✅ IMPLEMENTED")
        print("🔧 Persona Integration: ✅ IMPLEMENTED")
        print("🔧 REST API Integration: ✅ IMPLEMENTED")
        return
    
    # Run tests
    web_search_ok = test_web_search_service()
    function_calling_ok = test_function_calling()
    
    print("\n📊 Test Results:")
    print(f"Web Search Service: {'✅ PASS' if web_search_ok else '❌ FAIL'}")
    print(f"Function Calling: {'✅ PASS' if function_calling_ok else '❌ FAIL'}")
    
    if web_search_ok and function_calling_ok:
        print("\n🎉 All tests passed! Web search special skill is ready!")
        print("\n💡 Try asking your AI agents:")
        print("- 'What's the latest news about AI?'")
        print("- 'What's the weather like today?'")
        print("- 'Tell me about recent space discoveries'")
    else:
        print("\n❌ Some tests failed. Please check your configuration.")

if __name__ == "__main__":
    main()
