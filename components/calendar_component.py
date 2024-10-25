import datetime as dt
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarManager:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())
        return build("calendar", "v3", credentials=creds)

    def listar_horarios_disponibles(self):
        now = dt.datetime.utcnow().isoformat() + "Z"
        events_result = self.service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=10, singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return events

    def create_event(self, summary, start_time, end_time, timezone, attendees=None):
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': timezone},
            'end': {'dateTime': end_time, 'timeZone': timezone}
        }
        if attendees:
            event['attendees'] = [{"email": email} for email in attendees]
        return self.service.events().insert(calendarId="primary", body=event).execute()

    def is_time_available(self, start_time, end_time):
        time_min = start_time.isoformat() + "Z"
        time_max = end_time.isoformat() + "Z"
        events_result = self.service.events().list(
            calendarId='primary', timeMin=time_min, timeMax=time_max,
            maxResults=10, singleEvents=True, orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])
        return len(events) == 0
