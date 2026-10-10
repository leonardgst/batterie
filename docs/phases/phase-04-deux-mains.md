# Phase 04 — Vision : deux mains, kit complet

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| En cours (cadrée le 2026-10-10) | 6 à 10 h de ton temps | — | v0.4.0 |

## Objectif

Jouer avec deux baguettes sur quatre éléments (charleston fermée, caisse claire, tom médium, ride) devant la webcam, au lieu du clavier, et entendre le bon son à chaque coup. C'est la deuxième sous-version de la V3 (V3.1).
Référence : [cadrage](../00-cadrage.md) §5 (phase 04), exigences M9 (coup de baguette filmé → son du bon élément) et M11 (calibration des zones), user story US7 : sur 100 coups en croches à 90 BPM, ≥ 95 % détectés, ≤ 2 % de faux coups, ≥ 95 % attribués au bon élément ; latence geste → son ≤ 60 ms (cible 40 ms avec une caméra 60 images/s).

**Quatre éléments, choisis pour être côte à côte dans l'image** (de gauche à droite comme sur l'écran du kit) : `hihat_closed`, `snare`, `tom_mid`, `ride`. Le cadrage disait « un tom et une cymbale » ; ce choix est modifiable, tant que les zones restent côte à côte (voir « Risques »).

## Point de départ (phase 03, ADR 0002)

- Une baguette suivie par la webcam intégrée : 48 à 50 coups sur 50, 0 faux coup, 31,2 images/s, retard par rapport au clavier ≤ 55 ms. Les outils `tools/vision_debug.py` et `tools/vision_measure.py` (préréglages de cible) servent de base.
- **Couleurs (choisies le 2026-10-10)** : **main gauche orange, main droite verte**. Le bleu est réservé au pied (phase 05).
- **Caméra** : la phase démarre avec la webcam intégrée. Une webcam 60 images/s d'occasion (C922 ou StreamCam, ~40 €) est prévue pour les mains, en hauteur face à toi (disposition du cadrage §7, note du 2026-10-10). La décision d'achat se prend sur des chiffres après la PR 4, dans l'ADR 0004.
- **Réserves de l'ADR 0002 à lever ici** : deux mains (confusion de couleur), plusieurs éléments (attribution), tenue à 90 BPM en croches, retard détection + son au ras de 60 ms.
- **Pieds** : test anticipé en phase 03, suivi correct mais retard de +109 ms sur une séance ; décision pour les pieds repoussée au début de la phase 05. La phase 04 n'en dépend pas.

## Ce que je peux faire seul, ce qu'il te faudra faire

Comme en phase 03, je code et teste toute la logique (suivi, zones, anti-double-coup, calibration, attribution, statistiques) sur des images et des trajectoires synthétiques, sans caméra. Je n'ouvre pas ta webcam (R9). C'est toi qui : essaies l'orange devant ta caméra (PR 1), calibres tes zones (PR 3), joues (PR 4) et fais les séances de mesure de 100 coups (PR 5) ; tu fusionnes, et tu décides de l'achat de la caméra.

## Prérequis

- [x] Couleurs : main gauche orange, main droite verte (embout vert : ta brosse à dents de la phase 03)
- [ ] Un embout **orange vif** (ruban ou embout fluo, pas un orange pâle), pour la main gauche
- [ ] Phase découpée en PR (fait par ce document)

## Livrables

**PR 1 — Deux mains : suivi orange et vert** (`feat/vision-two-hands`)
- [x] `input/vision/color_tracker.py` : plage `ORANGE` (vive, non calibrée) ; `find_marker` inchangé
- [x] `input/vision/process.py` : un marqueur et un détecteur de coup **par main** (anti-rebond propre à chaque main), `VisionSample` porte les points et les coups par main ; image **retournée en miroir** pour que ta main gauche apparaisse à gauche, comme sur le kit
- [x] `tools/vision_debug.py --target hands` : deux points suivis (orange, vert), vitesse et compteur de coups par main
- [x] Tests : images synthétiques à deux marqueurs, coups indépendants par main, miroir, et teintes de peau synthétiques **non** suivies par l'orange
- [ ] Nécessite ta webcam : vérifier que l'orange suit ton embout sans s'accrocher à ta main, à ton visage ni à ton fond

