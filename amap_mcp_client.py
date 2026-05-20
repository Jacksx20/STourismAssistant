import requests
import json
import math
from typing import Optional, Dict, List, Any


class AmapMCPClient:
    def __init__(self, api_key: str, timeout: int = 60):
        self.api_key = api_key
        self.base_url = "https://restapi.amap.com/v3"
        self.timeout = timeout
    
    def _get(self, endpoint: str, params: Dict[str, Any]) -> Any:
        params['key'] = self.api_key
        params['output'] = 'json'
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, params=params, timeout=self.timeout)
        return response.json()
    
    def geocode(self, city: str) -> Optional[Dict[str, Any]]:
        params = {"address": city}
        return self._get("geocode/geo", params)
    
    def search_poi(self, keyword: str, location: Optional[str] = None, 
                   city: Optional[str] = None, radius: int = 3000, 
                   offset: int = 20) -> Optional[Dict[str, Any]]:
        params = {
            "keywords": keyword,
            "offset": str(offset)
        }
        if city:
            params["city"] = city
        if location:
            params["location"] = location
            params["radius"] = str(radius)
        return self._get("place/text", params)
    
    def search_nearby(self, keyword: str, location: str, 
                      radius: int = 3000, offset: int = 20) -> Optional[Dict[str, Any]]:
        params = {
            "keywords": keyword,
            "location": location,
            "radius": str(radius),
            "offset": str(offset)
        }
        return self._get("place/around", params)
    
    def search_detail(self, poi_id: str) -> Optional[Dict[str, Any]]:
        params = {"id": poi_id}
        return self._get("place/detail", params)
    
    def weather(self, city: str) -> Optional[Dict[str, Any]]:
        params = {"city": city, "extensions": "all"}
        return self._get("weather/weatherInfo", params)


def parse_geocode(result: Any) -> Optional[Dict[str, str]]:
    if not result or 'geocodes' not in result:
        return None
    geocodes = result['geocodes']
    if not geocodes:
        return None
    geo = geocodes[0]
    return {
        'location': geo.get('location', ''),
        'province': geo.get('province', ''),
        'city': geo.get('city', ''),
        'district': geo.get('district', '')
    }


def parse_poi_list(result: Any) -> List[Dict[str, Any]]:
    if not result or 'pois' not in result:
        return []
    pois = result['pois']
    poi_list = []
    for poi in pois:
        photos = poi.get('photos', [])
        photo = photos[0].get('url', '') if photos else ''
        
        poi_data = {
            'id': poi.get('id', ''),
            'name': poi.get('name', ''),
            'type': poi.get('type', ''),
            'address': poi.get('address', ''),
            'location': None,
            'tel': poi.get('tel', ''),
            'rating': poi.get('biz_ext', {}).get('rating', ''),
            'photo': photo
        }
        poi_list.append(poi_data)
    return poi_list


def parse_weather(result: Any, days: int = 4) -> List[Dict[str, Any]]:
    if not result or 'forecasts' not in result:
        return []
    
    forecasts = result['forecasts']
    if not forecasts:
        return []
    
    weather_list = []
    casts = forecasts[0].get('casts', [])
    
    for i, cast in enumerate(casts[:days]):
        weather_list.append({
            'date': cast.get('date', ''),
            'week': cast.get('week', ''),
            'dayweather': cast.get('dayweather', ''),
            'nightweather': cast.get('nightweather', ''),
            'daytemp': cast.get('daytemp', ''),
            'nighttemp': cast.get('nighttemp', '')
        })
    
    for i in range(len(weather_list), days):
        if weather_list:
            last_weather = weather_list[-1].copy()
            last_weather['date'] = f'第{i+1}天'
            weather_list.append(last_weather)
    
    return weather_list


def haversine_distance(loc1: str, loc2: str) -> float:
    if not loc1 or not loc2:
        return float('inf')
    
    try:
        lon1, lat1 = map(float, loc1.split(','))
        lon2, lat2 = map(float, loc2.split(','))
    except:
        return float('inf')
    
    R = 6371.0
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def estimate_travel_time(distance_km: float) -> float:
    speed_kmh = 30.0
    return distance_km / speed_kmh


def greedy_tsp(locations: List[Dict[str, Any]], start_location: str) -> List[Dict[str, Any]]:
    if not locations:
        return []
    
    sorted_locations = []
    remaining = locations.copy()
    current_loc = start_location
    
    while remaining:
        nearest_idx = 0
        nearest_dist = float('inf')
        
        for i, loc in enumerate(remaining):
            loc_str = loc.get('location', '')
            dist = haversine_distance(current_loc, loc_str)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_idx = i
        
        nearest_loc = remaining.pop(nearest_idx)
        sorted_locations.append(nearest_loc)
        current_loc = nearest_loc.get('location', '')
    
    return sorted_locations
