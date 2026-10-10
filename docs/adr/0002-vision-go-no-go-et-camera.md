# ADR 0002 — Vision : go/no-go et choix de caméra

| Statut | Date | Phase |
| --- | --- | --- |
| Accepté — décision prise sur les mesures de l'utilisateur | 2026-10-10 | 03 |

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

Séances faites par l'utilisateur avec `tools/vision_measure.py` (une séance clavier de référence, des séances caméra), puis rapportées à la fin de la phase. Les valeurs sont celles qu'il a lues à l'écran ; quand il n'a donné qu'une tranche, c'est la tranche qui est consignée, pas une valeur inventée. Le détail séance par séance n'a pas été relevé : l'utilisateur a jugé inutile de transmettre le texte du terminal.

Conditions : embout — brosse à dents verte fixée à la baguette ; réglages — valeurs par défaut du dépôt (couleur `GREEN`, plan de frappe à 150 ; aujourd'hui le préréglage `STICK` de `tools/vision_debug.py`) ; lumière — non précisée ; sortie audio — casque filaire ; webcam — intégrée du portable.

| Ce qu'on regarde | Seuil de la grille | Mesuré | Verdict |
| --- | --- | --- | --- |
| Coups détectés (la moins bonne séance caméra) | ≥ 45 / 50 | 48 à 50 / 50 | Atteint, au niveau de la cible finale de la V3 (95 %) |
| Faux coups | ≤ 2 par séance | 0 | Atteint |
| Retard par rapport au clavier | ≤ 55 ms | ≤ 55 ms (tranche choisie, valeur exacte non relevée) | Atteint |
| Images/s réelles | ≥ 25 | 31,2 | Atteint ; cadence nominale de la webcam (30), le traitement ne la ralentit pas |
| Traitement par image | médiane ≤ 5 ms | non relevé | Non vérifié directement ; une cadence de 31,2 images/s montre que le traitement tient dans l'intervalle entre deux images |

Au-delà des chiffres, l'utilisateur rapporte que l'embout est suivi sans décrocher, que le passage sur la ligne du plan de frappe est détecté de façon fiable et que le compteur de coups est juste.

## Décision

**Go, sans achat de caméra pour l'instant (option 2).** Le suivi de couleur sur CPU avec la webcam intégrée atteint le critère de fin de la phase 03 (≥ 90 % de 50 coups à 80 BPM) avec une marge, sans aucun faux coup, et la grille de lecture classe le retard dans la tranche « US7 déjà tenue avec la webcam intégrée ».

Réserves, pour ne pas surestimer ce résultat :

- une baguette, un seul élément, un seul embout : la phase 04 ajoute la deuxième main, plusieurs zones et plusieurs éléments, où les risques de confusion de couleur et de faux coups sont plus grands ;
- US7 demande le retard geste → *son* ≤ 60 ms : retard de détection ≤ 55 ms + environ 5 ms de moteur audio (ADR 0001) donnent au plus 60 ms, donc au ras du critère. À confirmer en phase 04, avec le son réellement joué ;
- le critère de la phase (90 % sur 50 coups à 80 BPM) est plus léger que US7 (95 % sur 100 coups à 90 BPM) : la tenue à 90 BPM et en croches n'est pas encore mesurée ;
- la lumière de la séance n'a pas été consignée : une pièce moins bien éclairée peut faire chuter la cadence de la webcam et le taux de détection.

## Caméra à viser pour la suite

**Ne rien acheter maintenant.** La webcam intégrée tient le critère de la phase 03, donc l'achat prévu par le cadrage (§7, phase 04) n'est pas déclenché par un manque de performance. Il le sera si l'un de ces points se présente, avec la caméra décrite ci-dessous :

- la cadence ou le taux de détection chutent quand la lumière baisse ;
- le retard geste → son dépasse 60 ms avec le son réel en phase 04 ;
- le placement devient le problème : la webcam du portable est fixée à l'écran, alors que le cadrage recommande une caméra en hauteur face au batteur (~1,8 m, inclinée vers le bas), et la phase 05 (pieds) demandera un second point de vue.

Caractéristiques à chercher le moment venu (cadrage §7, inchangées) : une webcam UVC (sans pilote), 1280×720 à 60 images/s réelles en MJPEG, exposition réglable manuellement, champ d'environ 80–90°, sous 45 €. Prix : une Logitech C922 neuve coûte 70 à 99 € ; d'occasion, une C922 ou une StreamCam se trouve vers 40 € (correction du 2026-10-10). Cette caméra rapprocherait la cible de 40 ms (16 ms par image au lieu de 33 ms).

## Conséquences

- La phase 04 (V3.1, deux mains) peut démarrer avec la webcam intégrée ; son livrable « achat de la caméra 60 images/s » devient conditionnel aux trois points ci-dessus.
- Le suivi de couleur avec embout vert reste la méthode ; MediaPipe n'est pas nécessaire à ce stade. Aucune dépendance ajoutée.
- `tools/vision_measure.py` et son protocole servent de référence pour comparer une future caméra, ou une future version du suivi, dans les mêmes conditions.
- Piste pour plus tard : l'outil affiche ses résultats sans les enregistrer ; en relever une trace dans un fichier rendrait les prochaines décisions plus précises que des valeurs lues et rapportées à la main.

## Test du pied — webcam intégrée au sol (ajout du 2026-10-10)

Contexte : la disposition des caméras choisie pour la V3 (note du [cadrage §7](../00-cadrage.md), 2026-10-10) réserve la webcam intégrée du portable aux **pieds** (ordinateur posé au sol à 50–80 cm devant les pieds), et prévoit une webcam 60 images/s séparée, en hauteur, pour les mains. Le test du pied est anticipé en phase 03 (PR 4, `--target foot`) : il est **informatif**, ne bloque pas la clôture de la phase et ne remet pas en cause la décision « go » ci-dessus, qui porte sur la baguette. Protocole : [phase 03, « Protocole de mesure — pied »](../phases/phase-03-vision-poc.md#protocole-de-mesure--pied-test-anticipé-de-la-phase-05).

### Options pour la disposition des caméras

| Option | Contenu | Coût | Atouts | Limites |
| --- | --- | --- | --- | --- |
| **(a)** | Webcam 60 images/s pour les mains + webcam intégrée au sol pour les pieds | ~40 € (caméra d'occasion) | Rien d'autre à acheter pour les pieds ; une seule caméra à placer en hauteur | Le portable doit être posé au sol, écran refermé à demi ; le pied doit rester visible et assez net à 30 images/s |
| **(b)** | Deuxième caméra dédiée aux pieds | Deux caméras d'occasion à ~40 € dépassent le budget de 50 € ; une caméra bon marché pour les pieds reste à chiffrer | Placement libre, indépendant du portable | Budget ; deux flux à traiter sur un processeur sans carte graphique ; deux calibrations |
| **(c)** | Pédales : vieux clavier USB au sol, touches frappées au pied (secours) | 0 € (si un clavier est disponible) | Passe par le clavier déjà géré (`input/keyboard.py`), latence validée en phase 01, aucun risque de détection | Pas « dans le vide » ; sensation de pédale à vérifier ; à tester pour le *ghosting* avec `tools/keytest.py` |

### Lecture du test du pied (grille fixée avant la mesure)

Même outil et mêmes seuils que pour la baguette, avec le préréglage `FOOT` (non calibré : seuils de départ estimés, à ajuster d'abord avec `vision_debug.py --target foot`).

| Résultat de la meilleure séance pied après calibration | Conclusion |
| --- | --- |
| ≥ 45 / 50 détectés, ≤ 2 faux coups, ≥ 25 images/s réelles | **Option (a) confirmée** : la webcam intégrée au sol suffit pour les pieds |
| Marqueur visible moins de 90 % du temps, ou détection entre 35 et 44 / 50, avec une cause identifiée (lumière, taille ou contraste du marqueur, réglage du plan ou des seuils) | Corriger la cause et refaire une séance avant de conclure ; en attendant, (a) reste l'hypothèse de travail |
| Moins de 35 / 50 après correction, pointe du pied masquée (par la jambe ou le pied gauche) ou cadence sous 25 images/s malgré une bonne lumière | **Option (c)** (pédales USB) pour la phase 05 ; (b) seulement si le budget le permet et si le problème vient du point de vue, pas du suivi |

Ce test ne mesure qu'une pointe de pied, sans pied gauche ni mains en même temps : il dit si le pied est suivable, pas que le kit complet l'est.

### Mesures — pied, webcam intégrée au sol

_À remplir avec les résultats de l'utilisateur (séance pied, `tools/vision_measure.py --target foot`)._

Conditions : placement — ordinateur à … cm des pieds, caméra à … cm du sol ; marqueur — … (couleur, taille, position sur la chaussure) ; lumière — … ; préréglage `FOOT` retenu après calibration — plan de frappe …, vitesse minimale …, anti-rebond … ; référence — séance clavier au doigt / pied sur un clavier USB au sol.

| Date | Séance | Coups détectés | Faux coups | Écart coup − clic (médiane, écart-type) | Marqueur visible | Images/s réelles | Traitement (médiane / p95 / max) | Retard par rapport au clavier |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| | Référence clavier | | | | — | — | — | — |
| | Pied 1 | | | | | | | |
| | Pied 2 | | | | | | | |
| | Pied 3 | | | | | | | |

### Décision caméras pour la suite

**Provisoire, en attendant les mesures : (a), avec (c) en secours** — c'est la disposition choisie avec l'utilisateur. À confirmer ou corriger avec le tableau de lecture ci-dessus.

Précision sur la décision « ne rien acheter maintenant » (plus haut) : elle valait pour la performance (la webcam intégrée suffit pour la baguette). Avec cette disposition, la webcam intégrée est affectée aux pieds, donc la webcam des mains sera forcément une autre caméra : le critère de **placement** est rempli, et l'achat d'une webcam 60 images/s d'occasion devient prévu, à faire quand la phase 04 en aura besoin (la phase 04 peut démarrer avec la webcam intégrée tant que la caméra n'est pas là, puisqu'elle a suffi pour la baguette en phase 03).
