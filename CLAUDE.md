# CLAUDE.md — Batterie

## 1. Contexte

Batterie est une batterie virtuelle pour Windows, en Python, destinée à être publiée en open source.
V1 : jouer au clavier (MVP). V2 : suivre des partitions dont les coups défilent avec leur touche.
V3 : jouer « dans le vide » devant des webcams, avec des baguettes à embout coloré et des marqueurs aux pieds.
L'utilisateur (GitHub `leonardgst`) ne code pas : il teste en jouant et fusionne les PR. Budget : 0 € de logiciel.
Tout le détail : [docs/00-cadrage.md](docs/00-cadrage.md).

## 2. Stack

- Python 3.12, environnement et dépendances gérés par **uv** (`pyproject.toml`, `uv.lock`)
- **pygame-ce ≥ 2.5** : fenêtre, dessin, clavier, audio (`pygame.mixer`)
- `tomllib` (stdlib) + `tomli-w`, `platformdirs` ; `mido` (V2) ; `opencv-python`, `numpy` (V3) ; `mediapipe` optionnel
- **Ruff** (lint + format), **pytest**, GitHub Actions sur `windows-latest`
- Aucune dépendance payante ; licences compatibles open source (éviter l'AGPL)

## 3. Commandes

```bash
uv sync                                  # installer / mettre à jour l'environnement
uv run batterie                          # lancer l'application
uv run pytest                            # tests
uv run ruff check . --fix                # lint
uv run ruff format .                     # formatage
uv run python tools/latency_probe.py     # mesure de latence (créé en phase 01)
uv run python tools/vision_measure.py    # séance de mesure vision, ouvre la webcam (--simulate : sans caméra)
```

## 4. Structure

```text
src/batterie/core/     logique pure (éléments, événements, partitions, transport, jugement) — sans pygame
src/batterie/audio/    moteur audio
src/batterie/input/    clavier, MIDI (Could), vision (V3)
src/batterie/ui/       scènes et dessin
src/batterie/config/   réglages utilisateur (%APPDATA%\Batterie)
assets/kits/           sons + kit.toml + LICENSE
scores/<style>/        partitions TOML (scores/local/ ignoré par Git)
tools/                 scripts utilitaires
tests/                 pytest
docs/                  cadrage, specs, architecture, adr/, phases/, journal, glossaire
```

## 5. Conventions

- **Langues** : code, identifiants, messages de commit, noms de branche et PR en **anglais** ; commentaires et docstrings en **français** ; documentation (`docs/`, README) en français.
- Type hints partout ; `dataclasses` pour le modèle ; chemins via `pathlib` ; fichiers lus/écrits en UTF-8 explicite.
- `core/` n'importe jamais pygame : tout ce qui peut être testé sans fenêtre ni son y vit.
- Commits : Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, `ci:`).
- Branches : `feat/<sujet>`, `fix/<sujet>`, `docs/<sujet>`, `chore/<sujet>` ; une branche = une PR = un sujet.
- Chaque PR : quoi, pourquoi, **comment tester en jouant** ; CI verte avant de demander la revue.
- Chaque kit et chaque partition déclare sa licence (CC0, CC-BY, domaine public ou original).

## 6. Collaboration — niveau 4 (semi-autonome)

Claude peut seul : créer une branche depuis `origin/main` à jour, modifier les fichiers, lancer uv/pytest/ruff, committer, pousser **sa branche**, ouvrir une PR avec `gh`, mettre à jour la doc.

Claude ne fait jamais : pousser sur `main`, fusionner une PR, force-push, supprimer des fichiers ou des branches sans accord, ajouter une dépendance payante, lire `.env` ou `captures/`, committer des images caméra ou du contenu sous droits.

Les autorisations correspondantes sont dans `.claude/settings.json`.

## 7. Documentation (à chaque fin de tâche)

- Cocher les livrables dans le document de la phase en cours.
- Ajouter une ligne datée dans `docs/journal.md`.
- Décision technique non triviale → nouvel ADR `docs/adr/NNNN-titre.md` (contexte, options, décision, conséquences).
- Changement visible pour l'utilisateur → `CHANGELOG.md`, section `[Unreleased]`.
- Clôture de phase : procédure de `docs/00-cadrage.md` §8.3 ; tag annoté `v0.<phase>.0` posé sur `main` après fusion.
- Ne jamais supprimer un document (une phase abandonnée garde son fichier, statut « Abandonnée »).

## 8. Phase en cours

**Phase 04 — Vision : deux mains, kit complet (V3.1)** → [docs/phases/phase-04-deux-mains.md](docs/phases/phase-04-deux-mains.md)
Prérequis avant d'y toucher : cadrer la phase en détail (découpage en PR) et demander à
l'utilisateur les deux couleurs d'embout qu'il compte utiliser — voir le document de phase.

Phases terminées :
- Phase 03 — Vision : preuve de concept (V3.0) terminée le 2026-10-10, tag `v0.3.0`, décision go sans achat de caméra (ADR 0002) → [docs/phases/phase-03-vision-poc.md](docs/phases/phase-03-vision-poc.md)
- Phase 02 — Partitions (V2) terminée le 2026-10-09, tag `v0.2.0` → [docs/phases/phase-02-partitions.md](docs/phases/phase-02-partitions.md)
- Phase 01 — Batterie au clavier (V1, MVP) terminée le 2026-10-09, tag `v0.1.0` → [docs/phases/phase-01-batterie-clavier.md](docs/phases/phase-01-batterie-clavier.md)

## 9. Interdits et pièges connus

- **Latence** : jouer le son dès la lecture de l'événement, jamais depuis le rendu. Entrées lues à chaque tour de boucle (≥ 500 Hz), rendu limité à 60 images/s.
- Appeler `pygame.mixer.pre_init(48000, -16, 2, 256)` **avant** `pygame.init()` ; réserver 32 canaux.
- Clavier : utiliser `event.scancode` (position physique, AZERTY et QWERTY) ; pas de `key.set_repeat`.
- Ne pas juger la latence avec un casque Bluetooth.
- Tests et CI : `SDL_VIDEODRIVER=dummy` et `SDL_AUDIODRIVER=dummy`.
- Vision (V3) : traitement d'image dans un **processus** séparé (`multiprocessing`), jamais dans le processus audio/rendu.
- Matériel de l'utilisateur : renseigné (cadrage §6.1) — Intel Core i7-1255U, 16 Go, Iris Xe intégrée, webcam intégrée seulement ; pas d'achat de caméra tant que l'ADR 0002 ne le justifie pas.
- Sous Windows, Claude Code dispose de deux shells (Git Bash et PowerShell) : les permissions sont déclarées pour les deux dans `.claude/settings.json`. Préférer Bash pour les commandes du projet.
