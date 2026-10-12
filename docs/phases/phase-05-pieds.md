# Phase 05 — Vision : pieds (V3.2)

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| À cadrer (squelette créé le 2026-10-12, à la clôture de la phase 04) | à estimer | — | v0.5.0 |

## Objectif

Jouer la **grosse caisse** et la **pédale de charleston** au pied, en plus des mains : suivi d'un marqueur sur la chaussure (webcam intégrée au sol), sinon pédales au clavier USB. Charleston ouverte / fermée selon le pied gauche (*Could*). Fin : **US8**, mêmes critères que US7 pour la grosse caisse et la pédale de charleston.
Référence : [cadrage](../00-cadrage.md) §5 (phase 05).

## Point de départ

- Phase 04 terminée (`v0.4.0`) : deux mains, quatre éléments, calibration par frappes, nuance, outil de mesure US7 avec diagnostic des coups manqués (`tools/vision_measure.py --pattern`). Voir [phase 04](phase-04-deux-mains.md) et sa rétrospective.
- **Pieds** : test anticipé en phase 03 (webcam intégrée au sol à 60–70 cm, une séance) : marqueur vu sur 100 % des images, 0 faux coup, 31 images/s, mais retard de **+109 ms** par rapport au clavier et un ruban qui s'est décollé. Décision repoussée à une séance de confirmation ([ADR 0002](../adr/0002-vision-go-no-go-et-camera.md), « Décision caméras pour la suite »).
- **Caméra des mains** : pas d'achat pour l'instant ; la décision dépend du choix des pieds ([ADR 0004](../adr/0004-camera-des-mains.md)).
- **Couleur du pied : jaune fluo** (le bleu est pris par la main gauche).

## À décider au cadrage

1. **Séance de confirmation du pied** (avant tout code) : marqueur jaune solidement fixé (ruban autour de la chaussure, pas seulement collé dessus), plan de frappe réglé avec l'outil de débogage, référence au clavier USB posé au sol, puis trois séances pied, lumière notée. Lecture : retard sous ~60 ms par rapport au clavier → option (a) confirmée ; au-dessus après correction → option (c), pédales USB.
2. **Disposition des caméras** : (a) webcam 60 images/s d'occasion pour les mains + webcam intégrée au sol pour les pieds (~40 €) ; (b) deux caméras dédiées (hors budget) ; (c) pédales USB au clavier pour les pieds, webcam intégrée pour les mains (0 €). Le choix fixe aussi la décision d'achat de l'ADR 0004.
3. **Essai gratuit de 60 images/s** sur la webcam intégrée (`[camera] fps = 60`, `mjpeg = true`) avant d'acheter quoi que ce soit.
4. Plage de couleur du **jaune fluo** (à écrire et à tester sur des teintes de peau, de sol et de jean synthétiques, comme pour le bleu), et règles d'attribution propres aux pieds (un marqueur par pied, deux éléments).
5. Découpage en PR et budget de temps.

## Livrables

_À définir au cadrage._

## Critères de fin (Definition of Done)

- [ ] US8 : grosse caisse et pédale de charleston, mesurés devant la caméra (ou aux pédales USB selon la décision), avec les critères de l'US7
- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] Décision caméras (pieds et mains) consignée

## Décisions prises (liens vers les ADR)

- [ADR 0002 — Vision : go/no-go et choix de caméra](../adr/0002-vision-go-no-go-et-camera.md)
- [ADR 0004 — Caméra des mains](../adr/0004-camera-des-mains.md)

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
