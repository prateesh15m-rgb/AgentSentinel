# v2_adk/travel_planner/tools/dest_info_tool.py

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from infra.env import ensure_env_loaded
from .google_maps_client import get_gmaps_client

logger = logging.getLogger(__name__)

# Ensure GOOGLE_MAPS_API_KEY (etc.) from .env are loaded before any client calls
ensure_env_loaded()


def _geocode_city(destination: str) -> Optional[Dict[str, Any]]:
    """
    Use Google Geocoding API to resolve a city name into
    lat/lng + formatted_address + country info.
    """
    gmaps = get_gmaps_client()
    try:
        results = gmaps.geocode(destination)
    except Exception as e:
        logger.warning("Geocoding failed for %s: %s", destination, e)
        return None

    if not results:
        return None

    res = results[0]
    geometry = res.get("geometry", {})
    location = geometry.get("location", {})

    lat = location.get("lat")
    lng = location.get("lng")
    formatted_address = res.get("formatted_address", destination)
    components = res.get("address_components", [])

    country = None
    admin_area = None
    for comp in components:
        types = comp.get("types", [])
        if "country" in types:
            country = comp.get("long_name")
        if "administrative_area_level_1" in types:
            admin_area = comp.get("long_name")

    return {
        "lat": lat,
        "lng": lng,
        "formatted_address": formatted_address,
        "country": country,
        "region": admin_area,
        "raw_result": res,
    }


def _search_representative_place(destination: str) -> Optional[Dict[str, Any]]:
    """
    Use Places API to find a representative place for the destination:
    typically a locality or popular attraction in that city.
    """
    gmaps = get_gmaps_client()

    try:
        resp = gmaps.places(
            query=destination,
            # You can further constrain via type="locality" or "tourist_attraction"
        )
    except Exception as e:
        logger.warning("Places search failed for %s: %s", destination, e)
        return None

    results = resp.get("results", [])
    if not results:
        return None

    # Just take the top result for now
    place = results[0]

    return {
        "name": place.get("name", destination),
        "place_id": place.get("place_id"),
        "types": place.get("types", []),
        "rating": place.get("rating"),
        "user_ratings_total": place.get("user_ratings_total"),
        "price_level": place.get("price_level"),  # 0–4 if present
    }


def _infer_tags_from_types(types: List[str]) -> List[str]:
    tags: List[str] = []
    tset = set(types or [])

    if any(t in tset for t in ["locality", "political", "administrative_area_level_1"]):
        tags.append("city")

    if any(t in tset for t in ["tourist_attraction", "point_of_interest"]):
        tags.append("touristic")

    if any(t in tset for t in ["natural_feature", "park"]):
        tags.append("nature")

    # You can keep adding more heuristics here

    return sorted(set(tags))


def get_destination_profile(destination: str) -> Dict[str, Any]:
    """
    Return a structured destination profile for use in the planner prompt.

    Example output:
    {
      "destination_input": "Tokyo",
      "resolved_city": {
        "lat": ...,
        "lng": ...,
        "formatted_address": "...",
        "country": "Japan",
        "region": "Tokyo"
      },
      "representative_place": {
        "name": "...",
        "place_id": "...",
        "types": [...],
        "rating": 4.6,
        "user_ratings_total": 21901,
        "price_level": 3
      },
      "tags": ["city", "touristic"]
    }
    """
    geo = _geocode_city(destination)
    place = _search_representative_place(destination)

    tags: List[str] = []
    if place:
        tags.extend(_infer_tags_from_types(place.get("types", [])))

    return {
        "destination_input": destination,
        "resolved_city": geo,
        "representative_place": place,
        "tags": sorted(set(tags)),
    }
