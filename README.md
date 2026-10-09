# Batterie

Batterie virtuelle pour Windows : jouez au clavier, suivez des partitions qui défilent, puis jouez « dans le vide » devant une webcam avec des baguettes à embout coloré.

> **Statut** : phase 01 (batterie au clavier) terminée — `v0.1.0`. Phase 02 (partitions) à venir.
> Voir [docs/00-cadrage.md](docs/00-cadrage.md) et [docs/phases/](docs/phases/).

## Feuille de route

| Version | Contenu | Statut |
| --- | --- | --- |
| V1 | Batterie au clavier | Terminé (`v0.1.0`) |
| V2 | Partitions qui défilent | À faire |
| V3 | Jeu à la caméra (mains, puis pieds) | À faire |

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

## Documentation

- [Cadrage](docs/00-cadrage.md) · [Spécifications](docs/01-specifications.md) · [Architecture](docs/02-architecture.md)
- [Phases](docs/phases/) · [Décisions (ADR)](docs/adr/) · [Journal](docs/journal.md) · [Glossaire](docs/glossaire.md)

## Licence

Code : MIT proposée, à confirmer avant publication. Sons et partitions : chaque fichier déclare sa propre licence (CC0, CC-BY, domaine public ou création originale).
