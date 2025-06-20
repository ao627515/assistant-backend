def checkBalance(user_state):
    return (
        f"Votre solde est de {user_state['wallet_balance']} francs "
        f"et votre crédit téléphonique est de {user_state['credit_balance']} francs."
    )
