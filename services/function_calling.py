import json
import requests
from typing import Dict, List, Optional, Any
from .web_search import web_search_service
from .weather import weather_service


# Define the web search function schema for Gemini
WEB_SEARCH_FUNCTION_DECLARATION = {
    "name": "search_web",
    "description": "Search the web for current information, news, facts, or any topic that requires up-to-date information. Use this when the user asks about recent events, current weather, latest news, stock prices, or any information that might have changed recently.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find information on the web. Be specific and include relevant keywords."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of search results to return (default: 3, max: 5)",
                "default": 3
            }
        },
        "required": ["query"]
    }
}

# Define the weather function schema for Gemini
WEATHER_FUNCTION_DECLARATION = {
    "name": "get_weather",
    "description": "Get the current weather for a given location (city, place, or address). Use this when the user asks about current temperature, conditions, wind, or weather now in a specific location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location to get weather for, e.g., 'Mumbai', 'New York', or 'Bengaluru, India'."
            }
        },
        "required": ["location"]
    }
}

class FunctionCallingService:
    """Service for handling Gemini function calling with special skills."""

    def __init__(self):
        # Optional per-request overrides (e.g., Tavily key)
        self.tavily_api_key_override: Optional[str] = None

        # Bind available functions at instance-level so handlers can access overrides
        self.functions = {
            "search_web": {
                "declaration": WEB_SEARCH_FUNCTION_DECLARATION,
                "handler": lambda **kwargs: web_search_service.search(
                    kwargs.get("query", ""),
                    kwargs.get("max_results", 3),
                    api_key_override=self.tavily_api_key_override,
                )
            },
            "get_weather": {
                "declaration": WEATHER_FUNCTION_DECLARATION,
                "handler": lambda **kwargs: weather_service.current_weather(
                    kwargs.get("location", "")
                )
            }
        }

    def set_tavily_api_key_override(self, api_key: Optional[str]) -> None:
        """Set per-request Tavily API key override."""
        self.tavily_api_key_override = api_key


    
    def get_function_declarations(self) -> List[Dict[str, Any]]:
        """Get all function declarations for Gemini API."""
        return [func["declaration"] for func in self.functions.values()]
    
    def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a function call and return the result.
        
        Args:
            function_name: Name of the function to execute
            parameters: Parameters to pass to the function
            
        Returns:
            Dictionary with function execution result
        """
        if function_name not in self.functions:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}",
                "result": None
            }
        
        try:
            print(f"[FUNCTION_CALL] Executing {function_name} with params: {parameters}")
            handler = self.functions[function_name]["handler"]
            result = handler(**parameters)
            
            return {
                "success": True,
                "function_name": function_name,
                "parameters": parameters,
                "result": result
            }
            
        except Exception as e:
            print(f"[FUNCTION_CALL] Error executing {function_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "function_name": function_name,
                "parameters": parameters,
                "result": None
            }
    
    def call_gemini_with_functions(
        self, 
        contents: List[Dict[str, Any]], 
        api_key: str, 
        model: str,
        max_function_calls: int = 3
    ) -> Dict[str, Any]:
        """
        Call Gemini API with function calling capability.
        
        Args:
            contents: Conversation contents
            api_key: Gemini API key
            model: Model name
            max_function_calls: Maximum number of function calls to allow
            
        Returns:
            Dictionary with final response and function call history
        """
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        
        # Prepare the payload with function declarations
        payload = {
            "contents": contents,
            "tools": [
                {
                    "function_declarations": self.get_function_declarations()
                }
            ]
        }
        
        function_calls_made = []
        conversation_contents = contents.copy()
        
        for call_iteration in range(max_function_calls):
            try:
                print(f"[FUNCTION_CALL] Gemini call iteration {call_iteration + 1}")
                
                response = requests.post(
                    endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=60
                )
                response.raise_for_status()
                data = response.json()
                
                candidates = data.get("candidates", [])
                if not candidates:
                    return {
                        "success": False,
                        "error": "No candidates in Gemini response",
                        "function_calls": function_calls_made
                    }
                
                candidate = candidates[0]
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                
                # Check if there are function calls to execute
                function_calls_in_response = []
                text_response = ""
                
                for part in parts:
                    if "functionCall" in part:
                        function_calls_in_response.append(part["functionCall"])
                    elif "text" in part:
                        text_response += part["text"]
                
                # If there are function calls, execute them
                if function_calls_in_response:
                    # Add the model's response with function calls to conversation
                    conversation_contents.append({
                        "role": "model",
                        "parts": parts
                    })
                    
                    # Execute each function call
                    function_responses = []
                    for func_call in function_calls_in_response:
                        func_name = func_call.get("name", "")
                        func_args = func_call.get("args", {})
                        
                        # Execute the function
                        exec_result = self.execute_function(func_name, func_args)
                        function_calls_made.append(exec_result)
                        
                        # Format the result for the conversation
                        if exec_result["success"]:
                            if func_name == "search_web":
                                # Format search results nicely for the conversation
                                formatted_result = web_search_service.format_search_results_for_llm(
                                    exec_result["result"]
                                )
                            elif func_name == "get_weather":
                                formatted_result = weather_service.format_for_llm(
                                    exec_result["result"]
                                )
                            else:
                                formatted_result = json.dumps(exec_result["result"], indent=2)
                        else:
                            formatted_result = f"Error: {exec_result.get('error', 'Unknown error')}"
                        
                        function_responses.append({
                            "functionResponse": {
                                "name": func_name,
                                "response": {"result": formatted_result}
                            }
                        })
                    
                    # Add function responses to conversation
                    conversation_contents.append({
                        "role": "user",
                        "parts": function_responses
                    })
                    
                    # Update payload for next iteration
                    payload["contents"] = conversation_contents
                    
                else:
                    # No function calls, we have the final response
                    return {
                        "success": True,
                        "response": text_response,
                        "function_calls": function_calls_made,
                        "conversation": conversation_contents
                    }
            
            except requests.RequestException as e:
                return {
                    "success": False,
                    "error": f"Gemini API error: {e}",
                    "function_calls": function_calls_made
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Unexpected error: {e}",
                    "function_calls": function_calls_made
                }
        
        # If we've reached max function calls, return what we have
        return {
            "success": False,
            "error": f"Maximum function calls ({max_function_calls}) reached",
            "function_calls": function_calls_made,
            "conversation": conversation_contents
        }


# Backward-compatible global instance (not used for per-request overrides)
function_calling_service = FunctionCallingService()
