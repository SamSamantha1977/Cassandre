# Cassandre WORKER — installation utilisateur (sans droits administrateur)

## Variantes fournies

- **Windows** : `INSTALL-WORKER-Utilisateur-Windows.cmd` (PowerShell 5.1 minimum, compte standard, aucune UAC).
- **Linux Debian / Ubuntu / Mint** : `INSTALL-WORKER-Utilisateur-Linux-Debian.sh`.
- **Linux Fedora / RHEL / Rocky / AlmaLinux** : `INSTALL-WORKER-Utilisateur-Linux-Fedora.sh`.
- **Autres distributions Linux** : `INSTALL-WORKER-Utilisateur-Linux-Universel.sh`.

Les trois variantes Linux reprennent les **trois familles de distribution** des packages administrateur, mais ne sont **pas** des installations système `.deb` / `.rpm`. Elles n'utilisent ni `dpkg -i`, ni `rpm -i`, ni `sudo`, ni `pkexec`. Elles partagent le même moteur d'installation utilisateur, et gardent leur entrée par famille.

**Ne pas séparer** `bootstrap_user.py` de son lanceur : les deux doivent être dans le même dossier.

### Prérequis

- Python 3.11 ou supérieur présent dans la session utilisateur, avec le module `venv` et `pip` ; accès HTTPS à GitHub et au contrôleur Cassandre.
- Linux : connexion à une session utilisateur, `systemd --user` conseillé (sinon autostart XDG lors de la prochaine connexion graphique).
- Windows : Windows PowerShell 5.1 ou supérieur. Si Python est absent, le lanceur tente une installation **dans le profil utilisateur**, depuis python.org, après contrôle de la signature numérique. Aucune élévation UAC.

### Installation

Windows : décompresser l'archive, double-cliquer sur `INSTALL-WORKER-Utilisateur-Windows.cmd`.
Linux : décompresser l'archive, exécuter le fichier `.sh` correspondant à sa famille, par exemple `sh INSTALL-WORKER-Utilisateur-Linux-Debian.sh`.

L'installateur télécharge **le package technique WORKER officiel existant**, vérifie son SHA-256 avec `SHA256SUMS.txt` publié sur la Release GitHub, le déploie dans le profil et applique un adaptateur spécifique sans droits administrateur.

### Emplacements

- Windows : `%LOCALAPPDATA%\Cassandre\Worker`.
- Linux : `${XDG_DATA_HOME:-~/.local/share}/cassandre-worker`.
- Configuration : `<répertoire WORKER>/State/worker.json`.
- Journaux : `<répertoire WORKER>/Logs/*.cmtrace.log`, format CMTrace.exe.

### Persistance et limites

- **Windows** : démarrage depuis la valeur `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\CassandreWorkerUser`. Les tâches de traitement sont lancées sans fenêtre visible avec `pythonw.exe` et sans élévation.
- **Linux** : service `systemd --user` ; repli vers `~/.config/autostart/cassandre-worker-user.desktop` pour les sessions graphiques.
- Une **session utilisateur doit être ouverte**. Le WORKER peut continuer si la session est simplement verrouillée ; il ne travaille pas avant authentification et ne garantit pas son fonctionnement après déconnexion.
- Les interventions exigeant un exécuteur **SYSTEM/root** ne sont pas prises en charge par ces versions. Les réglages d'alimentation système, services privilégiés et installations système restent réservés aux variantes administrateur.
- Les packages administrateur du dépôt ne sont **ni remplacés ni modifiés** par cette livraison.
- Sans privilèges, le WORKER peut exécuter des opérations relevant des permissions du compte courant : il ne peut pas utiliser les ressources ou opérations réservées à d'autres comptes.

### Maintenance

Les données opérationnelles et la configuration restent dans le profil. Le fichier `bootstrap_user.py` peut être réexécuté pour effectuer une installation/mise à niveau depuis la Release en conservant l'état existant.

`python bootstrap_user.py --family windows --mode status` (Windows), ou `python3 bootstrap_user.py --family universal --mode status` (Linux), affiche les chemins.

`python bootstrap_user.py --family windows --mode uninstall`, ou `python3 bootstrap_user.py --family universal --mode uninstall`, retire **uniquement l'autodémarrage** : les données restent volontairement en place, afin d'éviter toute perte accidentelle.

### Vérifications

Chaque installation doit être validée sur machine réelle (une machine Windows standard, une Debian/Ubuntu, une Fedora/RHEL et une distribution universelle). Les tests statiques et unitaires livrés ne prouvent pas à eux seuls le fonctionnement du réseau, de l'authentification et de la récupération des jobs sur ces OS.
