"""Shared GEE init helper, mirrored from the leaves-ph pipeline.

Auth sources in order:

    1. Service account key at TUBIG_MAP_EE_KEY (env var pointing to a JSON file).
    2. Service account key at <repo>/.ee-key.json (gitignored).
    3. Interactive credentials at ~/.config/earthengine/credentials.

Personal Earth Engine key only (GCP project poised-honor-217909); never a work
project. Re-import-safe: ee is only initialised once.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import ee

REPO_ROOT = Path(__file__).resolve().parent.parent

_initialised = False


def init() -> None:
    """Initialise Earth Engine. Idempotent."""
    global _initialised
    if _initialised:
        return

    env_key = os.environ.get("TUBIG_MAP_EE_KEY")
    if env_key and Path(env_key).exists():
        _init_service_account(env_key)
        _initialised = True
        return

    repo_key = REPO_ROOT / ".ee-key.json"
    if repo_key.exists():
        _init_service_account(str(repo_key))
        _initialised = True
        return

    interactive = Path.home() / ".config" / "earthengine" / "credentials"
    if interactive.exists():
        ee.Initialize()
        _initialised = True
        return

    raise RuntimeError(
        "Earth Engine not authenticated. Run `earthengine authenticate` for interactive "
        "auth, or place a service-account JSON at .ee-key.json."
    )


def _init_service_account(key_path: str) -> None:
    with open(key_path) as f:
        key = json.load(f)
    credentials = ee.ServiceAccountCredentials(key["client_email"], key_path)
    ee.Initialize(credentials)
