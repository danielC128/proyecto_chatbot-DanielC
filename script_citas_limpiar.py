from components.calendar_component import GoogleCalendarManager
from components.database_mysql_component import DataBaseMySQLManager
from datetime import datetime
import pytz

# Inicializar los componentes
calendar = GoogleCalendarManager()
dbMySQLManager = DataBaseMySQLManager()

def eliminar_citas_agendadas():
    try:
        # Obtener todas las citas en estado "agendada" de la base de datos
        citas_agendadas = dbMySQLManager.obtener_citas_por_estado("agendada")
        
        if not citas_agendadas:
            print("No hay citas en estado 'agendada' para eliminar.")
            return

        # Configurar la zona horaria de Lima
        lima_tz = pytz.timezone("America/Lima")
        ahora = datetime.now(lima_tz)

        for cita in citas_agendadas:
            #print(cita)
            fecha_cita = cita['fecha_cita']  # Formato 'YYYY-MM-DD HH:MM:SS'
            fecha_creacion = cita['fecha_creacion']  # Formato 'YYYY-MM-DD HH:MM:SS'
            cliente_id = cita['cliente_id']
            cita_id = cita['cita_id']
            

            # Asegurar que las fechas están en la zona horaria correcta
            if fecha_cita.tzinfo is None:
                fecha_cita = lima_tz.localize(fecha_cita)
            if fecha_creacion.tzinfo is None:
                fecha_creacion = lima_tz.localize(fecha_creacion)

            # Verificar si han pasado más de 24 horas desde la fecha de creación
            diferencia_horas = (ahora - fecha_creacion).total_seconds() / 3600
            if diferencia_horas < 24:
                print(f"La cita ID: {cita_id} aún no lleva 24 horas desde su creación.")
                continue

            # Formatear la fecha y hora para el método de eliminación
            fecha = fecha_cita.strftime("%Y-%m-%d")
            hora_inicio = fecha_cita.strftime("%H:%M")

            print(f"Procesando cita agendada: {fecha} {hora_inicio} del cliente {cliente_id}")
             

            try:
                # Usar el método actualizado para eliminar la cita
                eliminada = calendar.eliminar_evento_por_rango_horario(fecha, hora_inicio)
                
                if eliminada:
                    print(f"Cita eliminada en Google Calendar: {fecha} {hora_inicio} del cliente {cliente_id}")
                    # Actualizar el estado de la cita en la base de datos
                    dbMySQLManager.actualizar_estado_cita(cita_id, "eliminada")
                else:
                    print(f"No se encontró la cita en Google Calendar: {fecha} {hora_inicio}")
            except Exception as e:
                print(f"Error al eliminar cita {cita_id}: {e}")
    except Exception as e:
        print(f"Error al procesar las citas agendadas: {e}")

if __name__ == "__main__":
    eliminar_citas_agendadas()
