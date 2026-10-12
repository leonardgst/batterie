# ADR 0003 — Zones de frappe et calibration par frappes guidées

| Statut | Date | Phase |
| --- | --- | --- |
| Proposé — à confirmer par ton essai de la calibration devant la caméra | 2026-10-10 | 04 |

## Contexte

Avec deux mains et plusieurs éléments, un coup détecté ne suffit plus : il faut dire **quel élément** a été frappé (M9) et la position des éléments dans l'image dépend de ta pièce, de ta caméra et de où tu te places. Le cadrage demande donc une calibration des zones (M11) et prévoit un modèle `Zone (V3) : element_id, camera_id, polygon, strike_plane_y, marker_color`.

Trois choix à faire, qui se tiennent : **la forme des zones**, **la façon de les calibrer**, **où les ranger**. Contraintes : tu ne codes pas (pas de fichier de coordonnées à écrire à la main), et la calibration doit marcher sans autre matériel que la caméra et tes baguettes.

## Options

**Forme des zones**

1. **Rectangle + plan de frappe** — quatre bords et une ligne horizontale. Simple à calculer, à dessiner et à valider.
2. **Polygone** (le modèle du cadrage) — suit mieux une perspective ou un élément incliné. Plus de code (point dans un polygone, édition) pour un gain qu'on n'a pas besoin cette phase : les quatre éléments sont côte à côte.

**Calibration**

1. **Dessiner les zones à la souris** sur l'aperçu. Direct, mais oblige à deviner où tu frapperas, et à régler le plan de frappe au jugé.
2. **Frapper guidé** : l'écran demande « frappe la caisse claire 3 fois », puis l'élément suivant. La zone et le plan se déduisent de tes coups réels.
3. **Éditer un fichier** de coordonnées à la main. Exclu : contraire à ton usage.

**Rangement**

1. **Dans `settings.toml`.** Mais ce fichier n'est jamais réécrit (pour préserver tes modifications et ses commentaires, voir la phase 01) : y écrire des zones obligerait à le réécrire en perdant les commentaires.
2. **Dans un fichier séparé `zones.toml`**, écrit par l'application, à côté de `settings.toml`.

## Décision

- **Rectangles avec plan de frappe** (option 1). Chaque zone : `x_min`, `x_max`, `y_top`, `strike_plane_y`, `y_bottom`. Le polygone du cadrage est remplacé par un rectangle, écart assumé.
- **Calibration par frappes guidées** (option 2), 3 coups par élément, dans l'ordre de gauche à droite : charleston fermée, caisse claire, tom médium, ride. Les coups de n'importe quelle main comptent.
  - **Où** : la zone va de ton coup le plus à gauche au plus à droite, plus 20 px de marge. Deux zones voisines qui se chevauchent sont séparées à mi-chemin entre leurs coups ; si les coups se mélangent, la calibration le dit et demande d'écarter les éléments.
  - **Plan de frappe** : à 60 % de la course, entre le point haut du coup **le moins relevé** et le point bas du coup **le moins profond**. Donc sous le haut et au-dessus du bas de *chacun* de tes coups : tous franchissent le plan. 60 % et pas plus bas, pour déclencher avant le point bas (gagner de la latence, cadrage §3) ; pas plus haut, pour ne pas se déclencher sur un geste qui hésite.
  - **Garde-fous** : trois coups à moins de 50 px les uns des autres (un coup resté sur l'élément précédent doit passer pour un écart, pas pour une zone élargie), une course d'au moins 20 px, et 1,5 s d'attente après chaque élément avant de compter le coup suivant.
- **Fichier séparé `zones.toml`** (option 2) : `%APPDATA%\Batterie\zones.toml`, avec un numéro de version et la largeur de l'image de calibration, refusé s'il ne correspond plus. Écrit par fichier temporaire, jamais à moitié. Échap pendant la calibration n'écrit rien.
- **Pas d'éléments empilés** pour cette phase : les zones ne se chevauchent pas en largeur (validé à la lecture et à la calibration), parce qu'une frappe vers le bas sur un élément situé sous un autre traverserait d'abord le plan du premier.

## Conséquences

- **Les zones sont liées à ta position et à celle de la caméra.** Si l'un des deux bouge, elles ne correspondent plus : recalibrer prend une minute (12 coups). Les coordonnées sont celles de l'image réduite (320 px de large) **après le miroir**.
- **Tout est testé sans caméra**, sur des trajectoires synthétiques, y compris la propriété importante : *les coups avec lesquels on calibre sont bien détectés par les zones obtenues*. Seul ton essai dira si les seuils conviennent à tes vrais gestes.
- **Seuils de départ à ajuster en jouant** (constantes en haut de `input/vision/calibration.py`) : descente de 12 px et remontée de 10 px pour repérer un coup, course minimale de 25 px, vitesse de pointe minimale de 150 px/s, plan à 60 %, marge de 20 px, dispersion maximale de 50 px. Un geste très court (moins de 25 px de course, soit une dizaine de centimètres) n'est pas reconnu comme un coup pendant la calibration.
- **Le kit complet** (dix éléments, éléments empilés) demandera une autre règle d'attribution, par exemple au point bas du geste plutôt qu'au franchissement d'un plan ; cet ADR sera alors complété ou remplacé.
- Le polygone reste possible plus tard sans casser le fichier : le numéro de version permet de changer le format.
