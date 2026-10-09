"""Réglages utilisateur : touches et volume, dans ``%APPDATA%\\Batterie\\settings.toml``.

Au premier lancement, le fichier n'existe pas : on écrit un modèle commenté avec les
valeurs par défaut (cadrage §2.4), que tu peux ouvrir avec le Bloc-notes et modifier.
Les lancements suivants lisent ce fichier tel quel, sans jamais écraser tes modifications
ou tes commentaires.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

import tomli_w
from platformdirs import user_config_dir

from batterie.core.elements import ELEMENTS

APP_NAME = "Batterie"


def settings_path() -> Path:
    """Chemin de ``settings.toml`` (``%APPDATA%\\Batterie\\settings.toml`` sous Windows)."""
    return Path(user_config_dir(APP_NAME, appauthor=False, roaming=True)) / "settings.toml"


def _default_key_map() -> dict[str, str]:
    return {element.id: element.default_scancode_name for element in ELEMENTS}


@dataclass
class Settings:
    """Touches personnalisées (id d'élément -> nom de scancode) et volume (0.0 à 1.0)."""

    key_map: dict[str, str] = field(default_factory=_default_key_map)
    volume: float = 1.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _render_default_template() -> str:
    """Modèle commenté écrit au premier lancement, à partir des valeurs par défaut."""
    lines = [
        "# Réglages de Batterie.",
        "# volume : de 0.0 (muet) à 1.0 (fort).",
        "#",
        '# [keys] : une ligne par élément, élément = "NOM_TOUCHE".',
        "# NOM_TOUCHE est la position physique de la touche, nommée comme sur un clavier",
        "# QWERTY américain (pas forcément la lettre imprimée sur TON clavier). Le",
        "# commentaire en bout de ligne montre la lettre affichée en AZERTY français.",
        "# Exemples de noms valides : A-Z, 0-9, SPACE, LSHIFT, RETURN, TAB...",
        "volume = 1.0",
        "",
        "[keys]",
    ]
    width = max(len(element.id) for element in ELEMENTS)
    for element in ELEMENTS:
        assignment = f'{element.id:<{width}} = "{element.default_scancode_name}"'
        lines.append(f"{assignment}  # {element.key_label}")
    lines.append("")
    return "\n".join(lines)


def load_settings(path: Path | None = None) -> Settings:
    """Charge les réglages depuis ``path`` (ou le chemin par défaut).

    Si le fichier n'existe pas encore, l'écrit avec un modèle commenté et renvoie les
    valeurs par défaut.
    """
    target = path if path is not None else settings_path()
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_render_default_template(), encoding="utf-8")
        return Settings()

    with target.open("rb") as handle:
        data = tomllib.load(handle)

    key_map = {**_default_key_map(), **data.get("keys", {})}
    volume = _clamp01(float(data.get("volume", 1.0)))
    return Settings(key_map=key_map, volume=volume)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Écrit ``settings`` dans ``path`` (ou le chemin par défaut), sans commentaires."""
    target = path if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {"volume": settings.volume, "keys": settings.key_map}
    with target.open("wb") as handle:
        tomli_w.dump(data, handle)
