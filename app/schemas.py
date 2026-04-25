from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class StellarClass(str, Enum):
    """Rough mass/luminosity bins for procedural HZ."""

    M = "M"
    K = "K"
    G = "G"
    F = "F"


class LifeLevel(str, Enum):
    NONE = "none"
    MICROBIAL = "microbial"
    SIMPLE = "simple"  # multicellular / basic ecosystems
    COMPLEX = "complex"  # flora-fauna analog, stable biosphere
    INTELLIGENT = "intelligent"  # asignado tras la simulación temporal (civilización)


class StarOut(BaseModel):
    stellar_class: StellarClass
    mass_solar: float = Field(description="Mass in solar masses (approximate)")
    luminosity_solar: float
    habitable_zone_inner_au: float
    habitable_zone_outer_au: float


class PlanetOut(BaseModel):
    name: str
    orbital_distance_au: float
    radius_earth: float
    mass_earth: float
    surface_temperature_k: float
    liquid_water_fraction: float = Field(ge=0, le=1, description="0–1 proxy for surface/volatile water")
    atmosphere_pressure_bar: float
    oxygen_fraction: float = Field(ge=0, le=1, description="Molecular O2 mole fraction (proxy)")
    magnetic_field_earth: float = Field(description="Dipole strength vs Earth = 1")
    organic_chemistry_score: float = Field(ge=0, le=1, description="CHNOPS / prebiotic chemistry proxy")
    in_habitable_zone: bool
    habitability_index: float = Field(ge=0, le=100)
    life_level: LifeLevel
    life_notes: list[str] = Field(default_factory=list)


class SolarSystemOut(BaseModel):
    id: UUID
    name: str
    star: StarOut
    planets: list[PlanetOut]


class GenerateSystemRequest(BaseModel):
    seed: int | None = Field(default=None, description="Optional RNG seed for reproducibility")
    min_planets: int = Field(default=3, ge=1, le=20)
    max_planets: int = Field(default=10, ge=1, le=20)
    name: str | None = Field(default=None, description="Optional display name")


class HealthOut(BaseModel):
    status: str
    app: str


class ExtinctionCause(str, Enum):
    COLLAPSE = "collapse"
    TOTAL_WAR = "total_war"
    BIOSPHERE_FAILURE = "biosphere_failure"
    STELLAR_CATASTROPHE = "stellar_catastrophe"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    UNKNOWN = "unknown"


class ResourceExploitationTier(str, Enum):
    LOCAL = "local"
    PLANETARY = "planetary"
    SYSTEM_WIDE = "system_wide"
    STELLAR_HARVEST = "stellar_harvest"


class TechnologyEraOut(BaseModel):
    era_key: str
    label_es: str
    score_range_min: float
    score_range_max: float


class CivilizationOut(BaseModel):
    technology_score: float = Field(ge=0, le=100, description="Nivel tecnológico al cierre del fast-forward o al extinción")
    technology_era: TechnologyEraOut
    disposition_score: float = Field(
        ge=0,
        le=100,
        description="Tendencia civilizacional: 0 expansionista/hostil, 100 cooperativo/pacifista",
    )
    million_years_to_intelligent_life: float = Field(ge=0)
    million_years_to_advanced_technology: float | None = Field(
        default=None,
        description="My desde el inicio hasta superar el umbral; None si no se alcanzó",
    )
    advanced_technology_threshold: float = Field(ge=0, le=100, default=80)
    resource_exploitation_score: float = Field(
        ge=0,
        le=100,
        description="0 uso local, 100 extracción a escala estelar",
    )
    resource_exploitation_tier: ResourceExploitationTier
    hyper_technology_score: float = Field(
        ge=0,
        le=100,
        description="Sub-score 0–100 para física/tecnología de frontera (a partir de ~88 de tecnología global)",
    )
    is_hyper_technological: bool = Field(description="Civilización hipertecnológica (umbrales altos de tech / hiper-score)")
    is_multiplanetary: bool = False
    multiplanetary_score: float = Field(default=0, ge=0, le=100)
    estimated_controlled_worlds: int = Field(default=1, ge=1, le=99)
    is_dominant_system_polity: bool = True
    breakthrough_events: list[str] = Field(default_factory=list, description="Códigos de saltos o hallazgos anómalos")
    survived: bool = True
    extinct: bool = False
    extinction_million_years: float | None = Field(
        default=None,
        description="My desde el inicio de la simulación hasta la extinción civilizatoria",
    )
    extinction_cause: ExtinctionCause | None = None


class CivilizationListItem(BaseModel):
    id: UUID
    system_id: UUID
    system_name: str
    homeworld: str
    civilization: CivilizationOut
    run_label: str | None = None


class PlanetSimulationOut(BaseModel):
    planet: PlanetOut
    life_level_start: LifeLevel
    life_level_end: LifeLevel
    million_years_advanced: float = Field(ge=0, description="Fast-forward aplicado (My)")
    civilization: CivilizationOut | None = None


class SystemSimulationResult(BaseModel):
    system: SolarSystemOut
    planets: list[PlanetSimulationOut]
    colonizable_worlds_count: int = Field(ge=0, description="Planetas en HZ con habitabilidad mínima para expansión")
    system_multiplanetary_empire: bool = Field(
        default=False,
        description="Hay al menos un polo tecnológico dominante con presencia multiplanetaria",
    )


class BatchSimulationRequest(BaseModel):
    system_count: int = Field(ge=1, le=500, description="Sistemas generados y simulados uno tras otro")
    seed: int | None = Field(default=None, description="Semilla base; el sistema i usa seed+i si seed fija")
    min_planets: int = Field(default=3, ge=1, le=20)
    max_planets: int = Field(default=8, ge=1, le=20)
    name_prefix: str | None = Field(default=None, description="Opcional: nombres SystemName-1, SystemName-2, ...")
    advance_million_years: float = Field(
        default=800.0,
        ge=0,
        le=50_000,
        description="Años de fast-forward por sistema (millones de años)",
    )
    advanced_technology_threshold: float = Field(default=80.0, ge=0, le=100)


class BatchSimulationResult(BaseModel):
    generation_base_seed: int = Field(description="Semilla base usada (explícita o generada) para reproducir el lote")
    advance_million_years_per_system: float
    advanced_technology_threshold: float
    runs: list[SystemSimulationResult]


class AdvanceStoredSystemRequest(BaseModel):
    advance_million_years: float = Field(default=500.0, ge=0, le=50_000)
    advanced_technology_threshold: float = Field(default=80.0, ge=0, le=100)
    simulation_seed: int | None = Field(default=None, description="Semilla solo para la fase estocástica temporal")
