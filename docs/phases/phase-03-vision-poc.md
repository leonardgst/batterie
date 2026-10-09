# Phase 03 — Vision : preuve de concept

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| En cours | 4 à 6 h de ton temps | — | v0.3.0 |

## Objectif

Une baguette, un élément (la caisse claire), suivie par la webcam existante : vérifier
que le suivi d'un embout coloré est assez rapide et fiable pour remplacer le clavier,
avant d'acheter quoi que ce soit. C'est la première sous-version de la V3 (V3.0).
Référence : [cadrage](../00-cadrage.md), user story US7 (critères réduits à un seul
élément pour cette preuve de concept).

## Prérequis — obtenus le 2026-10-09

Le cadrage (§6.1) laissait ces informations « à faire plus tard » ; nécessaires
avant d'écrire du code de vision (résolution, fréquence d'image visées, et si un
modèle plus lourd comme MediaPipe est envisageable). Reportées dans le cadrage §6.1.

- [x] Processeur : Intel Core i7-1255U (12e génération, 1,70 GHz)
- [x] Mémoire vive : 16 Go
- [x] Carte graphique : Intel Iris Xe Graphics, intégrée — pas de VRAM dédiée
- [x] Webcam(s) : webcam intégrée à l'ordinateur portable (modèle non précisé), aucune caméra externe

**Lecture pour la suite** : processeur mobile récent sans carte graphique dédiée — cohérent
avec le choix du cadrage (suivi de couleur léger en 640×480 sur le processeur, OpenCV,
pas de MediaPipe par défaut). Pas de caméra externe : la preuve de concept se fait avec la
webcam intégrée (cadrage §3, risque 3) ; sa résolution et sa fréquence d'image réelles
restent à vérifier en tout début de phase (beaucoup de webcams intégrées plafonnent à
30 i/s, parfois moins en basse lumière). Aucun achat avant la fin de cette phase
(cadrage §7, « Recommandation caméra ») : la décision go/no-go et, si besoin, les
caractéristiques précises à chercher, seront consignées dans un ADR à la clôture.

## Ce que je peux faire seul, ce qu'il te faudra faire

Contrairement aux phases 01 et 02, une partie de cette phase ne peut pas être testée
ni mesurée par Claude Code : je n'ai pas de caméra, pas d'embout coloré, et je n'ouvrirai
pas ta webcam moi-même (R9 du cadrage, vie privée — à faire seulement si tu me le
demandes explicitement et pour un test précis). Je code et teste tout ce qui est logique
pure (PR 1 entièrement), je construis les outils (PR 2 et PR 3), mais c'est toi qui les
exécutes devant la caméra, calibres la couleur de ton embout et obtiens les chiffres du
critère de fin (détection, latence, décision go/no-go).

## Livrables

**PR 1 — Suivi de couleur et détection de coup (logique pure, testable sans caméra)** (`feat/vision-tracking`)
- [x] `core/events.py` : `HitEvent` (élément, vélocité, horodatage, source), `Source` (clavier/MIDI/vision)
- [x] `input/vision/color_tracker.py` : trouve le centre d'un embout coloré dans une image (HSV), testé sur des images synthétiques
- [x] `input/vision/strike_detector.py` : détecte un coup au franchissement d'un plan de frappe à vitesse descendante (cadrage §3), testé sur des trajectoires synthétiques
- [x] Dépendances `opencv-python` et `numpy` ajoutées (`pyproject.toml`)

**PR 2 — Processus caméra séparé et écran de débogage** (`feat/vision-capture`)
- [ ] `input/vision/process.py` : boucle caméra dans un `multiprocessing.Process`, envoie les `HitEvent` par file inter-processus (cadrage §4.1) ; source d'image injectable pour pouvoir tester la boucle sans caméra réelle
- [ ] `tools/vision_debug.py` : fenêtre de débogage — position suivie, vitesse, images/s, latence de traitement
- [ ] Nécessite ta webcam : à essayer et ajuster par toi (plage de couleur HSV à calibrer pour ton embout, ta lumière)

**PR 3 — Protocole de mesure et décision go/no-go** (`feat/vision-measure`)
- [ ] `tools/vision_measure.py` : séance guidée de 50 coups, compte les coups détectés et les statistiques de latence de traitement
- [ ] Protocole de mesure consigné dans cette page (comment mesurer, avec quoi)
- [ ] ADR 0002 : décision go/no-go et, si « go », caractéristiques de caméra à viser pour la suite — rempli avec tes résultats

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows) pour la logique testable sans caméra
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] ≥ 90 % de coups détectés sur 50 coups à 80 BPM (mesuré, toi devant la caméra)
- [ ] Latence geste → détection mesurée
- [ ] Décision go/no-go et choix de caméra consignés dans un ADR

## Décisions prises (liens vers les ADR)

_Aucune pour l'instant._

## Écarts par rapport au plan

- **PR 1 — seuils par défaut non calibrés.** `MIN_BLOB_AREA` (30 px²), `min_speed_px_per_s` (200 px/s) et `refractory_s` (0,15 s) dans `strike_detector.py`, ainsi que les plages de couleur `GREEN`/`MAGENTA` dans `color_tracker.py`, sont des valeurs de départ raisonnables mais pas mesurées sur une vraie image de ta webcam, ta lumière, ton embout. Attends-toi à devoir les ajuster une fois l'écran de débogage (PR 2) en main — ce sera plus rapide à l'œil qu'en théorie.

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
