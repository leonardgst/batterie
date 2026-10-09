# Phase 01 — Batterie au clavier

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| En cours | Octobre 2026 (2 à 3 semaines, 4–6 h de ton temps) | — | v0.1.0 |

## Objectif

Jouer de tout le kit au clavier, sans retard perçu, en enchaînant des coups rapides. C'est le MVP (V1).
Référence : [cadrage](../00-cadrage.md), user stories US1 à US3.

## Livrables

**PR 1 — Socle** (`chore/project-setup`)
- [x] `pyproject.toml` (uv, Python 3.12, pygame-ce, Ruff, pytest, script `batterie`)
- [x] `.github/workflows/ci.yml` : Ruff + pytest sur `windows-latest`
- [x] Squelette `src/batterie/` et `tests/` ; `uv run batterie` ouvre une fenêtre vide, Échap quitte
- [x] `Batterie.bat` (lanceur double-clic)

**PR 2 — Sons et audio** (`feat/audio-engine`)
- [x] `tools/gen_synth_kit.py` : kit synthétique de secours, sans aucune question de droits
- [x] Kit CC0 / domaine public choisi, licence vérifiée et recopiée : `assets/kits/default/` + `kit.toml` + `LICENSE` — voir écart ci-dessous
- [x] `audio/engine.py` : `pygame.mixer` 48 kHz, tampon 256, 32 voix, étouffement de la charleston ouverte
- [x] `tools/latency_probe.py` + mesures consignées dans l'ADR 0001

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

- **PR 2 — kit « default ».** Le plan prévoyait de choisir et vérifier un kit CC0 / domaine public enregistré (Hydrogen, SCC Drums, Meadowlark…), le générateur synthétique ne servant que de secours. Télécharger et vérifier la licence d'un pack externe demande une diligence (lire la licence exacte, l'attribution, les conditions de redistribution) que Claude Code ne peut pas mener de façon fiable depuis cet environnement (pas de navigateur, pas de téléchargement de binaire vérifié). Le kit synthétique (`tools/gen_synth_kit.py`) est donc devenu le kit `assets/kits/default/` : création 100 % originale du projet, dédiée au domaine public (CC0-1.0), donc aucun risque de droits. Remplacer ce kit par un kit enregistré sous licence libre reste possible plus tard (C4 « plusieurs kits sonores », cadrage §2.1) sans changer l'interface `AudioEngine`/`kit.toml`.
- **PR 2 — latence mesurée légèrement au-dessus de la cible.** Le tampon de 256 échantillons à 48 kHz (imposé par `CLAUDE.md`) a lui seul 5,33 ms de latence théorique, donc la latence totale estimée (≈ 5,37 ms) dépasse légèrement la cible « < 5 ms » de la phase. Voir ADR 0001 : décision provisoire de garder le tampon 256 et de confirmer (ou réduire à 128) après le test au casque filaire, une fois le clavier branché en PR 3.

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
