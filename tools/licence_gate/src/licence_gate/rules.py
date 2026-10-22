"""Licence and component rules for the model registry (ADR-005, NFR-S6).

Sources for the banned lists: research of 2026-10-17 recorded in
docs/research/sources-2026-10-17.md (InsightFace model licence, CelebAMask-HQ terms,
dlib iBUG 300-W restriction, CodeFormer S-Lab licence, Basel Face Model 2009, and
non-commercial or revenue-capped TTS licences), and research of 2026-10-22 in
docs/research/sources-2026-10-22.md (SMPL-X and AMASS licences, OpenPose licence).
"""

from __future__ import annotations

import re
from enum import Enum

ALLOWED_LICENCES = frozenset(
    {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "MPL-2.0", "Unlicense", "CC0-1.0"}
)

# Commercially usable, but only with obligations that reviewers must record in `conditions`.
CONDITIONAL_LICENCES = frozenset(
    {
        "CC-BY-4.0",
        "OpenMDW-1.1",
        "LiveKit-Model-License",
        "OpenRAIL-M",
        "CreativeML-OpenRAIL-M",
        "OpenRAIL++",
        "NVIDIA-Open-Model-License",
    }
)
CUSTOM_LICENCE_PREFIX = "LicenseRef-"

# Non-commercial, research-only or revenue-capped licences seen in candidate models.
BANNED_LICENCES = frozenset(
    name.lower()
    for name in (
        "Coqui-Public-Model-License",
        "Fish-Audio-Community-License",
        "NeuTTS-Open-License",
        "bilibili-Model-Use-License",
        "Boson-Community-License",
        "S-Lab-License-1.0",
        "Gaussian-Splatting-License",
    )
)
BANNED_LICENCE_PATTERN = re.compile(r"(-NC-|-NC$|noncommercial|non-commercial|research|academic)", re.I)

# Weight files and components that are non-commercial even when the host repo is permissive.
BANNED_COMPONENT_PATTERN = re.compile(
    r"insightface|buffalo_[a-z]|scrfd|2d106det|det_(?:10g|2\.5g|500m)|glintr100|w600k|inswapper"
    r"|79999_iter|celebamask|shape_predictor_68|codeformer|basel[ _-]?face|morphablemodel|(?<![a-z])bfm"
    # SMPL/SMPL-H/SMPL-X body models, AMASS motion data and OpenPose weights (spec v1.1, gestures).
    r"|(?<![a-z])smpl|(?<![a-z])amass|openpose",
    re.I,
)


class LicenceClass(Enum):
    ALLOWED = "allowed"
    CONDITIONAL = "conditional"
    BANNED = "banned"
    UNKNOWN = "unknown"


def classify_licence(identifier: str) -> LicenceClass:
    if identifier.lower() in BANNED_LICENCES or BANNED_LICENCE_PATTERN.search(identifier):
        return LicenceClass.BANNED
    if identifier in ALLOWED_LICENCES:
        return LicenceClass.ALLOWED
    if identifier in CONDITIONAL_LICENCES or identifier.startswith(CUSTOM_LICENCE_PREFIX):
        return LicenceClass.CONDITIONAL
    return LicenceClass.UNKNOWN


def is_banned_component(text: str) -> bool:
    return BANNED_COMPONENT_PATTERN.search(text) is not None
