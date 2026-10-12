# Phase 05 — Vision : pieds (V3.2)

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| Cadrée le 2026-10-12 — attend la séance de confirmation du pied (PR 1) | 3 à 8 h de ton temps selon la branche (voir « Décision préalable ») | — | v0.5.0 |

## Objectif

Jouer la **grosse caisse** et la **pédale de charleston** au pied, en plus des mains : un marqueur jaune sur chaque chaussure suivi par la webcam intégrée posée au sol, **sinon** des pédales au clavier USB. Charleston ouverte / fermée selon le pied gauche (*Could*). C'est la troisième sous-version de la V3 (V3.2).
Référence : [cadrage](../00-cadrage.md) §5 (phase 05), exigence **M10** (coups de pied filmés : grosse caisse et pédale de charleston), user story **US8** : mêmes critères que US7 pour ces deux éléments, soit sur 100 coups en croches à 90 BPM : ≥ 95 % détectés, ≤ 2 % de faux coups, ≥ 95 % attribués au bon élément, latence geste → son ≤ 60 ms (cible 40 ms avec une caméra 60 images/s).

**Deux éléments, un par pied** : `kick` (pied droit) et `hihat_pedal` (pied gauche). Les sons et les touches existent déjà (`Espace` et `C` ; la pédale ferme et coupe la charleston ouverte, `core/elements.py`). Il reste à les déclencher par le pied.

## Point de départ

- **Phase 04 terminée** (`v0.4.0`) : deux mains, quatre éléments, calibration guidée, nuance, outil de mesure US7 avec diagnostic des coups manqués. Tout ce qui est « géométrie de zone, détecteur, calibration, mesure » est réutilisable tel quel pour les pieds ; la calibration (`CalibrationRun`) accepte déjà une liste d'éléments quelconque.
- **Test du pied de la phase 03** (webcam intégrée au sol, 60–70 cm, une seule séance, [ADR 0002](../adr/0002-vision-go-no-go-et-camera.md)) : marqueur vu 100 % du temps, 0 faux coup, 31 images/s ; mais **+109 ms de retard** par rapport au clavier (trop pour la grosse caisse), un ruban qui s'est décollé, un préréglage non calibré, et une référence clavier non précisée. Rien ne confirme ni n'infirme la webcam au sol. **C'est la question de départ de la phase.**
- **Ce que la phase 04 a appris et qui s'applique ici** : le plan de frappe doit être calé sur *ton vrai geste* (sinon coups manqués ou détection en avance de ~100 ms) ; un coup manqué sur deux peut venir d'un seul réglage et le diagnostic le dit (`vision_measure.py` détaille position par position et cause par cause) ; les rapports sont lus tels quels, pas de mémoire ; la lumière doit être notée.
- **Caméra des mains** : pas d'achat pour l'instant ; elle dépend du choix des pieds ([ADR 0004](../adr/0004-camera-des-mains.md)).
- **Couleur du pied : jaune fluo** (le bleu est pris par la main gauche, le vert par la main droite).
- Matériel : Intel Core i7-1255U, 16 Go, Iris Xe, webcam intégrée seulement (cadrage §6.1) ; budget logiciel 0 €.

## Décision préalable : webcam au sol ou pédales USB

La phase se joue en deux temps, séparés par **un point de décision qui n'est pas à moi** :

