"""Service Type repository - persistence access only, no business rules."""
from __future__ import annotations

from app.models.service_type import ServiceType
from app.repositories.base import BaseRepository


class ServiceTypeRepository(BaseRepository[ServiceType]):
    model = ServiceType
