"""
Habitability and emergent 'life' evaluation.

Criteria are simplified Earth-analogs:
- Liquid water (temperature + water fraction)
- Atmospheric pressure and redox (O2 builds up with life; prebiotic needs other cues)
- Stellar distance (habitable zone)
- Shielding (magnetic field proxy vs radiation)
- Organic chemistry availability (CHNOPS proxy)

Not astrophysical simulation — scoring for game/emulator use.
"""

from __future__ import annotations

import math

from app.schemas import LifeLevel, PlanetOut, StarOut


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _temp_score_k(temp_k: float) -> float:
    """Peak around Earth mean ~288 K; allow cold/warm edges."""
    # Full liquid water at 1 atm is ~273–373 K; we score comfort band higher
    if temp_k < 200 or temp_k > 360:
        return 0.0
    # Gaussian-ish around 285 K
    sigma = 35.0
    return float(math.exp(-((temp_k - 285) ** 2) / (2 * sigma**2)))


def _water_score(liquid_water: float, temp_k: float) -> float:
    if liquid_water <= 0:
        return 0.0
    t = _temp_score_k(temp_k)
    return _clamp(liquid_water, 0, 1) * (0.3 + 0.7 * t)


def _atmosphere_score(pressure_bar: float, o2: float) -> float:
    # Too thin: no retention; too thick: runaway (simplified)
    if pressure_bar < 0.05 or pressure_bar > 50:
        return 0.2
    p = _clamp(pressure_bar, 0.1, 5.0)
    p_score = 1.0 - abs(math.log10(p)) / 2.0  # ~1 bar best
    p_score = _clamp(p_score, 0, 1)
    # Prebiotic: some O2 ok; high O2 often implies photosynthesis (flora proxy)
    o2_score = _clamp(o2 / 0.21, 0, 2) * 0.5 + 0.5 * (1.0 - abs(o2 - 0.21) / 0.5)
    o2_score = _clamp(o2_score, 0, 1)
    return 0.6 * p_score + 0.4 * o2_score


def _magnetosphere_score(b_earth: float) -> float:
    if b_earth < 0.05:
        return 0.3
    return _clamp(0.4 + 0.6 * min(b_earth, 2.0) / 2.0, 0, 1)


def compute_habitability_index(
    *,
    surface_temperature_k: float,
    liquid_water_fraction: float,
    atmosphere_pressure_bar: float,
    oxygen_fraction: float,
    magnetic_field_earth: float,
    organic_chemistry_score: float,
    in_habitable_zone: bool,
) -> float:
    if not in_habitable_zone:
        base = 0.35  # subsurface / exotic life window — keep nonzero rarely used
    else:
        base = 1.0

    w = _water_score(liquid_water_fraction, surface_temperature_k)
    t = _temp_score_k(surface_temperature_k)
    a = _atmosphere_score(atmosphere_pressure_bar, oxygen_fraction)
    m = _magnetosphere_score(magnetic_field_earth)
    c = _clamp(organic_chemistry_score, 0, 1)

    # Weighted blend → 0..100
    raw = base * (0.28 * w + 0.22 * t + 0.22 * a + 0.13 * m + 0.15 * c)
    return round(100 * _clamp(raw, 0, 1), 2)


def evaluate_life(
    star: StarOut,
    surface_temperature_k: float,
    liquid_water_fraction: float,
    atmosphere_pressure_bar: float,
    oxygen_fraction: float,
    magnetic_field_earth: float,
    organic_chemistry_score: float,
    in_habitable_zone: bool,
    habitability_index: float,
) -> tuple[LifeLevel, list[str]]:
    notes: list[str] = []

    if not in_habitable_zone:
        notes.append("Fuera de la zona habitable estelar; vida improbable salvo escenarios exóticos.")
        if habitability_index < 15:
            return LifeLevel.NONE, notes

    if liquid_water_fraction < 0.05:
        notes.append("Agua líquida insuficiente; difícil arranque bioquímico tipo terrestre.")
        if habitability_index < 25:
            return LifeLevel.NONE, notes

    if surface_temperature_k < 250 or surface_temperature_k > 340:
        notes.append("Temperatura marginal para agua líquida estable en superficie.")

    if atmosphere_pressure_bar < 0.3:
        notes.append("Presión atmosférica baja; evaporación y radiación UV adversas.")

    # Thresholds for emergence (stochastic layer can be added in generator)
    hi = habitability_index

    if hi < 35:
        return LifeLevel.NONE, notes

    if hi < 55:
        notes.append("Condiciones permiten química prebiótica sostenida; posible vida microbiana.")
        return LifeLevel.MICROBIAL, notes

    if hi < 75:
        notes.append("Hidrósfera y atmósfera estables; diversificación microbiana y ecosistemas simples plausibles.")
        if organic_chemistry_score < 0.35:
            notes.append("Inventario orgánico limitado; biota probablemente simple.")
        return LifeLevel.SIMPLE, notes

    notes.append("Biosfera potencialmente rica: ciclos de carbono/agua, oxígeno y campo magnético favorables (análogo flora/fauna).")
    if star.stellar_class.value in ("F",):
        notes.append("Estrella F: radiación UV elevada; estratosfera y ozono serían críticos.")
    return LifeLevel.COMPLEX, notes


def attach_life_to_planet(star: StarOut, p: PlanetOut) -> PlanetOut:
    hi = compute_habitability_index(
        surface_temperature_k=p.surface_temperature_k,
        liquid_water_fraction=p.liquid_water_fraction,
        atmosphere_pressure_bar=p.atmosphere_pressure_bar,
        oxygen_fraction=p.oxygen_fraction,
        magnetic_field_earth=p.magnetic_field_earth,
        organic_chemistry_score=p.organic_chemistry_score,
        in_habitable_zone=p.in_habitable_zone,
    )
    life, notes = evaluate_life(
        star,
        p.surface_temperature_k,
        p.liquid_water_fraction,
        p.atmosphere_pressure_bar,
        p.oxygen_fraction,
        p.magnetic_field_earth,
        p.organic_chemistry_score,
        p.in_habitable_zone,
        hi,
    )
    return p.model_copy(update={"habitability_index": hi, "life_level": life, "life_notes": notes})
