import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from components.twilio_component import TwilioManager
from components.openai_component import OpenAIManager
from components.calendar_component import GoogleCalendarManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
#from components.payments_component import CulqiManager

app = Flask(__name__)

# Inicializar Componentes
twilio = TwilioManager()
#openai = OpenAIManager()
#calendar = GoogleCalendarManager()
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()
#culqi = CulqiManager()

# Diccionario para almacenar temporizadores activos por cliente
timers = {}

# Función para enviar la respuesta al cliente después del retardo
def enviar_respuesta(cliente):
    print("Enviando respuesta a:", cliente.celular)
    # Obtener la conversación actual del cliente
    conversation_actual = dbMongoManager.obtener_conversacion_actual(cliente.celular)

    # Obtener el historial de conversaciones del cliente en caso tenga
    conversation_history = dbMongoManager.obtener_historial_conversaciones(cliente.celular)

    # Generamos un mensaje de respuesta
    response_message = "Hola"

    # Enviar respuesta al cliente
    twilio.send_message(cliente.celular, response_message)

    # Guardar la respuesta en la conversación actual
    dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente.celular, response_message)
    
    # Eliminar el temporizador del cliente una vez que se haya respondido
    timers.pop(cliente.celular, None)

@app.route('/bot', methods=['POST'])
def whatsapp_bot():
    try:
        incoming_msg = request.form.get('Body').lower()
        sender = request.form.get('From')
        print("Mensaje recibido:", incoming_msg)
        print("Remitente:", sender)
        
        # Obtener cliente de la base de datos
        cliente = dbMongoManager.obtener_cliente_por_celular(sender)
        if not cliente:
            print("Cliente no encontrado en la base de datos para el número:", sender)
            return "Cliente no encontrado", 404
        print("Cliente encontrado en la base de datos:", cliente)

        # Verificar si ya hay un temporizador en curso para este cliente
        if sender in timers:
            # Si ya existe un temporizador, lo cancelamos
            timers[sender].cancel()
            print("Temporizador existente cancelado para el cliente:", sender)

            # Agrega la interacción del cliente a la conversación actual
            dbMongoManager.guardar_mensaje_cliente_ultima_interaccion(sender, incoming_msg)
            print("Interacción del cliente guardada en la conversación actual.")

        # Crear un nuevo temporizador de 60 segundos antes de responder
        timer = threading.Timer(60, enviar_respuesta, args=[cliente])
        timers[sender] = timer
        timer.start()
        print("Nuevo temporizador iniciado para el cliente:", sender)

        return 'OK', 200

    except Exception as e:
        print("Error en whatsapp_bot:", e)
        return "Error interno del servidor", 500


@app.route('/test', methods=['GET'])
def test_endpoint():
    return "Ruta de prueba funcionando."


if __name__ == '__main__':
    # Iniciar el hilo en segundo plano para iniciar conversaciones automáticamente
    #threading.Thread(target=iniciar_conversacion_automaticamente).start()
    # Iniciar el hilo en segundo plano para verificar conversaciones inactivas
    #threading.Thread(target=verificar_conversaciones_inactivas).start()    
    # Iniciar el hilo en segundo plano para limpiar_citas_no_confirmadas
    #threading.Thread(target=limpiar_citas_no_confirmadas).start()     

    # Iniciar la aplicación Flask
    app.run(debug=True, port=5000)
