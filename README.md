# Assistant Vocal Orange Money – Backend

Ce projet est le backend Python Flask d’un assistant vocal pour la gestion des services Orange Money, conçu pour comprendre des commandes vocales ou textuelles en français (Burkina Faso). Ce backend agit comme un simulateur de traitement pour un MVP (Minimum Viable Product) : **aucune transaction réelle n’est effectuée**. Il est interfacé avec des modèles NLP locaux (spaCy, Vosk, LLM via Ollama) pour interpréter les requêtes et répondre vocalement.

> Ce backend est utilisé avec deux interfaces frontend indépendantes :
>
> - [assistant-frontend-react](https://github.com/ao627515/assistant-frontend-react.git)
> - [assistant-frontend-ionic](https://github.com/ao627515/assistant-frontend-ionic.git)

## Fonctionnalités principales

- Analyse du langage naturel en français (spaCy)
- Génération vocale des réponses (gTTS + pydub)
- Simulation des traitements Orange Money : solde, recharges, forfaits, historique...
- Intégration d’un LLM local (via [Ollama](https://ollama.com/)) pour l’assistant généraliste
- API REST (JSON) pour les échanges avec les clients web ou mobiles
- Prise en charge CORS pour une intégration multi-frontend

## Structure du projet

```
.
├── app.py                  # Backend principal
├── req.txt                # Fichier des dépendances Python
├── responses/             # Réponses vocales générées (.mp3)
├── tools/                 # Modèles vocaux (ex : Vosk)
├── users_data.json        # Données utilisateurs simulées (auto-créé)
└── ...
```

## Installation et Configuration

1. **Cloner le dépôt**

```bash
git clone https://github.com/ao627515/assistant-backend.git
cd assistant-backend
```

2. **Créer un environnement virtuel et installer les dépendances**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r req.txt
```

3. **Télécharger les modèles requis**

```bash
python -m spacy download fr_core_news_md
```

4. **Installer ffmpeg** (nécessaire pour pydub/gTTS)

```bash
sudo apt install ffmpeg
```

5. **Télécharger le modèle Vosk FR**
   Depuis [https://alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) et placer dans `tools/vosk-model-fr-0.22`

6. **(Optionnel) Intégration LLM via Ollama**

- Installer Ollama sur [https://ollama.com](https://ollama.com)
- Lancer `ollama run gemma:2b` (ou autre modèle)
- Le backend interrogera Ollama via `localhost:11434`

## Démarrage du serveur

```bash
flask run
```

Accès via : [http://localhost:5000](http://localhost:5000)

## Endpoints API

- `POST /process` : Traitement d'une requête utilisateur (texte) → réponse + ID audio
- `GET /audio/<audio_id>` : Récupération du fichier audio
- `GET /solde` : Renvoie un solde simulé
- `GET /health` : Vérifie l’état de fonctionnement
- `GET /demo` : Mini page web de test

## Auteurs

- [Tapsoba Faridatou](https://github.com/biabkaahfa)
- [Ouédraogo Abdoul Aziz](https://github.com/ao627515)
- [Simporé Elie](https://github.com/simporeelie)
- [Sawadogo Adam Sharif](https://github.com/Oursdingo)

## Licence

MIT — à adapter selon vos besoins.
