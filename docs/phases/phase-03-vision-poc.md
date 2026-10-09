# Phase 03 — Vision : preuve de concept

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| À faire | 4 à 6 h de ton temps | — | v0.3.0 |

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

## Livrables

_Repris du cadrage §5 ; le découpage en PR reste à définir une fois le matériel connu._

- [ ] Processus de vision séparé (`multiprocessing`), jamais dans le processus audio/rendu
- [ ] Suivi d'un embout coloré (OpenCV, HSV) sur une webcam
- [ ] Détection de coups sur la caisse claire (franchissement d'un plan de frappe à vitesse descendante, cadrage §3)
- [ ] Écran de débogage : position suivie, vitesse, latence mesurée
- [ ] Protocole de mesure consigné (comment on a mesuré, avec quoi)

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows) pour la logique testable sans caméra
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] ≥ 90 % de coups détectés sur 50 coups à 80 BPM (mesuré, toi devant la caméra)
- [ ] Latence geste → détection mesurée
- [ ] Décision go/no-go et choix de caméra consignés dans un ADR

## Décisions prises (liens vers les ADR)

_Aucune pour l'instant._

## Écarts par rapport au plan

_À remplir au fil de la phase._

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
