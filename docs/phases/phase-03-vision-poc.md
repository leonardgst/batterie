# Phase 03 — Vision : preuve de concept

| Statut | Prévue | Terminée le | Tag Git |
| --- | --- | --- | --- |
| Terminée | 4 à 6 h de ton temps | 2026-10-10 | v0.3.0 |

## Objectif

Une baguette, un élément (la caisse claire), suivie par la webcam existante : vérifier
que le suivi d'un embout coloré est assez rapide et fiable pour remplacer le clavier,
avant d'acheter quoi que ce soit. C'est la première sous-version de la V3 (V3.0).
Référence : [cadrage](../00-cadrage.md), user story US7 (critères réduits à un seul
élément pour cette preuve de concept).

## Prérequis — obtenus le 2026-10-09

Le cadrage (§6.1) laissait ces informations « à faire plus tard » ; nécessaires
avant d'écrire du code de vision (résolution, fréquence d'image visées, et si un
modèle plus lourd comme MediaPipe est envisageable). Reportées dans le cadrage §6.1.

- [x] Processeur : Intel Core i7-1255U (12e génération, 1,70 GHz)
- [x] Mémoire vive : 16 Go
- [x] Carte graphique : Intel Iris Xe Graphics, intégrée — pas de VRAM dédiée
- [x] Webcam(s) : webcam intégrée à l'ordinateur portable (modèle non précisé), aucune caméra externe

**Lecture pour la suite** : processeur mobile récent sans carte graphique dédiée — cohérent
avec le choix du cadrage (suivi de couleur léger en 640×480 sur le processeur, OpenCV,
pas de MediaPipe par défaut). Pas de caméra externe : la preuve de concept se fait avec la
webcam intégrée (cadrage §3, risque 3) ; sa résolution et sa fréquence d'image réelles
restent à vérifier en tout début de phase (beaucoup de webcams intégrées plafonnent à
30 i/s, parfois moins en basse lumière). Aucun achat avant la fin de cette phase
(cadrage §7, « Recommandation caméra ») : la décision go/no-go et, si besoin, les
caractéristiques précises à chercher, seront consignées dans un ADR à la clôture.

## Ce que je peux faire seul, ce qu'il te faudra faire

Contrairement aux phases 01 et 02, une partie de cette phase ne peut pas être testée
ni mesurée par Claude Code : je n'ai pas de caméra, pas d'embout coloré, et je n'ouvrirai
pas ta webcam moi-même (R9 du cadrage, vie privée — à faire seulement si tu me le
demandes explicitement et pour un test précis). Je code et teste tout ce qui est logique
pure (PR 1 entièrement), je construis les outils (PR 2 et PR 3), mais c'est toi qui les
exécutes devant la caméra, calibres la couleur de ton embout et obtiens les chiffres du
critère de fin (détection, latence, décision go/no-go).

## Livrables

**PR 1 — Suivi de couleur et détection de coup (logique pure, testable sans caméra)** (`feat/vision-tracking`)
- [x] `core/events.py` : `HitEvent` (élément, vélocité, horodatage, source), `Source` (clavier/MIDI/vision)
- [x] `input/vision/color_tracker.py` : trouve le centre d'un embout coloré dans une image (HSV), testé sur des images synthétiques
- [x] `input/vision/strike_detector.py` : détecte un coup au franchissement d'un plan de frappe à vitesse descendante (cadrage §3), testé sur des trajectoires synthétiques
- [x] Dépendances `opencv-python` et `numpy` ajoutées (`pyproject.toml`)

**PR 2 — Processus caméra séparé et écran de débogage** (`feat/vision-capture`)
- [x] `input/vision/process.py` : boucle caméra dans un `multiprocessing.Process`, transmet des `VisionSample` (position, vitesse, images/s, latence, éventuel `HitEvent`) par file inter-processus (cadrage §4.1) ; source d'image injectable pour tester la boucle sans caméra réelle
- [x] `tools/vision_debug.py` : fenêtre de débogage — aperçu caméra, plan de frappe, point suivi, vitesse, images/s, latence de traitement, compteur de coups
- [x] Nécessite ta webcam : essayé par toi le 2026-10-10 avec une brosse à dents verte comme embout ; les réglages par défaut (`GREEN`, plan à 150 px) ont suffi, suivi et compteur de coups corrects

