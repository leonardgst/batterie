# Changelog

Toutes les évolutions notables du projet sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versions : [SemVer](https://semver.org/lang/fr/), convention `v0.<phase>.0`.

## [Unreleased]

## [0.1.0] - 2026-10-09

Phase 01 — Batterie au clavier (V1, MVP) : jouer de tout le kit au clavier, sans retard perçu.

### Added

- Cadrage du projet (`docs/00-cadrage.md`), `CLAUDE.md`, réglages Claude Code niveau 4.
- Squelettes de documentation : spécifications, architecture, ADR 0001, phase 01, journal, glossaire.
- Socle du projet (phase 01, PR 1) : `pyproject.toml` (uv, Python 3.12, pygame-ce, Ruff, pytest), squelette `src/batterie/`, CI GitHub Actions (`windows-latest`), `Batterie.bat`. `uv run batterie` ouvre une fenêtre vide ; Échap ou la fermeture de la fenêtre quitte.
- Moteur audio (phase 01, PR 2) : `audio/engine.py` (`pygame.mixer` 48 kHz, tampon 256, 32 voix, étouffement de la charleston ouverte), kit synthétique de secours généré sans aucune question de droits (`tools/gen_synth_kit.py`, dédié au domaine public CC0-1.0, installé comme kit `default`), `tools/latency_probe.py` avec premières mesures dans l'ADR 0001.
- Fenêtre et clavier (phase 01, PR 3) : `core/elements.py` (les 10 éléments et leur touche par défaut), `input/keyboard.py` (lecture par scancode, pas de répétition), `ui/kit_view.py` (kit dessiné, touche affichée, illumination du coup). `uv run batterie` joue désormais tout le kit au clavier avec retour visuel.
- Finitions (phase 01, PR 4) : `config/settings.py` (touches et volume personnalisables via `%APPDATA%\Batterie\settings.toml`, modèle commenté généré au premier lancement), volume général dans `AudioEngine`, `tools/keytest.py` (testeur de touches simultanées, repère le « ghosting » du clavier), README complété (lancement, personnalisation, testeur de touches).

### Validated

- Testé en jouant par l'utilisateur : les 10 éléments, 3 touches simultanées, roulement rapide, aucun retard perçu au casque filaire. Latence logicielle estimée ≈ 5,37 ms (ADR 0001), ressenti confirmé malgré le léger dépassement de la cible théorique de 5 ms.