1. **PR 1 (jaune, calibration du pied, séance de confirmation)** : je construis l'outil ; **tu mesures** (30 à 45 minutes).
2. **Point de décision (ADR 0005)** : selon tes chiffres, **(a)** webcam intégrée au sol pour les pieds + une seconde caméra pour les mains (~40 € d'occasion), ou **(c)** pédales USB pour les pieds (0 €, si tu as un clavier de plus), la webcam intégrée restant celle des mains. Ce choix fixe aussi l'achat de la caméra des mains (ADR 0004).

Les deux branches sont décrites plus bas. La branche (c) est courte (1 à 2 h de ton temps) ; la branche (a) est le gros du travail (4 à 8 h).

**Grille de lecture de la séance de confirmation (fixée avant la mesure)** — meilleure séance pied après calibration, à 90 BPM sauf si tu t'entraînes à plus lent (le dire) :

| Résultat | Conclusion |
| --- | --- |
| ≥ 95 % détectés, ≤ 2 % de faux coups, latence ≤ 60 ms par rapport à une référence **au pied** sur un clavier USB, au moins 25 images/s | **(a) confirmée** : la webcam au sol suffit pour la grosse caisse |
| 85 à 94 % détectés, ou latence entre 60 et 100 ms, avec une **cause identifiée** par le diagnostic (plan, geste, lumière, marqueur) | corriger la cause et refaire des séances avant de conclure ; (a) reste l'hypothèse de travail |
| Moins de 85 % après correction, ou latence au-dessus de ~100 ms après correction, ou marqueur masqué (jambe, autre pied) ou cadence sous 25 images/s malgré une bonne lumière | **(c) pédales USB** ; (b) deux caméras seulement si le budget le permet et si le problème vient du point de vue |

À lire sur **trois séances** (pas une) et avec la **lumière notée** : la phase 04 a montré 86 % et 99 % dans les mêmes conditions. Les seuils intermédiaires sont mon choix de départ, plus indulgents que ceux de US7 car un seul pied et un seul élément ; tu peux les durcir.

## Ce que je peux faire seul, ce qu'il te faudra faire

Comme en phases 03 et 04, je code et teste toute la logique (plage jaune, ROI par pied, calibration, attribution, mesure) sur des images et des trajectoires synthétiques, et je vérifie l'outil de bout en bout avec un processus vision réel et une caméra fictive, **sans ouvrir ta webcam** (R9). C'est toi qui :

- colles le marqueur jaune sur la chaussure et poses l'ordinateur au sol (PR 1) ;
- calibres ton pied, fais la référence clavier au pied puis trois séances (PR 1) ;
- décides entre (a) et (c) (point de décision) ;
- en branche (a) : achètes la caméra des mains **après** la décision et la branches (PR 5), calibres les deux pieds, joues, fais les séances US8 ;
- en branche (c) : essaies les pédales, fais le test de touches simultanées et les séances au clavier.

## Prérequis

- [ ] Un marqueur **jaune fluo** (surligneur jaune classique ou ruban fluo, pas un jaune pâle ni doré) pour la chaussure droite ; un second pour la gauche si branche (a)
- [ ] De quoi le fixer **solidement** (ruban adhésif collé et **passé autour de la chaussure** : celui de la phase 03 s'est décollé)
- [ ] Un clavier USB (même vieux) posé au sol, pour la référence au pied et, selon la décision, comme pédales
- [ ] Une place au sol pour l'ordinateur, écran à demi refermé, à 50–80 cm des pieds ; la **lumière notée** à chaque séance (jour ou lampe, d'où elle vient)
- [ ] Phase découpée en PR (fait par ce document)

## Livrables

**PR 1 — Jaune, calibration du pied, séance de confirmation** (`feat/foot-confirmation`) — avant la décision
- [ ] `input/vision/color_tracker.py` : plage `YELLOW` (surligneur jaune : teinte vers 25–35, saturation et luminosité élevées pour ne pas suivre un sol clair, du bois, la peau ou un vert), testée sur des teintes de peau, de bois, de sol clair, de jean et sur le vert et l'orange ; non calibrée, à régler avec l'outil de débogage
- [ ] `input/vision/feet.py` (logique pure) : définition du pied à suivre (jaune, image en miroir comme pour les mains, élément `kick`) et son préréglage de départ ; même modèle de zone et de détecteur que les mains (`ZoneStrikeDetector`) pour que le plan de frappe se cale sur le geste réel
- [ ] Calibration guidée du pied : entrée **Calibrer le pied** à l'accueil (« lève et repose le pied 3 fois, talon au sol »), zone enregistrée dans `feet.toml` (fichier séparé, comme `zones.toml`, ADR 0003) ; réglage `[camera_feet]` (numéro, résolution, images/s) de `settings.toml`, facultatif
- [ ] `tools/vision_measure.py --feet` : séance de confirmation du pied (grosse caisse seule, 100 coups à 90 BPM par défaut, `--bpm` réglable), avec la même lecture que US7 : détectés, faux coups, **diagnostic des coups manqués**, latence par rapport à la référence clavier ; référence « au pied sur un clavier USB » (touche K) ; avertissement quand la détection précède la référence
- [ ] Protocole de la séance de confirmation consigné dans cette page
- [ ] Tests : plage jaune (peau, bois, sol, jean, autres couleurs), calibration d'un seul élément, séance de pied simulée de bout en bout
- [ ] Nécessite ta webcam : marqueur sur la chaussure, calibrer, référence au pied, 3 séances, coller les rapports avec la lumière

**Point de décision — ADR 0005 « Pieds : webcam au sol ou pédales USB »** (`docs/pieds-decision`) — PR de documentation, de ton choix
- [ ] Tes mesures séance par séance, lues selon la grille ci-dessus ; décision (a) ou (c), et décision d'achat de la caméra des mains qui en découle (mise à jour de l'ADR 0004)

### Branche (a) — pieds à la caméra (si la webcam au sol est confirmée)

