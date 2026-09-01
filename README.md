# Cassandre — mettre en commun la puissance disponible de nos ordinateurs

**Cassandre est un projet communautaire de calcul distribué.**

➡️ [Découvrir Cassandre et voir le compteur public](https://SamSamantha1977.github.io/Cassandre/)

Son principe est simple : de nombreux ordinateurs personnels disposent de ressources importantes — processeur, carte graphique, mémoire et stockage — qui ne sont pas exploitées à leur plein potentiel lorsque leur propriétaire ne les utilise pas.

Cassandre permet de mettre en commun cette capacité disponible afin de constituer collectivement une infrastructure de calcul pouvant servir à des projets trop lourds pour une seule machine.

Un ordinateur apporte une petite capacité. Des centaines ou des milliers d'ordinateurs peuvent, ensemble, en apporter énormément.

> Cassandre n'utilise les ressources de l'ordinateur que lorsque son utilisateur ne s'en sert pas. Dès que l'utilisateur revient, sa machine redevient prioritaire.

## Pourquoi Cassandre ?

Les besoins en calcul progressent rapidement, notamment pour la création numérique, la 3D, la simulation et l'intelligence artificielle.

La réponse habituelle consiste à construire ou louer toujours davantage d'infrastructures centralisées. Cassandre explore une autre voie : **utiliser intelligemment la capacité déjà présente dans les ordinateurs personnels de la communauté, uniquement lorsqu'ils ne sont pas utilisés par leur propriétaire.**

L'objectif n'est pas de remplacer tous les usages d'un datacenter, mais de créer une capacité de calcul complémentaire, distribuée et communautaire.

## Le principe en quatre étapes

1. Vous installez le WORKER Cassandre sur votre ordinateur.
2. Vous continuez à utiliser votre ordinateur normalement.
3. Lorsque votre ordinateur est disponible et que vous ne l'utilisez pas, Cassandre peut lui confier de petites tâches adaptées à ses capacités.
4. Lorsque vous recommencez à utiliser votre ordinateur, Cassandre lui rend la priorité.

Le réseau peut ainsi exploiter temporairement des capacités CPU, GPU, RAM et de stockage réparties sur de nombreuses machines, sans demander aux participants de réserver leur ordinateur exclusivement à Cassandre.

## Vous gardez le contrôle de votre ordinateur

Le WORKER dispose d'une interface web locale destinée à son propriétaire.

Elle permet notamment de consulter l'état du WORKER, son planning, les paramètres laissés au choix de l'utilisateur et sa contribution au réseau Cassandre.

L'espace disque pouvant être mis à disposition reste configurable. Cassandre détermine automatiquement la capacité de calcul réellement disponible au moment où la machine peut participer.

Les échanges nécessaires au fonctionnement du réseau sont protégés et l'installation, l'authentification du WORKER et les opérations courantes sont automatisées afin de ne pas imposer de connaissances techniques à l'utilisateur.

## Mes ordinateurs, applications et connexions

L'espace WORKER peut également regrouper les ordinateurs associés à un même participant afin de présenter plus clairement ses machines et leur contribution cumulée.

Il comprend désormais des espaces **APPLICATIONS** et **CONNEXIONS IA**. L'architecture de connecteurs permet à des logiciels compatibles de soumettre des traitements à Cassandre via le WORKER lorsqu'un connecteur est explicitement activé. Un premier connecteur est prévu pour **Blender**, notamment pour les usages de création et de rendu 3D.

L'installation ou la mise à jour d'un connecteur n'est pas poussée automatiquement à un WORKER : elle doit résulter d'une action explicite. Les mécanismes internes d'authentification et de sécurité du réseau restent volontairement hors de la documentation publique.

## Contribution

Chaque WORKER participant construit progressivement un **score de CONTRIBUTION** représentant sa participation cumulée au réseau Cassandre.

Ce système a vocation à permettre à la communauté de visualiser sa contribution individuelle et collective, de suivre la progression du réseau et, à terme, de participer à des équipes et objectifs communautaires.

La progression tient compte de la contribution réellement apportée par la machine au fil du temps.

## Ce que Cassandre pourra rendre possible

Plus la toile Cassandre grandira, plus les projets qu'elle pourra soutenir deviendront ambitieux.

À terme, cette infrastructure distribuée pourra notamment servir à des travaux nécessitant beaucoup de calcul, de mémoire, de GPU ou de stockage, et ouvrir la voie à de nouveaux usages collaboratifs entre ordinateurs personnels.

L'une des orientations étudiées est le **partage de capacité entre machines** : lorsqu'un ordinateur ne possède pas localement toutes les ressources nécessaires à un usage, des ressources disponibles ailleurs dans la toile Cassandre pourraient lui venir en aide lorsque l'architecture et les conditions techniques le permettent.

Exemple d'objectif : pouvoir un jour jouer avec un ami dont l'ordinateur n'est normalement pas assez puissant, en s'appuyant sur des ressources mises à disposition par la toile Cassandre plutôt que de lui imposer l'achat immédiat de nouveau matériel.

## Installation simple — aucune ligne de commande à connaître

La version destinée au grand public ne demande pas de savoir utiliser PowerShell, Terminal, `sudo` ou une invite de commandes.

### Windows

1. Ouvrez la [Release Cassandre Worker](https://github.com/SamSamantha1977/Cassandre/releases/tag/worker-bootstrap).
2. Téléchargez **`setup_windows.exe`**.
3. Double-cliquez sur le fichier téléchargé.
4. Validez la demande d'autorisation de Windows.
5. L'installation se poursuit automatiquement.

Aucune commande n'est à saisir.

### Linux — Debian / Ubuntu / Linux Mint et dérivés

1. Ouvrez la [Release Cassandre Worker](https://github.com/SamSamantha1977/Cassandre/releases/tag/worker-bootstrap).
2. Téléchargez **`M3DIA-Worker.deb`**.
3. Double-cliquez sur le fichier.
4. Cliquez sur **Installer** dans le gestionnaire de logiciels de votre distribution.
5. Validez l'autorisation demandée.

### Linux — Fedora / RHEL / Rocky Linux / AlmaLinux et dérivés

1. Ouvrez la [Release Cassandre Worker](https://github.com/SamSamantha1977/Cassandre/releases/tag/worker-bootstrap).
2. Téléchargez **`M3DIA-Worker.rpm`**.
3. Double-cliquez sur le fichier.
4. Cliquez sur **Installer**.
5. Validez l'autorisation demandée.

### Linux — méthode universelle

Pour les distributions ne prenant pas directement en charge les packages précédents, **`INSTALL-M3DIA-WORKER.sh`** reste disponible dans la Release.

Les packages `.deb` et `.rpm` restent recommandés aux utilisateurs non techniques.

### macOS — expérimental

Une version macOS est également publiée sous la forme **`INSTALL-M3DIA-WORKER-macOS.zip`**.

Le fonctionnement sur macOS reste expérimental et n'est pas garanti sur toutes les versions et configurations du système.

## Si Windows SmartScreen affiche un avertissement

Cassandre est un projet communautaire récent et les versions actuellement publiées ne bénéficient pas encore d'une réputation de signature largement établie auprès de Windows.

Un avertissement SmartScreen signifie que Windows ne dispose pas encore d'une réputation suffisante pour ce fichier ; ce n'est pas, à lui seul, une détection de logiciel malveillant.

Si l'avertissement apparaît pour le fichier téléchargé depuis la Release officielle Cassandre :

1. cliquez sur **Informations complémentaires** ;
2. cliquez sur **Exécuter quand même** ;
3. validez ensuite la demande d'autorisation Windows.

Nous travaillons à améliorer progressivement la chaîne de confiance et la vérification des versions publiées.

## Packages disponibles

La Release GitHub `worker-bootstrap` contient les points d'entrée grand public et les packages techniques :

- **Windows grand public** : `setup_windows.exe`
- **Windows package** : `M3DIA-Worker-Windows.zip`
- **Linux Debian/Ubuntu/Mint** : `M3DIA-Worker.deb`
- **Linux Fedora/RHEL/Rocky/Alma** : `M3DIA-Worker.rpm`
- **Linux universel** : `INSTALL-M3DIA-WORKER.sh`
- **Linux package technique** : `M3DIA-Worker-Linux.tar.gz`
- **macOS grand public** : `INSTALL-M3DIA-WORKER-macOS.zip`
- **macOS package technique** : `M3DIA-Worker-macOS.zip`

Les empreintes SHA-256 sont fournies dans **`SHA256SUMS.txt`** pour permettre de vérifier l'intégrité des fichiers téléchargés.

## Transparence

Le projet est distribué sous licence MIT. Les mécanismes internes qui relèvent de la sécurité opérationnelle, de l'authentification du réseau ou de la prévention des abus ne sont volontairement pas détaillés dans cette présentation publique.

## Participer

Cassandre est avant tout destiné à devenir une **communauté de personnes qui mettent en commun une partie de la capacité de leurs ordinateurs personnels lorsqu'elles ne les utilisent pas.**

Installer un WORKER, c'est ajouter une machine à cette capacité collective.

Aujourd'hui, Cassandre construit sa première communauté de participants. Chaque nouveau WORKER compte.

➡️ [Rejoindre Cassandre — télécharger le WORKER](https://github.com/SamSamantha1977/Cassandre/releases/tag/worker-bootstrap)

## Confidentialité et licence

Voir [Confidentialité](PRIVACY.md) et [LICENSE](LICENSE).
