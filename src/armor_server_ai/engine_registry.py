"""Strict discovery of pre-built TensorRT engines; never compiles or downloads a model.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

A directory must hold a non-empty ``daylight.engine`` and ``low_light.engine``.
When it also holds ``engines.json`` (``{"daylight": "<sha256>", "low_light":
"<sha256>"}``) every engine must match its recorded SHA-256, so a swapped or
corrupted engine is refused instead of being loaded onto the GPU. Without a
manifest the engines are accepted but reported as *unverified*.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

NAMES = ("daylight", "low_light")
MANIFEST = "engines.json"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EngineRegistryError(ValueError):
    """The engine directory cannot be trusted."""


@dataclass(frozen=True)
class EngineSet:
    daylight: Path
    low_light: Path
    #: True only when every engine matched a recorded SHA-256.
    verified: bool = False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_manifest(root: Path) -> dict[str, str] | None:
    path = root / MANIFEST
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise EngineRegistryError(f"{MANIFEST} cannot be read: {error}") from error
    if not isinstance(data, dict) or set(data) != set(NAMES):
        raise EngineRegistryError(f"{MANIFEST} must list exactly {', '.join(NAMES)}")
    for name, value in data.items():
        if not isinstance(value, str) or not _SHA256.match(value):
            raise EngineRegistryError(f"{MANIFEST}: {name} must be a lowercase SHA-256")
    return data


def discover_engines(root: Path) -> EngineSet:
    if not root.is_dir():
        raise EngineRegistryError("engine directory does not exist")
    paths = {name: root / f"{name}.engine" for name in NAMES}
    missing = [path.name for path in paths.values() if not path.is_file() or path.stat().st_size == 0]
    if missing:
        raise EngineRegistryError("missing non-empty engine files: " + ", ".join(missing))
    manifest = _read_manifest(root)
    if manifest is not None:
        wrong = [f"{name}.engine" for name, path in paths.items() if _sha256(path) != manifest[name]]
        if wrong:
            raise EngineRegistryError("engine does not match its recorded SHA-256: " + ", ".join(wrong))
    return EngineSet(**paths, verified=manifest is not None)