**PR 3 — Protocole de mesure et décision go/no-go** (`feat/vision-measure`)
- [x] `tools/vision_measure.py` : séance guidée de 50 coups, compte les coups détectés et les statistiques de latence de traitement (logique de comptage dans `input/vision/measure.py`, testée sans caméra)
- [x] Protocole de mesure consigné dans cette page (comment mesurer, avec quoi) — voir « Protocole de mesure » ci-dessous
- [x] ADR 0002 : décision go/no-go et, si « go », caractéristiques de caméra à viser pour la suite — **go, sans achat pour l'instant**, rempli avec tes résultats

**PR 4 — Test du pied avec la webcam intégrée au sol** (`feat/vision-foot`) — informatif, ne bloque pas les critères de fin
- [x] `--target stick|foot` (défaut `stick`) dans `tools/vision_debug.py` et `tools/vision_measure.py` : préréglages regroupés en haut de `vision_debug.py` (élément, couleur, plan de frappe, vitesse minimale, anti-rebond) ; préréglage pied non calibré, seuils estimés et justifiés en commentaire
- [x] `input/vision/process.py` : vitesse minimale et anti-rebond transmis au détecteur de coup (`color_tracker.py` et `strike_detector.py` inchangés)
- [x] Séance de `vision_measure.py` jouable sans regarder l'écran : déjà le cas (décompte aigu et métronome grave audibles, résultat affiché et imprimé à la fin) — rien changé
- [x] Tests : trajectoires de pied synthétiques (faible amplitude, plus lentes), sélection du préréglage, transmission des seuils
- [x] Protocole pied consigné dans cette page
- [x] ADR 0002 : options de disposition des caméras et section « pied » à remplir
- [x] Nécessite ton ordinateur au sol et ta webcam : séance pied faite le 2026-10-10, chiffres et lecture dans l'ADR 0002 (suivi correct, mais retard de +109 ms par rapport au clavier et une seule séance, ruban décollé : décision pieds repoussée à une séance de confirmation avant la phase 05)

## Critères de fin (Definition of Done)

- [x] Tests au vert (CI Windows) pour la logique testable sans caméra
- [x] Documentation à jour (README, CHANGELOG, journal)
- [x] ≥ 90 % de coups détectés sur 50 coups à 80 BPM (mesuré, toi devant la caméra) — 48 à 50 sur 50 pour la moins bonne séance caméra, 0 faux coup
- [x] Latence geste → détection mesurée — ≤ 55 ms par rapport au clavier (tranche retenue, valeur exacte non relevée) ; 31,2 images/s réelles
- [x] Décision go/no-go et choix de caméra consignés dans un ADR

## Protocole de mesure

**Avec quoi (0 €)** : la webcam intégrée ; une baguette — ou une cuillère en bois, un
crayon — dont le bout porte une couleur vive absente du décor (ruban adhésif vert vif ou
magenta, cadrage §3) ; ton casque **filaire** (jamais de Bluetooth pour une mesure de
retard) ; une pièce bien éclairée, lumière diffuse, sans contre-jour, et rien d'autre de
la couleur de l'embout dans le champ (vêtements compris).

**Étapes** (compte 15 à 20 minutes) :

1. *Facultatif, sans caméra* — `uv run python tools/vision_measure.py --simulate` montre
   le déroulé avec un embout fictif. Utile pour découvrir l'écran avant la vraie mesure.
2. **Calibrer** — `uv run python tools/vision_debug.py`. Ajuste la couleur et
   `strike_plane_y` du préréglage `STICK`, en haut de ce fichier, jusqu'à ce que : le cercle suive l'embout sans
   décrocher ; chaque coup ajoute 1 au compteur, et un seul ; remonter la baguette ou
   bouger sans frapper n'ajoute rien. La séance de mesure reprend automatiquement ces
   deux réglages. Note les valeurs retenues.
