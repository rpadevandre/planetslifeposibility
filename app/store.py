from __future__ import annotations

from uuid import UUID

from app.schemas import SolarSystemOut

_systems: dict[UUID, SolarSystemOut] = {}


def save_system(system: SolarSystemOut) -> SolarSystemOut:
    _systems[system.id] = system
    return system


def get_system(system_id: UUID) -> SolarSystemOut | None:
    return _systems.get(system_id)


def list_systems() -> list[SolarSystemOut]:
    return list(_systems.values())