**PR 2 — Deux pieds** (`feat/two-feet`) — logique pure
- [ ] Un marqueur par pied, **même jaune sur les deux chaussures**, séparés par leur position dans l'image (pied gauche = moitié gauche, pied droit = moitié droite, comme les zones des mains) : chaque pied suit le plus grand point jaune de **sa** moitié ; `kick` à droite, `hihat_pedal` à gauche ; validation des zones (pas de chevauchement) réutilisée
- [ ] Détecteur de coup par pied (anti-double-coup et anti-rebond propres à chaque pied) ; plan de frappe et vitesse minimale calés par la calibration ; le pied qui se lève sans se reposer ne donne pas de coup
- [ ] Tests : deux pieds qui alternent, un pied qui sort de sa moitié, rebond et tremblement, pied gauche qui entre dans la zone du droit
- [ ] Si deux marqueurs jaunes se confondent sur ta caméra, **repli : une couleur distincte pour le pied gauche** (décision à ce moment, avec ton essai)

**PR 3 — Calibration des deux pieds** (`feat/feet-calibration`)
- [ ] L'écran de calibration du pied calibre `hihat_pedal` (pied gauche) puis `kick` (pied droit), `feet.toml` à deux zones
- [ ] Nécessite ta webcam : calibrer tes deux pieds et vérifier qu'ils tiennent

**PR 4 — Les pieds dans l'application, avec les mains** (`feat/play-with-feet`)
- [ ] `input/vision/source.py` : **deux flux caméra** (mains et pieds), chacun dans son processus, lus à chaque tour de boucle ; le son est joué **dès la lecture de l'événement**, de l'un ou de l'autre flux (CLAUDE.md §9) ; réglages `[camera]` (mains) et `[camera_feet]` (pieds)
- [ ] « Jeu caméra » : le kit entier s'illumine et sonne ; état des deux caméras (images/s de chacune) ; messages clairs si une des deux est absente, occupée, ou si les zones des pieds ne sont pas calibrées (les mains marchent alors seules)
- [ ] Tests : deux files simulées, une caméra perdue, pas de zones des pieds
- [ ] Nécessite **la caméra des mains** (achetée après la décision) pour jouer les deux ensemble ; jusque-là, les pieds se jouent seuls avec la webcam intégrée
- [ ] Nécessite ta webcam : jouer pieds et mains, dire si le retard se sent

**PR 5 — Protocole et outil de mesure US8** (`feat/vision-us8`)
- [ ] `tools/vision_measure.py --feet-pattern` : 100 croches à 90 BPM, **grosse caisse sur les temps, pédale de charleston sur les contretemps**, pieds en alternance ; mêmes critères, même diagnostic que US7 (le module de mesure est généralisé : le « membre » d'un clic n'est plus seulement une main)
- [ ] Protocole consigné dans cette page
- [ ] Nécessite ta webcam : séances de 100 coups, chiffres relevés

**PR 6 — Charleston ouverte / fermée selon la pédale** (`feat/hihat-pedal-state`) — *Could*
- [ ] État de la pédale : pied gauche **baissé** = charleston fermée (coups de main de la zone charleston en `hihat_closed`), **levé** = ouverte (`hihat_open`) ; hystérésis pour ne pas basculer sur un tremblement ; le « chick » de la pédale reste le coup de `hihat_pedal`
- [ ] Livrée seulement si les PR 1 à 5 tiennent le budget de temps ; sinon reportée sans bloquer la clôture

### Branche (c) — pédales USB (si la webcam au sol n'est pas confirmée)

**PR 2c — Pédales au clavier USB** (`feat/foot-pedals`)
- [ ] Les touches de la grosse caisse et de la pédale de charleston (Espace et C par défaut, réglables dans `settings.toml`) peuvent se frapper au pied sur un clavier posé au sol : rien à coder pour le son ; **vérifier** les touches simultanées (`tools/keytest.py`, pieds et mains ensemble) et la sensation de pédale
- [ ] Charleston ouverte / fermée selon la pédale maintenue (touche **tenue** = fermée) : *Could*, même condition de budget que la PR 6
- [ ] `tools/vision_measure.py --pedals` : séance US8 au clavier (grosse caisse et pédale de charleston alternées, 100 croches à 90 BPM), pour consigner les critères US8 avec la même lecture
- [ ] Tests : séance au clavier avec attribution par touche
- [ ] Nécessite ton clavier USB : essayer les pédales et faire les séances

**Clôture** (PR de documentation, comme en phases 01 à 04) : rétrospective, cases cochées, CHANGELOG `[0.5.0]`, ADR 0005 accepté, tag `v0.5.0` après fusion.

## Risques de la phase

