# Journal de bord

Une ligne par session de travail, la plus récente en haut.

| Date | Phase | Qui | Ce qui a été fait | Suite |
| --- | --- | --- | --- | --- |
| 2026-10-03 | Cadrage | Claude (chat) | Cadrage complet, CLAUDE.md, réglages niveau 4, squelettes de documentation | Créer le dépôt, protéger `main`, lancer la PR 1 de la phase 01 |
| 2026-10-09 | 01 — Socle | Claude Code | PR 1 (`chore/project-setup`) : `pyproject.toml` (uv, Python 3.12, pygame-ce, Ruff, pytest), squelette `src/batterie/` et `tests/`, CI Windows (Ruff + pytest), `Batterie.bat`. `uv run batterie` ouvre une fenêtre vide, Échap quitte. CI et tests locaux au vert | PR 2 (sons et audio) |
| 2026-10-09 | 01 — Sons et audio | Claude Code | PR 2 (`feat/audio-engine`) : `audio/engine.py` (mixeur 48 kHz, tampon 256, 32 voix, étouffement charleston), kit synthétique `assets/kits/default/` généré par `tools/gen_synth_kit.py` (CC0-1.0, sans question de droits, écart documenté : pas de kit enregistré externe faute de pouvoir vérifier sa licence depuis Claude Code), `tools/latency_probe.py` et premières mesures dans l'ADR 0001 (≈ 5,37 ms estimés, légèrement au-dessus de la cible < 5 ms, à confirmer en jouant en PR 3) | PR 3 (fenêtre et clavier) |
