import threading
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from components.twilio_component import TwilioManager
from components.openai_component import OpenAIManager
from components.calendar_component import GoogleCalendarManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from components.leader_csv_component import LeadManager
#from components.payments_component import CulqiManager

app = Flask(__name__)

# Inicializar Componentes
twilio = TwilioManager()
openai = OpenAIManager()
calendar = GoogleCalendarManager()
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()
leaderManager = LeadManager("leads/Leads_2024_10_25.csv")
#culqi = CulqiManager()

# Diccionario para almacenar temporizadores activos por cliente
timers = {}

# Función para enviar la respuesta al cliente después del retardo
def enviar_respuesta(cliente, cliente_nuevo):
    print("Enviando respuesta a:", cliente["celular"])

    # Obtener o crear cliente en MySQL
    cliente_id_mysql = dbMySQLManager.insertar_cliente(
        documento_identidad=None,
        tipo_documento=None,
        nombre=cliente["nombre"],
        apellido="",
        celular=cliente["celular"],
        email=cliente.get("email", "")
    )    
    # Obtener su estado por id
    cliente_mysql = dbMySQLManager.obtener_cliente(cliente_id_mysql)
    # Verificar si existe una conversación activa en MySQL para el cliente
    conversacion_mysql = dbMySQLManager.obtener_conversacion_activa(cliente_id_mysql)
    if not conversacion_mysql:
        # Crear conversación activa en MySQL si no existe
        conversacion_id_mysql = dbMySQLManager.insertar_conversacion(
            cliente_id=cliente_id_mysql,
            mensaje="Inicio de conversación",
            tipo_conversacion="activa",
            resultado=None,
            estado_conversacion="activa"
        )
    else:
        conversacion_id_mysql = conversacion_mysql["conversacion_id"]


    # Obtener la conversación actual del cliente
    conversation_actual = dbMongoManager.obtener_conversacion_actual(cliente["celular"])

    # Obtener el historial de conversaciones del cliente en caso tenga
    conversation_history = dbMongoManager.obtener_historial_conversaciones(cliente["celular"])

    # Hacemos un mapeo de intenciones para determinar si el chatbot necesita algo específico
    # como agendar, pagar, horarios disponibles
    intencion = openai.clasificar_intencion(conversation_actual, conversation_history)
    print("Intención detectada:", intencion)
    # Generamos un mensaje de respuesta
    print("Cliente mysql", cliente_mysql)
    intencion_list = intencion.split(")")
    if intencion_list[0] == "1":
        response_message = openai.consulta(cliente_mysql,conversation_actual, conversation_history)
    elif intencion_list[0] == "2":
        print("Fecha de la cita:", intencion_list[1].strip())
        horarios_disponibles = calendar.listar_horarios_disponibles(intencion_list[1].strip())
        print("Horarios disponibles:", horarios_disponibles)
        response_message = openai.consultaHorarios(horarios_disponibles,conversation_actual,conversation_history,intencion_list[1])
    elif intencion_list[0] == "3":
        print("Fecha y hora de la cita:", intencion_list[1].lstrip())
        reserva_cita = calendar.reservar_cita(intencion_list[1].lstrip(), summary=f"Cita reservada para {cliente['nombre']}")
        print("Cita reservada:", reserva_cita)
        response_message = openai.consultaCitareservada(reserva_cita,conversation_actual, conversation_history)
    
        # Registrar la cita en MySQL y vincularla con la conversación activa
        dbMySQLManager.insertar_cita(
            cliente_id=cliente_id_mysql,
            fecha_cita=reserva_cita["fecha"],
            motivo="Consulta de cita",
            estado_cita="agendada",
            conversacion_id=conversacion_id_mysql
        )        

    elif intencion_list[0] == "4":
        # genero link de pago con culqui
        link_pago = "https://culqi.com"
        response_message = openai.consultaPago(link_pago, conversation_actual, conversation_history)
    elif intencion_list[0] == "5":
        cliente["nombre"] = intencion_list[1].strip()
        dbMongoManager.editar_cliente_por_celular(cliente["celular"], cliente["nombre"])
        response_message = openai.consulta(cliente,conversation_actual, conversation_history)

    # Enviar respuesta al cliente
    if cliente["nombre"] == "":
        response_message = openai.consultaNombre(cliente, response_message)

    print("Response message type:", type(response_message))
    response_message = response_message.replace("Asesor: ", "").strip('"')
    twilio.send_message(cliente["celular"], response_message)

    # Guardar la respuesta en la conversación actual
    print("Response message:", response_message)
    dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)

    # Eliminar el temporizador del cliente una vez que se haya respondido
    timers.pop(cliente["celular"], None)

@app.route('/bot', methods=['POST'])
def whatsapp_bot():
    try:
        incoming_msg = request.form.get('Body').lower()
        sender = request.form.get('From')
        celular = sender.split('whatsapp:')[1]
        print("Mensaje recibido:", incoming_msg)
        print("Remitente:", celular)
        
        # Obtener cliente de la base de datos
        cliente = dbMongoManager.obtener_cliente_por_celular(celular)
        cliente_nuevo = False
        if not cliente:
            cliente_nuevo = True
            cliente = dbMongoManager.crear_cliente(nombre="",celular=celular)
            print("Cliente creado:", cliente)
        print("Cliente encontrado en la base de datos:", cliente["nombre"])

        if not dbMongoManager.hay_conversacion_activa(celular):
            # Se crea una conversacion activa, solo se crea
            print("Creando una nueva conversación activa para el cliente.")
            dbMongoManager.crear_conversacion_activa(celular)
        # Verificar si ya hay un temporizador en curso para este cliente
        if celular in timers:
            # Si ya existe un temporizador, lo cancelamos
            timers[celular].cancel()
            print("Temporizador existente cancelado para el cliente:", cliente["nombre"])
                        # Agrega la interacción del cliente a la conversación actual
            dbMongoManager.guardar_mensaje_cliente_ultima_interaccion(celular, incoming_msg)
            print("Interacción del cliente guardada en la conversación actual.")
        else:
            # Si no existe un temporizador, crear una nueva interacción
            print("Creando una nueva interacción para el cliente.")
            dbMongoManager.crear_nueva_interaccion(celular, incoming_msg)            

        # Crear un nuevo temporizador de 60 segundos antes de responder
        timer = threading.Timer(10, enviar_respuesta, args=[cliente,cliente_nuevo])
        timers[celular] = timer
        timer.start()
        print("Nuevo temporizador iniciado para el cliente:", sender)

        return 'OK', 200

    except Exception as e:
        print("Error en whatsapp_bot:", e)
        return "Error interno del servidor", 500

