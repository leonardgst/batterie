# Batterie

Batterie virtuelle pour Windows : jouez au clavier, suivez des partitions qui défilent, puis jouez « dans le vide » devant une webcam avec des baguettes à embout coloré.

> **Statut** : phases 01 (batterie au clavier, `v0.1.0`), 02 (partitions, `v0.2.0`) et 03 (vision, preuve de concept, `v0.3.0`) terminées. Phase 04 (deux mains) à venir.
> Voir [docs/00-cadrage.md](docs/00-cadrage.md) et [docs/phases/](docs/phases/).

## Feuille de route

| Version | Contenu | Statut |
| --- | --- | --- |
| V1 | Batterie au clavier | Terminé (`v0.1.0`) |
| V2 | Partitions qui défilent | Terminé (`v0.2.0`) |
| V3 | Jeu à la caméra (mains, puis pieds) | Preuve de concept validée (`v0.3.0`) ; deux mains à venir |

## Installation (Windows)

Prérequis : [uv](https://docs.astral.sh/uv/) et Git.

```powershell
git clone https://github.com/leonardgst/batterie.git
cd batterie
uv sync
```

## Lancement

```powershell
uv run batterie
```

Ou double-clic sur `Batterie.bat`.

La fenêtre affiche le kit avec la touche de chaque élément. Appuie sur une touche pour
jouer le son correspondant et voir l'élément s'illuminer. Échap (ou fermer la fenêtre)
quitte.

**Touches par défaut (clavier AZERTY)** :

| Élément | Touche | Élément | Touche |
| --- | --- | --- | --- |
| Grosse caisse | Espace | Tom médium | K |
| Charleston (pédale) | C | Tom basse | L |
| Charleston fermée | D | Crash | Z |
| Charleston ouverte | E | Ride | I |
| Caisse claire | F | Tom aigu | J |

## Choisir et jouer une partition

Depuis l'accueil (`uv run batterie`), flèches haut/bas pour choisir, Entrée pour
valider :

1. **Partitions** → choisis un style (rock, jazz, other, solo).
2. Choisis une partition dans la liste (titre, tempo et difficulté affichés). Flèches
   gauche/droite pour régler le tempo (de 50 % à 120 %, par pas de 5 %).
3. Entrée : décompte d'une mesure, puis les coups à jouer défilent dans des couloirs
   au-dessus du kit, jusqu'à leur ligne de frappe. Joue-les aux mêmes touches qu'en jeu
   libre, au bon moment.
4. Échap met en pause (Entrée pour reprendre) ; Échap une seconde fois quitte vers la
   liste des partitions.
5. À la fin du morceau : écran de résultat avec ta précision (parfait / bien / raté,
   cadrage R7). Entrée pour rejouer, Échap pour revenir à la liste.

## Personnaliser les touches et le volume

Au premier lancement, `uv run batterie` crée un fichier `settings.toml` dans
`%APPDATA%\Batterie\settings.toml`, avec des commentaires expliquant chaque réglage.
Ouvre-le avec le Bloc-notes pour :

- changer le `volume` général (de `0.0`, muet, à `1.0`, fort) ;
- remplacer la touche d'un élément dans la section `[keys]`. Le nom de touche attendu
  est la position physique de la touche (comme nommée sur un clavier QWERTY américain),
  pas forcément la lettre imprimée sur ton clavier — le commentaire en bout de ligne
  indique la lettre affichée en AZERTY français.

Enregistre le fichier puis relance `uv run batterie` pour appliquer les changements.

## Testeur de touches simultanées

Certains claviers ne peuvent pas reporter certaines combinaisons de touches enfoncées
en même temps (« ghosting »), ce qui peut faire perdre un coup en jouant vite. Pour
vérifier le tien :

```powershell
uv run python tools/keytest.py
```

Maintiens plusieurs touches du kit à la fois : une touche qui reste grise malgré
l'appui n'est pas reçue par Windows dans cette combinaison.

## Vision : preuve de concept (phase 03)

La V3 remplacera le clavier par des baguettes à embout coloré filmées par webcam. La
preuve de concept (une baguette, la webcam intégrée) est concluante : décision « go »
sans achat de caméra, voir l'[ADR 0002](docs/adr/0002-vision-go-no-go-et-camera.md). Les
deux outils de cette phase restent disponibles pour calibrer et mesurer. Aucune image
n'est enregistrée.

```powershell
uv run python tools/vision_debug.py      # aperçu caméra, point suivi, plan de frappe : pour calibrer
uv run python tools/vision_measure.py    # séance mesurée : 50 coups à 80 BPM
```

1. **Calibrer** avec `vision_debug.py` : règle la couleur de l'embout et la hauteur du
   plan de frappe dans le préréglage de la cible (`STICK` ou `FOOT`, en haut du fichier),
   puis relance, jusqu'à ce que chaque coup soit compté une fois.
2. **Mesurer** avec `vision_measure.py` : touche K pour une séance de référence à la
   barre d'espace, touche V pour une séance à la baguette. Un métronome donne 4 clics de
   décompte puis 50 clics ; un coup par clic. À la fin : coups détectés, faux coups,
   images/s réelles, temps de traitement, et retard de la caméra par rapport au clavier.

Les deux outils suivent par défaut la baguette (`--target stick`, caisse claire).
`--target foot` suit la pointe du pied (grosse caisse), pour tester la webcam intégrée
posée au sol ; ce préréglage n'est pas calibré. `--target hands` suit les deux mains
(embout orange à gauche, vert à droite, image en miroir) : phase 04, aussi non calibré.
Pour voir le déroulé sans caméra : `uv run python tools/vision_measure.py --simulate`.
Protocoles : [baguette](docs/phases/phase-03-vision-poc.md#protocole-de-mesure) et
[pied](docs/phases/phase-03-vision-poc.md#protocole-de-mesure--pied-test-anticipé-de-la-phase-05).

## Calibrer la caméra (phase 04)

Pour jouer avec tes deux baguettes (embout orange à gauche, vert à droite), l'application
doit savoir où se trouve chaque élément dans l'image de ta caméra. Depuis l'accueil,
choisis **Calibrer la caméra** : l'écran te demande de frapper, à l'endroit où tu les
imagines, la charleston fermée, la caisse claire, le tom médium puis le ride, 3 coups chacun,
de gauche à droite. Les rectangles montrent où tu frappes, la ligne rouge où le coup se
déclenchera. **Entrée** enregistre (`%APPDATA%\Batterie\zones.toml`), **Échap** annule sans
rien changer, **R** recommence l'élément en cours. À refaire si ta caméra ou toi bougez.
Le jeu à la caméra lui-même arrive à la PR suivante.

## Documentation

- [Cadrage](docs/00-cadrage.md) · [Spécifications](docs/01-specifications.md) · [Architecture](docs/02-architecture.md)
- [Phases](docs/phases/) · [Décisions (ADR)](docs/adr/) · [Journal](docs/journal.md) · [Glossaire](docs/glossaire.md)

## Licence

Code : MIT proposée, à confirmer avant publication. Sons et partitions : chaque fichier déclare sa propre licence (CC0, CC-BY, domaine public ou création originale).
