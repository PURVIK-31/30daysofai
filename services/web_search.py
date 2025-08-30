import os
import requests
from typing import List, Dict, Optional


class WebSearchService:
    """Web search service using Tavily API directly via REST."""
    
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            print("[WEB_SEARCH] Warning: TAVILY_API_KEY not configured")
        self.base_url = "https://api.tavily.com"
    
    def search(self, query: str, max_results: int = 3, api_key_override: Optional[str] = None) -> Dict[str, object]:
        """
        Search the web using Tavily API.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 3)
            
        Returns:
            Dictionary with search results or error information
        """
        # Prefer override key when provided; fall back to instance key loaded from env
        effective_key = api_key_override or self.api_key
        if not effective_key:
            return {
                "success": False,
                "error": "Tavily API key not configured",
                "results": []
            }
        
        try:
            print(f"[WEB_SEARCH] Searching for: {query}")
            
            # Use Tavily REST API directly
            payload = {
                "api_key": effective_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": False
            }
            
            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant information from response
            results = []
            if "results" in data:
                for result in data["results"][:max_results]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0.0)
                    })
            
            return {
                "success": True,
                "query": query,
                "answer": data.get("answer", ""),  # AI-generated answer
                "results": results,
                "search_metadata": {
                    "query_time": data.get("query_time", 0),
                    "follow_up_questions": data.get("follow_up_questions", [])
                }
            }
            
        except requests.RequestException as e:
            print(f"[WEB_SEARCH] HTTP Error searching: {e}")
            return {
                "success": False,
                "error": f"HTTP Error: {e}",
                "query": query,
                "results": []
            }
        except Exception as e:
            print(f"[WEB_SEARCH] Error searching: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "results": []
            }
    
    def format_search_results_for_llm(self, search_response: Dict[str, object]) -> str:
        """
        Format search results in a way that's useful for LLM context.
        
        Args:
            search_response: Response from the search() method
            
        Returns:
            Formatted string with search results
        """
        if not search_response.get("success"):
            return f"Web search failed: {search_response.get('error', 'Unknown error')}"
        
        formatted = f"Web search results for: {search_response.get('query', '')}\n\n"
        
        # Add AI-generated answer if available
        if search_response.get("answer"):
            formatted += f"Quick Answer: {search_response['answer']}\n\n"
        
        # Add individual results
        results = search_response.get("results", [])
        if results:
            formatted += "Detailed Results:\n"
            for i, result in enumerate(results, 1):
                formatted += f"{i}. {result.get('title', 'No title')}\n"
                formatted += f"   URL: {result.get('url', 'No URL')}\n"
                formatted += f"   Content: {result.get('content', 'No content')[:200]}...\n\n"
        
        # Add follow-up questions if available
        follow_ups = search_response.get("search_metadata", {}).get("follow_up_questions", [])
        if follow_ups:
            formatted += "Related questions you might ask:\n"
            for question in follow_ups[:3]:  # Limit to 3 questions
                formatted += f"- {question}\n"
        
        return formatted


# Global instance for easy access
web_search_service = WebSearchService()


def search_web(query: str, max_results: int = 3) -> Dict[str, object]:
    """Convenience function for web search."""
    return web_search_service.search(query, max_results)


def format_search_for_llm(search_response: Dict[str, object]) -> str:
    """Convenience function for formatting search results."""
    return web_search_service.format_search_results_for_llm(search_response)
