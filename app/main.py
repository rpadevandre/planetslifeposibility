from __future__ import annotations

import random
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from pydantic import model_validator

from app.config import settings
from app import civ_registry
from app.generator import generate_solar_system
from app.tech_eras import list_all_eras
from app.schemas import (
    AdvanceStoredSystemRequest,
    BatchSimulationRequest,
    BatchSimulationResult,
    CivilizationListItem,
    GenerateSystemRequest,
    HealthOut,
    SolarSystemOut,
    SystemSimulationResult,
    TechnologyEraOut,
)
from app.simulation import simulate_system
from app import store

app = FastAPI(title=settings.app_name, version="0.1.0")


class GenerateSystemBody(GenerateSystemRequest):
    @model_validator(mode="after")
    def check_planet_bounds(self) -> GenerateSystemBody:
        if self.max_planets < self.min_planets:
            raise ValueError("max_planets must be >= min_planets")
        return self


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    return HealthOut(status="ok", app=settings.app_name)


@app.post("/systems/generate", response_model=SolarSystemOut)
def generate_system(body: GenerateSystemBody) -> SolarSystemOut:
    system = generate_solar_system(
        seed=body.seed,
        min_planets=body.min_planets,
        max_planets=body.max_planets,
        name=body.name,
    )
    return store.save_system(system)


@app.get("/systems", response_model=list[SolarSystemOut])
def list_systems() -> list[SolarSystemOut]:
    return store.list_systems()


@app.get("/systems/{system_id}", response_model=SolarSystemOut)
def get_system(system_id: UUID) -> SolarSystemOut:
    s = store.get_system(system_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    return s


class BatchSimulationBody(BatchSimulationRequest):
    @model_validator(mode="after")
    def check_planet_bounds(self) -> BatchSimulationBody:
        if self.max_planets < self.min_planets:
            raise ValueError("max_planets must be >= min_planets")
        return self


@app.post("/simulation/batch", response_model=BatchSimulationResult)
def simulation_batch(body: BatchSimulationBody) -> BatchSimulationResult:
    """
    Genera N sistemas solares en secuencia y aplica el mismo fast-forward (My) a cada uno.
    Respuestas basadas en scores: tecnología 0–100, disposición 0 (hostil) – 100 (pacifista).
    """
    runs: list[SystemSimulationResult] = []
    base = body.seed if body.seed is not None else random.randint(1, 2**30 - 1)
    for i in range(body.system_count):
        name = f"{body.name_prefix}-{i + 1}" if body.name_prefix else None
        system = generate_solar_system(
            seed=base + i,
            min_planets=body.min_planets,
            max_planets=body.max_planets,
            name=name,
        )
        store.save_system(system)
        srng = random.Random(base + i * 1_000_003 + 17)
        result = simulate_system(
            srng,
            system,
            body.advance_million_years,
            body.advanced_technology_threshold,
        )
        runs.append(result)
        for po in result.planets:
            if po.civilization is not None:
                civ_registry.record_from_simulation(
                    system=result.system,
                    planet_name=po.planet.name,
                    civilization=po.civilization,
                    run_label=f"batch:{base}:{i}",
                )
    return BatchSimulationResult(
        generation_base_seed=base,
        advance_million_years_per_system=body.advance_million_years,
        advanced_technology_threshold=body.advanced_technology_threshold,
        runs=runs,
    )


@app.post("/simulation/system/{system_id}", response_model=SystemSimulationResult)
def simulation_for_stored_system(
    system_id: UUID,
    body: AdvanceStoredSystemRequest,
) -> SystemSimulationResult:
    s = store.get_system(system_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Sistema no encontrado")
    srng = random.Random(
        body.simulation_seed if body.simulation_seed is not None else (system_id.int % (2**31))
    )
    result = simulate_system(srng, s, body.advance_million_years, body.advanced_technology_threshold)
    for po in result.planets:
        if po.civilization is not None:
            civ_registry.record_from_simulation(
                system=result.system,
                planet_name=po.planet.name,
                civilization=po.civilization,
                run_label=f"stored:{system_id}",
            )
    return result


@app.get("/civilizations", response_model=list[CivilizationListItem])
def list_civilizations(
    system_id: UUID | None = None,
    min_technology: float | None = Query(default=None, ge=0, le=100),
    extinct_only: bool = Query(default=False),
    multiplanetary_only: bool = Query(default=False),
    hyper_only: bool = Query(default=False),
) -> list[CivilizationListItem]:
    return civ_registry.list_civilizations(
        system_id=system_id,
        min_technology=min_technology,
        extinct_only=extinct_only,
        multiplanetary_only=multiplanetary_only,
        hyper_only=hyper_only,
    )


@app.get("/technology/eras", response_model=list[TechnologyEraOut])
def technology_eras() -> list[TechnologyEraOut]:
    return list_all_eras()
