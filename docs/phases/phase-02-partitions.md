# Phase 02 — Partitions

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| À faire | 6 à 10 h de ton temps | — | v0.2.0 |

## Objectif

Choisir une partition (rock, jazz, autre, ou batterie seule) et la jouer du début à la
fin en suivant les touches qui défilent au bon moment. C'est la V2.
Référence : [cadrage](../00-cadrage.md), user stories US4 à US6.

## Livrables

_Repris du cadrage §5 ; le découpage en PR reste à définir en début de phase._

- [ ] Format de partition TOML (grille façon tablature, cadrage §2.4) + chargeur, testé
- [ ] Au moins 12 partitions originales (3 par style : rock, jazz, autre, batterie seule), débutant à intermédiaire, licence déclarée
- [ ] Menu de choix d'une partition (style, morceau, tempo)
- [ ] Transport : horloge, métronome, décompte d'une mesure
- [ ] Couloirs de coups qui défilent vers une ligne de frappe, synchronisés au tempo
- [ ] Écran de fin de morceau
- [ ] Should : tempo réglable (50 % à 120 %, pas de 5 %)
- [ ] Should : jugement des coups (parfait / bien / raté) et score
- [ ] Should : import de fichiers MIDI personnels (`scores/local/`, ignoré par Git)

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal, specs si besoin)
- [ ] Testé en jouant : un morceau choisi et joué du début à la fin en suivant les touches affichées
- [ ] Dérive de synchronisation < 5 ms sur 5 minutes (test automatique)
- [ ] Licence de chaque partition vérifiée et documentée

## Décisions prises (liens vers les ADR)

_Aucune pour l'instant._

## Écarts par rapport au plan

_À remplir au fil de la phase._

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
