"""
Assistant Vocal Orange Money - MVP Simple
Version démo pour présentation
"""

import os
import re
import json
import uuid
import logging
import requests
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import vosk
import spacy
from gtts import gTTS
from pydub import AudioSegment
from pydub.utils import which

# Configuration simple
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Audio
AudioSegment.converter = which("ffmpeg")

# Flask app
app = Flask(__name__)
CORS(app)

# Modèle Vosk
model_path = r"./tools/vosk-model-fr-0.22"
if not os.path.exists(model_path):
    logger.error(f"Modèle Vosk introuvable : {model_path}")
    model = None
else:
    try:
        model = vosk.Model(model_path)
        logger.info("Modèle Vosk chargé")
    except Exception as e:
        logger.error(f"Erreur chargement Vosk: {e}")
        model = None

# Répertoire audio
AUDIO_DIR = "responses"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Modèle spaCy
try:
    nlp = spacy.load("fr_core_news_md")
    logger.info("Modèle spaCy chargé")
except Exception as e:
    logger.error(f"Erreur spaCy: {e}")
    nlp = None

# ========== BASE DE DONNÉES SIMPLE (fichier JSON) ==========

def load_user_data():
    """Charge les données utilisateur depuis un fichier JSON"""
    try:
        if os.path.exists("users_data.json"):
            with open("users_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Erreur chargement données: {e}")
    
    # Données par défaut
    return {
        "users": {
            "default": {
                "nom": "Client Orange",
                "telephone": "74000000",
                "solde_principal": 50000,
                "credit_communication": 2500,
                "internet_mb": 1024,
                "transactions": [],
                "bonus_fidelite": 500,
                "date_derniere_connexion": datetime.now().isoformat()
            }
        }
    }

def save_user_data(data):
    """Sauvegarde les données utilisateur"""
    try:
        with open("users_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Erreur sauvegarde: {e}")
        return False

# Chargement initial des données
user_database = load_user_data()

# ========== FONCTIONS UTILITAIRES ==========

def extraire_montant(texte):
    """Extrait un montant du texte"""
    # Cherche les patterns de montant
    patterns = [
        r'(\d+(?:\s*\d+)*)\s*(?:francs?|fcfa|f\b)',
        r'(\d+(?:\s*\d+)*)',  # Nombre simple
    ]
    
    for pattern in patterns:
        match = re.search(pattern, texte.lower())
        if match:
            # Nettoie le montant (supprime espaces)
            montant_str = re.sub(r'\s+', '', match.group(1))
            try:
                return int(montant_str)
            except ValueError:
                continue
    return None

def extraire_destinataire(texte, doc_spacy=None):
    """Extrait le destinataire d'un transfert"""
    # Numéro de téléphone
    phone_match = re.search(r'(\d{8})', texte)
    if phone_match:
        return f"Numéro {phone_match.group(1)}"
    
    # Nom avec spaCy si disponible
    if doc_spacy:
        for ent in doc_spacy.ents:
            if ent.label_ == "PER":
                return ent.text
    
    # Recherche de mots après "à"
    match = re.search(r'\bà\s+([A-Za-zÀ-ÿ\s]+)', texte)
    if match:
        nom = match.group(1).strip()
        if len(nom) > 1:
            return nom
    
    return None

def obtenir_reponse_llm(prompt):
    """Obtient une réponse du modèle LLaMA local"""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma:2b",
                "prompt": f"Tu es un assistant Orange Money au Burkina Faso. Réponds en français, de manière simple et amicale.\n\nQuestion: {prompt}\n\nRéponse:",
                "stream": False
            },
            timeout=8
        )
        if response.status_code == 200:
            return response.json().get("response", "Je n'ai pas compris votre demande.")
        else:
            return "Service momentanément indisponible."
    except Exception as e:
        logger.error(f"Erreur gemma:2b: {e}")
        return "Je n'ai pas pu traiter votre demande."

# ========== FONCTIONNALITÉS ORANGE MONEY ==========

def traiter_solde(user_id="default"):
    """Traite une demande de solde"""
    user = user_database["users"].get(user_id, user_database["users"]["default"])
    
    return (f"Voici vos soldes : "
            f"Solde principal {user['solde_principal']:,} FCFA, "
            f"Crédit communication {user['credit_communication']} FCFA, "
            f"Internet {user['internet_mb']} MB, "
            f"Bonus fidélité {user['bonus_fidelite']} FCFA.")

