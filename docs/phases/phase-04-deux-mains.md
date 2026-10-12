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
- **Couleurs (choisies le 2026-10-10, changées le 2026-10-12)** : **main gauche bleu fluo** (surligneur bleu, plage `BLUE`), **main droite verte**. Historique : l'orange (plage `ORANGE`, conservée) était trop proche de la peau, le rose fluo essayé ensuite n'a pas convenu à l'essai. Le **jaune fluo** est réservé au pied (phase 05) : le bleu avait d'abord été prévu pour le pied, mais il est maintenant pris par la main, et le jaune se distingue du jean et du sol.
- **Caméra** : la phase démarre avec la webcam intégrée. Une webcam 60 images/s d'occasion (C922 ou StreamCam, ~40 €) est prévue pour les mains, en hauteur face à toi (disposition du cadrage §7, note du 2026-10-10). La décision d'achat se prend sur des chiffres après la PR 4, dans l'ADR 0004.
- **Réserves de l'ADR 0002 à lever ici** : deux mains (confusion de couleur), plusieurs éléments (attribution), tenue à 90 BPM en croches, retard détection + son au ras de 60 ms.
- **Pieds** : test anticipé en phase 03, suivi correct mais retard de +109 ms sur une séance ; décision pour les pieds repoussée au début de la phase 05. La phase 04 n'en dépend pas.

## Ce que je peux faire seul, ce qu'il te faudra faire

Comme en phase 03, je code et teste toute la logique (suivi, zones, anti-double-coup, calibration, attribution, statistiques) sur des images et des trajectoires synthétiques, sans caméra. Je n'ouvre pas ta webcam (R9). C'est toi qui : essaies l'orange devant ta caméra (PR 1), calibres tes zones (PR 3), joues (PR 4) et fais les séances de mesure de 100 coups (PR 5) ; tu fusionnes, et tu décides de l'achat de la caméra.

## Prérequis

