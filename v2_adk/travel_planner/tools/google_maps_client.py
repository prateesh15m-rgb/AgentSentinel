# v2_adk/travel_planner/tools/google_maps_client.py

from __future__ import annotations

import os
import logging
from typing import Optional

import googlemaps

logger = logging.getLogger(__name__)


_gmaps_client: Optional[googlemaps.Client] = None


def get_gmaps_client() -> googlemaps.Client:
    """
    Singleton-style accessor for Google Maps client.
    Uses GOOGLE_MAPS_API_KEY from environment.
    """
    global _gmaps_client
    if _gmaps_client is not None:
        return _gmaps_client

    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GOOGLE_MAPS_API_KEY is not set. "
            "Please export it before running the travel planner."
        )

    _gmaps_client = googlemaps.Client(key=api_key)
    logger.info("Initialized Google Maps client.")
    return _gmaps_client
