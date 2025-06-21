# Assistant Vocal Orange Money - Backend

Ce projet est un backend Python Flask pour un assistant vocal Orange Money, conçu pour répondre à des commandes vocales ou textuelles liées à la gestion de compte mobile money (solde, transferts, recharges, achats de forfaits, historique, bonus fidélité, etc.) au Burkina Faso.  
Il s'interface avec des modèles NLP (spaCy, Vosk, llm local via Ollama) et génère des réponses audio via gTTS.

> **Ce backend est conçu pour fonctionner avec des frontends séparés :**
>
> - [assistant-frontend-react](https://github.com/ao627515/assistant-frontend-react.git)
> - [assistant-frontend-ionic](https://github.com/ao627515/assistant-frontend-ionic.git)

> **Lien du dépôt backend :**  
> [assistant-backend](https://github.com/ao627515/assistant-backend.git)

## Fonctionnalités principales

- Analyse de texte en français pour comprendre les demandes Orange Money
- Synthèse vocale des réponses (gTTS)
- Reconnaissance vocale (Vosk, à intégrer côté frontend)
- Gestion simple des utilisateurs et transactions (stockage JSON)
- API REST pour traitement des requêtes et récupération des fichiers audio
- Prise en charge des CORS pour intégration facile avec des frontends web/mobile

## Structure du projet

```
.
├── app.py                # Backend Flask principal
├── req.txt               # Dépendances Python
├── responses/            # Fichiers audio générés (.mp3)
├── tools/                # (Modèles Vosk, etc.)
├── .gitignore
└── ...
```

## Installation

1. **Cloner le dépôt**

```sh
git clone https://github.com/ao627515/assistant-backend.git
cd assistant-backend
```

2. **Installer les dépendances**

Créez un environnement virtuel puis installez les paquets requis :

```sh
python3 -m venv venv
source venv/bin/activate
pip install -r req.txt
```

3. **Télécharger le modèle spaCy français**

```sh
python -m spacy download fr_core_news_md
```

4. **Installer ffmpeg (pour pydub/gTTS)**

Sur Ubuntu/Debian :

```sh
sudo apt-get install ffmpeg
```

5. **Télécharger le modèle Vosk français**

Téléchargez le modèle depuis https://alphacephei.com/vosk/models et placez-le dans `tools/vosk-model-fr-0.22`.

6. **(Optionnel) LLM local via Ollama pour réponses avancées**

Le backend peut utiliser un LLM local via [Ollama](https://ollama.com/).  
Par défaut, le modèle utilisé est `gemma:2b`, mais vous pouvez le changer selon vos besoins.  
Ollama doit être installé et lancé sur `localhost:11434` avec le modèle souhaité chargé.

## Lancement du serveur

```sh
python app.py
flask run
```

Le serveur sera accessible sur [http://localhost:5000](http://localhost:5000).

## Endpoints principaux

- `POST /process` : Analyse une demande texte, retourne la réponse et l'ID audio
- `GET /audio/<audio_id>` : Récupère le fichier audio généré
- `GET /solde` : Retourne le solde de l'utilisateur par défaut
- `GET /health` : Vérifie l'état des services
- `GET /demo` : Page de démonstration web simple

## Utilisation avec les frontends

Utilisez ce backend avec l'un des frontends suivants :

- [assistant-frontend-react](https://github.com/ao627515/assistant-frontend-react.git)
- [assistant-frontend-ionic](https://github.com/ao627515/assistant-frontend-ionic.git)

## Remarques

- Les fichiers audio générés sont stockés dans le dossier `responses/`.
- Les données utilisateurs sont stockées dans `users_data.json` (créé automatiquement).
- Les modèles spaCy et Vosk doivent être installés localement.
- Les logs sont affichés en console pour le debug.

## Licence

Projet sous licence MIT (à adapter selon votre besoin).
