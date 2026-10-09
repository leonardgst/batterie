# Phase 01 — Batterie au clavier

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| À faire | Octobre 2026 (2 à 3 semaines, 4–6 h de ton temps) | — | v0.1.0 |

## Objectif

Jouer de tout le kit au clavier, sans retard perçu, en enchaînant des coups rapides. C'est le MVP (V1).
Référence : [cadrage](../00-cadrage.md), user stories US1 à US3.

## Livrables

**PR 1 — Socle** (`chore/project-setup`)
- [ ] `pyproject.toml` (uv, Python 3.12, pygame-ce, Ruff, pytest, script `batterie`)
- [ ] `.github/workflows/ci.yml` : Ruff + pytest sur `windows-latest`
- [ ] Squelette `src/batterie/` et `tests/` ; `uv run batterie` ouvre une fenêtre vide, Échap quitte
- [ ] `Batterie.bat` (lanceur double-clic)

**PR 2 — Sons et audio** (`feat/audio-engine`)
- [ ] `tools/gen_synth_kit.py` : kit synthétique de secours, sans aucune question de droits
- [ ] Kit CC0 / domaine public choisi, licence vérifiée et recopiée : `assets/kits/default/` + `kit.toml` + `LICENSE`
- [ ] `audio/engine.py` : `pygame.mixer` 48 kHz, tampon 256, 32 voix, étouffement de la charleston ouverte
- [ ] `tools/latency_probe.py` + mesures consignées dans l'ADR 0001

**PR 3 — Fenêtre et clavier** (`feat/keyboard-kit`)
- [ ] `core/elements.py` : les 10 éléments et la correspondance par défaut (cadrage §2.4)
- [ ] `ui/kit_view.py` : kit dessiné vu de dessus, légèrement de face, avec la touche sur chaque élément
- [ ] `input/keyboard.py` : scancodes, pas de répétition, entrées lues à ≥ 500 Hz
- [ ] Retour visuel du coup (illumination)

**PR 4 — Finitions** (`feat/settings`)
- [ ] Touches et volume personnalisables (`%APPDATA%\Batterie\settings.toml`)
- [ ] Testeur de touches simultanées (repère les combinaisons que ton clavier ne gère pas)
- [ ] README : installation et lancement

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal, ADR 0001)
- [ ] Testé en jouant : les 10 éléments, 3 touches simultanées, roulement rapide sur une touche, aucun retard perçu au casque filaire
- [ ] Latence logicielle touche → mixeur < 5 ms (mesurée)
- [ ] Licence du kit vérifiée et documentée

## Décisions prises (liens vers les ADR)

- [ADR 0001 — Choix du moteur audio](../adr/0001-choix-du-moteur-audio.md) (proposé)

## Écarts par rapport au plan

_À remplir au fil de la phase._

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
