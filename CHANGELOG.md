# Changelog

Toutes les évolutions notables du projet sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versions : [SemVer](https://semver.org/lang/fr/), convention `v0.<phase>.0`.

## [Unreleased]

### Added

- Suivi de couleur et détection de coup (phase 03, PR 1) : `core/events.py` (`HitEvent`/`Source`), `input/vision/color_tracker.py` (suivi HSV d'un embout coloré) et `input/vision/strike_detector.py` (détection d'un coup au franchissement d'un plan de frappe), logique pure testée sur des images et trajectoires synthétiques, sans caméra.

## [0.2.0] - 2026-10-09

Phase 02 — Partitions (V2) : choisir une partition et la jouer du début à la fin en suivant les touches qui défilent.

### Added

- Format de partition et chargeur (phase 02, PR 1) : `core/score.py` (grille façon tablature, symboles `-`/`x`/`X`/`g`, swing), `scores/rock/groove-de-base.toml` comme premier exemple réel.
- Bibliothèque de partitions (phase 02, PR 2) : 12 grooves originaux (3 par style : rock, jazz, other, solo), licence CC0-1.0, dans `scores/<style>/`.
- Transport et métronome (phase 02, PR 3) : `core/transport.py` (horloge beat ↔ secondes, tempo réglable 50-120 %, pause/reprise, décompte, clics de métronome), sans dérive mesurable sur 5 minutes simulées (`tests/test_transport.py`).
- Lecteur de partitions (phase 02, PR 4) : écran d'accueil (jeu libre / partitions), choix du style puis de la partition, couloirs de coups qui défilent au-dessus du kit, décompte visuel d'une mesure, pause (Échap) et écran de fin. `uv run batterie` permet maintenant de choisir et de jouer un morceau du début à la fin.
- Finitions V2 (phase 02, PR 5) : tempo réglable de 50 % à 120 % (flèches gauche/droite sur l'écran de sélection), jugement des coups (`core/judge.py`, cadrage R7 : parfait ≤ 35 ms, bien ≤ 90 ms, raté au-delà) avec retour visuel immédiat et précision affichée sur l'écran de fin, README complété (choisir et jouer une partition).

### Fixed

- La charleston fermée et la charleston ouverte (même position visuelle) masquaient parfois l'illumination l'une de l'autre selon l'ordre de dessin ; l'élément allumé passe maintenant toujours au premier plan (`ui/kit_view.py`).

### Changed

- Échap est maintenant contextuel (remonte d'un écran, met en pause, puis quitte depuis l'accueil) plutôt que de toujours fermer l'application immédiatement.

### Validated

- Testé en jouant par l'utilisateur : un morceau choisi et joué du début à la fin, couloirs de coups, pause/reprise et le nouveau comportement d'Échap.

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
