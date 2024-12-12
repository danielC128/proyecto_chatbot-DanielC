from datetime import datetime
from components.calendar_component import GoogleCalendarManager

# Inicializar el gestor de calendario
calendar = GoogleCalendarManager()

# Datos del evento a eliminar
fecha = "2024-12-08"
hora_inicio = "19:30"

# Llamar al método para eliminar el evento
evento_eliminado = calendar.eliminar_evento_por_rango_horario(fecha, hora_inicio)
if evento_eliminado:
    print("Evento eliminado exitosamente.")
else:
    print("No se encontró ningún evento en el rango especificado.")