def traiter_transfert(texte, user_id="default"):
    """Traite un transfert d'argent"""
    user = user_database["users"].get(user_id, user_database["users"]["default"])
    
    montant = extraire_montant(texte)
    doc = nlp(texte) if nlp else None
    destinataire = extraire_destinataire(texte, doc)
    
    if not destinataire:
        return "À qui voulez-vous envoyer de l'argent ? Donnez-moi un nom ou un numéro."
    
    if not montant:
        return f"Quel montant voulez-vous envoyer à {destinataire} ?"
    
    if montant > user["solde_principal"]:
        return f"Solde insuffisant. Votre solde est de {user['solde_principal']:,} FCFA."
    
    if montant < 100:
        return "Le montant minimum est de 100 FCFA."
    
    if montant > 500000:
        return "Le montant maximum par transaction est de 500,000 FCFA."
    
    # Frais de transfert (simplifié)
    frais = 0
    if montant <= 2500:
        frais = 100
    elif montant <= 15000:
        frais = 200
    else:
        frais = 500
    
    montant_total = montant + frais
    
    if montant_total > user["solde_principal"]:
        return f"Solde insuffisant pour les frais. Total nécessaire: {montant_total:,} FCFA (frais: {frais} FCFA)."
    
    # Exécution du transfert
    user["solde_principal"] -= montant_total
    
    # Enregistrement de la transaction
    transaction = {
        "id": str(uuid.uuid4())[:8],
        "type": "transfert",
        "montant": montant,
        "frais": frais,
        "destinataire": destinataire,
        "date": datetime.now().isoformat(),
        "statut": "succès"
    }
    user["transactions"].append(transaction)
    
    # Sauvegarde
    save_user_data(user_database)
    
    return (f"Transfert effectué ! {montant:,} FCFA envoyés à {destinataire}. "
            f"Frais: {frais} FCFA. Nouveau solde: {user['solde_principal']:,} FCFA. "
            f"Référence: {transaction['id']}")

def traiter_recharge_credit(texte, user_id="default"):
    """Traite une recharge de crédit de communication"""
    user = user_database["users"].get(user_id, user_database["users"]["default"])
    
    montant = extraire_montant(texte)
    
    if not montant:
        return "Quel montant voulez-vous recharger en crédit de communication ?"
    
    if montant > user["solde_principal"]:
        return f"Solde insuffisant. Votre solde est de {user['solde_principal']:,} FCFA."
    
    if montant < 500:
        return "Le montant minimum pour une recharge est de 500 FCFA."
    
    # Exécution de la recharge
    user["solde_principal"] -= montant
    user["credit_communication"] += montant
    
    # Transaction
    transaction = {
        "id": str(uuid.uuid4())[:8],
        "type": "recharge_credit",
        "montant": montant,
        "date": datetime.now().isoformat(),
        "statut": "succès"
    }
    user["transactions"].append(transaction)
    
    save_user_data(user_database)
    
    return (f"Recharge effectuée ! {montant:,} FCFA ajoutés à votre crédit. "
            f"Nouveau crédit: {user['credit_communication']:,} FCFA. "
            f"Solde restant: {user['solde_principal']:,} FCFA.")

def traiter_achat_internet(texte, user_id="default"):
    """Traite un achat de forfait internet"""
    user = user_database["users"].get(user_id, user_database["users"]["default"])
    
    # Forfaits disponibles
    forfaits = {
        "500": {"mb": 100, "prix": 500, "nom": "Forfait 100MB"},
        "1000": {"mb": 500, "prix": 1000, "nom": "Forfait 500MB"},
        "2000": {"mb": 1024, "prix": 2000, "nom": "Forfait 1GB"},
        "5000": {"mb": 3072, "prix": 5000, "nom": "Forfait 3GB"},
    }
    
    montant = extraire_montant(texte)
    
    if not montant:
        return ("Choisissez un forfait internet : "
                "500 FCFA pour 100MB, "
                "1000 FCFA pour 500MB, "
                "2000 FCFA pour 1GB, "
                "5000 FCFA pour 3GB.")
    
    forfait = forfaits.get(str(montant))
    if not forfait:
        return "Forfait non disponible. Montants disponibles: 500, 1000, 2000, 5000 FCFA."
    
    if montant > user["solde_principal"]:
        return f"Solde insuffisant. Votre solde est de {user['solde_principal']:,} FCFA."
    
    # Achat du forfait
    user["solde_principal"] -= montant
    user["internet_mb"] += forfait["mb"]
    
    # Transaction
    transaction = {
        "id": str(uuid.uuid4())[:8],
        "type": "achat_internet",
        "montant": montant,
        "forfait": forfait["nom"],
        "date": datetime.now().isoformat(),
        "statut": "succès"
    }
    user["transactions"].append(transaction)
    
    save_user_data(user_database)
    
    return (f"{forfait['nom']} acheté ! {forfait['mb']} MB ajoutés. "
            f"Internet total: {user['internet_mb']} MB. "
            f"Solde restant: {user['solde_principal']:,} FCFA.")

