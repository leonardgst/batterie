"""Zones de frappe calibrées : ``zones.toml`` dans ``%APPDATA%\\Batterie``.

Fichier séparé de ``settings.toml`` (qui n'est jamais réécrit, pour préserver tes
modifications et tes commentaires) : ``zones.toml`` est écrit par l'écran de calibration et
n'est pas fait pour être édité à la main. Les coordonnées sont celles de l'image réduite du
processus vision ; le fichier note la largeur de cette image (``working_width``) pour
refuser des zones calibrées avec une autre.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from batterie.config.settings import settings_path
from batterie.input.vision.zones import Zone, ZoneMap

FORMAT_VERSION = 1

_HEADER = (
    "# Zones de frappe de la caméra, écrites par l'écran de calibration de Batterie.\n"
    "# Ne pas éditer à la main : recalibre depuis l'application.\n"
)
_ZONE_FIELDS = ("x_min", "x_max", "y_top", "strike_plane_y", "y_bottom")


class ZonesError(ValueError):
    """``zones.toml`` illisible ou invalide (le message dit lequel et pourquoi)."""


def zones_path() -> Path:
    """Chemin de ``zones.toml``, à côté de ``settings.toml``."""
    return settings_path().with_name("zones.toml")


def load_zones(path: Path | None = None, *, working_width: int | None = None) -> ZoneMap:
    """Charge les zones depuis ``path`` (ou le chemin par défaut).

    Renvoie une ``ZoneMap`` vide si le fichier n'existe pas encore (rien n'est calibré).
    Si ``working_width`` est donné, refuse un fichier calibré avec une autre largeur
    d'image. Lève ``ZonesError`` si le fichier est invalide.
    """
    target = path if path is not None else zones_path()
    if not target.exists():
        return ZoneMap()

    try:
        with target.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as error:
        raise ZonesError(f"{target} : fichier illisible ({error})") from error

    if data.get("version") != FORMAT_VERSION:
        raise ZonesError(
            f"{target} : version {data.get('version')!r} non gérée (attendu : {FORMAT_VERSION})"
        )
    saved_width = data.get("working_width")
    if working_width is not None and saved_width != working_width:
        raise ZonesError(
            f"{target} : zones calibrées pour une image de {saved_width} px de large, "
            f"l'application en utilise {working_width} : recalibre"
        )

    zones = []
    for index, entry in enumerate(data.get("zones", []), start=1):
        label = f"{target} : zone n°{index}"
        if "element" not in entry:
            raise ZonesError(f"{label} : champ « element » manquant")
        for field_name in _ZONE_FIELDS:
            if field_name not in entry:
                raise ZonesError(f"{label} ({entry['element']}) : champ « {field_name} » manquant")
            if isinstance(entry[field_name], bool) or not isinstance(
                entry[field_name], int | float
            ):
                raise ZonesError(
                    f"{label} ({entry['element']}) : « {field_name} » doit être un nombre"
                )
        try:
            zones.append(
                Zone(
                    element_id=entry["element"],
                    **{name: float(entry[name]) for name in _ZONE_FIELDS},
                )
            )
        except ValueError as error:
            raise ZonesError(f"{label} : {error}") from error

    try:
        return ZoneMap(tuple(zones))
    except ValueError as error:
        raise ZonesError(f"{target} : {error}") from error


def save_zones(zones: ZoneMap, path: Path | None = None, *, working_width: int) -> None:
    """Écrit ``zones`` dans ``path`` (ou le chemin par défaut), en remplaçant le fichier."""
    target = path if path is not None else zones_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": FORMAT_VERSION,
        "working_width": working_width,
        "zones": [
            {"element": zone.element_id, **{name: getattr(zone, name) for name in _ZONE_FIELDS}}
            for zone in zones
        ],
    }
    # Écriture dans un fichier voisin puis remplacement : une coupure en cours d'écriture
    # ne laisse jamais un zones.toml à moitié écrit.
    temporary = target.with_name(target.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(_HEADER.encode("utf-8"))
        tomli_w.dump(data, handle)
    temporary.replace(target)
