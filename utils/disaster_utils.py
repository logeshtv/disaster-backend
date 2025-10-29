"""
Utility functions for disaster relief system
"""
import spacy
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Optional
import os

# Load spaCy model
MODEL_PATH = os.getenv('MODEL_PATH', 'disaster_ner_model')
try:
    nlp = spacy.load(MODEL_PATH)
    print(f"✅ Loaded custom NER model from {MODEL_PATH}")
except:
    print(f"⚠️ Could not load model from {MODEL_PATH}, using default")
    nlp = spacy.load("en_core_web_sm")

# Initialize geocoder
geolocator = Nominatim(user_agent="disaster_relief_system")


def extract_location_from_tweet(tweet_text: str) -> Optional[str]:
    """
    Extract location from tweet using trained NER model
    """
    doc = nlp(tweet_text)
    locations = [ent.text for ent in doc.ents if ent.label_ in ["LOC", "GPE"]]
    return locations[0] if locations else None


def geocode_location(location_name: str) -> Optional[Tuple[float, float]]:
    """
    Convert location name to latitude/longitude
    Returns: (latitude, longitude) or None
    """
    try:
        location = geolocator.geocode(location_name, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None


def calculate_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """
    Calculate distance between two coordinates in kilometers
    """
    return geodesic(coord1, coord2).kilometers


def find_nearby_hubs(location: Tuple[float, float], hubs: List[Dict], max_distance_km: float = 50) -> List[Dict]:
    """
    Find hubs within specified distance from location
    Returns list of hubs with distance added
    """
    nearby = []
    for hub in hubs:
        hub_coords = (hub['latitude'], hub['longitude'])
        distance = calculate_distance(location, hub_coords)
        if distance <= max_distance_km:
            hub_with_distance = hub.copy()
            hub_with_distance['distance_km'] = round(distance, 2)
            nearby.append(hub_with_distance)
    
    # Sort by distance
    nearby.sort(key=lambda x: x['distance_km'])
    return nearby


def match_items(requested: Dict[str, int], available: Dict[str, int]) -> Dict[str, int]:
    """
    Match requested items with available inventory
    Returns: dict of items that can be fulfilled with quantities
    """
    matched = {}
    for item, quantity in requested.items():
        if item in available and available[item] > 0:
            matched[item] = min(quantity, available[item])
    return matched


def calculate_match_score(requested: Dict[str, int], available: Dict[str, int]) -> float:
    """
    Calculate how well available items match requested items (0-100)
    """
    if not requested:
        return 0.0
    
    total_requested = sum(requested.values())
    matched = match_items(requested, available)
    total_matched = sum(matched.values())
    
    return (total_matched / total_requested) * 100


def find_best_hub_for_request(victim_location: Tuple[float, float], 
                               requested_items: Dict[str, int],
                               hubs: List[Dict]) -> Optional[Dict]:
    """
    Find the best hub to fulfill a victim request
    Considers both distance and inventory match
    """
    scored_hubs = []
    
    for hub in hubs:
        hub_coords = (hub['latitude'], hub['longitude'])
        distance = calculate_distance(victim_location, hub_coords)
        
        # Skip hubs too far away (>100km)
        if distance > 100:
            continue
        
        # Calculate match score
        inventory = hub.get('inventory', {})
        match_score = calculate_match_score(requested_items, inventory)
        
        # Skip hubs with no matching items
        if match_score == 0:
            continue
        
        # Combined score: 70% match, 30% distance (inverse)
        # Lower distance is better, so we use 1/(1+distance)
        distance_score = 100 / (1 + distance)
        combined_score = (match_score * 0.7) + (distance_score * 0.3)
        
        scored_hubs.append({
            **hub,
            'distance_km': round(distance, 2),
            'match_score': round(match_score, 1),
            'combined_score': round(combined_score, 1)
        })
    
    # Sort by combined score
    scored_hubs.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return scored_hubs[0] if scored_hubs else None


def classify_disaster_type(tweet_text: str) -> str:
    """
    Simple keyword-based disaster type classification
    """
    tweet_lower = tweet_text.lower()
    
    keywords = {
        'earthquake': ['earthquake', 'tremor', 'seismic', 'quake'],
        'flood': ['flood', 'flooding', 'inundation', 'deluge'],
        'hurricane': ['hurricane', 'cyclone', 'typhoon', 'storm'],
        'wildfire': ['wildfire', 'fire', 'blaze', 'burning'],
        'tornado': ['tornado', 'twister'],
        'tsunami': ['tsunami', 'tidal wave'],
        'landslide': ['landslide', 'mudslide'],
        'volcano': ['volcano', 'volcanic', 'eruption'],
        'drought': ['drought', 'dry', 'water shortage'],
        'blizzard': ['blizzard', 'snowstorm', 'winter storm']
    }
    
    for disaster_type, words in keywords.items():
        if any(word in tweet_lower for word in words):
            return disaster_type
    
    return 'unknown'


def assess_severity(tweet_text: str) -> str:
    """
    Simple keyword-based severity assessment
    """
    tweet_lower = tweet_text.lower()
    
    critical_keywords = ['death', 'dead', 'killed', 'catastrophic', 'devastating', 
                        'destroyed', 'massive', 'severe', 'emergency']
    high_keywords = ['major', 'serious', 'significant', 'heavy', 'damage']
    medium_keywords = ['moderate', 'warning', 'alert']
    
    if any(word in tweet_lower for word in critical_keywords):
        return 'critical'
    elif any(word in tweet_lower for word in high_keywords):
        return 'high'
    elif any(word in tweet_lower for word in medium_keywords):
        return 'medium'
    else:
        return 'low'
