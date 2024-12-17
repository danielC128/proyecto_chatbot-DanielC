from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from components.twilio_component import TwilioManager
from datetime import datetime
import pytz
import locale

# Configurar el idioma local a español
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

# Inicializar los componentes
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()
twilio = TwilioManager()

# Función auxiliar para formatear la hora con AM/PM
def formatear_hora(fecha):
    hora = fecha.hour
    minuto = fecha.minute
    if hora >= 12:
        periodo = "p.m."
        hora = hora - 12 if hora > 12 else hora
    else:
        periodo = "a.m."
        hora = 12 if hora == 0 else hora
    return f"{hora:02}:{minuto:02} {periodo}"

def primer_aviso_citas_agendadas():
    try:
        # Obtener todas las citas en estado "agendada" de la base de datos
        citas_agendadas = dbMySQLManager.obtener_citas_por_estado_con_numero("agendada")
        
        # Filtrar las citas donde 'aviso' está en 0
        citas_sin_aviso = [cita for cita in citas_agendadas if cita.get('aviso') == 0]

        if not citas_sin_aviso:
            print("No hay citas en estado 'agendada' para dar primer aviso.")
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
            nombre_cliente = cita['nombre']
            if nombre_cliente == None:
                nombre_cliente = ""

            # Asegurar que las fechas están en la zona horaria correcta
            if fecha_cita.tzinfo is None:
                fecha_cita = lima_tz.localize(fecha_cita)
            if fecha_creacion.tzinfo is None:
                fecha_creacion = lima_tz.localize(fecha_creacion)

            # Verificar si han pasado más de 24 horas desde la fecha de creación
            diferencia_horas = (ahora - fecha_creacion).total_seconds() / 3600
            if diferencia_horas < 23:
                print(f"La cita ID: {cita_id} aún no lleva 24 horas desde su creación.")
                continue

            # Formatear la fecha y hora para el método de primer aviso
            fecha = fecha_cita.strftime("%Y-%m-%d")
            hora_inicio = fecha_cita.strftime("%H:%M")

            print(f"Procesando cita agendada: {fecha} {hora_inicio} del cliente {cliente_id}")
             

            try:
                
                # Formatear la fecha en un formato amigable
                fecha_amigable = fecha_cita.strftime("%A, %d de %B de %Y").capitalize()
                hora_inicio_mensaje = formatear_hora(fecha_cita)

                mensaje = (
                    f"Hola {nombre_cliente}, le recordamos que tiene una cita agendada el {fecha_amigable} a las {hora_inicio_mensaje}. "
                    f"El costo de la cita es de 60 soles. Puede pagar el total (60 soles) o adelantar 30 soles y cancelar el resto en la consulta. "
                    f"¡Por favor no olvide confirmar su cita! Gracias."
                )
                print(mensaje)
                
                # Usar el método actualizado para dar primer aviso
                twilio.send_message(celular, mensaje)
                
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, mensaje)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, datetime.now())

                dbMySQLManager.actualizar_aviso_cita(cita_id, 1) # 1 - Primer aviso
            except Exception as e:
                print(f"Error al dar el primer aviso de la  cita {cita_id}: {e}")
    except Exception as e:
        print(f"Error al procesar las citas agendadas: {e}")

if __name__ == "__main__":
    primer_aviso_citas_agendadas()
