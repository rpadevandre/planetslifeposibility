from __future__ import annotations

from uuid import UUID, uuid4

from app.schemas import CivilizationListItem, CivilizationOut, SolarSystemOut


_records: list[CivilizationListItem] = []


def record_from_simulation(
    *,
    system: SolarSystemOut,
    planet_name: str,
    civilization: CivilizationOut,
    run_label: str | None = None,
) -> CivilizationListItem:
    item = CivilizationListItem(
        id=uuid4(),
        system_id=system.id,
        system_name=system.name,
        homeworld=planet_name,
        civilization=civilization,
        run_label=run_label,
    )
    _records.append(item)
    return item


def list_civilizations(
    *,
    system_id: UUID | None = None,
    min_technology: float | None = None,
    extinct_only: bool = False,
    multiplanetary_only: bool = False,
    hyper_only: bool = False,
) -> list[CivilizationListItem]:
    out = _records
    if system_id is not None:
        out = [r for r in out if r.system_id == system_id]
    if min_technology is not None:
        out = [r for r in out if r.civilization.technology_score >= min_technology]
    if extinct_only:
        out = [r for r in out if r.civilization.extinct]
    if multiplanetary_only:
        out = [r for r in out if r.civilization.is_multiplanetary]
    if hyper_only:
        out = [r for r in out if r.civilization.is_hyper_technological]
    return list(reversed(out))


def clear_registry() -> None:
    _records.clear()