def traiter_historique(user_id="default"):
    """Affiche l'historique des transactions"""
    user = user_database["users"].get(user_id, user_database["users"]["default"])
    
    if not user["transactions"]:
        return "Aucune transaction dans votre historique."
    
    # Dernières 5 transactions
    dernieres = user["transactions"][-5:]
    
    historique = "Vos dernières transactions : "
    for t in dernieres:
        date = datetime.fromisoformat(t["date"]).strftime("%d/%m à %H:%M")
        if t["type"] == "transfert":
            historique += f"{date} - Transfert {t['montant']:,} FCFA à {t['destinataire']}. "
        elif t["type"] == "recharge_credit":
            historique += f"{date} - Recharge crédit {t['montant']:,} FCFA. "
        elif t["type"] == "achat_internet":
            historique += f"{date} - {t['forfait']} {t['montant']:,} FCFA. "
    
    return historique

def traiter_bonus_fidelite(user_id="default"):
    """Gère les bonus de fidélité Orange"""
    user = user_database["users"].get(user_id, user_database["users"]["default"])
    
    if user["bonus_fidelite"] <= 0:
        return "Vous n'avez pas de bonus de fidélité disponible actuellement."
    
    # Ajoute le bonus au solde principal
    bonus = user["bonus_fidelite"]
    user["solde_principal"] += bonus
    user["bonus_fidelite"] = 0
    
    # Transaction
    transaction = {
        "id": str(uuid.uuid4())[:8],
        "type": "bonus_fidelite",
        "montant": bonus,
        "date": datetime.now().isoformat(),
        "statut": "succès"
    }
    user["transactions"].append(transaction)
    
    save_user_data(user_database)
    
    return f"Bonus de fidélité ajouté ! {bonus:,} FCFA crédités sur votre compte. Nouveau solde: {user['solde_principal']:,} FCFA."

# ========== ANALYSE NLP PRINCIPALE ==========

def analyser_demande(texte):
    """Analyse la demande de l'utilisateur et retourne une réponse"""
    texte_lower = texte.lower()
    
    # Salutations
    if re.search(r'\b(bonjour|salut|bonsoir|hello)\b', texte_lower):
        return "Bonjour ! Je suis votre assistant Orange Money. Comment puis-je vous aider aujourd'hui ?"
    
    # Heure
    if re.search(r'\b(heure|temps|quelle heure)\b', texte_lower):
        return f"Il est {datetime.now().strftime('%H heures %M minutes')}."
    
    # Solde
    if re.search(r'\b(solde|combien|argent|mon compte)\b', texte_lower):
        return traiter_solde()
    
    # Transfert d'argent
    if re.search(r'\b(envoie|transfert|transfère|donne|paye|envoi)\b', texte_lower):
        return traiter_transfert(texte)
    
    # Recharge crédit
    if re.search(r'\b(recharge|crédit|communication|appel)\b', texte_lower):
        return traiter_recharge_credit(texte)
    
    # Internet
    if re.search(r'\b(internet|data|forfait|mb|gb)\b', texte_lower):
        return traiter_achat_internet(texte)
    
    # Historique
    if re.search(r'\b(historique|transaction|dernière|opération)\b', texte_lower):
        return traiter_historique()
    
    # Bonus fidélité
    if re.search(r'\b(bonus|fidélité|cadeau|récompense)\b', texte_lower):
        return traiter_bonus_fidelite()
    
    # Services Orange
    if re.search(r'\b(orange|service|aide|assistance)\b', texte_lower):
        return ("Services Orange Money disponibles : "
                "Consulter solde, "
                "Envoyer argent, "
                "Recharger crédit, "
                "Acheter internet, "
                "Voir historique, "
                "Récupérer bonus fidélité.")
    
    # Remerciements
    if re.search(r'\b(merci|thanks)\b', texte_lower):
        return "Avec plaisir ! Y a-t-il autre chose que je puisse faire pour vous ?"
    
    # Au revoir
    if re.search(r'\b(au revoir|bye|à bientôt)\b', texte_lower):
        return "Au revoir ! Merci d'avoir utilisé Orange Money. À bientôt !"
    
    # Demande non reconnue - utilise
    logger.info("reponse llm")
    return obtenir_reponse_llm(texte)

