# Phase 04 — Vision : deux mains, kit complet

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| À cadrer | 6 à 10 h de ton temps | — | v0.4.0 |

## Objectif

Jouer avec deux baguettes sur plusieurs éléments (caisse claire, charleston, un tom, une cymbale) devant la webcam, au lieu du clavier. C'est la deuxième sous-version de la V3 (V3.1).
Référence : [cadrage](../00-cadrage.md) §8 (phase 04), user story US7 (critères complets : 100 coups en croches à 90 BPM, ≥ 95 % détectés, ≤ 2 % de faux coups, ≥ 95 % attribués au bon élément, latence geste → son ≤ 60 ms).

## Point de départ (phase 03, ADR 0002)

- Le suivi d'un embout vert avec la webcam intégrée a atteint le critère de la phase 03 : 48 à 50 coups sur 50, 0 faux coup, 31,2 images/s, retard par rapport au clavier ≤ 55 ms.
- **Pas d'achat de caméra décidé.** Le livrable « achat de la caméra 60 images/s » du cadrage devient conditionnel : cadence ou détection qui chutent en lumière faible, retard geste → son au-dessus de 60 ms avec le son réel, ou placement de la caméra devenu le problème.
- Réserves de l'ADR à lever ici : deux mains (risque de confusion de couleur), plusieurs éléments, tenue à 90 BPM en croches, retard détection + son au ras de 60 ms.
- `tools/vision_debug.py` et `tools/vision_measure.py` servent de base pour calibrer et mesurer ; la calibration par édition de constantes (écart de la phase 03) sera probablement à remplacer par un vrai écran de calibration, puisque cette phase en multiplie les réglages.

## Prérequis

- [ ] Les deux couleurs d'embout (main gauche / main droite) que tu comptes utiliser, et de quoi les fabriquer (ruban adhésif, embouts)
- [ ] Phase détaillée et découpée en PR (à faire au démarrage)

## Livrables

_À détailler au démarrage de la phase, d'après le cadrage : deux couleurs ; zones par élément ; écran de calibration ; anti-double-coup ; nuance de vélocité (Should)._

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] US7 sur caisse claire, charleston, un tom et une cymbale (mesuré, toi devant la caméra)
- [ ] Décision d'achat (ou non) d'une caméra consignée dans un ADR

## Décisions prises (liens vers les ADR)

- [ADR 0002 — Vision : go/no-go et choix de caméra](../adr/0002-vision-go-no-go-et-camera.md) (héritée de la phase 03)

## Écarts par rapport au plan

_Aucun pour l'instant._

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
