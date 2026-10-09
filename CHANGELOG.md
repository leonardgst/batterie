# Changelog

Toutes les évolutions notables du projet sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versions : [SemVer](https://semver.org/lang/fr/), convention `v0.<phase>.0`.

## [Unreleased]

### Added

- Cadrage du projet (`docs/00-cadrage.md`), `CLAUDE.md`, réglages Claude Code niveau 4.
- Squelettes de documentation : spécifications, architecture, ADR 0001, phase 01, journal, glossaire.
- Socle du projet (phase 01, PR 1) : `pyproject.toml` (uv, Python 3.12, pygame-ce, Ruff, pytest), squelette `src/batterie/`, CI GitHub Actions (`windows-latest`), `Batterie.bat`. `uv run batterie` ouvre une fenêtre vide ; Échap ou la fermeture de la fenêtre quitte.