- [x] Couleurs : main gauche orange, main droite verte (embout vert : ta brosse à dents de la phase 03)
- [ ] Un embout **bleu fluo** (surligneur bleu, pas un bleu terne ou sombre), pour la main gauche (c'était un orange vif avant le 2026-10-12)
- [ ] Phase découpée en PR (fait par ce document)

## Livrables

**PR 1 — Deux mains : suivi orange et vert** (`feat/vision-two-hands`)
- [x] `input/vision/color_tracker.py` : plage `ORANGE` (vive, non calibrée) ; `find_marker` inchangé
- [x] `input/vision/process.py` : un marqueur et un détecteur de coup **par main** (anti-rebond propre à chaque main), `VisionSample` porte les points et les coups par main ; image **retournée en miroir** pour que ta main gauche apparaisse à gauche, comme sur le kit
- [x] `tools/vision_debug.py --target hands` : deux points suivis (orange, vert), vitesse et compteur de coups par main
- [x] Tests : images synthétiques à deux marqueurs, coups indépendants par main, miroir, et teintes de peau synthétiques **non** suivies par l'orange
- [x] Nécessite ta webcam : essayé par toi le 2026-10-10, « tout est parfait » (orange et vert suivis, rien d'accroché à ta main, ton visage ni ton fond)

**PR 2 — Zones, attribution à l'élément et anti-double-coup** (`feat/vision-zones`) — logique pure
- [x] `input/vision/zones.py` : `Zone` (élément, rectangle dans l'image, plan de frappe) et leur validation (pas de chevauchement en largeur, un élément une seule fois)
- [x] Détecteur de coup par zone : un coup = franchissement vers le bas du plan d'une zone, **point de franchissement dans le rectangle de la zone**, un seul coup par geste
- [x] **Anti-double-coup** : ré-armement seulement après une remontée du marqueur au-dessus du plan (hystérésis), en plus de l'anti-rebond temporel ; une frappe en diagonale ne déclenche qu'un élément
- [x] `config/zones.py` : lecture et écriture de `zones.toml` dans `%APPDATA%\Batterie` (fichier séparé de `settings.toml`, voir ADR 0003), erreurs claires
- [x] Tests : mains qui alternent sur 4 zones, rebond et tremblement ignorés, diagonale, validation, aller-retour de lecture/écriture

**PR 3 — Écran de calibration guidée** (`feat/vision-calibration`) — M11
- [x] `input/vision/calibration.py` (logique pure) : repère les coups dans la trajectoire de l'embout, calcule la zone de chaque élément (rectangle avec marge, plan de frappe réglé sur la course réelle du geste), sépare deux zones voisines qui se chevauchent, et déroule la calibration élément par élément
- [x] Écran dans l'application (entrée « Calibrer la caméra » à l'accueil) : aperçu miroir avec les zones au fur et à mesure, « Frappe : Caisse claire — coup 2 / 3 », liste des éléments faits, R pour recommencer un élément, validation par Entrée ; Échap abandonne sans rien écraser ; enregistre `zones.toml`
- [x] Les zones restent affichées sur l'aperçu pendant le jeu (voir si tu as bougé depuis la calibration) — fonction de dessin livrée ici (`ui/camera_view.py`), utilisée dans le jeu à la PR 4
- [x] ADR 0003 : zones en rectangles, calibration guidée par des frappes (pas de dessin à la souris), `zones.toml` séparé
- [ ] Nécessite ta webcam : calibrer tes 4 zones et vérifier qu'elles tiennent

**PR 4 — Jouer à la caméra dans l'application** (`feat/vision-play`) — M9
- [x] `input/vision/source.py` : démarre le processus vision, lit sa file à chaque tour de boucle (≥ 500 Hz), transmet les `HitEvent` ; le son est joué **dès la lecture de l'événement**, jamais depuis le rendu (CLAUDE.md §9)
- [x] Entrée « Jeu caméra » à l'accueil : le kit s'illumine et sonne au rythme de tes coups ; état de la caméra visible (images/s) ; message clair si la caméra est absente, occupée, ou si aucune zone n'est calibrée
- [x] `config/settings.py` : section facultative `[camera]` (numéro de caméra, résolution, images/s demandées, MJPEG) ; l'application demande et affiche ce qu'elle obtient réellement. Les `settings.toml` existants restent valables tels quels
- [x] Tests : file simulée → sons joués, caméra perdue, pas de zones
- [ ] Nécessite ta webcam : jouer librement, dire si le retard se sent
- [ ] **Point de décision caméra** : ton ressenti, plus les images/s réelles, nourrissent la décision d'achat (ADR 0004)

**PR 5 — Protocole et outil de mesure US7** (`feat/vision-us7`)
- [x] `input/vision/measure.py` : séance où chaque clic a un élément attendu ; calcule coups détectés, faux coups et **attribution** (bon élément ou non), en plus des latences existantes ; tests sur des séries synthétiques
- [x] `tools/vision_measure.py --pattern` : 100 croches à 90 BPM, motif de 8 croches répété sur les 4 éléments, mains en alternance ; décompte et métronome audibles, résultat à la fin. Sans son sur tes coups (comme en phase 03, sinon tu cales ton geste sur le son et le retard disparaît de la mesure) ; la latence geste → son s'obtient en ajoutant les ≈ 5 ms du moteur audio (ADR 0001)
- [x] Protocole consigné dans cette page (section « Protocole de mesure US7 » ci-dessous)
- [ ] Nécessite ta webcam : séances de 100 coups, chiffres relevés

**PR 6 — Nuance : la vitesse du geste règle le volume** (`feat/vision-velocity`) — S7, *Should*
- [x] `input/vision/velocity.py` : vitesse du geste → vélocité 0 à 1, courbe réglable (`[velocity]` de `settings.toml`), testée ; utilisée par le moteur audio (qui accepte déjà une vélocité). L'écran « Jeu caméra » affiche la vitesse et le volume du dernier coup pour régler la courbe
- [x] Livrée (les PR 1 à 5 tenaient le budget de temps ; elle ne bloque pas la clôture)
- [ ] Nécessite ta webcam : jouer doucement puis fort, régler `soft_speed` / `hard_speed` d'après l'écran, dire si la nuance se sent et si elle te plaît (sinon `enabled = false`)

**Clôture** (PR de documentation, comme en phases 01 à 03) : ADR 0004 (décision d'achat de la caméra des mains, avec tes chiffres), cases cochées, rétrospective, CHANGELOG `[0.4.0]`, tag `v0.4.0` après fusion.

## Risques de la phase

- **Orange et peau.** Un orange peu saturé ressemble à la peau (main, visage). Parades : orange vif ou fluo, test de non-accrochage sur des teintes de peau synthétiques (PR 1) puis sur ta main (toi). Si l'orange ne tient pas, autre couleur très saturée et absente du décor (le magenta est déjà défini dans `color_tracker.py`).
- **Éléments empilés.** Dans l'image, une frappe vers le bas sur un élément situé sous un autre (caisse claire sous le tom aigu, sur l'écran du kit) traverse d'abord le plan de l'élément du dessus : faux coup et mauvaise attribution. Parade pour cette phase : 4 éléments côte à côte, zones qui ne se chevauchent pas en largeur (validé en PR 2). Pour le kit complet, il faudra une autre règle (par exemple attribuer le coup au point bas du geste) : à traiter plus tard, pas ici.
- **Les zones dépendent de ta position.** Elles sont calibrées dans l'image de la caméra : si tu bouges ou que la caméra bouge, elles ne correspondent plus. D'où l'affichage des zones sur l'aperçu pendant le jeu, et une calibration courte (3 frappes par élément).
- **Retard au ras du critère.** Détection ≤ 55 ms + ≈ 5 ms de son : pile sur 60 ms avec la webcam à 30 images/s. Parade : la caméra 60 images/s ; l'ADR 0004 tranche sur les chiffres de la PR 4 et de la PR 5.
- **Caméra 60 images/s non testable ici.** Le code demande résolution et cadence, affiche ce qu'il obtient, et marche aussi avec ta webcam intégrée à 30 images/s ; le comportement réel de la nouvelle caméra (MJPEG, cadence, exposition) ne se vérifiera qu'avec toi, une fois achetée.
- **Bleu et jean.** Un jean ou un vêtement bleu a une teinte voisine du bleu fluo, mais une saturation moyenne et une luminosité basse : la plage `BLUE` exige les deux (saturation ≥ 150, luminosité ≥ 130), donc un bleu terne n'est pas suivi (testé sur des teintes de jean synthétiques). Si ton vêtement ou ton fond s'accroche quand même, resserrer la plage.
- **Éclairage.** L'orange change de teinte selon la lumière (lampe chaude contre lumière du jour) : la plage est à régler dans ta pièce, avec l'outil de débogage.

## Hors périmètre (phases suivantes)

Charleston ouverte/fermée selon une pédale, grosse caisse et pédale de charleston, pieds (phase 05) ; jouer une partition à la caméra et compenser la latence dans le jugement (phase 06) ; zones en polygones, calibration à la souris, plusieurs caméras ; kit complet de dix éléments.

## Critères de fin (Definition of Done)

- [ ] Tests au vert (CI Windows)
- [ ] Documentation à jour (README, CHANGELOG, journal)
- [ ] US7 sur charleston fermée, caisse claire, tom médium et ride, deux mains (mesuré, toi devant la caméra, 100 croches à 90 BPM) : ≥ 95 % détectés, ≤ 2 % de faux coups, ≥ 95 % attribués au bon élément, latence geste → son ≤ 60 ms
- [ ] Zones calibrables depuis l'application (M11)
- [ ] Décision d'achat (ou non) d'une caméra consignée dans l'ADR 0004

## Protocole de mesure US7

Mesure le critère US7 : **100 croches à 90 BPM** sur la charleston fermée, la caisse claire, le tom médium et le ride, **deux mains**. Un outil fait tout le comptage ; tu n'as qu'à jouer et à me rapporter le texte affiché.

**Avant de commencer**
- Zones calibrées avec tes vraies baguettes, à ta place de jeu (« Calibrer la caméra » dans l'application) ; si tu as bougé depuis, recalibre. Sans zones, l'outil refuse de démarrer et le dit.
- Embouts réglés : le point bleu (main gauche) et le point vert (main droite) suivent bien tes embouts (`uv run python tools/vision_debug.py --target hands`).
- Lumière **constante** pendant toute la mesure (même éclairage pour la référence et les 3 séances). Casque ou enceintes **filaires** (jamais de Bluetooth).
- Réglages caméra : ceux de ta section `[camera]` de `settings.toml` (par défaut 640×480 à 30 images/s) ; l'outil écrit à la fin ce que la caméra a réellement accordé. Note ce qu'il affiche.
- Aucun son n'est joué sur tes coups, exprès (comme en phase 03) : tu te calerais dessus et le retard disparaîtrait de la mesure.

**Déroulé** : `uv run python tools/vision_measure.py --pattern`
(`--bpm 70` pour une séance plus lente : utile pour s'entraîner ou si 90 est trop rapide. Le critère US7 est défini à **90 BPM** : un résultat à 70 ne le valide pas, l'outil l'écrit dans le rapport. Fais la référence clavier **au même tempo** que les séances caméra, dans le même lancement.)
1. **Référence clavier** (touche K) : 8 clics aigus de décompte (une mesure de croches), puis un appui sur la **barre d'espace** à chacun des 100 clics graves. Elle donne ton écart naturel par rapport au clic.
2. **Trois séances caméra** (touche V, une par essai, entrée pour démarrer) : même décompte, puis un coup de baguette sur chaque clic grave, **sur l'élément et avec la main indiqués** par la case en surbrillance. Le premier clic de chaque motif est plus aigu pour te repérer.
3. À la fin de chaque séance, le résultat s'affiche à l'écran et dans le terminal ; **copie le texte du terminal** (les trois séances et la référence) et envoie-le-moi. Si une séance est ratée (tu t'es perdu, le marqueur a quitté l'image), refais-la plutôt que de la garder.

**Le motif** (8 croches, répété, 100 clics au total ; la main gauche joue les positions 1, 3, 5, 7, la droite les positions 2, 4, 6, 8) :

| Position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Main | G | D | G | D | G | D | G | D |
| Élément | Charleston | Caisse claire | Caisse claire | Tom médium | Charleston | Ride | Caisse claire | Tom médium |

**Lecture des quatre critères** (affichés par l'outil, avec « atteint » / « NON ATTEINT ») :

| Critère | Exigé | Comment l'outil le calcule |
| --- | --- | --- |
| Coups détectés | ≥ 95 % | clics touchés par au moins un coup, dans une fenêtre d'une demi-croche (≈ 167 ms) de part et d'autre du clic |
| Faux coups | ≤ 2 % | détections en trop (un clic ne garde que son coup le plus proche), en part des 100 clics |
| Attribués au bon élément | ≥ 95 % | parmi les coups détectés, ceux dont l'élément est celui du motif ; les confusions sont listées (« attendu Caisse claire, obtenu Tom médium : 3 ») |
| Latence geste → son | ≤ 60 ms | (écart médian coup − clic de la séance caméra) − (celui de la référence clavier) + 5 ms de moteur audio (ADR 0001) |

**Ce que la mesure ne dit pas** (à garder en tête en lisant les chiffres)
- Un coup parasite tombé dans la fenêtre d'un clic **raté** compte comme la détection de ce clic : il peut masquer un raté (visible alors dans les confusions s'il tombe sur un autre élément). Les coups pendant le décompte ou après la fin sont ignorés.
- La latence suppose que ton geste de baguette et ton appui sur la barre d'espace anticipent le clic de la même façon ; ce n'est pas exact (la baguette est plus lente à arrêter), d'où un chiffre indicatif, à lire avec les trois séances (écart-type et variation d'une séance à l'autre).
- Le retard interne de la caméra (exposition, transfert) est inclus dans la latence puisque le clavier n'en a pas ; il n'est pas séparé du reste.
- Une seule personne, une pièce, une lumière : c'est un test d'acceptation, pas une statistique.

**Sans caméra** : `uv run python tools/vision_measure.py --pattern --simulate` joue la séance avec deux mains fictives et des zones fictives, pour voir le déroulé et le format du résultat ; elle ne mesure rien de ta caméra.

## Décisions prises (liens vers les ADR)

- [ADR 0002 — Vision : go/no-go et choix de caméra](../adr/0002-vision-go-no-go-et-camera.md) (héritée de la phase 03)
- [ADR 0003 — Zones de frappe et calibration par frappes guidées](../adr/0003-zones-et-calibration.md) — proposé, à confirmer par ton essai de la PR 3
- ADR 0004 (caméra des mains : achat ou non) — à écrire à la clôture

## Écarts par rapport au plan

- **PR 6 — la vitesse du coup est le pic de descente sur les 0,12 s qui précèdent, pas la vitesse entre deux images.** À 30 images/s, la vitesse entre deux images bouge de façon visible d'un coup à l'autre pour le même geste (une image de plus ou de moins dans la descente) ; le pic sur 3 à 4 images est plus stable et ne sous-estime pas un coup qui ralentit en touchant le plan. Testé sur des trajectoires synthétiques (dont un coup rapide qui ralentit au franchissement).
- **PR 6 — les vitesses par défaut sont des points de départ, estimés, pas mesurés.** `soft_speed` 200 px/s (le coup le plus doux détectable, le seuil de détection), `hard_speed` 900 px/s, volume minimal 0,3 : une vitesse en pixels dépend de ta distance à la caméra et de ton geste. D'où l'affichage de la vitesse et du volume du dernier coup dans le jeu caméra, pour régler d'après tes vrais coups. La nuance est **activée par défaut** (`enabled = false` pour revenir à tous les coups à fond).
- **PR 6 — le volume suit directement la vélocité (amplitude linéaire).** Le moteur audio la multiplie telle quelle ; la courbe (`gamma`) sert à compenser si les coups moyens paraissent trop doux ou trop forts. L'illumination du kit ne dépend pas de la vitesse.
- **PR 6 — nuance seulement dans le jeu caméra.** La séance de mesure US7 ne joue aucun son sur les coups (et la vitesse n'entre pas dans ses critères) : elle n'utilise pas la courbe.
- **PR 5 — « 90 BPM en croches » : un clic toutes les 1/3 s.** `SessionPlan` gagne `clicks_per_beat` (2 pour des croches) pour que « BPM » garde son sens de temps ; le décompte est d'une mesure de croches (8 clics) au lieu de 4 clics. Non prévu au plan, nécessaire pour que le motif de 8 croches tienne dans une mesure.
- **PR 5 — le premier clic de chaque motif est plus aigu.** Non prévu au plan : sans repère, il est facile de perdre le début du motif de 8 croches sans regarder l'écran.
- **PR 5 — l'attribution se compte sur les coups détectés.** Un clic raté fait baisser « coups détectés », pas « attribués au bon élément » : chaque critère mesure un défaut différent, sans compter deux fois le même raté.
- **PR 5 — l'API de `tools/vision_measure.py` change :** `parse_arguments` renvoie un objet `Options` (cible, simulation, séance US7) au lieu d'un couple ; les tests existants sont adaptés.
- **PR 3 — le flux caméra de l'application arrive ici, pas en PR 4.** L'écran de calibration a besoin de lancer le processus vision et de lire ses images : `input/vision/source.py` (`VisionFeed`) est créé dans cette PR, la PR 4 le complètera pour le jeu. De même `input/vision/hands.py` : une seule définition des deux mains (orange, verte, miroir) pour l'application et pour `tools/vision_debug.py`, avec un test qui vérifie qu'ils ne divergent pas.
- **PR 3 — l'élément à frapper est annoncé dans la colonne de droite, pas en surbrillance sur le kit.** « Frappe : Caisse claire », avec la liste des quatre éléments cochés au fur et à mesure et les zones déjà calibrées tracées sur l'aperçu ; le dessin du kit n'est pas affiché pendant la calibration.
- **PR 3 — l'affichage des zones pendant le jeu passe en PR 4.** Le jeu à la caméra n'existe pas encore ; la fonction de dessin des zones est prête et déjà utilisée par l'écran de calibration.
- **PR 3 — garde-fous plus stricts que prévu, trouvés par un essai de bout en bout.** Avec une caméra fictive qui donne un coup de trop sur chaque élément, ce coup tombait juste après la fin de l'attente et comptait pour l'élément suivant, avec une dispersion maximale de 90 px qui laissait passer une zone élargie à tort. Attente portée à 1,5 s et dispersion maximale à 50 px (explication dans l'ADR 0003).
- **PR 3 — sens de `Zone.y_top`.** C'est la hauteur d'où part le coup *le moins relevé*, pas le point le plus haut atteint : c'est ce qui garantit que chacun de tes coups se ré-arme (précision apportée à la docstring de PR 2).

- **PR 2 — les zones sont branchées dans le processus vision dès cette PR.** Le plan ne prévoyait que la logique pure, mais le coup est détecté dans le processus vision (c'est lui qui voit les images, cadrage §4.1) : `MarkerSpec` accepte donc des `zones`, et un `ZoneStrikeDetector` par main attribue chaque coup à l'élément frappé. Ça permet aussi de tester l'attribution à travers le vrai pipeline, sur des images synthétiques à deux mains. Rien n'est encore utilisé par les outils ni par l'application : les zones n'existent pas avant la calibration (PR 3).
- **PR 2 — ré-armement : valeurs de départ.** Après un coup, la main doit remonter au-dessus du plan d'un quart de la hauteur de la zone (au moins 4 px) avant de pouvoir frapper de nouveau, en plus de l'anti-rebond de 0,15 s. Conséquence à garder en tête : un geste dont l'amplitude est inférieure à cette marge ne se ré-arme pas ; la calibration (PR 3) règle le haut de chaque zone sur la course réelle du geste. Quart et minimum sont à ajuster en jouant (PR 4).
- **PR 2 — `y_bottom` ne sert pas à la détection.** Le bas de la zone est enregistré pour l'affichage et la calibration (PR 3) ; seuls `x_min`, `x_max`, le plan et la hauteur au-dessus du plan interviennent dans le coup.
- **PR 1 — `VisionSample` change de forme.** Il porte un échantillon par embout (`markers`) au lieu d'un seul point : c'est le minimum pour suivre deux mains, et les raccourcis `point`, `velocity_px_per_s` et `hit_event` (premier embout) gardent la baguette et le pied inchangés. Dans les outils, `TargetPreset` regroupe maintenant un ou plusieurs `MarkerPreset` ; les deux mains portent le même élément (`snare`) jusqu'aux zones de la PR 2.
- **PR 1 — l'orange est réglé par la saturation.** Teinte de l'orange et de la peau confondues, c'est une saturation minimale élevée (160) qui les sépare ; un orange pâle n'est donc volontairement pas suivi. Valeurs de départ, non calibrées, vérifiées seulement sur des teintes de peau synthétiques.

## Rétrospective : ce qui a marché, ce qui a coincé

_À remplir à la clôture._