3. **Lancer la mesure** — `uv run python tools/vision_measure.py`.
4. **Séance clavier (touche K), une fois** — 4 clics aigus de décompte, puis tape la
   barre d'espace d'un doigt sur chacun des 50 clics graves. C'est la référence.
5. **Séance caméra (touche V), trois fois** — même exercice avec la baguette, sur une
   caisse claire imaginaire : un coup par clic grave, le point bas du geste *sur* le
   clic, comme tu jouerais vraiment. Trois séances pour ne pas conclure sur un coup de
   chance (ou de malchance) ; la première sert aussi d'échauffement.
6. **Me transmettre les résultats** — ils s'affichent à l'écran et dans le terminal à la
   fin de chaque séance : copie-colle le texte du terminal dans la conversation (ou
   lance l'outil avec `! uv run python tools/vision_measure.py` depuis Claude Code, la
   sortie y arrive directement). Ajoute les réglages de l'étape 2 et deux mots sur tes
   conditions (lumière, embout). Je remplis l'ADR 0002 avec.

Aucun son n'est joué sur tes coups pendant une séance, exprès : avec un son, tu
avancerais ton geste sans t'en rendre compte pour que le son tombe sur le clic, et le
retard disparaîtrait de la mesure.

**Ce que l'outil mesure** :

| Ligne du résultat | Ce que c'est | Comment c'est obtenu |
| --- | --- | --- |
| Coups détectés | Critère de fin : ≥ 45 sur 50 (90 %) | Chaque clic accepte au plus un coup, dans un demi-temps de part et d'autre (± 375 ms à 80 BPM). Les gestes pendant le décompte ne comptent pas |
| Faux coups | Détections en trop | Deuxième détection sur un clic déjà touché (double déclenchement, rebond) |
| Écart coup − clic | Où tombent tes coups par rapport au clic (négatif = avant) | Médiane et écart-type sur les coups détectés |
| Embout visible | Part des images où l'embout est trouvé | Sous 90 %, le problème est la couleur ou la lumière : recalibrer avant de conclure |
| Images/s réelles | Cadence réelle de la webcam pendant la séance | Intervalle médian entre deux images traitées |
| Traitement par image | Temps de calcul (réduction, suivi, détection) | Médiane, 95ᵉ centile, maximum |
| Retard logiciel estimé | Plancher du retard : attente moyenne de l'image suivante (un demi-intervalle) + traitement | Ne contient pas le retard interne de la caméra (exposition, transfert USB), invisible depuis le programme |
| Retard par rapport au clavier | **La latence geste → détection** au sens du critère de fin | Écart médian de la séance caméra − écart médian de la séance clavier |

**Pourquoi comparer au clavier.** Mesurer directement l'instant du geste demanderait du
matériel (caméra rapide, micro). À la place, tu fais le même exercice deux fois : ton
anticipation naturelle du clic et le retard de la sortie audio sont identiques dans les
deux séances et s'annulent dans la différence ; il reste le retard propre à la caméra,
clavier pris comme zéro (son retard, de quelques millisecondes, a été validé en
phase 01). Avec 50 coups par séance, la précision est d'une dizaine de millisecondes.
Deux limites à garder en tête : frapper dans le vide n'a pas de contact, donc ton
« point bas » est moins net qu'une touche ; et le plan de frappe est franchi *avant* le
point bas (cadrage §3), ce qui peut donner un retard faible, voire négatif. C'est
justement ce nombre-là qui compte pour jouer, et c'est lui que le jugement devra
compenser plus tard (cadrage R7).

**Ce qui n'est pas mesuré** : le retard interne de la caméra pris isolément, et la
latence geste → *son* (US7), qui ajoute au retard ci-dessus les ≈ 5 ms du moteur audio
(ADR 0001).

## Protocole de mesure — pied (test anticipé de la phase 05)

