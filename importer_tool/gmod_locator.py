from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class GModInstall:
    game_root: Path

    @property
    def mod_root(self) -> Path:
        return self.game_root / "garrysmod"

    @property
    def game_executable(self) -> Path | None:
        for exe_name in ("gmod.exe", "hl2.exe"):
            exe_path = self.game_root / exe_name
            if exe_path.exists():
                return exe_path
        return None

    def is_valid(self) -> bool:
        return self.game_root.exists() and self.mod_root.is_dir() and self.game_executable is not None


_LIBRARY_PATH_RE = re.compile(r'"\d+"\s*\{[^\{\}]*?"path"\s*"([^"]+)"', re.IGNORECASE | re.DOTALL)
_LIBRARY_VALUE_RE = re.compile(r'"path"\s*"([^"]+)"', re.IGNORECASE)



def _has_gmod_executable(path: Path) -> bool:
    return any((path / exe_name).exists() for exe_name in ("gmod.exe", "hl2.exe"))



def _looks_like_gmod_root(path: Path) -> bool:
    return path.exists() and (path / "garrysmod").is_dir() and _has_gmod_executable(path)



def normalize_game_root(path: str | Path) -> GModInstall:
    raw = Path(path).expanduser().resolve()

    if _looks_like_gmod_root(raw):
        return GModInstall(game_root=raw)

    if raw.name.lower() == "garrysmod" and raw.is_dir() and _looks_like_gmod_root(raw.parent):
        return GModInstall(game_root=raw.parent)

    raise FileNotFoundError(
        (
            f"Could not verify Garry's Mod install at '{raw}'. "
            "Pick the folder that contains gmod.exe (or hl2.exe on older installs) and the garrysmod directory."
        )
    )



def find_gmod_installations() -> list[GModInstall]:
    candidates: list[Path] = []
    seen: set[str] = set()

    def add_candidate(path: Path) -> None:
        try:
            path = path.resolve()
        except Exception:
            return
        key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        candidates.append(path)

    for steam_root in _find_steam_roots():
        add_candidate(steam_root / "steamapps" / "common" / "GarrysMod")
        add_candidate(steam_root / "steamapps" / "common" / "Garry's Mod")
        library_file = steam_root / "steamapps" / "libraryfolders.vdf"
        if library_file.is_file():
            for library_path in _parse_libraryfolders(library_file):
                add_candidate(library_path / "steamapps" / "common" / "GarrysMod")
                add_candidate(library_path / "steamapps" / "common" / "Garry's Mod")

    installs: list[GModInstall] = []
    for candidate in candidates:
        if _looks_like_gmod_root(candidate):
            installs.append(GModInstall(game_root=candidate))
    return installs



def _find_steam_roots() -> Iterable[Path]:
    env_candidates = [
        os.environ.get("STEAMDIR"),
        os.environ.get("STEAM_PATH"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("PROGRAMFILES"),
    ]

    for value in env_candidates:
        if not value:
            continue
        base = Path(value)
        if base.name.lower() == "steam":
            steam_path = base
        else:
            steam_path = base / "Steam"
        if steam_path.exists():
            yield steam_path

    if sys.platform == "win32":
        for steam_path in _steam_roots_from_registry():
            yield steam_path



def _steam_roots_from_registry() -> Iterable[Path]:
    try:
        import winreg
    except Exception:
        return []

    locations = [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamExe"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
    ]

    results: list[Path] = []
    for hive, key_path, value_name in locations:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                value, _ = winreg.QueryValueEx(key, value_name)
        except OSError:
            continue
        steam_path = Path(value)
        if steam_path.suffix.lower() == ".exe":
            steam_path = steam_path.parent
        if steam_path.exists():
            results.append(steam_path)
    return results



def _parse_libraryfolders(path: Path) -> list[Path]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    results: list[Path] = []

    for match in _LIBRARY_PATH_RE.finditer(text):
        raw = match.group(1).replace("\\\\", "\\")
        results.append(Path(raw))

    # Fallback for older / differently formatted VDF files.
    if not results:
        for raw in _LIBRARY_VALUE_RE.findall(text):
            normalized = raw.replace("\\\\", "\\")
            if "steamapps" in normalized.lower() or Path(normalized).exists():
                results.append(Path(normalized))

    deduped: list[Path] = []
    seen: set[str] = set()
    for item in results:
        key = str(item).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
