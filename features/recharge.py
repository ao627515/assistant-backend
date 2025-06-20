import re
from venv import logger


def recharge(text,user_state):
  logger.info("Détection : recharge")

  match = re.search(r"(recharge[r]?|recharger|créditer)[^\d]*(\d+)", text.lower())
  if match:
      action, amount_str = match.groups()
      amount = int(amount_str)
      if amount > user_state["wallet_balance"]:
          return f"Solde insuffisant pour recharger {amount} francs."
      user_state["wallet_balance"] -= amount
      user_state["credit_balance"] += amount
      return (
          f"Très bien, je {action} {amount} francs. "
          f"Crédit : {user_state['credit_balance']} francs, "
          f"solde restant : {user_state['wallet_balance']} francs."
      )

  amount = re.search(r"\d+", text)
  if amount:
      amount = int(amount.group())
      if amount > user_state["wallet_balance"]:
          return f"Solde insuffisant pour recharger {amount} francs."
      user_state["wallet_balance"] -= amount
      user_state["credit_balance"] += amount
      return (
          f"Très bien, je recharge {amount} francs. "
          f"Crédit : {user_state['credit_balance']} francs, "
          f"solde restant : {user_state['wallet_balance']} francs."
      )

  return "Quel montant souhaitez-vous recharger ?"