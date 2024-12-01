import datetime as dt
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import pytz
import os.path

SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarManager:
    CALENDAR_ID = "195010dac8c1b91a8bbee7c8b9476895cc5cbf034e9d09bbf9fb7490e3f89d07@group.calendar.google.com"

    def __init__(self):
        self.service = self._authenticate()

    def _authenticate(self):
        """Autenticación usando una cuenta de servicio."""
        credentials = Credentials.from_service_account_file(
            "service_account_credentials.json",  # Archivo JSON descargado
            scopes=SCOPES
        )
        return build("calendar", "v3", credentials=credentials)

    def listar_eventos_calendario(self):
        """Listar eventos del calendario configurado."""
        try:
            print(f"Intentando acceder al calendario con ID: {self.CALENDAR_ID}")
            events_result = self.service.events().list(
                calendarId=self.CALENDAR_ID,
                timeMin=dt.datetime.utcnow().isoformat() + "Z",  # Desde ahora
                maxResults=10,
                singleEvents=True,
                orderBy="startTime"
            ).execute()

            events = events_result.get("items", [])
            if not events:
                print("No se encontraron eventos en este calendario.")
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(f"Evento: {event['summary']} - Inicia: {start}")
        except Exception as e:
            print(f"Error al listar eventos: {e}")

    def listar_calendarios(self):
        """Listar calendarios disponibles"""
        print("Iniciando listado de calendarios...")
        try:
            calendars = self.service.calendarList().list().execute()
            print("Calendarios encontrados:, ", calendars)
            for calendar in calendars.get('items', []):
                print(f"Calendario: {calendar['summary']}")
        except Exception as e:
            print(f"Error al listar calendarios: {e}")


    def listar_horarios_disponibles(self, fecha, max_results=10):
        """Listar horarios disponibles para una fecha."""
        lima_tz = pytz.timezone('America/Lima')
        hoy = dt.datetime.now(lima_tz).date()
        input_date = dt.datetime.strptime(fecha, '%Y-%m-%d')  # Define input_date antes de usarlo

        # Definir horarios según el día de la semana
        if input_date.weekday() in [1, 3]:  # Martes y jueves
            working_hours = [{"start": dt.time(13, 30), "end": dt.time(20, 30)}]  # 1:30 PM a 8:30 PM
        elif input_date.weekday() == 5:  # Sábados
            working_hours = [{"start": dt.time(10, 0), "end": dt.time(17, 0)}]  # 10:00 AM a 5:00 PM
        else:
            working_hours = []  # Otros días no tienen disponibilidad

        start_of_day = lima_tz.localize(dt.datetime.combine(input_date, dt.time(0, 0)))
        end_of_day = lima_tz.localize(dt.datetime.combine(input_date, dt.time(23, 59, 59)))

        print("Rango de tiempo para disponibilidad:", start_of_day, end_of_day)

        try:
            events_result = self.service.events().list(
                calendarId=self.CALENDAR_ID,
                timeMin=start_of_day.isoformat(),
                timeMax=end_of_day.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            events = events_result.get('items', [])
            print("Eventos existentes:", events)

            available_slots = []
            now = dt.datetime.now(lima_tz)  # Hora actual en Lima

            for hours in working_hours:
                start_time = lima_tz.localize(dt.datetime.combine(input_date, hours["start"]))
                end_time = lima_tz.localize(dt.datetime.combine(input_date, hours["end"]))

                if input_date.date() == hoy and start_time < now:
                    now_plus_one_hour = (now + dt.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                    start_time = max(start_time, now_plus_one_hour)

                for event in events:
                    event_start = dt.datetime.fromisoformat(event['start']['dateTime']).astimezone(lima_tz)
                    event_end = dt.datetime.fromisoformat(event['end']['dateTime']).astimezone(lima_tz)

                    if start_time < event_end and event_start < end_time:
                        if event_start > start_time:
                            available_slots.append(f"{start_time.strftime('%H:%M')} - {event_start.strftime('%H:%M')}")
                        start_time = event_end

                if start_time < end_time:
                    available_slots.append(f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}")

            if not available_slots:
                print("No hay horarios disponibles.")
            else:
                print("Horarios disponibles:", available_slots)

            return available_slots

        except Exception as e:
            print(f"Error al listar horarios disponibles: {e}")
            return []

    def create_event(self, summary, start_time, end_time, timezone="America/Lima", attendees=None):
        """Crear un evento en el calendario."""
        event = {
            'summary': summary,
            'start': {'dateTime': start_time, 'timeZone': timezone},
            'end': {'dateTime': end_time, 'timeZone': timezone}
        }
        if attendees:
            event['attendees'] = [{"email": email} for email in attendees]
        try:
            evento = self.service.events().insert(calendarId=self.CALENDAR_ID, body=event).execute()
            print(f"Evento creado: {evento['id']}")
            return evento
        except Exception as e:
            print(f"Error al crear el evento: {e}")
            return None

    def is_time_available(self, start_time, end_time):
        """Verificar si un horario está disponible."""
        try:
            # Asegurarse de que start_time y end_time estén en la zona horaria de Lima
            lima_tz = pytz.timezone("America/Lima")
            if start_time.tzinfo is None:
                start_time = lima_tz.localize(start_time)
            if end_time.tzinfo is None:
                end_time = lima_tz.localize(end_time)

            # Convertir fechas al formato ISO sin forzar UTC
            time_min = start_time.isoformat()
            time_max = end_time.isoformat()
            
            events_result = self.service.events().list(
                calendarId=self.CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=10,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            print(f"Verificando conflictos para {start_time} - {end_time}. Eventos encontrados: {len(events)}")
            return len(events) == 0
            # proximamente se implementara la verificacion de eventos
            for event in events:
                # Manejar eventos con dateTime o date
                event_start = event.get('start').get('dateTime')
                event_end = event.get('end').get('dateTime')

                # Si no hay dateTime, manejarlo como un evento de todo el día
                if not event_start or not event_end:
                    continue                
                # Obtener inicio y fin del evento existente
                event_start = dt.datetime.fromisoformat(event['start']['dateTime']).astimezone(pytz.UTC)
                event_end = dt.datetime.fromisoformat(event['end']['dateTime']).astimezone(pytz.UTC)

                # Comparar si hay solapamiento
                if not (end_time <= event_start or start_time >= event_end):
                    print(f"Conflicto detectado con evento: {event['summary']} ({event_start} - {event_end})")
                    return False

            # Si no hay conflictos, el horario está disponible
            return True
        except Exception as e:
            print(f"Error al verificar disponibilidad: {e}")
            return False

    def reservar_cita(self, fecha_hora, summary="Cita reservada", timezone="America/Lima", duration_minutes=60, attendees=None):
        """
        Reservar una cita en el calendario configurado.
        
        :param fecha_hora: Fecha y hora de inicio en formato "YYYY-MM-DD HH:MM".
        :param summary: Resumen o título de la cita.
        :param timezone: Zona horaria del evento (por defecto, "America/Lima").
        :param duration_minutes: Duración de la cita en minutos (por defecto, 60).
        :param attendees: Lista de asistentes (opcional).
        :return: El evento creado, o None si ocurre un error.
        """
        try:
            # Convertir la fecha y hora de inicio en un objeto datetime
            start_datetime = dt.datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M")

            # Calcular la fecha y hora de fin sumando la duración de la cita
            end_datetime = start_datetime + dt.timedelta(minutes=duration_minutes)

            # Verificar si el horario está disponible
            if not self.is_time_available(start_datetime, end_datetime):
                print("El horario no está disponible. Por favor, elige otro horario.")
                return "Horario no disponible"

            # Formatear las fechas y horas en el formato ISO con zona horaria
            start_time = start_datetime.isoformat()
            end_time = end_datetime.isoformat()

            # Crear el evento en el calendario configurado
            event = self.create_event(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone,
                attendees=attendees
            )

            print(f"Cita reservada exitosamente: {event['id']}")
            return event

        except Exception as e:
            print(f"Error al reservar cita: {e}")
            return None