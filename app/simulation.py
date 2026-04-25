"""
Fast-forward temporal simulation: intelligence, technology, eras, extinctions, multiplanetary empires.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.schemas import (
    CivilizationOut,
    ExtinctionCause,
    LifeLevel,
    PlanetOut,
    PlanetSimulationOut,
    ResourceExploitationTier,
    SolarSystemOut,
    SystemSimulationResult,
)
from app.tech_eras import era_for_technology_score


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _years_to_intelligence_my(rng: random.Random, life: LifeLevel, habitability_index: float) -> float | None:
    if life is LifeLevel.NONE:
        return None
    hi = _clamp(habitability_index, 1, 100)
    speed = 0.45 + 0.9 * (hi / 100)
    if life is LifeLevel.MICROBIAL:
        base = 2200.0
    elif life is LifeLevel.SIMPLE:
        base = 750.0
    else:
        base = 140.0
    t = (base / speed) * rng.uniform(0.35, 1.65)
    return max(5.0, t)


def _life_level_after_wait(
    rng: random.Random,
    start: LifeLevel,
    habitability_index: float,
    wait_my: float,
) -> LifeLevel:
    if start is LifeLevel.NONE:
        return LifeLevel.NONE
    cur = start
    hi = habitability_index / 100.0
    if cur is LifeLevel.MICROBIAL and wait_my > 200 * (1.1 - hi * 0.25):
        if rng.random() < _clamp(0.15 + hi * 0.35, 0, 0.85):
            cur = LifeLevel.SIMPLE
    if cur is LifeLevel.SIMPLE and wait_my > 120 * (1.05 - hi * 0.2):
        if rng.random() < _clamp(0.2 + hi * 0.45, 0, 0.9):
            cur = LifeLevel.COMPLEX
    return cur


def _disposition_at_awakening(rng: random.Random, habitability_index: float, stellar_uv_stress: float) -> float:
    hi = _clamp(habitability_index, 0, 100)
    mu = 32.0 + hi * 0.38 - stellar_uv_stress * 8.0
    sigma = 16.0 + rng.uniform(-2, 2)
    return round(_clamp(rng.gauss(mu, sigma), 0.0, 100.0), 2)


def _tech_after_intel_my(tech_my: float, tau: float) -> float:
    if tech_my <= 0:
        return 0.0
    return 100.0 * (1.0 - math.exp(-tech_my / tau))


def _my_needed_for_tech(tau: float, target: float) -> float | None:
    if target <= 0:
        return 0.0
    if target >= 100:
        return None
    inner = 1.0 - (target / 100.0)
    if inner <= 0:
        return None
    return -tau * math.log(inner)


def _stellar_uv_stress(stellar_class: str) -> float:
    return {"M": 0.0, "K": 0.2, "G": 0.45, "F": 1.0}.get(stellar_class, 0.4)


def _extinction_roll(
    rng: random.Random,
    t_intel: float,
    wait: float,
    disposition: float,
    habitability_index: float,
    uv: float,
) -> tuple[float | None, ExtinctionCause | None, float]:
    """
    Returns (absolute extinction time from sim start, cause, years after intel until end or death).
    """
    remaining = wait - t_intel
    if remaining <= 0:
        return None, None, 0.0
    p = 0.075 + (50 - disposition) / 260 + (52 - habitability_index) / 420 + uv * 0.055
    p = _clamp(p, 0.028, 0.5)
    if rng.random() > p:
        return None, None, remaining
    t_die = t_intel + rng.uniform(max(4.0, remaining * 0.06), remaining * 0.94)
    weights: list[tuple[ExtinctionCause, float]] = [
        (ExtinctionCause.TOTAL_WAR, max(0.08, (48 - disposition) / 220)),
        (ExtinctionCause.BIOSPHERE_FAILURE, max(0.09, (55 - habitability_index) / 200)),
        (ExtinctionCause.RESOURCE_EXHAUSTION, 0.14),
        (ExtinctionCause.COLLAPSE, 0.18),
        (ExtinctionCause.STELLAR_CATASTROPHE, 0.08 + uv * 0.12),
        (ExtinctionCause.UNKNOWN, 0.12),
    ]
    total = sum(w for _, w in weights)
    r = rng.random() * total
    acc = 0.0
    cause = ExtinctionCause.UNKNOWN
    for c, w in weights:
        acc += w
        if r <= acc:
            cause = c
            break
    eff_after = max(0.0, t_die - t_intel)
    return t_die, cause, eff_after


def _breakthroughs(rng: random.Random, tech: float) -> tuple[float, list[str]]:
    t = tech
    ev: list[str] = []
    if rng.random() < 0.052 and t < 60:
        t = min(76.0, t + rng.uniform(14, 32))
        ev.append("anachronistic_leap")
    if rng.random() < 0.034 and 55 < t < 88:
        t = min(92.0, t + rng.uniform(4, 14))
        ev.append("paradigm_shift")
    if rng.random() < 0.018:
        ev.append("forbidden_physics_hint")
        t = min(100.0, t + rng.uniform(1, 6))
    if rng.random() < 0.012 and t >= 78:
        ev.append("computational_singularity_seed")
        t = min(100.0, t + rng.uniform(2, 9))
    return round(_clamp(t, 0, 100), 2), ev


def _resource_from_tech(tech: float, rng: random.Random) -> tuple[ResourceExploitationTier, float]:
    if tech < 36:
        tier = ResourceExploitationTier.LOCAL
        score = 12 + tech * 0.65
    elif tech < 60:
        tier = ResourceExploitationTier.PLANETARY
        score = 35 + (tech - 36) * 0.95
    elif tech < 84:
        tier = ResourceExploitationTier.SYSTEM_WIDE
        score = 56 + (tech - 60) * 0.85
    else:
        tier = ResourceExploitationTier.STELLAR_HARVEST
        score = 78 + (tech - 84) * 3.2
    score += rng.uniform(-3, 3)
    return tier, round(_clamp(score, 0, 100), 2)


def _hyper_metrics(tech: float) -> tuple[float, bool]:
    h = _clamp((tech - 87.0) / 13.0 * 100.0, 0.0, 100.0)
    is_h = tech >= 91.0 or h >= 58.0
    return round(h, 2), is_h


def _advanced_tech_milestone(
    tau: float,
    threshold: float,
    t_intel: float,
    wait: float,
    t_extinct: float | None,
) -> float | None:
    dt = _my_needed_for_tech(tau, threshold)
    if dt is None:
        return None
    t_hit = t_intel + dt
    limit = t_extinct if t_extinct is not None else wait
    if t_hit <= limit + 1e-9:
        return round(t_hit, 3)
    return None


@dataclass
class _SimParams:
    advance_my: float
    tech_threshold: float


def _make_civilization(
    *,
    rng: random.Random,
    tech: float,
    disposition: float,
    t_intel: float,
    wait: float,
    t_extinct: float | None,
    cause: ExtinctionCause | None,
    tau: float,
    params: _SimParams,
    breakthrough_events: list[str],
) -> CivilizationOut:
    survived = t_extinct is None
    extinct = not survived
    tier, rscore = _resource_from_tech(tech, rng)
    hyper_s, is_hyper = _hyper_metrics(tech)
    my_adv = _advanced_tech_milestone(tau, params.tech_threshold, t_intel, wait, t_extinct)

    return CivilizationOut(
        technology_score=tech,
        technology_era=era_for_technology_score(tech),
        disposition_score=disposition,
        million_years_to_intelligent_life=round(t_intel, 3),
        million_years_to_advanced_technology=my_adv,
        advanced_technology_threshold=params.tech_threshold,
        resource_exploitation_score=rscore,
        resource_exploitation_tier=tier,
        hyper_technology_score=hyper_s,
        is_hyper_technological=is_hyper,
        breakthrough_events=breakthrough_events,
        survived=survived,
        extinct=extinct,
        extinction_million_years=round(t_extinct, 3) if t_extinct is not None else None,
        extinction_cause=cause if extinct else None,
    )


def simulate_planet(
    rng: random.Random,
    planet: PlanetOut,
    habitability_index: float,
    stellar_class: str,
    params: _SimParams,
) -> PlanetSimulationOut:
    wait = params.advance_my
    matured = _life_level_after_wait(rng, planet.life_level, habitability_index, wait)

    t_intel = _years_to_intelligence_my(rng, planet.life_level, habitability_index)
    uv = _stellar_uv_stress(stellar_class)

    if t_intel is None or t_intel > wait:
        return PlanetSimulationOut(
            planet=planet,
            life_level_start=planet.life_level,
            life_level_end=matured,
            million_years_advanced=round(wait, 3),
            civilization=None,
        )

    disposition = _disposition_at_awakening(rng, habitability_index, uv)
    t_die, cause, eff_after = _extinction_roll(rng, t_intel, wait, disposition, habitability_index, uv)

    tau = 130.0 + 420.0 * rng.random()
    tau *= 1.05 - 0.35 * (habitability_index / 100.0)

    if t_die is None:
        base_tech = _tech_after_intel_my(eff_after, tau)
        t_extinct = None
        ext_cause = None
    else:
        base_tech = _tech_after_intel_my(eff_after, tau)
        t_extinct = t_die
        ext_cause = cause

    tech, b_events = _breakthroughs(rng, round(base_tech, 2))
    civ = _make_civilization(
        rng=rng,
        tech=tech,
        disposition=disposition,
        t_intel=t_intel,
        wait=wait,
        t_extinct=t_extinct,
        cause=ext_cause,
        tau=tau,
        params=params,
        breakthrough_events=b_events,
    )

    return PlanetSimulationOut(
        planet=planet,
        life_level_start=planet.life_level,
        life_level_end=LifeLevel.INTELLIGENT,
        million_years_advanced=round(wait, 3),
        civilization=civ,
    )


def _multiplanetary_adjust(
    rng: random.Random,
    civ: CivilizationOut,
    colonizable: int,
    is_dominant: bool,
    competing_civs: int,
) -> CivilizationOut:
    if not is_dominant:
        minor = round(_clamp(8 + civ.technology_score * 0.12 + rng.uniform(-4, 4), 0, 35), 2)
        return civ.model_copy(
            update={
                "is_multiplanetary": False,
                "multiplanetary_score": minor,
                "estimated_controlled_worlds": 1,
                "is_dominant_system_polity": False,
            }
        )
    if civ.extinct or civ.technology_score < 62:
        return civ.model_copy(
            update={
                "is_multiplanetary": False,
                "multiplanetary_score": round(rng.uniform(0, 18), 2),
                "estimated_controlled_worlds": 1,
                "is_dominant_system_polity": True,
            }
        )
    if colonizable < 2:
        return civ.model_copy(
            update={
                "is_multiplanetary": False,
                "multiplanetary_score": round(rng.uniform(4, 22), 2),
                "estimated_controlled_worlds": 1,
                "is_dominant_system_polity": True,
            }
        )
    base_p = (
        0.11
        + (civ.technology_score - 62) / 170
        + max(0, colonizable - 2) * 0.065
        - max(0, competing_civs - 1) * 0.16
    )
    if civ.disposition_score < 38:
        base_p += 0.09
    elif civ.disposition_score > 72:
        base_p += 0.05
    base_p = _clamp(base_p, 0, 0.84)
    if rng.random() > base_p:
        return civ.model_copy(
            update={
                "is_multiplanetary": False,
                "multiplanetary_score": round(rng.uniform(6, 28), 2),
                "estimated_controlled_worlds": 1,
                "is_dominant_system_polity": True,
            }
        )
    worlds = min(colonizable, 2 + int(rng.random() * min(6, max(1, colonizable - 1))))
    mscore = _clamp(42 + (civ.technology_score - 68) * 0.85 + rng.uniform(-10, 20), 0, 100)
    tier = civ.resource_exploitation_tier
    rscore = civ.resource_exploitation_score + rng.uniform(8, 20)
    if civ.technology_score >= 76 and tier != ResourceExploitationTier.STELLAR_HARVEST:
        tier = ResourceExploitationTier.SYSTEM_WIDE
    if civ.technology_score >= 86:
        tier = ResourceExploitationTier.STELLAR_HARVEST
    rscore = round(_clamp(rscore, 0, 100), 2)
    return civ.model_copy(
        update={
            "is_multiplanetary": True,
            "multiplanetary_score": round(mscore, 2),
            "estimated_controlled_worlds": worlds,
            "is_dominant_system_polity": True,
            "resource_exploitation_tier": tier,
            "resource_exploitation_score": rscore,
        }
    )


def _finalize_system_empire(
    rng: random.Random,
    planets_out: list[PlanetSimulationOut],
    colonizable_worlds: int,
) -> list[PlanetSimulationOut]:
    civ_idx = [i for i, p in enumerate(planets_out) if p.civilization is not None]
    if not civ_idx:
        return planets_out
    competing = len(civ_idx)
    primary_i = max(
        civ_idx,
        key=lambda i: (
            planets_out[i].civilization.technology_score if planets_out[i].civilization else -1,
            planets_out[i].planet.habitability_index,
        ),
    )
    out: list[PlanetSimulationOut] = []
    for i, po in enumerate(planets_out):
        if po.civilization is None:
            out.append(po)
            continue
        civ = _multiplanetary_adjust(
            rng,
            po.civilization,
            colonizable_worlds,
            is_dominant=(i == primary_i),
            competing_civs=competing,
        )
        out.append(po.model_copy(update={"civilization": civ}))
    return out


def simulate_system(
    rng: random.Random,
    system: SolarSystemOut,
    advance_million_years: float,
    advanced_technology_threshold: float,
) -> SystemSimulationResult:
    colonizable = sum(
        1 for p in system.planets if p.in_habitable_zone and p.habitability_index >= 33.0
    )
    params = _SimParams(advance_my=advance_million_years, tech_threshold=advanced_technology_threshold)
    planets_out: list[PlanetSimulationOut] = []
    for p in system.planets:
        planets_out.append(
            simulate_planet(
                rng,
                p,
                p.habitability_index,
                system.star.stellar_class.value,
                params,
            )
        )
    planets_out = _finalize_system_empire(rng, planets_out, colonizable)
    empire = any(
        po.civilization is not None and po.civilization.is_multiplanetary for po in planets_out
    )
    return SystemSimulationResult(
        system=system,
        planets=planets_out,
        colonizable_worlds_count=colonizable,
        system_multiplanetary_empire=empire,
    )
