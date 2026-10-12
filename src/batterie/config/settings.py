"""Réglages utilisateur : touches et volume, dans ``%APPDATA%\\Batterie\\settings.toml``.

Au premier lancement, le fichier n'existe pas : on écrit un modèle commenté avec les
valeurs par défaut (cadrage §2.4), que tu peux ouvrir avec le Bloc-notes et modifier.
Les lancements suivants lisent ce fichier tel quel, sans jamais écraser tes modifications
ou tes commentaires.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field, replace
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


@dataclass(frozen=True)
class CameraSettings:
    """Ce qu'on demande à la caméra (section facultative ``[camera]`` de ``settings.toml``).

    La caméra n'est pas obligée d'accepter : l'application lit ce qu'elle a réellement
    obtenu et l'affiche (``CameraInfo`` dans ``input/vision/process.py``).
    """

    device_index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    mjpeg: bool = False  # format compressé MJPEG : souvent nécessaire pour 60 images/s


@dataclass(frozen=True)
class VelocitySettings:
    """Nuance du jeu à la caméra (section facultative ``[velocity]`` de ``settings.toml``).

    La vitesse du geste règle le volume : ``soft_speed`` (px/s dans l'image réduite) donne le
    volume ``floor``, ``hard_speed`` le volume maximal, ``gamma`` courbe l'entre-deux.
    ``enabled = false`` : tous les coups sonnent à fond, comme avant. Voir
    ``input/vision/velocity.py``.
    """

    enabled: bool = True
    soft_speed: float = 200.0
    hard_speed: float = 900.0
    floor: float = 0.1
    gamma: float = 1.0


@dataclass
class Settings:
    """Touches personnalisées (id d'élément -> nom de scancode), volume (0.0 à 1.0), caméra."""

    key_map: dict[str, str] = field(default_factory=_default_key_map)
    volume: float = 1.0
    camera: CameraSettings = field(default_factory=CameraSettings)
    velocity: VelocitySettings = field(default_factory=VelocitySettings)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _camera_from_data(data: dict) -> CameraSettings:
    """Lit la section ``[camera]`` ; une valeur absente ou invalide garde sa valeur par défaut."""
    default = CameraSettings()

    def positive_int(name: str, fallback: int, minimum: int) -> int:
        value = data.get(name, fallback)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            return fallback
        return value

    return CameraSettings(
        device_index=positive_int("device_index", default.device_index, 0),
        width=positive_int("width", default.width, 1),
        height=positive_int("height", default.height, 1),
        fps=positive_int("fps", default.fps, 1),
        mjpeg=bool(data.get("mjpeg", default.mjpeg)),
    )


def _velocity_from_data(data: dict) -> VelocitySettings:
    """Lit la section ``[velocity]`` ; une valeur invalide, ou une courbe incohérente
    (``soft_speed`` pas inférieur à ``hard_speed``, ``floor`` pas dans ]0 ; 1]), garde les
    valeurs par défaut."""
    default = VelocitySettings()

    def number(name: str, fallback: float) -> float:
        value = data.get(name, fallback)
        if isinstance(value, bool) or not isinstance(value, int | float):
            return fallback
        return float(value)

    enabled = data.get("enabled", default.enabled)
    candidate = VelocitySettings(
        enabled=enabled if isinstance(enabled, bool) else default.enabled,
        soft_speed=number("soft_speed", default.soft_speed),
        hard_speed=number("hard_speed", default.hard_speed),
        floor=number("floor", default.floor),
        gamma=number("gamma", default.gamma),
    )
    coherent = (
        0 <= candidate.soft_speed < candidate.hard_speed
        and 0.0 < candidate.floor <= 1.0
        and candidate.gamma > 0
    )
    return candidate if coherent else replace(default, enabled=candidate.enabled)


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
    lines += [
        "",
        "# Caméra (jeu à la caméra) : facultatif, enlève les # pour changer une valeur.",
        "# La caméra n'accepte pas toujours : l'application affiche ce qu'elle obtient.",
        "# [camera]",
        "# device_index = 0   # numéro de la caméra (0 = la première)",
        "# width = 640",
        "# height = 480",
        "# fps = 30           # images par seconde demandées",
        "# mjpeg = false      # true : format MJPEG, souvent nécessaire pour 60 images/s",
        "",
        "# Nuance (jeu à la caméra) : la vitesse de ton geste règle le volume du coup.",
        "# L'écran « Jeu caméra » affiche la vitesse et le volume de ton dernier coup : joue",
        "# doucement puis fort, et règle soft_speed / hard_speed d'après ce que tu lis.",
        "# [velocity]",
        "# enabled = true      # false : tous les coups sonnent à fond",
        '# soft_speed = 200    # vitesse (px/s) d\'un coup doux = volume "floor"',
        "# hard_speed = 900    # vitesse (px/s) d'un coup fort = volume maximal",
        "# floor = 0.1         # volume du coup le plus doux : 0.1 = 20 dB sous un coup fort",
        "# gamma = 1.0         # courbe : > 1 garde les coups moyens doux, < 1 les rend forts",
        "",
    ]
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
    camera = _camera_from_data(data.get("camera", {}))
    velocity = _velocity_from_data(data.get("velocity", {}))
    return Settings(key_map=key_map, volume=volume, camera=camera, velocity=velocity)


def save_settings(settings: Settings, path: Path | None = None) -> None:
    """Écrit ``settings`` dans ``path`` (ou le chemin par défaut), sans commentaires."""
    target = path if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "volume": settings.volume,
        "keys": settings.key_map,
        "camera": asdict(settings.camera),
        "velocity": asdict(settings.velocity),
    }
    with target.open("wb") as handle:
        tomli_w.dump(data, handle)
