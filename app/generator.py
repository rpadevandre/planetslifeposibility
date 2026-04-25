"""
Procedural solar system generation with Earth-like habitability heuristics.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

from app.life import attach_life_to_planet
from app.schemas import LifeLevel, PlanetOut, SolarSystemOut, StarOut, StellarClass


@dataclass(frozen=True)
class _StarTemplate:
    mass_solar: float
    luminosity_solar: float
    hz_inner_au: float
    hz_outer_au: float


# Approximate HZ for main-sequence (very rough game values)
_TEMPLATES: dict[StellarClass, _StarTemplate] = {
    StellarClass.M: _StarTemplate(0.45, 0.04, 0.12, 0.28),
    StellarClass.K: _StarTemplate(0.75, 0.45, 0.45, 0.95),
    StellarClass.G: _StarTemplate(1.0, 1.0, 0.85, 1.35),
    StellarClass.F: _StarTemplate(1.25, 2.2, 1.15, 2.15),
}

_PLANET_NAMES = (
    "Astra",
    "Boreal",
    "Calyx",
    "Dysis",
    "Eos",
    "Fen",
    "Gyre",
    "Helix",
    "Ixion",
    "Jura",
    "Kest",
    "Lumen",
    "Mire",
    "Nadir",
    "Orin",
    "Pyre",
    "Quill",
    "Riven",
    "Sable",
    "Tarn",
)


def _rng(seed: int | None) -> random.Random:
    return random.Random(seed)


def _pick_star(rng: random.Random) -> StarOut:
    cls = rng.choices(
        [StellarClass.M, StellarClass.K, StellarClass.G, StellarClass.F],
        weights=[0.35, 0.35, 0.25, 0.05],
        k=1,
    )[0]
    t = _TEMPLATES[cls]
    # jitter HZ edges slightly
    j = 0.92 + 0.16 * rng.random()
    inner = t.hz_inner_au * j
    outer = t.hz_outer_au * (1.1 - 0.2 * rng.random())
    return StarOut(
        stellar_class=cls,
        mass_solar=round(t.mass_solar * (0.95 + 0.1 * rng.random()), 3),
        luminosity_solar=round(t.luminosity_solar * (0.9 + 0.2 * rng.random()), 3),
        habitable_zone_inner_au=round(inner, 4),
        habitable_zone_outer_au=round(outer, 4),
    )


def _planet_temperature_k(star: StarOut, distance_au: float, greenhouse: float) -> float:
    # Very rough equilibrium temperature + greenhouse delta (Earth ~288 K)
    d = max(distance_au, 0.05)
    t_eff = 278 * (star.luminosity_solar**0.25) / (d**0.5)
    return t_eff + greenhouse


def generate_solar_system(
    *,
    seed: int | None,
    min_planets: int,
    max_planets: int,
    name: str | None,
) -> SolarSystemOut:
    rng = _rng(seed)
    star = _pick_star(rng)
    n = rng.randint(min_planets, max(max_planets, min_planets))

    # spacing: log-uniform distances from star
    inner_orbit = star.habitable_zone_inner_au * 0.35
    outer_orbit = star.habitable_zone_outer_au * 2.8
    distances = sorted(
        [inner_orbit * (outer_orbit / inner_orbit) ** rng.random() for _ in range(n)]
    )

    used_names = set()
    planets: list[PlanetOut] = []
    for i, d_au in enumerate(distances):
        pname = f"{rng.choice(_PLANET_NAMES)}-{i + 1}"
        while pname in used_names:
            pname = f"{rng.choice(_PLANET_NAMES)}-{i + 1}-{rng.randint(1, 999)}"
        used_names.add(pname)

        in_hz = star.habitable_zone_inner_au <= d_au <= star.habitable_zone_outer_au
        greenhouse = rng.uniform(5, 65) if in_hz else rng.uniform(-40, 35)
        temp_k = _planet_temperature_k(star, d_au, greenhouse)

        # Water & atmosphere correlate with HZ and mass
        mass_earth = round(10 ** rng.uniform(-0.2, 1.1), 3)
        radius_earth = round(mass_earth ** (1 / 3.7), 3)

        if in_hz and temp_k > 265 and temp_k < 330:
            water = rng.uniform(0.1, 1.0)
        elif temp_k < 273:
            water = rng.uniform(0, 0.25)
        else:
            water = rng.uniform(0, 0.6)

        if in_hz:
            pressure = round(10 ** rng.uniform(-0.5, 0.5), 3)  # ~0.3–3 bar
        else:
            pressure = round(10 ** rng.uniform(-2.5, 0.2), 4)

        # O2: higher if we already have stable water + temp (photosynthesis proxy)
        if in_hz and water > 0.35 and 270 < temp_k < 315:
            o2 = rng.uniform(0.05, 0.25)
        else:
            o2 = rng.uniform(0, 0.08)

        b_field = round(10 ** rng.uniform(-0.8, 0.4), 3)
        organic = round(rng.uniform(0.15, 0.95) if in_hz else rng.uniform(0.05, 0.5), 3)

        p = PlanetOut(
            name=pname,
            orbital_distance_au=round(d_au, 5),
            radius_earth=radius_earth,
            mass_earth=mass_earth,
            surface_temperature_k=round(temp_k, 2),
            liquid_water_fraction=round(water, 3),
            atmosphere_pressure_bar=pressure,
            oxygen_fraction=round(o2, 4),
            magnetic_field_earth=b_field,
            organic_chemistry_score=organic,
            in_habitable_zone=in_hz,
            habitability_index=0.0,
            life_level=LifeLevel.NONE,
            life_notes=[],
        )
        p = attach_life_to_planet(star, p)
        planets.append(p)

    sys_name = name or f"System-{str(uuid.uuid4())[:8]}"
    return SolarSystemOut(id=uuid.uuid4(), name=sys_name, star=star, planets=planets)
