from components.database_mysql_component import DataBaseMySQLManager
from datetime import datetime
import pytz

# Inicializar los componentes
dbMySQLManager = DataBaseMySQLManager()

def segundo_aviso_citas_agendadas():
    try:
        # Obtener todas las citas en estado "agendada" de la base de datos
        citas_agendadas = dbMySQLManager.obtener_citas_por_estado_con_numero("agendada")
        
        # Filtrar las citas donde 'aviso' está en 1
        citas_sin_aviso = [cita for cita in citas_agendadas if cita.get('aviso') == 1]

        if not citas_sin_aviso:
            print("No hay citas en estado 'agendada' para dar segundo aviso.")
            return

        # Configurar la zona horaria de Lima
        lima_tz = pytz.timezone("America/Lima")
        ahora = datetime.now(lima_tz)

        for cita in citas_sin_aviso:
            #print(cita)
            fecha_cita = cita['fecha_cita']  # Formato 'YYYY-MM-DD HH:MM:SS'
            fecha_creacion = cita['fecha_creacion']  # Formato 'YYYY-MM-DD HH:MM:SS'
            cliente_id = cita['cliente_id']
            cita_id = cita['cita_id']
            celular = cita['celular']
            

            # Asegurar que las fechas están en la zona horaria correcta
            if fecha_cita.tzinfo is None:
                fecha_cita = lima_tz.localize(fecha_cita)
            if fecha_creacion.tzinfo is None:
                fecha_creacion = lima_tz.localize(fecha_creacion)

            # Verificar si han pasado más de 24 horas desde la fecha de creación
            diferencia_horas = (ahora - fecha_creacion).total_seconds() / 3600
            if diferencia_horas < 46:
                print(f"La cita ID: {cita_id} aún no lleva 46 horas desde su creación.")
                continue

            # Formatear la fecha y hora para el método de primer aviso
            fecha = fecha_cita.strftime("%Y-%m-%d")
            hora_inicio = fecha_cita.strftime("%H:%M")

            print(f"Procesando cita agendada: {fecha} {hora_inicio} del cliente {cliente_id}")
             

            try:
                
                dbMySQLManager.actualizar_aviso_cita(cita_id, 2) # 2 - Segundo aviso
            except Exception as e:
                print(f"Error al dar el segundo aviso de la  cita {cita_id}: {e}")
    except Exception as e:
        print(f"Error al procesar las citas agendadas: {e}")

if __name__ == "__main__":
    segundo_aviso_citas_agendadas()
