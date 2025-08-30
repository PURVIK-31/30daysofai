import requests
from typing import Dict, Optional


class WeatherService:
    """Simple weather service powered by Open-Meteo and geocoding via Nominatim.

    - Geocodes a location name to coordinates using Nominatim (OpenStreetMap)
    - Fetches current weather from Open-Meteo for those coordinates
    """

    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.weather_url = "https://api.open-meteo.com/v1/forecast"

    def geocode(self, location: str) -> Optional[Dict[str, float]]:
        try:
            params = {
                "q": location,
                "format": "json",
                "limit": 1,
            }
            headers = {"User-Agent": "30daysofai-weather/1.0"}
            r = requests.get(self.nominatim_url, params=params, headers=headers, timeout=20)
            r.raise_for_status()
            data = r.json()
            if not data:
                return None
            item = data[0]
            return {
                "lat": float(item.get("lat")),
                "lon": float(item.get("lon")),
                "display_name": item.get("display_name", location),
            }
        except Exception:
            return None

    def current_weather(self, location: str) -> Dict[str, object]:
        if not location or not location.strip():
            return {"success": False, "error": "Location is required"}

        coords = self.geocode(location)
        if not coords:
            return {"success": False, "error": f"Could not find location: {location}"}

        try:
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "current_weather": True,
                "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weathercode",
            }
            r = requests.get(self.weather_url, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()

            current = data.get("current_weather", {})
            # Some helpful fields
            result = {
                "location": coords.get("display_name", location),
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "temperature_c": current.get("temperature"),
                "windspeed_kmh": current.get("windspeed"),
                "winddirection_deg": current.get("winddirection"),
                "weathercode": current.get("weathercode"),
                "time": current.get("time"),
            }

            # Map weathercode to simple description (subset)
            weathercode_map = {
                0: "Clear sky",
                1: "Mainly clear",
                2: "Partly cloudy",
                3: "Overcast",
                45: "Fog",
                48: "Depositing rime fog",
                51: "Light drizzle",
                53: "Moderate drizzle",
                55: "Dense drizzle",
                61: "Slight rain",
                63: "Moderate rain",
                65: "Heavy rain",
                71: "Slight snow",
                73: "Moderate snow",
                75: "Heavy snow",
                80: "Rain showers",
                81: "Heavy rain showers",
                82: "Violent rain showers",
                95: "Thunderstorm",
            }
            code = result.get("weathercode")
            if isinstance(code, int) and code in weathercode_map:
                result["conditions"] = weathercode_map[code]

            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def format_for_llm(self, weather_response: Dict[str, object]) -> str:
        if not weather_response.get("success"):
            return f"Weather lookup failed: {weather_response.get('error', 'Unknown error')}"
        data = weather_response.get("data", {})
        parts = []
        loc = data.get("location", "the specified location")
        temp = data.get("temperature_c")
        cond = data.get("conditions") or f"code {data.get('weathercode', '?')}"
        wind = data.get("windspeed_kmh")
        parts.append(f"Current weather for {loc}:")
        if temp is not None:
            parts.append(f"- Temperature: {temp}°C")
        parts.append(f"- Conditions: {cond}")
        if wind is not None:
            parts.append(f"- Wind: {wind} km/h")
        time = data.get("time")
        if time:
            parts.append(f"- Time: {time}")
        return "\n".join(parts)


weather_service = WeatherService()


def get_current_weather(location: str) -> Dict[str, object]:
    return weather_service.current_weather(location)


def format_weather_for_llm(weather_response: Dict[str, object]) -> str:
    return weather_service.format_for_llm(weather_response)


