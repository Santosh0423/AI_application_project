"""Persistent user profile (the application's memory of the user's situation)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

NOT_SET = "Not set"
CITIZENSHIP_OPTIONS = [NOT_SET, "EU/EEA or Nordic citizen", "Non-EU citizen"]
STUDENT_TYPE_OPTIONS = [NOT_SET, "Degree student", "Exchange student", "Graduated / looking for work"]
STAY_OPTIONS = [NOT_SET, "Less than 1 year", "1 year or more"]
MAX_CITY_CHARS = 60


@dataclass
class UserProfile:
    citizenship: str = NOT_SET
    student_type: str = NOT_SET
    stay_length: str = NOT_SET
    city: str = ""

    def __post_init__(self):
        # Invalid stored values fall back to "Not set" instead of crashing.
        if self.citizenship not in CITIZENSHIP_OPTIONS:
            self.citizenship = NOT_SET
        if self.student_type not in STUDENT_TYPE_OPTIONS:
            self.student_type = NOT_SET
        if self.stay_length not in STAY_OPTIONS:
            self.stay_length = NOT_SET
        self.city = (self.city or "").strip()[:MAX_CITY_CHARS]

    def is_empty(self) -> bool:
        return self == UserProfile()

    def describe(self) -> str:
        """Short text used in the model prompt."""
        parts = []
        if self.citizenship != NOT_SET:
            parts.append(f"Citizenship: {self.citizenship}")
        if self.student_type != NOT_SET:
            parts.append(f"Status: {self.student_type}")
        if self.stay_length != NOT_SET:
            parts.append(f"Planned stay in Finland: {self.stay_length}")
        if self.city:
            parts.append(f"City: {self.city}")
        return "; ".join(parts) if parts else "Unknown (the user has not set a profile)"


class ProfileStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> UserProfile:
        if not self.path.exists():
            return UserProfile()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            fields = UserProfile.__dataclass_fields__
            return UserProfile(**{k: v for k, v in data.items() if k in fields and isinstance(v, str)})
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Could not read profile file %s: %s", self.path, exc)
            return UserProfile()

    def save(self, profile: UserProfile) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
