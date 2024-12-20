from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from components.twilio_component import TwilioManager
from datetime import datetime,timedelta
import pytz

# Inicializar los componentes
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()
twilio = TwilioManager()

def primer_recordatorio_clientes_interesados():
    try:
        #Obtener todos los clientes en estado "interesado" de la base de datos
        filtro = "estado = 'interesado'"
        clientes_interesados = dbMySQLManager.obtener_clientes_por_filtro(filtro)
        

        if not clientes_interesados:
            print("No hay clientes en estado interesado para dar primer recordatorio.")
            return

        # Configurar la zona horaria de Lima
        lima_tz = pytz.timezone("America/Lima")
        ahora = datetime.now(lima_tz)


        for cliente in clientes_interesados:
            #print(cliente)
            cliente_id = cliente['cliente_id']
            fecha_ultima_interaccion = cliente['fecha_ultima_interaccion']
            celular = cliente['celular']
            nombre_cliente = cliente['nombre']
            if nombre_cliente == None:
                nombre_cliente = ""


            if fecha_ultima_interaccion == None:
                print(f"El cliente ID: {cliente_id} no tiene fecha de ultima interaccion.")
                continue

            fecha_ultima_interaccion = fecha_ultima_interaccion - timedelta(hours=5)
            # Asegurar que las fechas están en la zona horaria correcta
            if fecha_ultima_interaccion.tzinfo is None:
                fecha_ultima_interaccion = lima_tz.localize(fecha_ultima_interaccion)

            #print(f"fecha_ultima_interaccion: {fecha_ultima_interaccion}")
            # Verificar si han pasado más de 24 horas desde la fecha de creación
            diferencia_horas = (ahora - fecha_ultima_interaccion).total_seconds() / 3600
            if diferencia_horas < 23 or diferencia_horas > 46:
                print(f"El cliente ID: {cliente_id} aún no lleva 24 horas desde su ultima interacion o ya le se ha dado un recordatorio.")
                continue

            # Formatear la fecha y hora para el método de primer aviso
            fecha = fecha_ultima_interaccion.strftime("%Y-%m-%d")
            hora_inicio = fecha_ultima_interaccion.strftime("%H:%M")

            print(f"Procesando cliente interesado con ultima interacion : {fecha} {hora_inicio} del cliente {cliente_id}")
             

            try:

                mensaje = (
                    f"Hola {nombre_cliente} 😊, ¡esperamos que estés muy bien! "
                    f"Queríamos recordarte que estamos aquí para ayudarte a programar tu cita. "
                    f"¿Te gustaría agendar un horario que se ajuste a tus necesidades? "
                    f"¡Será un placer atenderte! 🙌"
                )
                #print(mensaje)
                
                # Usar el método actualizado para dar primer aviso
                twilio.send_message(celular, mensaje)
                
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, mensaje)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, datetime.now())
            except Exception as e:
                print(f"Error al dar el primer recordatorio al cliente interesado {cliente_id}: {e}")
    except Exception as e:
        print(f"Error al procesar las clientes interesados para el primer recordatorio: {e}")

if __name__ == "__main__":
    primer_recordatorio_clientes_interesados()
