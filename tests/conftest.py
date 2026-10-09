"""Configuration pytest : pilotes SDL factices (pas d'écran, pas de son en CI/local)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
