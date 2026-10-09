# Batterie

Batterie virtuelle pour Windows : jouez au clavier, suivez des partitions qui défilent, puis jouez « dans le vide » devant une webcam avec des baguettes à embout coloré.

> **Statut** : cadrage terminé, phase 01 (batterie au clavier) à venir. Voir [docs/00-cadrage.md](docs/00-cadrage.md).

## Feuille de route

| Version | Contenu | Statut |
| --- | --- | --- |
| V1 | Batterie au clavier | À faire |
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

Ou double-clic sur `Batterie.bat` (disponible après la phase 01).

## Documentation

- [Cadrage](docs/00-cadrage.md) · [Spécifications](docs/01-specifications.md) · [Architecture](docs/02-architecture.md)
- [Phases](docs/phases/) · [Décisions (ADR)](docs/adr/) · [Journal](docs/journal.md) · [Glossaire](docs/glossaire.md)

## Licence

Code : MIT proposée, à confirmer avant publication. Sons et partitions : chaque fichier déclare sa propre licence (CC0, CC-BY, domaine public ou création originale).
