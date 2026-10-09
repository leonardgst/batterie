# Phase 02 — Partitions

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| En cours | 6 à 10 h de ton temps | — | v0.2.0 |

## Objectif

Choisir une partition (rock, jazz, autre, ou batterie seule) et la jouer du début à la
fin en suivant les touches qui défilent au bon moment. C'est la V2.
Référence : [cadrage](../00-cadrage.md), user stories US4 à US6.

## Livrables

**PR 1 — Format de partition et chargeur** (`feat/score-format`)
- [x] `core/score.py` : `Score`/`Note`, grille façon tablature (`-`/`x`/`X`/`g`), swing (cadrage §2.4)
- [x] Chargeur TOML testé (erreurs claires sur élément inconnu, ligne de mauvaise longueur, symbole inconnu)
- [x] Un premier exemple réel dans `scores/rock/` (sert de test ET de première partition)

**PR 2 — Bibliothèque de partitions** (`feat/score-library`)
- [ ] Au moins 12 partitions originales (3 par style : rock, jazz, other, solo), débutant à intermédiaire
- [ ] Chaque partition déclare sa licence (CC0 ou création originale, cadrage R8)
- [ ] Test : toutes les partitions de `scores/` se chargent sans erreur

**PR 3 — Transport et métronome** (`feat/transport`)
- [ ] `core/transport.py` : horloge (`time.perf_counter_ns`), tempo, facteur de tempo, conversion beat → secondes, métronome
- [ ] Test automatique : dérive de synchronisation < 5 ms sur 5 minutes simulées (US5)

**PR 4 — Menu, couloirs défilants, écran de fin** (`feat/score-player`)
- [ ] Écran d'accueil : choisir un style puis une partition (titre, tempo, difficulté affichés — US4)
- [ ] Couloirs de coups qui défilent vers une ligne de frappe, avec la touche (US5)
- [ ] Décompte d'une mesure avant le début
- [ ] Échap met en pause ; fin du morceau → écran de résultat
- [ ] Testé en jouant : un morceau choisi et joué du début à la fin

**PR 5 — Finitions V2** (`feat/score-finishing`)
- [ ] Tempo réglable, 50 % à 120 % par pas de 5 % (US6, Should mais requis par le critère de fin de la phase)
- [ ] Jugement simple des coups (parfait / bien / raté, cadrage R7) et affichage du score (Should)
- [ ] README mis à jour (choisir et jouer une partition)

**Hors périmètre de cette phase** (écart assumé, voir cadrage §2.1 S6) :
import de fichiers MIDI personnels. Nécessite la dépendance `mido` et un mappage General
MIDI → éléments ; reporté à une phase ultérieure pour ne pas alourdir la V2, qui fonctionne
très bien sans (les partitions TOML suffisent à jouer un morceau en entier).

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] Testé en jouant : un morceau choisi et joué du début à la fin en suivant les touches affichées
- [ ] Dérive de synchronisation < 5 ms sur 5 minutes (test automatique)
- [ ] Licence de chaque partition vérifiée et documentée

## Décisions prises (liens vers les ADR)

_Aucune pour l'instant._

## Écarts par rapport au plan

- **PR 1 — précision du format laissée ouverte par le cadrage.** Le cadrage donne l'exemple `swing = 0.0 # droit, 0.66 = ternaire` sans formule précise. J'ai choisi : `swing` est directement la position (0 à 1) du contretemps dans sa paire de cases (0.5 = droit, 0.66 ≈ ternaire), avec `0.0` traité comme cas particulier signifiant « droit » (plutôt que littéralement la position 0). Les paires sont formées par cases consécutives (case paire = temps, case impaire = contretemps) ; ça couvre le cas documenté (grille de croches, 2 cases par temps) et les grilles plus fines sans erreur, sans viser un rendu de swing fidèle au-delà des croches.

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
