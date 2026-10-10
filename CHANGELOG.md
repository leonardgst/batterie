# Changelog

Toutes les évolutions notables du projet sont consignées ici.
Format : [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) · Versions : [SemVer](https://semver.org/lang/fr/), convention `v0.<phase>.0`.

## [Unreleased]

### Added

- Zones de frappe et anti-double-coup (phase 04, PR 2) : `input/vision/zones.py` (`Zone` rectangulaire avec plan de frappe, `ZoneMap` qui refuse un élément en double ou des zones qui se chevauchent en largeur, `ZoneStrikeDetector` : un coup est attribué à l'élément de la zone dont le plan est franchi, avec ré-armement après remontée et anti-rebond), `config/zones.py` (`zones.toml` dans `%APPDATA%\Batterie`, écrit sans risque de fichier à moitié écrit, erreurs claires) et prise en charge des zones par le processus vision (`MarkerSpec.zones`). Pas encore visible en jouant : les zones se calibrent à la PR suivante.
- Deux mains (phase 04, PR 1) : plage de couleur `ORANGE` (vive, volontairement exigeante en saturation pour ne pas suivre la peau), suivi de plusieurs embouts à la fois dans `input/vision/process.py` (`MarkerSpec`, `track_markers`, `run_markers_process` : un détecteur de coup par main, anti-rebond propre à chaque main, image retournée en miroir en option), et cible `--target hands` dans `tools/vision_debug.py` et `tools/vision_measure.py` (main gauche orange, main droite verte). Préréglage non calibré, à essayer devant ta caméra.

### Changed

- `VisionSample` porte maintenant un échantillon par embout (`markers`) ; `point`, `velocity_px_per_s` et `hit_event` restent disponibles pour le premier embout, donc la baguette et le pied marchent comme avant. Dans les outils, un préréglage de cible (`TargetPreset`) regroupe maintenant un ou plusieurs embouts (`MarkerPreset`).

## [0.3.0] - 2026-10-10

Phase 03 — Vision : preuve de concept (V3.0) : une baguette à embout coloré, suivie par la webcam intégrée, détectée assez vite et assez sûrement pour continuer.

### Added

- Suivi de couleur et détection de coup (phase 03, PR 1) : `core/events.py` (`HitEvent`/`Source`), `input/vision/color_tracker.py` (suivi HSV d'un embout coloré) et `input/vision/strike_detector.py` (détection d'un coup au franchissement d'un plan de frappe), logique pure testée sur des images et trajectoires synthétiques, sans caméra.
- Processus caméra et écran de débogage (phase 03, PR 2) : `input/vision/process.py` (capture dans un processus séparé, file de `VisionSample`), `tools/vision_debug.py` (aperçu caméra, plan de frappe, vitesse, images/s, latence, compteur de coups) — à calibrer et essayer avec ta webcam.
- Séance de mesure vision (phase 03, PR 3) : `tools/vision_measure.py` (métronome à 80 BPM, 4 clics de décompte puis 50 coups ; séance caméra et séance clavier de référence ; coups détectés, faux coups, images/s réelles, temps de traitement, retard de la caméra par rapport au clavier ; mode `--simulate` sans caméra), logique de comptage dans `input/vision/measure.py`. Protocole de mesure dans la page de la phase 03 ; ADR 0002 (go/no-go et choix de caméra) créé, en attente des mesures.
- ADR 0002 (go/no-go et choix de caméra) : décision **go, sans achat de caméra pour l'instant**, grille de lecture et mesures consignées.
- Test du pied avec la webcam intégrée au sol (phase 03, PR 4, informatif) : argument `--target stick|foot` (défaut `stick`) dans `tools/vision_debug.py` et `tools/vision_measure.py`, préréglages de cible regroupés en haut de `vision_debug.py` (élément, couleur, plan de frappe, vitesse minimale, anti-rebond) avec un préréglage pied non calibré, protocole de mesure du pied dans la page de la phase 03, options de disposition des caméras et section « pied » dans l'ADR 0002 (à remplir avec tes mesures).

### Changed

- `input/vision/process.py` transmet la vitesse minimale et l'anti-rebond au détecteur de coup. Dans `tools/vision_debug.py`, les constantes `COLOR_RANGE`, `STRIKE_PLANE_Y` et `ELEMENT_ID` deviennent le préréglage `STICK` (mêmes valeurs).
- Cadrage : disposition des caméras du 2026-10-10 (webcam 60 images/s d'occasion en hauteur pour les mains, webcam intégrée au sol pour les pieds, pédales au clavier USB en secours ; « cadrage large » abandonné) et correction du prix de la C922 (70 à 99 € neuve, ~40 € d'occasion).

### Validated

- Testé en jouant par l'utilisateur avec une brosse à dents verte comme embout : suivi sans décrochage, passage du plan de frappe détecté, compteur de coups juste ; séance de mesure de 50 coups à 80 BPM : 48 à 50 détectés, 0 faux coup, 31,2 images/s réelles, retard par rapport au clavier ≤ 55 ms.
- Test du pied par l'utilisateur (informatif, webcam intégrée au sol à 60–70 cm, une séance) : marqueur vu sur 100 % des images, 0 faux coup, 31,0 images/s ; 41 coups sur 50 comptés, les 9 autres n'ayant pas été joués selon l'utilisateur (ruban décollé) ; retard de +109 ms par rapport au clavier, trop élevé pour conclure : décision pour les pieds repoussée à une séance de confirmation (ADR 0002).

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