- **Retard du pied (+109 ms en phase 03).** Il peut venir d'un plan de frappe mal placé (le coup est déclaré tard ou trop tôt dans la course du pied : phase 04 a montré les deux), d'une référence clavier faite d'un doigt au lieu du pied (le pied n'anticipe pas le clic comme un doigt), ou de la caméra elle-même (une caméra tournée vers le sol, plus sombre, allonge son temps de pose). Parade : calibrer le plan sur ton geste, référence au pied sur un clavier au sol, lumière notée, diagnostic des coups manqués, essai gratuit de 60 images/s (`[camera_feet]`), et **(c) comme secours assumé**.
- **Jaune et décor.** Un sol clair, du bois, un jean ou une lampe peuvent ressembler au jaune ; un jaune doré ou pâle est trop proche. Parades : jaune fluo, tests de non-accrochage (peau, bois, sol, jean, vert, orange) en PR 1, puis ton essai ; si ça accroche, resserrer la saturation ou changer de couleur.
- **Contre-jour et ombre du corps.** Une caméra au sol voit des pieds à contre-jour d'une fenêtre ou dans l'ombre de ton corps. Parade : lumière devant toi, sol éclairé ; à noter à chaque séance.
- **Deux pieds, un seul jaune.** Le pied gauche qui entre dans la moitié droite de l'image, ou une jambe qui passe devant, peut brouiller l'attribution. Parades : séparation par moitié d'image, un seul point jaune par moitié, test des cas limites en PR 2 ; repli : couleur distincte pour le pied gauche.
- **Marqueur qui se décolle.** A coûté 9 coups « non joués » en phase 03, et l'outil ne distingue pas un coup raté d'un coup non joué. Parade : fixer le marqueur autour de la chaussure ; l'outil affichera le détail par position et la cause des coups manqués (« embout non vu » désignera un marqueur perdu).
- **Deux caméras en même temps (branche (a)).** Deux processus vision, deux flux USB, un processeur sans carte graphique : la cadence de l'une peut baisser quand l'autre travaille, et Windows peut renuméroter les caméras. Parades : un processus par caméra, mesure des images/s de chacune affichée, numéros réglables ; si ça ne tient pas, branche (c).
- **Un pied n'est pas une main.** Une pédale se joue talon au sol et pointe qui se lève et retombe : course courte (quelques centimètres), vitesse plus faible. Les seuils des mains (200 px/s, anti-rebond 0,15 s) ne sont pas ceux du pied ; calibration sur le geste, et seuils propres au pied (vitesse minimale et anti-rebond réglables).
- **Charleston d'état (Could).** « Pédale baissée / levée » est un *état*, pas un coup : le détecteur ne le fait pas aujourd'hui, et un faux basculement ouvre ou ferme la charleston au mauvais moment. Parade : hystérésis, fonction facultative et reportable.
- **Pédales USB : pas dans le vide.** (c) ne remplit pas l'esprit de la V3 (jouer « dans le vide ») pour les pieds, mais elle est robuste et déjà validée en latence ; ghosting possible (`tools/keytest.py`).

## Hors périmètre (phases suivantes)

Jouer une partition à la caméra et compenser la latence dans le jugement, réglages de sensibilité, assistant de placement des caméras, mode mixte clavier + caméra (phase 06) ; publication (phase 07) ; kit complet de dix éléments par la caméra ; caméras stéréo (C8) ; tom aigu, tom basse, crash par la caméra.

## Critères de fin (Definition of Done)

- [ ] **US8** : grosse caisse et pédale de charleston, 100 croches à 90 BPM, ≥ 95 % détectés, ≤ 2 % de faux coups, ≥ 95 % attribués au bon élément, latence geste → son ≤ 60 ms (mesuré, toi devant la caméra, ou aux pédales USB selon la décision)
- [ ] Les pieds se jouent dans l'application (branche (a) : caméra ; branche (c) : pédales), avec les mains
- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] Décision pieds et caméra des mains consignée (ADR 0005, ADR 0004 mis à jour)

## Décisions prises (liens vers les ADR)

- [ADR 0002 — Vision : go/no-go et choix de caméra](../adr/0002-vision-go-no-go-et-camera.md) (héritée : « Décision caméras pour la suite »)
- [ADR 0003 — Zones de frappe et calibration par frappes guidées](../adr/0003-zones-et-calibration.md) (le modèle de zone sert aussi aux pieds)
- [ADR 0004 — Caméra des mains](../adr/0004-camera-des-mains.md) — accepté ; sa décision d'achat dépend du choix des pieds
- ADR 0005 (pieds : webcam au sol ou pédales USB) — au point de décision, après la PR 1

## Écarts par rapport au plan

_À remplir au fil des PR._

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
