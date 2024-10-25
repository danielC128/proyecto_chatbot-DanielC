import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from components.twilio_component import TwilioManager
from components.openai_component import OpenAIManager
from components.google_calendar_component import GoogleCalendarManager
from components.database_component import DatabaseManager
from components.payments_component import CulqiManager
from helpers.conversation_helpers import obtener_horarios_disponibles, clasificar_intencion, es_horario_laboral, formatear_fecha_hora

app = Flask(__name__)

# Inicializar Componentes
twilio = TwilioManager()
openai = OpenAIManager()
calendar = GoogleCalendarManager()
db = DatabaseManager()
culqi = CulqiManager()

# Diccionario para almacenar temporizadores activos por cliente
timers = {}

# Función para enviar la respuesta al cliente después del retardo
def enviar_respuesta(cliente_id, conversation_actual):
    # Aquí obtenemos el mensaje más reciente y generamos la respuesta
    response_message = openai.consult_product(conversation_actual[-1]['cliente'], conversation_actual)
    
    # Guardar la respuesta en la conversación actual
    db.guardar_interaccion_conversacion_actual(cliente_id, conversation_actual[-1]['cliente'], response_message)

    # Enviar respuesta al cliente
    twilio.send_message(cliente_id, response_message)
    
    # Eliminar el temporizador del cliente una vez que se haya respondido
    timers.pop(cliente_id, None)

@app.route('/bot', methods=['POST'])
def whatsapp_bot():
    incoming_msg = request.form.get('Body').lower()
    sender = request.form.get('From')
    
    # Obtener cliente de la base de datos
    cliente = db.obtener_cliente_por_celular(sender)
    if not cliente:
        return "Cliente no encontrado", 404

    nombre_cliente = cliente['Nombre']
    celular_cliente = cliente['Celular']

    # Obtener la conversación actual del cliente
    conversation_actual = db.obtener_conversacion_actual(sender)
    
    conversation_history = db.obtener_conversaciones_completas(sender)

    # Clasificar intención
    intencion = openai.clasificar_intencion(incoming_msg, conversation_actual)
    
    # Intención "dudas, consultas, etc." -> pasamos el mensaje del cliente, la conversación actual y el historial para obtener una respuesta.
    if intencion == "cliente tiene dudas, consultas u otros":
        response_message = openai.consult_product(incoming_msg, conversation_actual)

    elif intencion == "agendar una cita sin fecha":
        # Aquí se manejarían las fechas disponibles.
        pass

    elif intencion == "agendar una cita con fecha":
        user_date_str, user_time_str = openai.extract_datetime(incoming_msg)
        if user_date_str and user_time_str:
            user_date = datetime.strptime(user_date_str, '%Y-%m-%d').date()
            user_time = datetime.strptime(user_time_str, '%H:%M').time()
            if es_horario_laboral(user_date, user_time):
                provisional_message = calendar.schedule_appointment(user_date_str, user_time_str, nombre_cliente, celular_cliente)
                response_message = provisional_message + " Ahora, completa el pago para confirmar la cita: " + culqi.generar_enlace_pago(5000, "PEN", "Cita provisional", cliente['Email'])
            else:
                response_message = "No atendemos en ese horario. Consulta los horarios disponibles."

    # Guardar el nuevo mensaje en la conversación actual
    db.guardar_interaccion_conversacion_actual(sender, incoming_msg, None)  # Guardamos la interacción sin respuesta todavía

    # Verificar si ya hay un temporizador en curso para este cliente
    if sender in timers:
        # Si ya existe un temporizador, lo cancelamos
        timers[sender].cancel()

    # Crear un nuevo temporizador de 60 segundos antes de responder
    timer = threading.Timer(60, enviar_respuesta, args=[sender, conversation_actual])
    timers[sender] = timer
    timer.start()

    return 'OK', 200

@app.route('/culqi/webhook', methods=['POST'])
def recibir_confirmacion_pago():
    data = request.json
    if data['object']['state'] == 'paid':
        client_email = data['object']['client_details']['email']

        # Confirmar la cita provisional
        cita = db.obtener_cita_no_confirmada_por_email(client_email)
        if cita:
            calendar.confirmar_cita(client_email, cita['fecha'], cita['hora'])

            # Mensaje de confirmación
            confirmation_message = "¡Pago recibido! Tu cita ha sido confirmada para el día " + cita['fecha'] + " a las " + cita['hora'] + "."

            # Enviar el mensaje al cliente
            twilio.send_message(f"whatsapp:+{client_email}", confirmation_message)

            # Guardar la confirmación en la conversación actual
            db.guardar_interaccion_conversacion_actual(client_email, "Pago completado", confirmation_message)
            
            # Eliminar la cita provisional
            db.eliminar_cita_no_confirmada(client_email)
    
    return "Webhook recibido", 200


# Tarea en segundo plano para iniciar conversaciones con leads no contactados
def iniciar_conversacion_automaticamente():
    while True:
        print("Iniciando conversación con leads no contactados...")
        # Obtener leads no contactados y enviar mensajes
        leads_no_contactados = db.obtener_leads_no_contactados()
        if leads_no_contactados:
            for lead in leads_no_contactados:
                nombre = lead['Nombre']
                celular = lead['Celular']
                
                # Crear mensaje proactivo
                mensaje = f"Hola {nombre}, soy parte del equipo de Trasplante Capilar. ¿Tienes alguna duda sobre nuestros tratamientos o prefieres agendar una cita?"
                
                # Enviar el mensaje usando Twilio
                twilio.send_message(f"whatsapp:+{celular}", mensaje)
                
                # Marcar el lead como contactado
                db.marcar_lead_contactado(lead['_id'])
                
                # Guardar el mensaje en el historial
                db.guardar_conversacion(lead['_id'], "Mensaje enviado por chatbot", mensaje)
        
        # Esperar 24 horas antes de revisar nuevamente (86400 segundos)
        time.sleep(86400)

# Tarea en segundo plano para verificar conversaciones inactivas
def verificar_conversaciones_inactivas():
    while True:
        print("Verificando conversaciones inactivas...")
        # Obtener todas las conversaciones activas
        conversaciones_activas = db.obtener_conversaciones_activas()
        ahora = datetime.utcnow()

        for conversacion in conversaciones_activas:
            # Verificar si la última interacción fue hace más de 24 horas
            ultima_interaccion = conversacion['ultima_interaccion']
            if ahora - ultima_interaccion > timedelta(hours=24):
                # Marcar la conversación como completa y moverla al historial
                db.mover_conversacion_a_historial(conversacion['_id'])
        
        # Esperar 1 hora antes de volver a verificar (3600 segundos)
        time.sleep(3600)        

def limpiar_citas_no_confirmadas():
    while True:
        print("Limpiando citas no confirmadas...")
        # Eliminar citas no confirmadas que tengan más de 2 horas
        db.eliminar_citas_no_confirmadas_antiguas(2)
        
        # Esperar 2 horas antes de la siguiente limpieza
        time.sleep(7200)


if __name__ == '__main__':
    # Iniciar el hilo en segundo plano para iniciar conversaciones automáticamente
    threading.Thread(target=iniciar_conversacion_automaticamente).start()
    # Iniciar el hilo en segundo plano para verificar conversaciones inactivas
    threading.Thread(target=verificar_conversaciones_inactivas).start()    
    # Iniciar el hilo en segundo plano para limpiar_citas_no_confirmadas
    threading.Thread(target=limpiar_citas_no_confirmadas).start()     

    # Iniciar la aplicación Flask
    app.run(debug=True, port=5000)