Même outil, même séance de 50 coups à 80 BPM, avec `--target foot` : un coup de grosse
caisse (`kick`) par clic grave, la pointe du pied qui se lève et retombe, talon au sol,
comme sur une pédale. Informatif : ça ne conditionne pas la clôture de la phase 03, ça
sert à choisir la disposition des caméras (ADR 0002, « Test du pied »).

**Avec quoi (0 €)** : la webcam intégrée de l'ordinateur ; le ruban adhésif vert de la
baguette, collé sur la **pointe de la chaussure droite**, un carré de 3 à 4 cm sur le
dessus du bout (assez gros pour rester visible à 50–80 cm, mais pas plus : plus il est
grand, plus son centre bouge quand le pied tourne) ; une chaussure de couleur neutre,
sans rien de vert ; ton casque filaire.

**Placement** :

- l'ordinateur posé **au sol**, sur une surface plane et stable, à **50–80 cm devant
  tes pieds** ; la webcam (en haut de l'écran) doit se trouver à **20–30 cm du sol** :
  l'écran n'a pas besoin d'être grand ouvert, juste assez pour que la caméra voie ;
- l'écran un peu **refermé** (incliné vers l'avant) pour que la caméra vise tes pieds et
  non le plafond ; la pointe de ton pied droit doit rester dans l'image dans tout son
  mouvement, le pied gauche hors de l'image ou au moins loin du marqueur ;
- **éclairage** : lumière du plafond ou d'une lampe devant toi, jamais une fenêtre ou une
  lampe derrière tes pieds (contre-jour) ; le sol doit être éclairé, pas dans l'ombre de
  ton corps. Le sol sous le marqueur ne doit rien avoir de vert.

**Étapes** (compte 20 à 30 minutes) :

1. *Facultatif, sans caméra* — `uv run python tools/vision_measure.py --target foot --simulate`
   montre le déroulé avec le préréglage pied.
2. **Calibrer** — place l'ordinateur comme ci-dessus, puis
   `uv run python tools/vision_debug.py --target foot`. Le préréglage `FOOT` est un point
   de départ **non calibré** (voir ses commentaires dans `tools/vision_debug.py`) : régler
   avant de mesurer. Frappe quelques coups et ajuste, dans le fichier, le plan de frappe
   (la ligne rouge doit couper la trajectoire de la pointe vers le milieu de sa course),
   la vitesse minimale (trop haute : coups ratés ; trop basse : coups en trop quand le
   point tremble) et l'anti-rebond, jusqu'à : un seul coup compté par frappe, rien quand
   tu lèves le pied sans le reposer ni quand tu changes d'appui. Note les valeurs
   retenues.
3. **Référence clavier** — `uv run python tools/vision_measure.py --target foot`, touche
   K. Deux façons, de la meilleure à la plus simple : (i) un clavier USB posé au sol,
   barre d'espace frappée **du pied** (même geste, même anticipation que la mesure
   caméra, et c'est aussi un essai de l'option « pédales ») ; (ii) à défaut, la barre
   d'espace du portable d'un doigt — le retard par rapport au clavier sera alors moins
   fiable pour le pied, car le pied n'anticipe pas le clic comme un doigt. Dis-moi
   laquelle tu as utilisée.
4. **Séance pied (touche V), trois fois** — appuie sur V, vérifie que le marqueur est suivi
   (cercle jaune), puis Entrée : l'outil laisse environ 4 secondes (1 seconde + 4 clics
   aigus de décompte) pour reprendre position. Après, **tu peux ne plus regarder
   l'écran** : un coup sur chacun des 50 clics graves. À la fin, l'écran de résultat
   s'affiche et le même texte est imprimé dans le terminal.
