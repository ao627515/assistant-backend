from features.check_balance import checkBalance
import vosk
import requests
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from vosk import Model, KaldiRecognizer
import wave, os, json, uuid
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which
from datetime import datetime
import tempfile
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lien vers ffmpeg pour conversion audio
AudioSegment.converter = which("ffmpeg")

app = Flask(__name__)
CORS(app)  # Permet les requêtes cross-origin

# Chemin vers ton modèle Vosk français
model_path = r"C:\Users\Mr.Adam's\Desktop\ODC\outils\python\vosk-model-fr-0.22"

# Vérification de l'existence du modèle
if not os.path.exists(model_path):
    logger.error(f"Modèle Vosk non trouvé : {model_path}")
    raise FileNotFoundError(f"Modèle Vosk non trouvé : {model_path}")

try:
    model = vosk.Model(model_path)
    logger.info("Modèle Vosk chargé avec succès")
except Exception as e:
    logger.error(f"Erreur lors du chargement du modèle : {e}")
    raise

# Répertoire pour stocker les fichiers audio générés
AUDIO_DIR = "responses"
os.makedirs(AUDIO_DIR, exist_ok=True)

#creation de la fonction llama
def get_llama_response(prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False  # Si tu veux recevoir toute la réponse d’un coup
        }
    )
    return response.json()["response"]
# Analyse des intentions améliorée
def analyze_intent(text):
    text = text.lower().strip()

    if not text:
        return "Je n'ai pas entendu votre message."

    """
    """
    # Mots-clés pour l'heure
    if any(word in text for word in ["heure", "temps", "quelle heure"]):
        return f"Il est {datetime.now().strftime('%H heures %M minutes')}"

    # Salutations
    elif any(word in text for word in ["salut", "bonjour", "bonsoir", "hello"]):
        return "Bonjour ! Comment puis-je vous aider aujourd'hui ?"

    # Remerciements
    elif any(word in text for word in ["merci", "merci beaucoup"]):
        return "De rien ! Je suis là pour vous aider."

    # Questions sur l'identité
    elif any(phrase in text for phrase in ["qui es-tu", "qui êtes-vous", "comment tu t'appelles"]):
        return "Je suis votre assistant vocal personnel. Je peux vous aider avec diverses tâches."

    # Météo (exemple basique)
    elif any(word in text for word in ["météo", "temps qu'il fait", "pluie"]):
        return "Désolé, je ne peux pas encore consulter la météo en temps réel."

    # Consultation de solde
    elif any(phrase in text for phrase in ["solde", "mon solde", "combien j'ai", "consulter mon solde", "mon argent"]):
        return checkBalance()
    
    # Au revoir
    elif any(word in text for word in ["au revoir", "bye", "à bientôt"]):
        return "Au revoir ! À bientôt !"

    else:
        return get_llama_response(text)