def generer_audio(texte):
    """Génère un fichier audio à partir du texte"""
    try:
        audio_id = str(uuid.uuid4())
        audio_filename = f"response_{audio_id}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        
        tts = gTTS(texte, lang='fr', slow=False)
        tts.save(audio_path)
        
        logger.info(f"Audio généré: {audio_path}")
        return audio_id
        
    except Exception as e:
        logger.error(f"Erreur génération audio: {e}")
        return None

# ========== ROUTES FLASK ==========

@app.route('/process', methods=['POST'])
def traiter_texte():
    """Traite une demande en texte"""
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({'error': 'Le champ "text" est requis'}), 400
        
        texte = data['text'].strip()
        if not texte:
            return jsonify({'error': 'Le texte ne peut pas être vide'}), 400
        
        # Analyse et réponse
        reponse = analyser_demande(texte)
        
        # Génération audio
        audio_id = generer_audio(reponse)
        
        return jsonify({
            "text": texte,
            "response": reponse,
            "audio_id": audio_id,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erreur dans /process: {e}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/audio/<audio_id>', methods=['GET'])
def obtenir_audio(audio_id):
    """Récupère un fichier audio"""
    try:
        audio_filename = f"response_{audio_id}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        
        if not os.path.exists(audio_path):
            return jsonify({"error": "Fichier audio non trouvé"}), 404
        
        return send_file(audio_path, mimetype="audio/mpeg")
        
    except Exception as e:
        logger.error(f"Erreur dans /audio: {e}")
        return jsonify({"error": "Erreur serveur"}), 500

@app.route('/solde', methods=['GET'])
def obtenir_solde():
    """API pour obtenir le solde directement"""
    try:
        user = user_database["users"]["default"]
        return jsonify({
            "solde_principal": user["solde_principal"],
            "credit_communication": user["credit_communication"],
            "internet_mb": user["internet_mb"],
            "bonus_fidelite": user["bonus_fidelite"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def check_sante():
    """Vérification de l'état du service"""
    return jsonify({
        "status": "OK",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "vosk": model is not None,
            "spacy": nlp is not None,
            "database": os.path.exists("users_data.json")
        }
    })

@app.route('/demo', methods=['GET'])
def page_demo():
    """Page de démonstration simple"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Assistant Orange Money - Démo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; }
            input[type="text"] { width: 100%; padding: 10px; margin: 10px 0; }
            button { padding: 10px 20px; background: #FF6600; color: white; border: none; cursor: pointer; }
            .response { margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧡 Assistant Orange Money</h1>
            <h3>Testez votre assistant vocal !</h3>
            
            <p><strong>Exemples de commandes :</strong></p>
            <ul>
                <li>"Quel est mon solde ?"</li>
                <li>"Envoie 5000 francs à Marie"</li>
                <li>"Recharge 2000 francs de crédit"</li>
                <li>"Achète un forfait internet de 1000 francs"</li>
                <li>"Montre mon historique"</li>
                <li>"Récupère mon bonus fidélité"</li>
            </ul>
            
            <input type="text" id="userInput" placeholder="Tapez votre message ici..." />
            <button onclick="envoyerMessage()">Envoyer</button>
            
            <div id="response" class="response" style="display:none;"></div>
            <audio id="audioPlayer" controls style="display:none; width:100%; margin-top:10px;"></audio>
        </div>
        
        <script>
            function envoyerMessage() {
                const input = document.getElementById('userInput');
                const responseDiv = document.getElementById('response');
                const audioPlayer = document.getElementById('audioPlayer');
                
                if (!input.value.trim()) return;
                
                responseDiv.innerHTML = 'Traitement en cours...';
                responseDiv.style.display = 'block';
                
                fetch('/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: input.value })
                })
                .then(response => response.json())
                .then(data => {
                    responseDiv.innerHTML = '<strong>Vous:</strong> ' + data.text + 
                                          '<br><strong>Assistant:</strong> ' + data.response;
                    
                    if (data.audio_id) {
                        audioPlayer.src = '/audio/' + data.audio_id;
                        audioPlayer.style.display = 'block';
                        audioPlayer.play();
                    }
                    
                    input.value = '';
                })
                .catch(error => {
                    responseDiv.innerHTML = 'Erreur: ' + error.message;
                });
            }
            
            document.getElementById('userInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') envoyerMessage();
            });
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    logger.info("Démarrage de l'Assistant Orange Money...")
    app.run(debug=True, host='0.0.0.0', port=5000)