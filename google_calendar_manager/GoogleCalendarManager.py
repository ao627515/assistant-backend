from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class GoogleCalendarManager:
    def __init__(self, credentials_file='credentials.json', token_file='token.pickle'):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Authentification avec Google Calendar API"""
        creds = None

        # Le fichier token.pickle stocke les tokens d'accès et de rafraîchissement de l'utilisateur
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # Si il n'y a pas de credentials valides disponibles, laissez l'utilisateur se connecter
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Sauvegarde des credentials pour la prochaine exécution
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("Authentification Google Calendar réussie")

    def create_event(self, title, start_datetime, end_datetime, description="", location=""):
        """
        Crée un événement dans Google Calendar

        Args:
            title (str): Titre de l'événement
            start_datetime (datetime): Date et heure de début
            end_datetime (datetime): Date et heure de fin
            description (str): Description de l'événement
            location (str): Lieu de l'événement

        Returns:
            dict: Informations de l'événement créé ou None si erreur
        """
        try:
            # Format de l'événement pour Google Calendar
            event = {
                'summary': title,
                'location': location,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': 'Europe/Paris',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'Europe/Paris',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 60},  # Email 1h avant
                        {'method': 'popup', 'minutes': 15},  # Popup 15min avant
                    ],
                },
            }

            # Création de l'événement
            event_result = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()

            logger.info(f"Événement créé: {event_result.get('htmlLink')}")

            return {
                'id': event_result.get('id'),
                'link': event_result.get('htmlLink'),
                'status': 'created'
            }

        except HttpError as error:
            logger.error(f"Erreur lors de la création de l'événement: {error}")
            return None

    def create_appointment_from_analysis(self, analysis_result, default_duration_hours=1):
        """
        Crée un rendez-vous basé sur l'analyse NLP

        Args:
            analysis_result (dict): Résultat de l'analyse NLP
            default_duration_hours (int): Durée par défaut en heures

        Returns:
            dict: Résultat de la création ou message d'erreur
        """
        if not analysis_result['is_appointment']:
            return {'error': 'Ce n\'est pas une demande de rendez-vous'}

        try:
            # Construction de la date et heure de début
            date_str = str(analysis_result['date'])
            time_str = analysis_result['time']
            start_datetime_str = f"{date_str} {time_str}"
            start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")

            # Calcul de la fin (durée par défaut)
            end_datetime = start_datetime + timedelta(hours=default_duration_hours)

            # Titre de l'événement
            title = f"{analysis_result['appointment_type'].capitalize()}"
            if 'affaire' in analysis_result['description']:
                title += " d'affaires"

            # Création de l'événement
            result = self.create_event(
                title=title,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                description=f"Créé automatiquement depuis: {analysis_result['description']}"
            )

            if result:
                return {
                    'success': True,
                    'message': f"Rendez-vous programmé le {analysis_result['date']} à {analysis_result['time']}",
                    'event_id': result['id'],
                    'calendar_link': result['link'],
                    'reminder_time': analysis_result['reminder_time']
                }
            else:
                return {'error': 'Erreur lors de la création du rendez-vous'}

        except Exception as e:
            logger.error(f"Erreur lors de la création du rendez-vous: {e}")
            return {'error': f'Erreur: {str(e)}'}

    def list_upcoming_events(self, max_results=10):
        """Liste les prochains événements"""
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            return events

        except HttpError as error:
            logger.error(f"Erreur lors de la récupération des événements: {error}")
            return []

    def delete_event(self, event_id):
        """Supprime un événement"""
        try:
            self.service.events().delete(
                calendarId='primary',
                eventId=event_id
            ).execute()

            return {'success': True, 'message': 'Événement supprimé'}

        except HttpError as error:
            logger.error(f"Erreur lors de la suppression: {error}")
            return {'error': 'Erreur lors de la suppression'}


# Exemple d'utilisation
if __name__ == "__main__":
    # Test du gestionnaire Google Calendar
    calendar_manager = GoogleCalendarManager()

    # Exemple d'analyse
    analysis_example = {
        'is_appointment': True,
        'appointment_type': 'rendez-vous',
        'date': datetime.now().date() + timedelta(days=1),
        'time': '15:00',
        'description': 'rendez-vous d\'affaire demain à 15h',
        'reminder_time': datetime.now() + timedelta(days=1, hours=14),
        'confidence': 100
    }

    # Création du rendez-vous
    result = calendar_manager.create_appointment_from_analysis(analysis_example)
    print(f"Résultat: {result}")