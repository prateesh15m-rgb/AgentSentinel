# v2_adk/travel_planner/app/__init__.py

"""
Travel Planner ADK app package.

Exposes create_app() via main.py so that ADK / Supervisor can load the root agent.
"""

from .main import create_app  # noqa: F401
