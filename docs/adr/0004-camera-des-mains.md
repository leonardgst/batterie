# ADR 0004 — Caméra des mains : acheter une webcam 60 images/s ou garder la webcam intégrée

| Statut | Date | Phase |
| --- | --- | --- |
| Proposé — à accepter par l'utilisateur en fusionnant la PR de clôture de la phase 04 | 2026-10-12 | 04 |

## Contexte

La phase 03 avait conclu « go, sans achat de caméra pour l'instant » ([ADR 0002](0002-vision-go-no-go-et-camera.md)) : la webcam intégrée (30 images/s) suffisait pour une baguette. L'achat d'une webcam 60 images/s d'occasion (~40 €) était resté **conditionnel**, à décider sur des chiffres après la phase 04. Les conditions de l'ADR 0002 :

1. la cadence ou le taux de détection chutent quand la lumière baisse ;
2. le retard geste → son dépasse 60 ms avec le son réel ;
3. le placement devient le problème : avec la disposition (a) (webcam intégrée au sol pour les pieds), la caméra des mains doit être une autre caméra.

La phase 04 a produit les mesures qui manquaient : deux mains, quatre éléments, 100 croches à 90 BPM, avec le son réel du moteur audio dans l'application (hors séance de mesure, qui ne joue rien sur les coups).

## Options

