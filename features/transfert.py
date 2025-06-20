import re
from venv import logger


def transfert(text,doc,user_state):
  logger.info("Détection : transfert ou dépôt")

  # Extrait des montants même avec ou sans "francs"/"fcfa"
  match = re.search(
      r"(dépos[ea]?|transfèr[e]?|transfert|envoi[e]?|verse|donne)[^\d]*(\d[\d\s.,]*)\s*(?:francs?|fcfa|f)?[^\w]+à\s+([\w\s]+)",
      text.lower()
  )
  if match:
      action, raw_amount, target = match.groups()
      try:
          amount = int(re.sub(r"[^\d]", "", raw_amount))  # Nettoyage montant : supprime espaces, virgules, points
      except ValueError:
          return "Je n’ai pas compris le montant à transférer."

      if amount > user_state["wallet_balance"]:
          return f"Solde insuffisant pour envoyer {amount} francs."

      user_state["wallet_balance"] -= amount
      target = target.strip().capitalize()
      return f"D'accord, je {action} {amount} francs à {target}. Il vous reste {user_state['wallet_balance']} francs."

  # Fallback spaCy + montant simple
  amount_match = re.search(r"\d[\d\s.,]*\s*(?:francs?|fcfa|f)?", text.lower())
  receiver = next((ent.text for ent in doc.ents if ent.label_ == "PER"), None)

  if amount_match and receiver:
      try:
          amount = int(re.sub(r"[^\d]", "", amount_match.group()))
      except ValueError:
          return "Je n’ai pas compris le montant à envoyer."

      if amount > user_state["wallet_balance"]:
          return f"Solde insuffisant pour envoyer {amount} francs."

      user_state["wallet_balance"] -= amount
      return f"D'accord, j'envoie {amount} francs à {receiver}. Il vous reste {user_state['wallet_balance']} francs."
  elif receiver:
      return f"À combien dois-je envoyer à {receiver} ?"
  else:
      return "À qui dois-je envoyer de l'argent ?"