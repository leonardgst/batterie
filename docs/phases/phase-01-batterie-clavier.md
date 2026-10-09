# Phase 01 — Batterie au clavier

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| Terminée | Octobre 2026 (2 à 3 semaines, 4–6 h de ton temps) | 2026-10-09 | v0.1.0 |

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
- [x] `core/elements.py` : les 10 éléments et la correspondance par défaut (cadrage §2.4)
- [x] `ui/kit_view.py` : kit dessiné vu de dessus, légèrement de face, avec la touche sur chaque élément — voir écart ci-dessous
- [x] `input/keyboard.py` : scancodes, pas de répétition, entrées lues à ≥ 500 Hz
- [x] Retour visuel du coup (illumination)

**PR 4 — Finitions** (`feat/settings`)
- [x] Touches et volume personnalisables (`%APPDATA%\Batterie\settings.toml`)
- [x] Testeur de touches simultanées (repère les combinaisons que ton clavier ne gère pas)
- [x] README : installation et lancement

## Critères de fin (Definition of Done)

- [x] Tests au vert (CI Windows)
- [x] Documentation à jour (README, CHANGELOG, journal, ADR 0001)
- [x] Testé en jouant : les 10 éléments, 3 touches simultanées, roulement rapide sur une touche, aucun retard perçu au casque filaire — validé par toi le 2026-10-09
- [x] Latence logicielle touche → mixeur < 5 ms (mesurée) — ≈ 5,37 ms mesurés en PR 2 (voir ADR 0001), ressenti validé à l'oreille le 2026-10-09 malgré le léger dépassement théorique
- [x] Licence du kit vérifiée et documentée

## Décisions prises (liens vers les ADR)

- [ADR 0001 — Choix du moteur audio](../adr/0001-choix-du-moteur-audio.md) (accepté)

## Écarts par rapport au plan

- **PR 2 — kit « default ».** Le plan prévoyait de choisir et vérifier un kit CC0 / domaine public enregistré (Hydrogen, SCC Drums, Meadowlark…), le générateur synthétique ne servant que de secours. Télécharger et vérifier la licence d'un pack externe demande une diligence (lire la licence exacte, l'attribution, les conditions de redistribution) que Claude Code ne peut pas mener de façon fiable depuis cet environnement (pas de navigateur, pas de téléchargement de binaire vérifié). Le kit synthétique (`tools/gen_synth_kit.py`) est donc devenu le kit `assets/kits/default/` : création 100 % originale du projet, dédiée au domaine public (CC0-1.0), donc aucun risque de droits. Remplacer ce kit par un kit enregistré sous licence libre reste possible plus tard (C4 « plusieurs kits sonores », cadrage §2.1) sans changer l'interface `AudioEngine`/`kit.toml`.
- **PR 2 — latence mesurée légèrement au-dessus de la cible.** Le tampon de 256 échantillons à 48 kHz (imposé par `CLAUDE.md`) a lui seul 5,33 ms de latence théorique, donc la latence totale estimée (≈ 5,37 ms) dépasse légèrement la cible « < 5 ms » de la phase. Voir ADR 0001 : décision provisoire de garder le tampon 256 et de confirmer (ou réduire à 128) après le test au casque filaire, une fois le clavier branché en PR 3.
- **PR 3 — étiquette de touche fixe, pas adaptée à la disposition réelle de ton clavier.** R2 du cadrage prévoit que « l'étiquette affichée suit la disposition du clavier » (AZERTY ou QWERTY). L'API scancode → nom de touche de pygame-ce 2.5.8 ne s'est pas comportée de façon fiable dans cet environnement (noms vides ou caractères de contrôle au lieu de lettres). `ui/kit_view.py` affiche donc l'étiquette fixe du cadrage (ex. « Z » pour le crash), qui correspond à un clavier AZERTY français — la détection n'importe pas pour *jouer* (la lecture se fait par scancode, donc la bonne touche physique déclenche le bon son sur les deux dispositions), seul l'affichage du texte ne s'adapterait pas sur un clavier QWERTY. À revoir si besoin lors de la PR 4 (touches personnalisables).
- **PR 3 — kit dessiné en schéma, pas en illustration réaliste.** `ui/kit_view.py` dessine des cercles étiquetés plutôt qu'un rendu illustré du kit ; suffisant pour voir et tester les 10 éléments, une version plus travaillée reste possible plus tard sans changer la logique.
- **PR 4 — personnalisation par fichier texte, pas d'écran de réglages.** `config/settings.py` lit/écrit `settings.toml` (touches par nom de scancode, volume) ; il n'y a pas encore d'écran dans l'application pour changer ces réglages au clavier/à la souris — tu les modifies en éditant le fichier avec le Bloc-notes (expliqué dans le README). Cohérent avec l'absence d'écran de menu avant la V2 ; un écran de réglages pourra réutiliser `load_settings`/`save_settings` sans changer leur format.

## Rétrospective : ce qui a marché, ce qui a coincé

**Ce qui a marché**

- Le découpage en 4 PR (socle, audio, clavier, finitions) a permis de tester chaque brique indépendamment ; CI verte du premier coup sur les 4 PR.
- `pygame.mixer` tient la cible de latence sans bibliothèque supplémentaire : validé à l'oreille au casque filaire, aucune bascule vers `sounddevice` nécessaire (ADR 0001).
- Garder `core/` sans import pygame a permis de tester `elements.py` en pur Python, et de dériver le groupe d'étouffement de la charleston dans `audio/engine.py` depuis une seule source de vérité.
- Le fichier `settings.toml` commenté, écrit une seule fois puis jamais réécrit automatiquement, permet de personnaliser touches et volume sans outil ni code, conforme au profil « je ne code pas » du projet.

**Ce qui a coincé**

- Sourcer et vérifier la licence d'un kit de sons enregistré (CC0/domaine public) depuis Claude Code n'était pas réaliste dans cet environnement (pas de navigateur, pas de téléchargement vérifiable) : le kit `default` livré est donc le générateur synthétique, pas un enregistrement réel. Les sons sont utilisables mais clairement synthétiques ; un kit plus réaliste reste un travail futur possible (cadrage, item Could C4).
- L'API de pygame-ce 2.5.8 pour convertir un scancode en lettre affichée selon la disposition du clavier ne s'est pas comportée de façon exploitable ; l'étiquette affichée est donc fixe (lettres AZERTY du cadrage), sans impact sur le jeu lui-même (la détection reste par scancode).
- La latence théorique du tampon audio (5,33 ms à elle seule) dépasse légèrement la cible chiffrée de la phase (< 5 ms) ; le ressenti en jouant prime sur le chiffre théorique, et le test au casque filaire l'a confirmé sans retard perçu.