def iniciar_conversacion_leads():
    while True:
        print("Iniciando conversación con leeds...")
        # Obtener los leeds de la base de datos
        leeds = leaderManager.get_unanalyzed_leads(limit=10)
        for lead in leeds:
            if lead["Mobile"] == "":
                continue            
            # Buscar en la base de datos con su número de teléfono móvil
            cliente = dbMongoManager.obtener_cliente_por_celular(lead["Mobile"])
            if not cliente:
                # Si el cliente no existe, crear un nuevo cliente
                cliente = dbMongoManager.crear_cliente(lead["Record Id"],lead["Lead Name"],lead["Mobile"])
                # Crear cliente en MySQL
                cliente_id_mysql = dbMySQLManager.insertar_cliente(
                    documento_identidad=None,
                    tipo_documento=None,
                    nombre=lead["Lead Name"],
                    apellido="",
                    celular=lead["Mobile"],
                    email=lead.get("Email", None)
                )            
                print("Cliente creado:", cliente)
                # Crear conversación activa en MongoDB y MySQL
                dbMongoManager.crear_conversacion_activa(lead["Mobile"])
                conversacion_id_mysql = dbMySQLManager.insertar_conversacion(
                    cliente_id=cliente_id_mysql,
                    mensaje="Inicio de conversación por lead",
                    tipo_conversacion="activa",
                    resultado=None,
                    estado_conversacion="activa"
                )
                
                # Crear un lead en MySQL
                lead_id_mysql = dbMySQLManager.insertar_lead(
                    cliente_id=cliente_id_mysql,
                    fecha_contacto=datetime.now(),
                    prioridad_lead=lead.get("Prioridad", 1),
                    lead_source=lead.get("Lead Source", "Desconocido"),
                    campaña=lead.get("Campaña", ""),
                    canal_lead=lead.get("Canal Lead", "Desconocido"),
                    estado_lead=lead.get("Lead Status", "nuevo"),
                    notas="Lead generado automáticamente"
                )                
            else:
                print("Cliente encontrado:", cliente)

                cliente_id_mysql = dbMySQLManager.obtener_id_cliente_por_celular(lead["Mobile"])

                # Si no hay conversación activa en MySQL, crearla
                if not dbMySQLManager.obtener_conversacion_activa(cliente_id_mysql):
                    dbMongoManager.crear_conversacion_activa(lead["Mobile"])
                    dbMySQLManager.insertar_conversacion(
                        cliente_id=cliente_id_mysql,
                        mensaje="Inicio de conversación por lead",
                        tipo_conversacion="activa",
                        resultado=None,
                        estado_conversacion="activa"
                    )
                                # Crear un lead en MySQL
                lead_id_mysql = dbMySQLManager.insertar_lead(
                    cliente_id=cliente_id_mysql,
                    fecha_contacto=datetime.now(),
                    prioridad_lead=lead.get("Prioridad", 1),
                    lead_source=lead.get("Lead Source", "Desconocido"),
                    campaña=lead.get("Campaña", ""),
                    canal_lead=lead.get("Canal Lead", "Desconocido"),
                    estado_lead=lead.get("Lead Status", "nuevo"),
                    notas="Lead generado automáticamente"
                )


            # Obtener el número de teléfono móvil del lead
            mobile = lead["Mobile"]
            print("Enviando mensaje a:", mobile)
            # Obtener el nombre del lead
            resultado_lead = openai.consultaLead(lead)
            print("Response resultado_lead lead:", resultado_lead)
            estado_lead = resultado_lead.split("-")[0].strip().replace('"','')

            response_message = resultado_lead.split("-")[1].strip().replace('"','')
            twilio.send_message(mobile, response_message)
            leaderManager.update_lead(lead["Record Id"], "Analizado", "Sí")
            # Actualizar el estado del cliente segun su lead en MySQL
            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, estado_lead)                
            # Guardar la respuesta en la conversación actual
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(mobile, response_message)            
            print("Estado del lead:", estado_lead)
            print("Mensaje de respuesta:", response_message)
        #print("Todos los leads:", leeds)
        time.sleep(86400)


if __name__ == '__main__':
    # Iniciar el hilo en segundo plano para iniciar conversaciones automáticamente
    threading.Thread(target=iniciar_conversacion_leads).start()
    # Iniciar el hilo en segundo plano para verificar conversaciones inactivas
    #threading.Thread(target=verificar_conversaciones_inactivas).start()    
    # Iniciar el hilo en segundo plano para limpiar_citas_no_confirmadas
    #threading.Thread(target=limpiar_citas_no_confirmadas).start()     

    # Iniciar la aplicación Flask
    app.run(debug=True, port=5000)
