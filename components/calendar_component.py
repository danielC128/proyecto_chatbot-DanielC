import datetime as dt
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import pytz
import os.path

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarManager:
    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            creds = self._get_new_credentials(creds)

        return build("calendar", "v3", credentials=creds)

    def _get_new_credentials(self, creds):
        """Reautenticación si el token ha expirado o es inválido."""
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print("Token expirado o revocado, se requiere nueva autenticación.")
                creds = self._run_authentication_flow()
        else:
            creds = self._run_authentication_flow()
        
        with open("token.json", "w") as token:
            token.write(creds.to_json())
        
        return creds

    def _run_authentication_flow(self):
        """Inicia el flujo de autenticación para obtener nuevas credenciales."""
        flow = InstalledAppFlow.from_client_secrets_file("client_secret_app_escritorio_oauth.json", SCOPES)
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow.authorization_url(prompt='consent')
        print(f"Por favor, abre este enlace en tu navegador: {auth_url}")
        
        # Después de autenticarte, obtén el código de autorización
        code = input('Introduce el código de autorización: ')
        flow.fetch_token(code=code)
        
        return flow.credentials

    def listar_horarios_disponibles(self, fecha, max_results=10):
            # Definir horarios de trabajo
            working_hours = [
                {"start": dt.time(9, 0), "end": dt.time(13, 0)},   # De 9:00 AM a 1:00 PM
                {"start": dt.time(14, 0), "end": dt.time(19, 0)}   # De 2:00 PM a 7:00 PM
            ]
            
            # Configurar zona horaria de Lima
            lima_tz = pytz.timezone('America/Lima')
            hoy = dt.datetime.now(lima_tz).date()

            # Convertir la fecha de entrada a datetime en la zona horaria de Lima
            input_date = dt.datetime.strptime(fecha, '%Y-%m-%d')
            start_of_day = lima_tz.localize(dt.datetime.combine(input_date, dt.time(0, 0)))
            end_of_day = lima_tz.localize(dt.datetime.combine(input_date, dt.time(23, 59, 59)))

            print("Rango de tiempo para disponibilidad: ", start_of_day, end_of_day.isoformat())

            # Obtener eventos existentes en Google Calendar
            events_result = self.service.events().list(
                calendarId='primary', timeMin=start_of_day.isoformat(), timeMax=end_of_day.isoformat(),
                maxResults=max_results, singleEvents=True, orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            print("Eventos existentes: ", events)

            available_slots = []
            now = dt.datetime.now(lima_tz)  # Hora actual en Lima

            for hours in working_hours:
                # Establecer el rango de trabajo para el día actual
                start_time = lima_tz.localize(dt.datetime.combine(input_date, hours["start"]))
                end_time = lima_tz.localize(dt.datetime.combine(input_date, hours["end"]))

                if input_date.date() == hoy and start_time < now:
                    # Añadir una hora y redondear hacia la siguiente hora exacta
                    now_plus_one_hour = (now + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                    start_time = max(start_time, now_plus_one_hour)            

                # Restar los eventos ocupados dentro del horario de trabajo
                for event in events:
                    event_start = dt.datetime.fromisoformat(event['start'].get('dateTime')).astimezone(lima_tz)
                    event_end = dt.datetime.fromisoformat(event['end'].get('dateTime')).astimezone(lima_tz)

                    # Si el evento interfiere con los horarios de trabajo
                    if start_time < event_end and event_start < end_time:
                        if event_start > start_time:
                            available_slots.append(f"{start_time.strftime('%Y-%m-%d %H:%M %p')} - {event_start.strftime('%Y-%m-%d %H:%M %p')}")
                        start_time = event_end

                # Si quedan intervalos disponibles después de los eventos
                if start_time < end_time:
                    available_slots.append(f"{start_time.strftime('%Y-%m-%d %H:%M %p')} - {end_time.strftime('%Y-%m-%d %H:%M %p')}")

            if not available_slots:
                print('No hay horarios disponibles.')
            else:
                print("Horarios disponibles: ", available_slots)

            return available_slots

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

    def reservar_cita(self, fecha_hora, summary="Cita reservada", timezone="America/Lima", duration_minutes=60, attendees=None):
        # Convertir la fecha y hora de inicio en un objeto datetime
        start_datetime = dt.datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")
        
        # Calcular la fecha y hora de fin sumando la duración de la cita
        end_datetime = start_datetime + dt.timedelta(minutes=duration_minutes)
        
        # Formatear las fechas y horas en el formato ISO con zona horaria
        start_time = start_datetime.isoformat()
        end_time = end_datetime.isoformat()
        
        # Llamar al método `create_event` para crear la cita en Google Calendar
        event = self.create_event(summary=summary, start_time=start_time, end_time=end_time, timezone=timezone, attendees=attendees)
        
        return event
