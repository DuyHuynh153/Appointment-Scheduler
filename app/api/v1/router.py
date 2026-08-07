"""Aggregates all v1 API routers under a single `APIRouter`.

Included from `app/main.py` with the `/api/v1` prefix.
"""
from fastapi import APIRouter

from app.api.v1 import appointments, availability

api_v1_router = APIRouter()
api_v1_router.include_router(appointments.router)
api_v1_router.include_router(availability.router)

