# v2_adk/travel_planner/tools/weather_tool.py

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from infra.env import ensure_env_loaded
from .google_maps_client import get_gmaps_client

logger = logging.getLogger(__name__)

CLIMATE_URL = "https://climate-api.open-meteo.com/v1/climate"

# Ensure env (.env → os.environ) is loaded so Google Maps can see its key
ensure_env_loaded()


def _geocode_city(destination: str) -> Optional[Dict[str, Any]]:
    """Use Google Geocoding to resolve destination to lat/lng."""
    gmaps = get_gmaps_client()
    try:
        results = gmaps.geocode(destination)
    except Exception as e:
        logger.warning("Geocoding for weather failed for %s: %s", destination, e)
        return None

    if not results:
        return None

    res = results[0]
    loc = res.get("geometry", {}).get("location", {})
    return {
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "formatted_address": res.get("formatted_address"),
    }


def _get_climate_normals(lat: float, lon: float, month: Optional[int]) -> Optional[Dict[str, Any]]:
    """Fetch climate normals from Open-Meteo."""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "auto",
        }
        if month is not None:
            params["month"] = month

        resp = requests.get(CLIMATE_URL, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Climate API failed for lat=%s lon=%s: %s", lat, lon, e)
        return None


def get_weather_profile(destination: str, month: Optional[int] = None) -> Dict[str, Any]:
    """
    High-level weather profile used by the planner.

    Output schema:
    {
      "destination": "...",
      "formatted_address": "...",
      "lat": ...,
      "lon": ...,
      "month": 4,
      "avg_temp_c": 16.2,
      "avg_precip_mm": 85.3,
      "rain_risk": "low|medium|high|unknown",
      "summary": "Mild temperatures with medium rain risk."
    }
    """
    geo = _geocode_city(destination)
    if not geo or geo.get("lat") is None or geo.get("lng") is None:
        return {
            "destination": destination,
            "formatted_address": None,
            "lat": None,
            "lon": None,
            "month": month,
            "avg_temp_c": None,
            "avg_precip_mm": None,
            "rain_risk": "unknown",
            "summary": "Weather data not available; assume typical mild conditions.",
        }

    lat = float(geo["lat"])
    lon = float(geo["lng"])

    climate = _get_climate_normals(lat, lon, month)
    if not climate or "daily" not in climate:
        return {
            "destination": destination,
            "formatted_address": geo.get("formatted_address"),
            "lat": lat,
            "lon": lon,
            "month": month,
            "avg_temp_c": None,
            "avg_precip_mm": None,
            "rain_risk": "unknown",
            "summary": "Weather service unavailable; assume mild conditions and mention uncertainty.",
        }

    daily = climate["daily"]
    temps = daily.get("temperature_2m_mean") or []
    rains = daily.get("precipitation_sum") or []

    avg_temp_c = sum(temps) / len(temps) if temps else None
    avg_precip = sum(rains) / len(rains) if rains else None

    if avg_precip is None:
        rain_risk = "unknown"
    elif avg_precip < 40:
        rain_risk = "low"
    elif avg_precip < 100:
        rain_risk = "medium"
    else:
        rain_risk = "high"

    if avg_temp_c is not None:
        if avg_temp_c < 8:
            temp_desc = "cold"
        elif avg_temp_c < 22:
            temp_desc = "mild"
        else:
            temp_desc = "warm"
    else:
        temp_desc = "typical"

    summary = f"{temp_desc.capitalize()} temperatures with {rain_risk} rain risk."

    return {
        "destination": destination,
        "formatted_address": geo.get("formatted_address"),
        "lat": lat,
        "lon": lon,
        "month": month,
        "avg_temp_c": round(avg_temp_c, 1) if avg_temp_c is not None else None,
        "avg_precip_mm": round(avg_precip, 1) if avg_precip is not None else None,
        "rain_risk": rain_risk,
        "summary": summary,
    }
