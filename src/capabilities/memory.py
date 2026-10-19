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
