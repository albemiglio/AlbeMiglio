"""Centralised configuration.

NOTE: the API key is hard-coded here on explicit user request so the packaged
tool works with a single double-click (no setup). This is *not* a good practice
for shared/public code — anyone with this file has the key. Rotate it if it
leaks beyond your control. An environment variable, when set, still takes
precedence over the hard-coded value.
"""

from __future__ import annotations

import os

# Hard-coded fallback key (used for whichever remote provider is selected).
HARDCODED_API_KEY = "bkm8aWGw4IJgsjtiLPg3j2Osip1P1ag1Iw9Kti3y09138172"

# Default provider/language for the packaged, ready-to-run build.
DEFAULT_PROVIDER = "winston"
DEFAULT_LANGUAGE = "it"

# Per-provider environment variable names.
ENV_VARS = {
    "gptzero": "GPTZERO_API_KEY",
    "sapling": "SAPLING_API_KEY",
    "winston": "WINSTON_API_KEY",
}


def resolve_api_key(provider: str, explicit: str | None = None) -> str | None:
    """Key precedence: explicit arg > provider env var > hard-coded fallback."""
    if explicit:
        return explicit
    env_name = ENV_VARS.get(provider)
    if env_name and os.getenv(env_name):
        return os.getenv(env_name)
    return HARDCODED_API_KEY or None