5. **Relever** (pour l'ADR 0002, section « Test du pied ») : coups détectés sur 50,
   faux coups, part des images où le marqueur est vu, images/s réelles (elles peuvent
   baisser quand la caméra regarde le sol, plus sombre), temps de traitement, retard par
   rapport au clavier ; les valeurs du préréglage retenues à l'étape 2 ; la distance
   ordinateur-pieds, la hauteur de la caméra, la lumière ; et deux mots sur ce qui
   gêne (marqueur perdu quand le pied tourne, pied gauche qui entre dans l'image,
   reflets sur le sol…). Colle le texte du terminal dans la conversation, je remplis
   le tableau.

**Lecture** : grille fixée dans l'ADR 0002 avant la mesure. Ce test ne mesure qu'une
pointe de pied seule : il dit si le pied est suivable avec la webcam intégrée au sol,
pas si le kit complet (pieds et mains en même temps) tient.

## Décisions prises (liens vers les ADR)

- [ADR 0002 — Vision : go/no-go et choix de caméra](../adr/0002-vision-go-no-go-et-camera.md) — **accepté le 2026-10-10 : go, sans achat de caméra pour l'instant** ; l'achat d'une caméra 60 images/s devient conditionnel (lumière, retard geste → son, placement).

## Écarts par rapport au plan

- **PR 4 — test du pied anticipé sur la phase 05 : informatif, ne bloque pas les critères de fin.** Le plan de la phase ne couvrait qu'une baguette ; on profite de la phase 03 pour tester aussi le pied avec la webcam intégrée au sol, avant tout achat, parce que la disposition des caméras choisie le 2026-10-10 (note du cadrage §7) réserve cette webcam aux pieds. Ajouté après la clôture documentaire de la phase (qui reste « Terminée », ses critères étant atteints) et avant la pose du tag `v0.3.0`. Les résultats alimentent l'ADR 0002 ; ils ne changent ni la décision « go » ni les critères de fin.
- **PR 4 — préréglages de cible dans `tools/vision_debug.py` au lieu de constantes séparées.** `COLOR_RANGE`, `STRIKE_PLANE_Y` et `ELEMENT_ID` sont remplacés par deux préréglages (`STICK`, `FOOT`) regroupant en plus la vitesse minimale et l'anti-rebond, qui n'étaient pas réglables depuis l'outil (`input/vision/process.py` ne les transmettait pas). La calibration reste « éditer le fichier puis relancer », au même endroit.
- **PR 4 — préréglage pied non calibré.** Plan de frappe (100 px), vitesse minimale (80 px/s) et anti-rebond (0,20 s) sont des estimations d'ordre de grandeur (mouvement du pied plus court et plus lent qu'une baguette), pas des mesures ; justifiées en commentaire dans `tools/vision_debug.py`. À régler avec `vision_debug.py --target foot` avant la mesure.

