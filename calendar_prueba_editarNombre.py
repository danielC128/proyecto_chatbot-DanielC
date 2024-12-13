from datetime import datetime
from components.calendar_component import GoogleCalendarManager
from components.database_mysql_component import DataBaseMySQLManager

# Inicializar el gestor de calendario
calendar = GoogleCalendarManager()
dbMySQL = DataBaseMySQLManager()
# Datos del evento a eliminar
#fecha = "2024-12-12"
#hora_inicio = "14:00"

cita = dbMySQL.obtener_cita_mas_cercana(6)

fecha_cita = cita['fecha_cita']  # Formato 'YYYY-MM-DD HH:MM:SS'

# Formatear la fecha y hora para el método de eliminación
fecha = fecha_cita.strftime("%Y-%m-%d")
hora_inicio = fecha_cita.strftime("%H:%M")

print(f"Procesando cita agendada: {fecha} {hora_inicio} del cliente {cita["cliente_id"]}")

# Llamar al método para editar el evento
evento_editado = calendar.actualizar_evento_a_confirmado(fecha, hora_inicio)
if evento_editado:
    print("Evento confirmado exitosamente.")
else:
    print("No se encontró ningún evento en el rango especificado.")
