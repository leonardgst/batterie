# ADR 0002 — Vision : go/no-go et choix de caméra

| Statut | Date | Phase |
| --- | --- | --- |
| Proposé — grille de lecture fixée, en attente des mesures de l'utilisateur | 2026-10-10 | 03 |

## Contexte

La V3 remplace le clavier par des baguettes à embout coloré filmées par webcam. C'est le risque n° 3 du cadrage (« vision trop lente ou peu fiable ») : à 30 images/s, une image dure 33 ms, et l'éclairage ou un mauvais seuil peuvent faire rater des coups ou en inventer. Le cadrage prévoit donc une preuve de concept à 0 € — une baguette, la caisse claire, la webcam intégrée du portable (Intel Core i7-1255U, pas de carte graphique dédiée) — et **aucun achat avant d'avoir décidé**, sur des chiffres, si l'approche tient.

Cet ADR consigne cette décision. La grille de lecture ci-dessous est écrite **avant** la mesure, pour ne pas ajuster les seuils aux résultats.

Repères du cadrage :

- critère de fin de la phase 03 : ≥ 90 % de coups détectés sur 50 coups à 80 BPM, latence geste → détection mesurée ;
- cible finale de la V3 (US7) : ≥ 95 % détectés, ≤ 2 % de faux coups, latence geste → son ≤ 60 ms (cible 40 ms avec une caméra 60 images/s) ;
- le son ajoute ≈ 5 ms à la détection (ADR 0001) ;
- budget caméra : 50 € au maximum.

## Options

1. **Go, avec achat d'une webcam 60 images/s** (recommandation de départ du cadrage §7) — la détection fonctionne, et le retard restant vient surtout de la cadence de la webcam intégrée.
2. **Go, sans achat immédiat** — la webcam intégrée suffit déjà pour la phase 04 (deux mains) ; l'achat est repoussé au moment où il devient nécessaire (placement en hauteur, pieds).
3. **Go sous condition** — le critère n'est pas atteint, mais la cause est identifiée et se corrige sans changer d'approche (éclairage, couleur de l'embout, seuils de détection) : on corrige, on remesure.
4. **No-go sur le suivi de couleur** — ni la calibration ni une caméra à ≤ 45 € ne peuvent corriger le problème : la V3 est repensée (autre méthode de suivi, MediaPipe, capteur) ou abandonnée, et le projet reste sur clavier + partitions (V1 et V2, déjà livrées).

## Grille de lecture (fixée avant la mesure)

Mesures faites avec `tools/vision_measure.py`, selon le protocole de [la phase 03](../phases/phase-03-vision-poc.md#protocole-de-mesure) : une séance clavier de référence, trois séances caméra.

| Ce qu'on regarde | Seuil | Si le seuil n'est pas atteint |
| --- | --- | --- |
| Coups détectés | ≥ 45 / 50 sur au moins 2 séances caméra sur 3 | Regarder « Embout visible » : sous 90 %, c'est la couleur ou la lumière (option 3) ; au-dessus, ce sont les seuils de détection — plan de frappe, vitesse minimale (option 3) |
| Faux coups | ≤ 2 par séance (indicatif : pas un critère de fin de cette phase, mais US7 en demandera ≤ 2 %) | Ajuster l'anti-rebond et la vitesse minimale ; à traiter au plus tard en phase 04 (« anti-double-coup ») |
| Retard par rapport au clavier (médiane des séances caméra) | ≤ 55 ms : US7 déjà tenue avec la webcam intégrée | Entre 55 et 100 ms : go, et une caméra 60 images/s est justifiée si les images/s réelles mesurées sont ≤ 30 (option 1). Au-delà de 100 ms : chercher d'abord la cause (cadence qui chute en basse lumière, retard interne de la caméra) avant de trancher entre les options 1 et 4 |
| Images/s réelles | ≥ 25 | En dessous, la webcam intégrée allonge son temps de pose : ajouter de la lumière et remesurer avant de conclure |
| Traitement par image | Médiane ≤ 5 ms | Au-dessus, réduire encore l'image de travail ; le processeur n'est pas le facteur limitant attendu |

No-go (option 4) seulement si, après correction de la calibration et de l'éclairage, le taux de détection reste sous 90 % **et** que rien n'indique qu'une meilleure caméra changerait le résultat.

## Mesures

_À remplir avec les résultats de l'utilisateur._

Conditions : lumière — … ; embout — … ; `COLOR_RANGE` — … ; `STRIKE_PLANE_Y` — … ; sortie audio — casque filaire.

| Date | Séance | Coups détectés | Faux coups | Écart coup − clic (médiane, écart-type) | Embout visible | Images/s réelles | Traitement (médiane / p95 / max) | Retard logiciel estimé | Retard par rapport au clavier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | Clavier (référence) | | | | — | — | — | — | — |
| | Caméra 1 | | | | | | | | |
| | Caméra 2 | | | | | | | | |
| | Caméra 3 | | | | | | | | |

## Décision

_En attente des mesures._

## Caméra à viser pour la suite

_À confirmer ou corriger avec les mesures._ Point de départ, tiré du cadrage §7 : une seule webcam UVC (sans pilote), 1280×720 à 60 images/s réelles en MJPEG, exposition réglable manuellement, champ d'environ 80–90°, à moins de 45 €. Les mesures diront si la cadence est bien le facteur limitant (images/s réelles, retard par rapport au clavier) et si l'exposition manuelle est indispensable (cadence qui chute quand la lumière baisse).

## Conséquences

_À écrire avec la décision._ Déjà acquis quelle que soit l'issue : `tools/vision_measure.py` et son protocole restent l'outil de référence pour comparer une future caméra à la webcam intégrée, dans les mêmes conditions.
