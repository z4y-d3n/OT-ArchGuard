"""Public validated-model entry points. No partial model escapes on fatal input."""

import hashlib
from dataclasses import dataclass
from pathlib import Path

from otarchguard.contract import RESOURCE_LIMITS, ResourceLimits
from otarchguard.domain import ArchitectureSnapshot
from otarchguard.loading import YamlValue, load_bytes, load_file
from otarchguard.normalization import canonical_bytes, normalize
from otarchguard.parsing import parse_model
from otarchguard.validation import validate_structure


@dataclass(frozen=True, slots=True)
class ValidatedArchitecture:
    model: ArchitectureSnapshot
    canonical_json: bytes
    sha256: str


def _validate(value: YamlValue, limits: ResourceLimits) -> ValidatedArchitecture:
    model = parse_model(value, limits)
    validate_structure(model)
    normalized = normalize(model)
    canonical = canonical_bytes(normalized)
    return ValidatedArchitecture(normalized, canonical, hashlib.sha256(canonical).hexdigest())


def validate_bytes(data: bytes, limits: ResourceLimits = RESOURCE_LIMITS) -> ValidatedArchitecture:
    return _validate(load_bytes(data, limits), limits)


def validate_file(path: Path, limits: ResourceLimits = RESOURCE_LIMITS) -> ValidatedArchitecture:
    return _validate(load_file(path, limits), limits)