**PR 2 — Zones, attribution à l'élément et anti-double-coup** (`feat/vision-zones`) — logique pure
- [ ] `input/vision/zones.py` : `Zone` (élément, rectangle dans l'image, plan de frappe) et leur validation (pas de chevauchement en largeur, un élément une seule fois)
- [ ] Détecteur de coup par zone : un coup = franchissement vers le bas du plan d'une zone, **point de franchissement dans le rectangle de la zone**, un seul coup par geste
- [ ] **Anti-double-coup** : ré-armement seulement après une remontée du marqueur au-dessus du plan (hystérésis), en plus de l'anti-rebond temporel ; une frappe en diagonale ne déclenche qu'un élément
- [ ] `config/zones.py` : lecture et écriture de `zones.toml` dans `%APPDATA%\Batterie` (fichier séparé de `settings.toml`, voir ADR 0003), erreurs claires
- [ ] Tests : mains qui alternent sur 4 zones, rebond et tremblement ignorés, diagonale, validation, aller-retour de lecture/écriture

**PR 3 — Écran de calibration guidée** (`feat/vision-calibration`) — M11
- [ ] `input/vision/calibration.py` (logique pure) : à partir de quelques coups enregistrés sur un élément, calcule sa zone (rectangle avec marge, plan de frappe réglé sur la course réelle du geste)
- [ ] Écran dans l'application (entrée « Calibrer la caméra » à l'accueil) : aperçu miroir, l'élément à frapper mis en évidence sur le kit, « frappe-le 3 fois », puis l'élément suivant ; Échap abandonne sans rien écraser ; enregistre `zones.toml`
- [ ] Les zones restent affichées sur l'aperçu pendant le jeu (voir si tu as bougé depuis la calibration)
- [ ] ADR 0003 : zones en rectangles, calibration guidée par des frappes (pas de dessin à la souris), `zones.toml` séparé
- [ ] Nécessite ta webcam : calibrer tes 4 zones et vérifier qu'elles tiennent

**PR 4 — Jouer à la caméra dans l'application** (`feat/vision-play`) — M9
- [ ] `input/vision/source.py` : démarre le processus vision, lit sa file à chaque tour de boucle (≥ 500 Hz), transmet les `HitEvent` ; le son est joué **dès la lecture de l'événement**, jamais depuis le rendu (CLAUDE.md §9)
- [ ] Entrée « Jeu caméra » à l'accueil : le kit s'illumine et sonne au rythme de tes coups ; état de la caméra visible (images/s) ; message clair si la caméra est absente, occupée, ou si aucune zone n'est calibrée
- [ ] `config/settings.py` : section facultative `[camera]` (numéro de caméra, résolution, images/s demandées, MJPEG) ; l'application demande et affiche ce qu'elle obtient réellement. Les `settings.toml` existants restent valables tels quels
- [ ] Tests : file simulée → sons joués, caméra perdue, pas de zones
- [ ] Nécessite ta webcam : jouer librement, dire si le retard se sent
- [ ] **Point de décision caméra** : ton ressenti, plus les images/s réelles, nourrissent la décision d'achat (ADR 0004)

**PR 5 — Protocole et outil de mesure US7** (`feat/vision-us7`)
- [ ] `input/vision/measure.py` : séance où chaque clic a un élément attendu ; calcule coups détectés, faux coups et **attribution** (bon élément ou non), en plus des latences existantes ; tests sur des séries synthétiques
- [ ] `tools/vision_measure.py --pattern` : 100 croches à 90 BPM, motif de 8 croches répété sur les 4 éléments, mains en alternance ; décompte et métronome audibles, résultat à la fin. Sans son sur tes coups (comme en phase 03, sinon tu cales ton geste sur le son et le retard disparaît de la mesure) ; la latence geste → son s'obtient en ajoutant les ≈ 5 ms du moteur audio (ADR 0001)
- [ ] Protocole consigné dans cette page
- [ ] Nécessite ta webcam : séances de 100 coups, chiffres relevés

**PR 6 — Nuance : la vitesse du geste règle le volume** (`feat/vision-velocity`) — S7, *Should*
- [ ] `input/vision/velocity.py` : vitesse du geste → vélocité 0 à 1, courbe réglable, testée ; utilisée par le moteur audio (qui accepte déjà une vélocité)
- [ ] Livrée seulement si les PR 1 à 5 tiennent le budget de temps ; sinon reportée à la phase 06, sans bloquer la clôture

