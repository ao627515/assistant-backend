import re
from datetime import datetime, timedelta
import spacy
from dateutil import parser
from dateutil.relativedelta import relativedelta


class AppointmentAnalyzer:
    def __init__(self):
        # Dictionnaires de mots-clés
        self.time_keywords = {
            'demain': 1,
            'après-demain': 2,
            'lundi': 'monday',
            'mardi': 'tuesday',
            'mercredi': 'wednesday',
            'jeudi': 'thursday',
            'vendredi': 'friday',
            'samedi': 'saturday',
            'dimanche': 'sunday'
        }

        self.appointment_types = {
            'rendez-vous': 'rendez-vous',
            'réunion': 'réunion',
            'meeting': 'meeting',
            'entretien': 'entretien',
            'rdv': 'rendez-vous',
            'appel': 'appel téléphonique'
        }

    def analyze_appointment_request(self, text):
        """
        Analyse le texte pour extraire les informations du rendez-vous
        """
        text = text.lower().strip()

        result = {
            'is_appointment': False,
            'appointment_type': None,
            'date': None,
            'time': None,
            'description': text,
            'reminder_time': None,
            'confidence': 0
        }

        # Vérifier si c'est une demande de rendez-vous
        if self._is_appointment_request(text):
            result['is_appointment'] = True
            result['appointment_type'] = self._extract_appointment_type(text)
            result['date'] = self._extract_date(text)
            result['time'] = self._extract_time(text)
            result['reminder_time'] = self._calculate_reminder_time(result['date'], result['time'])
            result['confidence'] = self._calculate_confidence(result)

        return result

    def _is_appointment_request(self, text):
        """Vérifie si le texte contient une demande de rendez-vous"""
        keywords = ['programme', 'planifie', 'créé', 'ajoute', 'rendez-vous', 'réunion', 'rdv']
        return any(keyword in text for keyword in keywords)

    def _extract_appointment_type(self, text):
        """Extrait le type de rendez-vous"""
        for keyword, app_type in self.appointment_types.items():
            if keyword in text:
                return app_type
        return 'rendez-vous'

    def _extract_date(self, text):
        """Extrait la date du texte"""
        today = datetime.now().date()

        # Recherche de "demain", "après-demain"
        if 'demain' in text and 'après-demain' not in text:
            return today + timedelta(days=1)
        elif 'après-demain' in text:
            return today + timedelta(days=2)

        # Recherche de jours de la semaine
        for day_fr, day_en in self.time_keywords.items():
            if day_fr in text and day_en != 1 and day_en != 2:
                return self._get_next_weekday(today, day_en)

        # Recherche de dates spécifiques (format dd/mm ou dd/mm/yyyy)
        date_pattern = r'(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?'
        match = re.search(date_pattern, text)
        if match:
            day, month, year = match.groups()
            year = year or datetime.now().year
            try:
                return datetime(int(year), int(month), int(day)).date()
            except ValueError:
                pass

        return today  # Par défaut, aujourd'hui

    def _extract_time(self, text):
        """Extrait l'heure du texte"""
        # Patterns pour différents formats d'heure
        patterns = [
            r'(\d{1,2})h(\d{2})',  # 15h30
            r'(\d{1,2})h',  # 15h
            r'(\d{1,2}):(\d{2})',  # 15:30
            r'à (\d{1,2})h(\d{2})',  # à 15h30
            r'à (\d{1,2})h',  # à 15h
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    hour, minute = match.groups()
                    return f"{hour.zfill(2)}:{minute.zfill(2)}"
                else:
                    hour = match.groups()[0]
                    return f"{hour.zfill(2)}:00"

        return "14:00"  # Heure par défaut

    def _get_next_weekday(self, date, weekday_name):
        """Trouve le prochain jour de la semaine"""
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }

        target_weekday = weekdays[weekday_name]
        days_ahead = target_weekday - date.weekday()

        if days_ahead <= 0:  # Le jour cible est aujourd'hui ou dans le passé
            days_ahead += 7

        return date + timedelta(days=days_ahead)

    def _calculate_reminder_time(self, date, time):
        """Calcule l'heure du rappel (1 heure avant par défaut)"""
        if not date or not time:
            return None

        try:
            # Combine date et heure
            datetime_str = f"{date} {time}"
            appointment_datetime = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

            # Rappel 1 heure avant
            reminder_datetime = appointment_datetime - timedelta(hours=1)
            return reminder_datetime

        except ValueError:
            return None

    def _calculate_confidence(self, result):
        """Calcule le niveau de confiance de l'analyse"""
        confidence = 0

        if result['appointment_type']:
            confidence += 30
        if result['date']:
            confidence += 30
        if result['time']:
            confidence += 40

        return confidence


# Exemple d'utilisation
if __name__ == "__main__":
    analyzer = AppointmentAnalyzer()

    test_phrases = [
        "programme moi un rendez-vous d'affaire demain à 15h",
        "créé une réunion mardi à 10h30",
        "ajoute un rdv avec le client vendredi à 14h",
        "planifie un entretien le 25/12 à 9h"
    ]

    for phrase in test_phrases:
        result = analyzer.analyze_appointment_request(phrase)
        print(f"Phrase: {phrase}")
        print(f"Résultat: {result}")
        print("-" * 50)