@app.route('/transcribe', methods=['POST'])
def transcribe():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'Aucun fichier audio fourni'}), 400

        audio_file = request.files['audio']

        # Génération d'un nom unique pour éviter les conflits
        unique_id = str(uuid.uuid4())
        temp_webm = f"temp_{unique_id}.webm"
        temp_wav = f"temp_{unique_id}.wav"

        # Sauvegarde du fichier audio
        audio_file.save(temp_webm)
        logger.info(f"Fichier audio sauvegardé : {temp_webm}")

        # Conversion en .wav pour Vosk
        try:
            audio = AudioSegment.from_file(temp_webm, format="webm")

            # Informations sur l'audio original
            logger.info(f"Audio original: {audio.frame_rate}Hz, {audio.channels} canaux, {len(audio)}ms")

            # Conversion optimisée pour Vosk
            audio = audio.set_frame_rate(16000).set_channels(1)

            # Normalisation du volume
            audio = audio.normalize()

            # Augmentation du volume si nécessaire
            if audio.max_dBFS < -20:
                audio = audio + (abs(audio.max_dBFS) - 10)
                logger.info("Volume augmenté")

            # Export avec paramètres optimisés
            audio.export(temp_wav, format="wav", parameters=["-ar", "16000", "-ac", "1"])

            logger.info(f"Audio converti: {len(audio)}ms, volume max: {audio.max_dBFS}dBFS")

        except Exception as e:
            logger.error(f"Erreur de conversion audio : {e}")
            return jsonify({"error": "Conversion audio échouée", "details": str(e)}), 500
        finally:
            # Suppression du fichier webm
            if os.path.exists(temp_webm):
                os.remove(temp_webm)

        # Traitement avec Vosk
        try:
            wf = wave.open(temp_wav, "rb")

            # Affichage des informations audio pour debug
            logger.info(f"Format audio: {wf.getframerate()}Hz, {wf.getnchannels()} canaux, {wf.getnframes()} frames")

            # Ajustement automatique si nécessaire
            if wf.getframerate() != 16000 or wf.getnchannels() != 1:
                wf.close()
                logger.info("Reconversion nécessaire...")
                audio = AudioSegment.from_wav(temp_wav)
                audio = audio.set_frame_rate(16000).set_channels(1)
                audio.export(temp_wav, format="wav")
                wf = wave.open(temp_wav, "rb")
                logger.info(f"Audio reconverti: {wf.getframerate()}Hz, {wf.getnchannels()} canaux")

            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)  # Activation des mots individuels

            text_result = ""
            results = []

            # Lecture par chunks plus grands
            while True:
                data = wf.readframes(8000)  # Chunks plus grands
                if len(data) == 0:
                    break

                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if result.get("text"):
                        text_result += result["text"] + " "
                        results.append(result["text"])
                        logger.info(f"Résultat partiel: {result['text']}")

            # Récupération du dernier résultat (très important!)
            final_result = json.loads(rec.FinalResult())
            if final_result.get("text"):
                text_result += final_result["text"]
                results.append(final_result["text"])
                logger.info(f"Résultat final: {final_result['text']}")

            wf.close()

            # Nettoyage du texte
            text_result = text_result.strip()

            logger.info(f"Transcription complète: '{text_result}'")
            logger.info(f"Tous les résultats: {results}")

            # Vérification si on a vraiment du texte
            if not text_result:
                logger.warning("Aucun texte transcrit - possible problème de qualité audio")
                return jsonify({
                    "text": "",
                    "response": "Je n'ai pas réussi à comprendre votre message. Pouvez-vous parler plus fort et plus clairement ?",
                    "audio_id": None,
                    "debug": "Aucune transcription"
                })

        except Exception as e:
            logger.error(f"Erreur Vosk : {e}")
            return jsonify({"error": "Erreur de transcription", "details": str(e)}), 500
        finally:
            # Suppression du fichier wav
            if os.path.exists(temp_wav):
                os.remove(temp_wav)

        # Analyse d'intention et génération de réponse
        response_text = analyze_intent(text_result.strip())

        # Génération TTS
        try:
            tts = gTTS(response_text, lang='fr', slow=False)
            audio_filename = f"response_{unique_id}.mp3"
            audio_path = os.path.join(AUDIO_DIR, audio_filename)
            tts.save(audio_path)
            logger.info(f"Audio TTS généré : {audio_path}")
        except Exception as e:
            logger.error(f"Erreur TTS : {e}")
            return jsonify({"error": "Erreur de génération audio", "details": str(e)}), 500

        return jsonify({
            "text": text_result.strip(),
            "response": response_text,
            "audio_id": unique_id
        })

    except Exception as e:
        logger.error(f"Erreur générale : {e}")
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
        logger.error(f"Erreur envoi audio : {e}")
        return jsonify({"error": "Erreur serveur"}), 500


@app.route('/test-model', methods=['GET'])
def test_model():
    """Test basique du modèle Vosk avec un fichier audio de test"""
    try:
        # Informations sur le modèle
        model_info = {
            "model_path": model_path,
            "model_exists": os.path.exists(model_path),
            "vosk_version": vosk.__version__ if hasattr(vosk, '__version__') else "Unknown"
        }

        return jsonify({
            "status": "OK",
            "message": "Modèle Vosk chargé et prêt",
            "model_info": model_info
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "OK", "message": "Serveur fonctionnel"})


# Nettoyage périodique des fichiers temporaires (optionnel)
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
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)