- **PR 3 — séance clavier de référence ajoutée.** Le plan ne prévoyait que les statistiques de latence de *traitement*, qui ne suffisent pas au critère de fin « latence geste → détection mesurée » : le temps de calcul n'est qu'une petite partie du retard, le reste (attente de l'image, retard interne de la caméra) ne se voit pas depuis le programme. L'outil propose donc la même séance au clavier, et la différence entre les deux donne le retard de la caméra sans matériel de mesure (détail et limites dans « Protocole de mesure »).
- **PR 3 — mode `--simulate`.** Un embout fictif remplace la webcam. Il me permet de vérifier l'outil de bout en bout sans ouvrir ta caméra (R9), et te permet de voir le déroulé avant la vraie mesure. Ses chiffres ne disent rien de ta webcam.
- **PR 3 — pas de son sur les coups pendant la mesure.** Voulu : un retour sonore fausserait la mesure du retard (voir le protocole). Entendre la caisse claire en frappant dans le vide viendra en phase 04.
- **PR 2 — calibration par édition de constantes, pas d'écran de réglage en direct.** `tools/vision_debug.py` affiche la couleur suivie et le plan de frappe, mais pour changer la plage HSV ou la position du plan il faut éditer les constantes en haut du fichier et relancer (pas de flèches/souris en direct). Un canal de configuration en direct entre les deux processus était possible mais alourdissait cette PR pour un outil de diagnostic ponctuel ; éditer-relancer reste rapide (la caméra se réinitialise en une seconde environ). À reconsidérer si la calibration s'avère trop fastidieuse en pratique.
- **PR 2 — image réduite avant détection (`WORKING_WIDTH` = 320 px).** Le suivi et la détection de coup se font sur l'image déjà réduite, pas sur la résolution native de la caméra : ça garde `STRIKE_PLANE_Y` dans le même repère que ce qui s'affiche à l'écran (plus simple à calibrer), et ça allège le calcul sur un processeur sans carte graphique dédiée.
- **PR 1 — seuils par défaut non calibrés.** `MIN_BLOB_AREA` (30 px²), `min_speed_px_per_s` (200 px/s) et `refractory_s` (0,15 s) dans `strike_detector.py`, ainsi que les plages de couleur `GREEN`/`MAGENTA` dans `color_tracker.py`, sont des valeurs de départ raisonnables mais pas mesurées sur une vraie image de ta webcam, ta lumière, ton embout. Attends-toi à devoir les ajuster une fois l'écran de débogage (PR 2) en main — ce sera plus rapide à l'œil qu'en théorie.

## Rétrospective : ce qui a marché, ce qui a coincé

**Ce qui a marché**

- Le découpage en 3 PR (suivi et détection, processus caméra et débogage, mesure et décision) a permis de tout construire et tester sans caméra : la logique pure (`color_tracker`, `strike_detector`, `measure`) est couverte par des images et des trajectoires synthétiques, et la boucle caméra par une source d'images injectable. Quand tu as branché ta webcam, il n'y avait plus qu'à calibrer.
- Les réglages par défaut posés en PR 1 sans pouvoir les mesurer (plage `GREEN`, plan de frappe, seuils) se sont avérés suffisants pour ta baguette et ton embout. Prévenir qu'ils n'étaient pas calibrés, plutôt que de les présenter comme sûrs, était la bonne posture.
- Le mode `--simulate` a permis de vérifier l'outil de mesure de bout en bout, à travers le vrai processus séparé, sans ouvrir ta webcam (R9).
- Fixer la grille de lecture de l'ADR avant la mesure a rendu la décision immédiate : il ne restait qu'à comparer des chiffres à des seuils déjà écrits.
- La séance clavier de référence donne un retard geste → détection sans aucun matériel de mesure.

**Ce qui a coincé**

- Je ne pouvais ni voir ta caméra ni tester avec ta baguette : tout ce qui touche à la réalité (couleur, lumière, tenue du suivi) reposait sur ton essai. Ça a marché, mais la phase s'est jouée en un aller-retour de test plutôt qu'en itérations rapides.
- Les résultats ont été rapportés de mémoire, en tranches (≤ 55 ms, 48 à 50 coups) plutôt qu'en valeurs exactes, et la lumière n'a pas été consignée. Suffisant pour décider, mais l'ADR le dit explicitement et ses réserves en tiennent compte. Faire écrire à l'outil ses résultats dans un fichier rendrait la prochaine mesure exacte.
- Le critère de la phase (90 % sur 50 coups à 80 BPM, une baguette) est nettement plus léger que US7 (95 % sur 100 coups à 90 BPM, plusieurs éléments) : « go » ne veut pas dire que US7 est acquise, seulement que l'approche est assez prometteuse pour continuer.

**Addendum — test du pied (PR 4)**

- Le suivi du pied avec la webcam intégrée au sol a fonctionné du premier coup avec le préréglage non calibré (marqueur vu sur 100 % des images, 0 faux coup, 31 images/s), mais le retard mesuré est élevé (+109 ms par rapport au clavier, contre ≤ 55 ms pour la baguette) et la séance est unique. Ni confirmation ni infirmation de l'option « webcam intégrée au sol » : l'ADR 0002 repousse la décision pour les pieds à une séance de confirmation.
- Le ruban adhésif s'est décollé de la chaussure en cours de séance : 9 coups sur 50 n'ont pas été joués (selon toi), et l'outil n'a aucun moyen de les distinguer de coups ratés. Pour les prochaines mesures : fixer le marqueur mieux qu'avec un simple ruban.
