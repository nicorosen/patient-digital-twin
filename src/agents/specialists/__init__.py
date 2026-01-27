"""
Specialist agents for clinical consultation.

Provides a registry of all available specialists and a factory function.
"""

from src.agents.specialists.base import BaseSpecialist, Recommendation, SpecialistResponse
from src.agents.specialists.cardiology import CardiologySpecialist
from src.agents.specialists.dermatology import DermatologySpecialist
from src.agents.specialists.endocrinology import EndocrinologySpecialist
from src.agents.specialists.gastroenterology import GastroenterologySpecialist
from src.agents.specialists.nephrology import NephrologySpecialist
from src.agents.specialists.neurology import NeurologySpecialist
from src.agents.specialists.oncology import OncologySpecialist
from src.agents.specialists.orthopedics import OrthopedicsSpecialist
from src.agents.specialists.primary_care import PrimaryCareSpecialist
from src.agents.specialists.psychiatry import PsychiatrySpecialist
from src.agents.specialists.pulmonology import PulmonologySpecialist

SPECIALIST_REGISTRY: dict[str, type[BaseSpecialist]] = {
    "primary_care": PrimaryCareSpecialist,
    "cardiology": CardiologySpecialist,
    "endocrinology": EndocrinologySpecialist,
    "pulmonology": PulmonologySpecialist,
    "neurology": NeurologySpecialist,
    "gastroenterology": GastroenterologySpecialist,
    "oncology": OncologySpecialist,
    "psychiatry": PsychiatrySpecialist,
    "orthopedics": OrthopedicsSpecialist,
    "nephrology": NephrologySpecialist,
    "dermatology": DermatologySpecialist,
}

_instances: dict[str, BaseSpecialist] = {}


def get_specialist(name: str) -> BaseSpecialist:
    """Get a singleton specialist instance by name."""
    if name not in SPECIALIST_REGISTRY:
        raise ValueError(f"Unknown specialist: {name}. Available: {list(SPECIALIST_REGISTRY.keys())}")
    if name not in _instances:
        _instances[name] = SPECIALIST_REGISTRY[name]()
    return _instances[name]


__all__ = [
    "BaseSpecialist",
    "Recommendation",
    "SpecialistResponse",
    "SPECIALIST_REGISTRY",
    "get_specialist",
    "PrimaryCareSpecialist",
    "CardiologySpecialist",
    "EndocrinologySpecialist",
    "PulmonologySpecialist",
    "NeurologySpecialist",
    "GastroenterologySpecialist",
    "OncologySpecialist",
    "PsychiatrySpecialist",
    "OrthopedicsSpecialist",
    "NephrologySpecialist",
    "DermatologySpecialist",
]