1. **Acheter maintenant** une webcam 60 images/s pour les mains (~40 € d'occasion).
2. **Ne rien acheter maintenant, décider au début de la phase 05**, quand le choix des pieds (webcam intégrée au sol, option (a), ou pédales USB, option (c)) dira si une seconde caméra est nécessaire.
3. **Ne jamais acheter** : garder la webcam intégrée pour les mains, et les pieds aux pédales USB (c).

## Mesures (webcam intégrée, 640×480 demandé et obtenu, 31 images/s, une personne, une pièce)

Tout vient de `tools/vision_measure.py --pattern`, rapports collés par l'utilisateur. Référence clavier à 90 BPM : écart médian −10 ms, écart-type 17 ms (100 / 100).

**À 90 BPM, le tempo du critère US7 (100 croches, motif de 8 sur 4 éléments, deux mains)**

| Séance | Détectés | Faux coups | Bon élément | Écart au clic (médiane, écart-type) | Latence geste → son | Images/s | Traitement par image |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | 98 % | 1 | 100 % (98 / 98) | +2 ms, 44 ms | non mesurée (pas de référence dans ce lancement) | 31,0 | 0,86 ms |
| B | **86 %** | 1 | 100 % (86 / 86) | −29 ms, 48 ms | −14 ms : détection *avant* la référence, « à interpréter » | 31,1 | 0,82 ms |
| C | 99 % | 0 | 99 % (98 / 99) | +2 ms, 42 ms | **+17 ms** | 31,2 | 0,82 ms |

- Séance B : 14 coups manqués, dont 11 « plan de frappe jamais atteint » (il manque 16 px en médiane), concentrés sur la **caisse claire de la main gauche** (positions 3 et 7 du motif : 7 / 13 et 6 / 12). Aucune des quatre positions de l'autre main n'a plus d'un coup manqué. La séance C, jouée juste après, a un seul coup manqué (plan non atteint de 18 px).
- Dans les trois séances l'embout est visible sur 100 % des images ; l'intervalle maximal entre deux images est de 83 à 88 ms (deux ou trois images perdues de temps en temps), l'intervalle médian de 32 ms.

**À 70 BPM (tempo choisi par l'utilisateur pour s'entraîner, non critère)**

| Séance | Détectés | Faux coups | Bon élément | Écart au clic | Remarque |
| --- | --- | --- | --- | --- | --- |
| 1 | 51 % | 0 | 100 % | −93 ms | premier essai, plan calé sur des coups plus appuyés que le jeu |
| 2 | 58 % | 0 | 100 % | −99 ms | idem, embout visible 93 % |
| 3 | 89 % | 2 | 100 % | −23 ms | après recalibration au geste du motif |
| 4 | 50 % | 0 | 100 % | −123 ms | **autre instrument bleu** : main gauche 0 / 50, « embout non vu » à chaque clic, cause confirmée par le diagnostic |
| 5 | 96 % | 2 | 100 % | −100 ms | −83 ms par rapport au clavier : détection en avance |

Ressenti de l'utilisateur dans l'application (jeu caméra) : « tout est bien », la nuance « fonctionne vraiment bien » ; il a demandé des corrections de **volume** de la charleston fermée et de la caisse claire (sons du kit, corrigés), pas de retard.

## Lecture

| Question | Constat | Conclusion |
| --- | --- | --- |
| Détection ≥ 95 % à 90 BPM | 98 %, 86 %, 99 % : tenue dans 2 séances sur 3 | atteint **de façon non constante** ; la séance qui échoue a une cause identifiée (course de la main gauche sur la caisse claire) |
| Faux coups ≤ 2 % | 1 %, 1 %, 0 % | atteint |
| Attribution ≥ 95 % | 100 %, 100 %, 99 % | atteint |
| Latence geste → son ≤ 60 ms (condition 2 de l'ADR 0002) | +17 ms mesurés (séance C) ; une séance en avance sur la référence ; une non mesurée | **condition non déclenchée** (une seule séance de latence exploitable) |
| Cadence et lumière (condition 1) | 31 images/s à chaque séance, traitement < 1 ms ; **la lumière n'a pas été consignée ni variée** | **non testée** : cette condition reste ouverte |
| Placement (condition 3) | la phase 04 s'est jouée avec la webcam intégrée, sans problème de placement pour les mains | dépend du choix des pieds (phase 05) |

Ce que les chiffres **ne disent pas** : si une caméra à 60 images/s ferait disparaître les coups manqués par « plan non atteint ». À 30 images/s un geste rapide ne laisse sans doute que quelques images dans sa descente, et l'image la plus basse peut tomber juste au-dessus du plan alors que la baguette l'a franchi ; ou bien le geste est réellement plus court. Le diagnostic ne sépare pas les deux (il lit les positions reçues, pas le geste).

## Décision

**Option 2 : ne rien acheter maintenant ; décider au début de la phase 05.**

- À 90 BPM, la webcam intégrée tient la détection, les faux coups et l'attribution dans deux séances sur trois, et la latence, mesurée sur une séance, est de +17 ms pour un maximum de 60 ms (les quatre critères sont tenus dans la séance C). Rien n'oblige à acheter pour la phase 04.
- Le besoin d'une seconde caméra dépend d'une décision qui n'est pas prise : la disposition des pieds. Si l'option (a) est confirmée (webcam intégrée au sol pour les pieds), la caméra des mains doit être une autre caméra : l'achat d'occasion (~40 €) devient prévu. Si l'option (c) l'emporte (pédales USB pour les pieds), la webcam intégrée reste celle des mains et il n'y a rien à acheter.
- Un essai gratuit avant tout achat : demander 60 images/s à la webcam intégrée (`[camera] fps = 60`, `mjpeg = true` dans `settings.toml`) et lire sur l'écran « Caméra obtenue » ce qu'elle accorde. Si elle le donne, refaire une séance de mesure ; si les « plan jamais atteint » disparaissent, la cadence était en cause.

**Ce qui déclencherait un achat avant la phase 05** : la lumière de ta pièce fait chuter la cadence ou le taux de détection (à mesurer, avec la lumière notée) ; ou les séances à 90 BPM échouent de façon répétée avec des causes qui désignent la cadence.

## Conséquences

- Budget inchangé : 0 € de logiciel, aucun achat engagé.
- La phase 05 commence par la séance de confirmation des pieds prévue par l'ADR 0002 ; sa décision (a) ou (c) fixe aussi la décision d'achat pour les mains.
- Les prochaines mesures noteront la **lumière** (jour ou lampe, orientation) et feront trois séances par tempo, car la séance B d'aujourd'hui (86 %) et la séance C (99 %) ont été jouées dans les mêmes conditions : un seul essai ne suffit pas.
- Le critère de détection n'est pas encore tenu de façon régulière : en phase suivante, un réglage ou une calibration plus clémente de la caisse claire de la main gauche (course) reste à explorer si l'écart persiste.
- **Réserves :** une personne, une pièce, une caméra, des séances à la suite ; les résultats à 70 BPM ne valent pas pour le critère (défini à 90 BPM) ; la latence n'est mesurée que sur une séance exploitable.
