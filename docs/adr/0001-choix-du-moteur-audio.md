# ADR 0001 — Choix du moteur audio

| Statut | Date | Phase |
| --- | --- | --- |
| Accepté, validé en jouant à la clôture de la phase 01 | 2026-10-09 | 01 |

## Contexte

La V1 exige qu'une touche déclenche le son « sans latence perceptible » et qu'on puisse enchaîner des coups rapides, sous Windows, en Python, sans outil payant. Au-delà d'une vingtaine de millisecondes, un décalage devient gênant pour un batteur (ordre de grandeur, à vérifier en jouant). La latence totale additionne : clavier (USB), boucle du programme, tampon audio, pilote Windows et sortie (le Bluetooth ajoute beaucoup).

## Options

1. **`pygame.mixer` (SDL)** — déjà fourni par pygame-ce ; mixage en C dans un fil séparé, donc indépendant du GIL Python ; tampon réglable. Moins de contrôle sur le mode du pilote Windows.
2. **`sounddevice` (PortAudio) + mixeur numpy, WASAPI exclusif** — latence potentiellement plus basse ; mais mixage en Python dans le rappel audio (risque de craquements quand le rendu occupe le GIL) et plus de code.
3. **Autres liaisons C/C++ (miniaudio, rtmixer…)** — maintenance et installation plus incertaines.

## Décision

Option 1 : `pygame.mixer.pre_init(48000, -16, 2, 256)`, 32 canaux, groupe d'étouffement pour la charleston.
Le moteur est placé derrière une interface minimale (`play(element, velocity)`, `choke(group)`) pour pouvoir basculer vers l'option 2 sans toucher au reste.

**Critère de bascule** : latence logicielle + tampon > 20 ms mesurée, ou craquements audibles au tampon 256.

## Conséquences

- Aucune dépendance supplémentaire en V1.
- `tools/latency_probe.py` mesure le délai événement → mixeur et note la configuration.
- Mesures à consigner ci-dessous à la fin de la phase 01.

## Mesures

Mesurées avec `tools/latency_probe.py` (PR 2, `AudioEngine.play`, 200 essais sur `snare`, kit synthétique par défaut).

| Date | Sortie audio | Tampon | Délai logiciel | Ressenti | Décision |
| --- | --- | --- | --- | --- | --- |
| 2026-10-09 | Sortie par défaut Windows (mesure logicielle) | 256 échantillons @ 48 kHz | Appel Python : 0,036 ms (moy.), 0,174 ms (max). Tampon théorique : 5,33 ms. Total estimé : ≈ 5,37 ms | Non testé en jouant à ce stade (pas encore de clavier branché, PR 3) | Garder le tampon à 256 pour l'instant : le coût logiciel de l'appel est négligeable, le plancher vient du tampon SDL. 5,37 ms dépasse légèrement la cible de < 5 ms de la phase, mais reste loin du seuil de bascule (> 20 ms) |
| 2026-10-09 | Casque filaire | 256 échantillons @ 48 kHz (inchangé) | ≈ 5,37 ms (mesure logicielle ci-dessus, inchangée) | Validé par l'utilisateur : aucun retard perçu au casque filaire, sur les 10 éléments, 3 touches simultanées et un roulement rapide | Clôture : tampon 256 conservé tel quel, aucune bascule vers `sounddevice` nécessaire |
