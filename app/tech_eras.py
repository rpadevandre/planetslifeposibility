"""
Etapas civilizatorias nombradas según technology_score (0–100). Referencia lúdica, no histórica estricta.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import TechnologyEraOut


@dataclass(frozen=True)
class _EraBand:
    key: str
    label_es: str
    score_min: float
    score_max: float


_BANDS: tuple[_EraBand, ...] = (
    _EraBand("paleolithic", "Edad de piedra (paleolítico)", 0, 4),
    _EraBand("neolithic", "Neolítico y primeras aldeas", 4, 11),
    _EraBand("bronze_age", "Edad de bronce", 11, 21),
    _EraBand("classical", "Antigüedad clásica", 21, 33),
    _EraBand("medieval", "Edad media / feudal", 33, 45),
    _EraBand("early_modern", "Edad moderna temprana", 45, 55),
    _EraBand("industrial", "Revolución industrial", 55, 65),
    _EraBand("atomic_early_space", "Era atómica / primer espacio", 65, 74),
    _EraBand("information", "Informática y globalización", 74, 82),
    _EraBand("interplanetary", "Civilización interestelar local / multiplaneta", 82, 90),
    _EraBand("stellar_harvesting", "Dominio del sistema estelar (recursos estelares)", 90, 96),
    _EraBand("hypertechnological", "Hipertecnología / física de frontera", 96, 100.01),
)


def era_for_technology_score(tech: float) -> TechnologyEraOut:
    t = max(0.0, min(100.0, tech))
    for b in _BANDS:
        if b.score_min <= t < b.score_max:
            return TechnologyEraOut(
                era_key=b.key,
                label_es=b.label_es,
                score_range_min=b.score_min,
                score_range_max=b.score_max,
            )
    last = _BANDS[-1]
    return TechnologyEraOut(
        era_key=last.key,
        label_es=last.label_es,
        score_range_min=last.score_min,
        score_range_max=100.0,
    )


def list_all_eras() -> list[TechnologyEraOut]:
    return [
        TechnologyEraOut(
            era_key=b.key,
            label_es=b.label_es,
            score_range_min=b.score_min,
            score_range_max=min(b.score_max, 100.0),
        )
        for b in _BANDS
    ]
