from features.check_balance import checkBalance                   
from features.recharge import recharge
from features.transfert import transfert                   
import vosk
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from vosk import Model
import os, json, uuid, wave, re, logging
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which
from datetime import datetime
import spacy

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Audio
AudioSegment.converter = which("ffmpeg")

# Flask app
app = Flask(__name__)
CORS(app)

# Chemin modèle
model_path = r"/home/ao627515/Projects/assistant/outils/vosk-model-fr-0.22"
if not os.path.exists(model_path):
    logger.critical(f"Modèle Vosk introuvable : {model_path}")
    raise FileNotFoundError(f"Modèle Vosk introuvable : {model_path}")

try:
    model = vosk.Model(model_path)
    logger.info("Modèle Vosk chargé avec succès")
except Exception as e:
    logger.critical("Erreur lors du chargement du modèle", exc_info=e)
    raise

# Répertoire de réponses audio
AUDIO_DIR = "responses"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Chargement NLP
try:
    nlp = spacy.load("fr_core_news_md")
    logger.info("Modèle spaCy chargé")
except Exception as e:
    logger.critical("Erreur chargement spaCy", exc_info=e)
    raise

# Contexte utilisateur simple (à stocker dans Redis ou BDD plus tard)
user_state = {
    "wallet_balance": 10000,  # solde initial fictif
    "credit_balance": 0       # crédit téléphone
}


# Fonctions

def get_llama_response(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=5
        )
        response.raise_for_status()
        return response.json().get("response", "Je n’ai pas compris.")
    except requests.exceptions.RequestException as e:
        logger.error("Erreur requête LLaMA", exc_info=e)
        return "Je rencontre un problème pour obtenir une réponse."

def analyze_intent_spacy(text: str) -> str:
    try:
        doc = nlp(text.lower())

        if any(token.lemma_ in ["bonjour", "salut", "bonsoir"] for token in doc):
            return "Bonjour ! Comment puis-je vous aider aujourd'hui ?"

        if "heure" in text or "temps" in text:
            return f"Il est {datetime.now().strftime('%H heures %M minutes')}"

        if any(word in text for word in ["solde", "mon solde", "combien j'ai", "mon argent"]):
            return checkBalance(user_state);

        # Détection des intentions de transfert ou dépôt
        if any(
            (token.pos_ in ["VERB", "NOUN"]) and token.lemma_ in ["envoyer", "transférer", "donner", "payer", "dépôt", "déposer"]
            for token in doc
        ) or re.search(r"(dépos[ea]?|transfèr[e]?|transfert|envoi[e]?|verse|donne)", text.lower()):

            return transfert(text, doc, user_state)


        # Détection des recharges
        if "recharge" in text or re.search(r"(recharge[r]?|recharger|créditer|mets?[\s\-]*du[\s\-]*crédit)", text.lower()):
            return recharge(text, user_state)



        if any(word in text for word in ["merci", "thanks", "merci beaucoup"]):
            return "Avec plaisir !"

        if any(word in text for word in ["au revoir", "bye", "à bientôt"]):
            return "Au revoir ! À bientôt !"

        return get_llama_response(text)

    except Exception as e:
        logger.error("Erreur analyse NLP", exc_info=e)
        return "Désolé, je n’ai pas pu analyser votre demande."


@app.route('/nlp', methods=['POST'])
def transcribe():
    try:
        data = request.get_json(force=True)
        if not data or 'text' not in data:
            return jsonify({'error': 'Le champ "text" est requis'}), 400

        text_result = data['text'].strip()
        if not text_result:
            return jsonify({'error': 'Le texte est vide'}), 400

        response_text = analyze_intent_spacy(text_result)

        unique_id = str(uuid.uuid4())
        audio_filename = f"response_{unique_id}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        try:
            tts = gTTS(response_text, lang='fr', slow=False)
            tts.save(audio_path)
            logger.info(f"TTS généré : {audio_path}")
        except Exception as e:
            logger.error("Erreur génération TTS", exc_info=e)
            return jsonify({"error": "Erreur lors de la génération audio", "details": str(e)}), 500

        return jsonify({
            "text": text_result,
            "response": response_text,
            "audio_id": unique_id
        })

    except Exception as e:
        logger.error("Erreur dans /nlp", exc_info=e)
        return jsonify({"error": "Erreur serveur", "details": str(e)}), 500


@app.route('/response-audio/<audio_id>', methods=['GET'])
def get_audio(audio_id):
    try:
        audio_filename = f"response_{audio_id}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)

        if not os.path.exists(audio_path):
            return jsonify({"error": "Fichier audio non trouvé"}), 404

        return send_file(audio_path, mimetype="audio/mpeg")

    except Exception as e:
        logger.error("Erreur dans /response-audio", exc_info=e)
        return jsonify({"error": "Erreur serveur"}), 500


@app.route('/test-model', methods=['GET'])
def test_model():
    try:
        model_info = {
            "model_path": model_path,
            "model_exists": os.path.exists(model_path),
            "vosk_version": vosk.__version__ if hasattr(vosk, '__version__') else "unknown"
        }

        return jsonify({
            "status": "OK",
            "message": "Modèle Vosk prêt",
            "model_info": model_info
        })
    except Exception as e:
        logger.error("Erreur test modèle", exc_info=e)
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Serveur fonctionnel"})


@app.route('/cleanup', methods=['POST'])
def cleanup_files():
    try:
        count = 0
        for filename in os.listdir(AUDIO_DIR):
            if filename.startswith("response_") and filename.endswith(".mp3"):
                os.remove(os.path.join(AUDIO_DIR, filename))
                count += 1
        return jsonify({"message": f"{count} fichiers supprimés"})
    except Exception as e:
        logger.error("Erreur nettoyage fichiers", exc_info=e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
