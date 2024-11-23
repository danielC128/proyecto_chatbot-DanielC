
from components.calendar_component import GoogleCalendarManager

calendar = GoogleCalendarManager()

#calendar.listar_calendarios()
#calendar.listar_eventos_calendario("195010dac8c1b91a8bbee7c8b9476895cc5cbf034e9d09bbf9fb7490e3f89d07@group.calendar.google.com")

#calendar.listar_horarios_disponibles('2024-11-28')

#print("=== Listar eventos del calendario ===")
#calendar.listar_eventos_calendario()


print("=== Listar horarios disponibles para el 2024-11-25 ===")
horarios = calendar.listar_horarios_disponibles("2024-11-25")
print("Horarios disponibles:", horarios)

#print("=== Listar calendarios disponibles ===")
#calendar.listar_calendarios()