"""RCA method implementations and registry."""

from methods.base import RCAMethod
from methods.fault_tree import FaultTreeMethod
from methods.fishbone import FishboneMethod
from methods.five_why import FiveWhyMethod

_REGISTRY: dict[str, type[RCAMethod]] = {
    FiveWhyMethod.name: FiveWhyMethod,
    FishboneMethod.name: FishboneMethod,
    FaultTreeMethod.name: FaultTreeMethod,
}


def get_method(name: str) -> RCAMethod:
    """Return an instance of the registered RCA method strategy."""
    try:
        return _REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown RCA method: {name!r}. Known: {sorted(_REGISTRY)}") from exc


__all__ = [
    "FaultTreeMethod",
    "FishboneMethod",
    "FiveWhyMethod",
    "RCAMethod",
    "get_method",
]
