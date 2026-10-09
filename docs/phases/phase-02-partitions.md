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
- [x] Au moins 12 partitions originales (3 par style : rock, jazz, other, solo), débutant à intermédiaire
- [x] Chaque partition déclare sa licence (CC0 ou création originale, cadrage R8)
- [x] Test : toutes les partitions de `scores/` se chargent sans erreur

**PR 3 — Transport et métronome** (`feat/transport`)
- [x] `core/transport.py` : horloge (`time.perf_counter_ns`), tempo, facteur de tempo, conversion beat → secondes, métronome
- [x] Test automatique : dérive de synchronisation < 5 ms sur 5 minutes simulées (US5)

**PR 4 — Menu, couloirs défilants, écran de fin** (`feat/score-player`)
- [x] Écran d'accueil : choisir un style puis une partition (titre, tempo, difficulté affichés — US4)
- [x] Couloirs de coups qui défilent vers une ligne de frappe, avec la touche (US5)
- [x] Décompte d'une mesure avant le début
- [x] Échap met en pause ; fin du morceau → écran de résultat
- [ ] Testé en jouant : un morceau choisi et joué du début à la fin — à toi de valider

**PR 5 — Finitions V2** (`feat/score-finishing`)
- [x] Tempo réglable, 50 % à 120 % par pas de 5 % (US6, Should mais requis par le critère de fin de la phase)
- [x] Jugement simple des coups (parfait / bien / raté, cadrage R7) et affichage du score (Should)
- [x] README mis à jour (choisir et jouer une partition)

**Hors périmètre de cette phase** (écart assumé, voir cadrage §2.1 S6) :
import de fichiers MIDI personnels. Nécessite la dépendance `mido` et un mappage General
MIDI → éléments ; reporté à une phase ultérieure pour ne pas alourdir la V2, qui fonctionne
très bien sans (les partitions TOML suffisent à jouer un morceau en entier).

## Critères de fin (Definition of Done)

- [x] Tests au vert (CI Windows)
- [x] Documentation à jour (README, CHANGELOG, journal)
- [ ] Testé en jouant : un morceau choisi et joué du début à la fin en suivant les touches affichées — à toi de valider
- [x] Dérive de synchronisation < 5 ms sur 5 minutes (test automatique) — `tests/test_transport.py`
- [x] Licence de chaque partition vérifiée et documentée — CC0-1.0, créations originales (`scores/<style>/*.toml`)

## Décisions prises (liens vers les ADR)

_Aucune pour l'instant._

## Écarts par rapport au plan

- **PR 5 — tempo réglable seulement avant de lancer la partition, pas pendant.** Changer `tempo_factor` en cours de lecture décalerait d'un coup toutes les notes déjà passées (le calcul `beat × secondes/beat` recalibre toute la chronologie, pas seulement la suite) : un changement à la volée aurait fait sauter les couloirs. Le tempo se choisit donc sur l'écran de sélection (flèches gauche/droite), avant le décompte ; il reste modifiable entre deux morceaux sans tout refermer.
- **PR 4 — Échap ne quitte plus directement l'application.** Avant cette PR, Échap fermait l'application depuis n'importe quel écran (comportement validé à la clôture de la phase 01). Avec l'arrivée d'un accueil et de plusieurs écrans, Échap est maintenant contextuel : il remonte d'un écran (partition → style → accueil), met en pause pendant la lecture d'un morceau, puis quitte l'application depuis l'accueil (ou la fermeture de la fenêtre, à tout moment). À re-tester : ce n'est plus exactement le comportement que tu avais validé en phase 01.
- **PR 4 — métronome visuel, pas sonore.** Le décompte et le suivi du tempo pendant la lecture sont uniquement visuels (grand chiffre puis couloirs qui défilent) ; aucun clic audio de métronome. Ajouter un son demanderait un nouvel asset et un chemin de lecture dédié (le clic n'est pas un élément du kit) ; reporté pour garder cette PR raisonnable. Possible en PR 5 ou plus tard si tu le souhaites.
- **PR 4 — orchestration des écrans dans `app.py`, pas de `ui/scenes/`.** L'architecture du cadrage esquissait un dossier `ui/scenes/` ; avec seulement 6 écrans de logique simple (accueil, jeu libre, style, partition, lecture, résultat), un module unique reste plus lisible qu'une collection de petits fichiers. À revoir si la V3 (plusieurs écrans de calibration vision) rend ce découpage utile.
- **PR 4 — bug trouvé et corrigé en marge.** En vérifiant visuellement le rendu, j'ai remarqué que la charleston fermée et ouverte (même position à l'écran, par choix de la PR 3) s'illuminaient bien l'une sur l'autre : l'une masquait toujours le flash de l'autre selon l'ordre de dessin, donc frapper « D » ne montrait jamais rien. Corrigé dans `ui/kit_view.py` (l'élément allumé se dessine toujours en dernier) et couvert par un test de non-régression ; ça concerne aussi le jeu libre de la phase 01.
- **PR 2 — grooves pas encore testés en jouant.** Les 12 partitions sont validées structurellement (elles se chargent, le bon nombre de notes, aucune erreur), mais je ne peux pas les jouer moi-même pour confirmer qu'elles « sonnent » bien musicalement — pas d'oreille, et le lecteur de partition (PR 4) n'existe pas encore pour les essayer en situation. À vérifier par toi, en tant que batteur, une fois la PR 4 en place ; un groove qui ne te convient pas se corrige facilement dans son fichier `.toml`.
- **PR 1 — précision du format laissée ouverte par le cadrage.** Le cadrage donne l'exemple `swing = 0.0 # droit, 0.66 = ternaire` sans formule précise. J'ai choisi : `swing` est directement la position (0 à 1) du contretemps dans sa paire de cases (0.5 = droit, 0.66 ≈ ternaire), avec `0.0` traité comme cas particulier signifiant « droit » (plutôt que littéralement la position 0). Les paires sont formées par cases consécutives (case paire = temps, case impaire = contretemps) ; ça couvre le cas documenté (grille de croches, 2 cases par temps) et les grilles plus fines sans erreur, sans viser un rendu de swing fidèle au-delà des croches.

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