**Clôture** (PR de documentation, comme en phases 01 à 03) : ADR 0004 (décision d'achat de la caméra des mains, avec tes chiffres), cases cochées, rétrospective, CHANGELOG `[0.4.0]`, tag `v0.4.0` après fusion.

## Risques de la phase

- **Orange et peau.** Un orange peu saturé ressemble à la peau (main, visage). Parades : orange vif ou fluo, test de non-accrochage sur des teintes de peau synthétiques (PR 1) puis sur ta main (toi). Si l'orange ne tient pas, autre couleur très saturée et absente du décor (le magenta est déjà défini dans `color_tracker.py`).
- **Éléments empilés.** Dans l'image, une frappe vers le bas sur un élément situé sous un autre (caisse claire sous le tom aigu, sur l'écran du kit) traverse d'abord le plan de l'élément du dessus : faux coup et mauvaise attribution. Parade pour cette phase : 4 éléments côte à côte, zones qui ne se chevauchent pas en largeur (validé en PR 2). Pour le kit complet, il faudra une autre règle (par exemple attribuer le coup au point bas du geste) : à traiter plus tard, pas ici.
- **Les zones dépendent de ta position.** Elles sont calibrées dans l'image de la caméra : si tu bouges ou que la caméra bouge, elles ne correspondent plus. D'où l'affichage des zones sur l'aperçu pendant le jeu, et une calibration courte (3 frappes par élément).
- **Retard au ras du critère.** Détection ≤ 55 ms + ≈ 5 ms de son : pile sur 60 ms avec la webcam à 30 images/s. Parade : la caméra 60 images/s ; l'ADR 0004 tranche sur les chiffres de la PR 4 et de la PR 5.
- **Caméra 60 images/s non testable ici.** Le code demande résolution et cadence, affiche ce qu'il obtient, et marche aussi avec ta webcam intégrée à 30 images/s ; le comportement réel de la nouvelle caméra (MJPEG, cadence, exposition) ne se vérifiera qu'avec toi, une fois achetée.
- **Éclairage.** L'orange change de teinte selon la lumière (lampe chaude contre lumière du jour) : la plage est à régler dans ta pièce, avec l'outil de débogage.

## Hors périmètre (phases suivantes)

Charleston ouverte/fermée selon une pédale, grosse caisse et pédale de charleston, pieds (phase 05) ; jouer une partition à la caméra et compenser la latence dans le jugement (phase 06) ; zones en polygones, calibration à la souris, plusieurs caméras ; kit complet de dix éléments.

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] US7 sur charleston fermée, caisse claire, tom médium et ride, deux mains (mesuré, toi devant la caméra, 100 croches à 90 BPM) : ≥ 95 % détectés, ≤ 2 % de faux coups, ≥ 95 % attribués au bon élément, latence geste → son ≤ 60 ms
- [ ] Zones calibrables depuis l'application (M11)
- [ ] Décision d'achat (ou non) d'une caméra consignée dans l'ADR 0004

## Décisions prises (liens vers les ADR)

- [ADR 0002 — Vision : go/no-go et choix de caméra](../adr/0002-vision-go-no-go-et-camera.md) (héritée de la phase 03)
- ADR 0003 (zones et calibration) — à écrire en PR 3
- ADR 0004 (caméra des mains : achat ou non) — à écrire à la clôture

## Écarts par rapport au plan

- **PR 1 — `VisionSample` change de forme.** Il porte un échantillon par embout (`markers`) au lieu d'un seul point : c'est le minimum pour suivre deux mains, et les raccourcis `point`, `velocity_px_per_s` et `hit_event` (premier embout) gardent la baguette et le pied inchangés. Dans les outils, `TargetPreset` regroupe maintenant un ou plusieurs `MarkerPreset` ; les deux mains portent le même élément (`snare`) jusqu'aux zones de la PR 2.
- **PR 1 — l'orange est réglé par la saturation.** Teinte de l'orange et de la peau confondues, c'est une saturation minimale élevée (160) qui les sépare ; un orange pâle n'est donc volontairement pas suivi. Valeurs de départ, non calibrées, vérifiées seulement sur des teintes de peau synthétiques.

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
