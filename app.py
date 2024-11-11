import threading
import time
import os
import hmac
import hashlib
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from components.twilio_component import TwilioManager
from components.openai_component import OpenAIManager
from components.calendar_component import GoogleCalendarManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from components.leader_csv_component import LeadManager
from components.zoho_component import ZohoCRMManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
#from components.payments_component import CulqiManager

app = Flask(__name__)

# Inicializar Componentes
twilio = TwilioManager()
openai = OpenAIManager()
calendar = GoogleCalendarManager()
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()
leaderManager = LeadManager("leads/Leads_Prueba.csv")
zoho_manager = ZohoCRMManager(client_id_zoho, client_secret_zoho, 'http://localhost', refresh_token_zoho)
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
        email= cliente.get("email", None) or None
    )    
    # Obtener cliente por id
    cliente_mysql = dbMySQLManager.obtener_cliente(cliente_id_mysql)
    estado_actual = cliente_mysql['estado']
    dbMySQLManager.actualizar_fecha_ultima_interaccion(cliente_id_mysql, datetime.now())
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
        nuevo_estado = 'seguimiento'
        if es_transicion_valida(estado_actual, nuevo_estado):
            cliente_mysql["estado"] = 'seguimiento'
            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)
            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)
        else:
            print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")
        response_message = openai.consulta(cliente_mysql,conversation_actual, conversation_history)
    elif intencion_list[0] == "2":
        nuevo_estado = 'interesado'
        if es_transicion_valida(estado_actual, nuevo_estado):
            cliente_mysql["estado"] = 'interesado'
            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)  
            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)      
        print("Fecha de la cita:", intencion_list[1].strip())
        horarios_disponibles = calendar.listar_horarios_disponibles(intencion_list[1].strip())
        print("Horarios disponibles:", horarios_disponibles)
        response_message = openai.consultaHorarios(cliente_mysql,horarios_disponibles,conversation_actual,conversation_history,intencion_list[1])
    elif intencion_list[0] == "3":
        nuevo_estado = 'promesas de pago'   
        if es_transicion_valida(estado_actual, nuevo_estado):
            cliente_mysql["estado"] = 'promesas de pago'
            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)
            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)
        else:
            print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")             
        print("Fecha y hora de la cita:", intencion_list[1].lstrip())
        reserva_cita = calendar.reservar_cita(intencion_list[1].lstrip(), summary=f"Cita reservada para {cliente['nombre']}")
        print("Cita reservada:", reserva_cita)
        response_message = openai.consultaCitareservada(cliente_mysql,reserva_cita,conversation_actual, conversation_history)
    
        fecha_cita = datetime.fromisoformat(reserva_cita["start"]["dateTime"]).strftime('%Y-%m-%d %H:%M:%S')
        # Registrar la cita en MySQL y vincularla con la conversación activa
        dbMySQLManager.insertar_cita(
            cliente_id=cliente_id_mysql,
            fecha_cita=fecha_cita,
            motivo="Consulta de cita",
            estado_cita="agendada",
            conversacion_id=conversacion_id_mysql
        )        

    elif intencion_list[0] == "4":
        # genero link de pago con culqui
        link_pago = "https://culqi.com"
        
        nuevo_estado = 'promesas de pago'   
        if es_transicion_valida(estado_actual, nuevo_estado):
            cliente_mysql["estado"] = 'promesas de pago'
            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)
            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)
        else:
            print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")
        response_message = openai.consultaPago(cliente_mysql,link_pago, conversation_actual, conversation_history)

    elif intencion_list[0] == "5":
        cliente["nombre"] = intencion_list[1].strip()
        cliente_mysql["nombre"] = intencion_list[1].strip()
        dbMongoManager.editar_cliente_por_celular(cliente["celular"], cliente["nombre"])
        dbMySQLManager.actualizar_nombre_cliente(cliente_id_mysql, cliente["nombre"])
        #dbMySQLManager.
        response_message = openai.consulta(cliente_mysql,conversation_actual, conversation_history)
    elif intencion_list[0] == "6":
        categoria = intencion_list[1].split('-')[0].strip()
        detalle = intencion_list[1].split('-')[1].strip()
        print("Causa de no interes : ", categoria)
        if es_transicion_valida(estado_actual, 'no interesado'):
            cliente_mysql["estado"] = 'no interesado'
            dbMySQLManager.actualizar_estado_cliente_no_interes(cliente_id_mysql, 'no interesado', categoria, detalle)
            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, 'no interesado')
        else:
            print(f"No se actualiza el estado desde {estado_actual} a no interesado.")
        response_message = openai.consulta(cliente_mysql,conversation_actual, conversation_history)

    # Enviar respuesta al cliente
    if cliente["nombre"] == "":
        response_message = openai.consultaNombre(cliente, response_message)

    print("Response message type:", type(response_message))
    response_message = response_message.replace("Asesor: ", "").strip('"')
    twilio.send_message(cliente["celular"], response_message)

    # Guardar la respuesta en la conversación actual
    print("Response message:", response_message)
    dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
    dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())
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
        timer = threading.Timer(2, enviar_respuesta, args=[cliente,cliente_nuevo])
        timers[celular] = timer
        timer.start()
        print("Nuevo temporizador iniciado para el cliente:", sender)

        return 'OK', 200

    except Exception as e:
        print("Error en whatsapp_bot:", e)
        return "Error interno del servidor", 500

@app.route('/iniciar-conversacion-leads', methods=['POST'])
def iniciar_conversacion_leads():
    while True:
        print("Iniciando conversación con leads...")
        # Obtener los leeds de la base de datos
        leeds = leaderManager.get_unanalyzed_leads(limit=10)
        for lead in leeds:
            if lead["Mobile"] == "":
                continue            
            # Buscar en la base de datos con su número de teléfono móvil
            cliente = dbMongoManager.obtener_cliente_por_celular(lead["Mobile"])
            if not cliente:
                # Si el cliente no existe, crear un nuevo cliente
                cliente = dbMongoManager.crear_cliente(lead["Lead Name"],lead["Mobile"],lead["Record Id"])
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

            #creamos la interaccion en mongo
            dbMongoManager.crear_nueva_interaccion_vacia(lead["Mobile"])

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
            estado_lead = estado_lead.lower()
            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, estado_lead)                
            # Guardar la respuesta en la conversación actual
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(mobile, response_message)
            dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())            
            print("Estado del lead:", estado_lead)
            print("Mensaje de respuesta:", response_message)
        time.sleep(86400)


from datetime import datetime
import time

@app.route('/iniciar-conversacion-leads-zoho', methods=['POST'])
def iniciar_conversacion_leads_zoho():
    if os.path.exists("/tmp/iniciar_conversacion.lock"):
        print("El hilo de conversación ya está en ejecución. Saltando inicialización.")
        return
    with open("/tmp/iniciar_conversacion.lock", "w") as f:
        f.write("running")

    try:
        while True:
            print("Iniciando conversación con leads desde Zoho...")

            # Obtener leads desde ZohoCRMManager
            leads = zoho_manager.obtener_todos_los_leads(limit=10)  # Llama al método con un límite de 10 leads
            for lead in leads:
                if not lead.get("Mobile"):
                    continue

                # Buscar en la base de datos MongoDB usando el número de teléfono del lead
                cliente = dbMongoManager.obtener_cliente_por_celular(lead["Mobile"])
                if not cliente:
                    # Si el cliente no existe en MongoDB, crear nuevo cliente
                    cliente = dbMongoManager.crear_cliente(lead.get("First_Name", "") + " " + lead.get("Last_Name", ""), lead["Mobile"], lead["id"])

                    # Crear cliente en MySQL
                    cliente_id_mysql = dbMySQLManager.insertar_cliente(
                        documento_identidad=None,
                        tipo_documento=None,
                        nombre=lead.get("First_Name", ""),
                        apellido=lead.get("Last_Name", ""),
                        celular=lead["Mobile"],
                        email=lead.get("Email", None),
                        estado="contactado"
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
                else:
                    print("Cliente encontrado:", cliente)
                    cliente_id_mysql = dbMySQLManager.obtener_id_cliente_por_celular(lead["Mobile"])

                    # Verificar si ya existe una conversación activa en MySQL
                    if not dbMySQLManager.obtener_conversacion_activa(cliente_id_mysql):
                        dbMongoManager.crear_conversacion_activa(lead["Mobile"])
                        dbMySQLManager.insertar_conversacion(
                            cliente_id=cliente_id_mysql,
                            mensaje="Inicio de conversación por lead",
                            tipo_conversacion="activa",
                            resultado=None,
                            estado_conversacion="activa"
                        )


                    # Registrar el lead en MySQL
                lead_id_mysql = dbMySQLManager.insertar_lead_zoho(
                    cliente_id=cliente_id_mysql,
                    fecha_contacto=datetime.now(),
                    prioridad_lead=lead.get("Prioridad_Lead", 1),
                    lead_source=lead.get("Lead_Source", "Desconocido"),
                    campaña=lead.get("Campaing_Name", ""),
                    canal_lead=lead.get("Canal_Lead", "Desconocido"),
                    estado_lead=lead.get("Lead_Status", "nuevo").lower(),
                    notas="Lead generado automáticamente",
                    tipo_lead= lead["Tipo_de_Lead"]
                )        

                # Crear una interacción en MongoDB
                dbMongoManager.crear_nueva_interaccion_vacia(lead["Mobile"])

                # Enviar mensaje al lead usando Twilio
                mobile = lead["Mobile"]
                print("Enviando mensaje a:", mobile)
                resultado_lead = openai.consultaLeadZoho(lead)
                estado_lead = resultado_lead.split("-")[0].strip().replace('"','')
                response_message = resultado_lead.split("-")[1].strip().replace('"','')
                #twilio.send_message(mobile, response_message)
                #zoho_manager.marcar_lead_como_analizado(lead["id"])  # Ejemplo de función para actualizar estado en Zoho

                # Actualizar estado en MySQL y MongoDB
                #dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, estado_lead.lower())
                dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, estado_lead.lower())
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(mobile, response_message)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())
                print("Estado del lead:", estado_lead)
                print("Mensaje de respuesta:", response_message)

            time.sleep(86400)  # Espera 24 horas antes de procesar de nuevo
    finally:
        os.remove("/tmp/iniciar_conversacion.lock")

def verificar_estados_clientes():
    while True:
        print("Verificando estados de clientes...")
        clientes = dbMySQLManager.obtener_todos_los_clientes()
        fecha_actual = datetime.now()
        for cliente in clientes:
            if(cliente['nombre'] != "Daniel"):
                continue
            cliente_id = cliente['cliente_id']
            estado = cliente['estado']
            fecha_ultima_interaccion = cliente['fecha_ultima_interaccion']
            fecha_ultima_interaccion_bot = cliente['fecha_ultima_interaccion_bot']
            celular = cliente['celular']
            
            # Reglas basadas en el estado y las fechas de última interacción
            if estado == 'interesado':
                if fecha_ultima_interaccion is not None:
                    dias_sin_interaccion = (fecha_actual - fecha_ultima_interaccion).days
                    if dias_sin_interaccion >= 2 and dias_sin_interaccion <= 7:
                        # Enviar mensaje de seguimiento
                        conversation_actual = dbMongoManager.obtener_conversacion_actual(celular)
                        conversation_history = dbMongoManager.obtener_historial_conversaciones(celular)
                        response_message = openai.consulta(cliente, conversation_actual, conversation_history)
                        twilio.send_message(celular, response_message)
                        # Actualizar fechas de última interacción
                        dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
                        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, response_message)

            elif estado == 'promesas de pago':
                # Obtener la cita agendada para este cliente en estado 'agendada'
                cita = dbMySQLManager.obtener_cita_agendada_por_cliente(cliente_id)
                if cita:
                    fecha_agendada = cita['fecha_agendada']  # Asegúrate de tener este campo
                    horas_desde_agendada = (fecha_actual - fecha_agendada).total_seconds() / 3600

                    if horas_desde_agendada >= 48:
                        # Cancelar la cita
                        dbMySQLManager.actualizar_estado_cita(cita['cita_id'], 'cancelada')
                        # Actualizar el estado del cliente a 'seguimiento' o 'inactivo'
                        nuevo_estado = 'seguimiento'
                        if es_transicion_valida(estado, nuevo_estado):
                            dbMySQLManager.actualizar_estado_cliente(cliente_id, nuevo_estado)
                        else:
                            print(f"No se actualiza el estado desde {estado} a {nuevo_estado}.")
                        # Notificar al cliente sobre la cancelación
                        response_message = "Estimado cliente, su cita ha sido cancelada debido a la falta de pago en el tiempo establecido. Si desea reprogramar, por favor contáctenos."
                        twilio.send_message(celular, response_message)
                        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, response_message)
                        dbMySQLManager.actualizar_fecha_ultima_interaccion(cliente_id, fecha_actual)
                        dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)

                    elif horas_desde_agendada >= 24 and horas_desde_agendada < 48:
                        # Enviar recordatorio de pago si no se ha enviado ya
                        if fecha_ultima_interaccion_bot is not None:
                            horas_desde_ultima_interaccion_bot = (fecha_actual - fecha_ultima_interaccion_bot).total_seconds() / 3600
                            if horas_desde_ultima_interaccion_bot >= 24:
                                # Enviar recordatorio de pago
                                link_pago = "https://culqi.com"  # Genera el link de pago real si es necesario
                                conversation_actual = dbMongoManager.obtener_conversacion_actual(celular)
                                conversation_history = dbMongoManager.obtener_historial_conversaciones(celular)
                                response_message = openai.consultaPago(cliente, link_pago, conversation_actual, conversation_history)
                                twilio.send_message(celular, response_message)
                                # Actualizar fechas de última interacción
                                dbMySQLManager.actualizar_fecha_ultima_interaccion(cliente_id, fecha_actual)
                                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
                                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, response_message)
                else:
                    # Si no hay cita agendada, puedes decidir cómo manejarlo
                    pass

            elif estado == 'seguimiento':
                if fecha_ultima_interaccion is not None:
                    dias_sin_interaccion = (fecha_actual - fecha_ultima_interaccion).days
                    if dias_sin_interaccion >= 7 and dias_sin_interaccion <= 30:
                        # Enviar mensaje de seguimiento
                        conversation_actual = dbMongoManager.obtener_conversacion_actual(celular)
                        conversation_history = dbMongoManager.obtener_historial_conversaciones(celular)
                        response_message = openai.consulta(cliente, conversation_actual, conversation_history)
                        twilio.send_message(celular, response_message)
                        # Actualizar fechas de última interacción
                        dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
                        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, response_message)

            # Regla para clientes inactivos
            if fecha_ultima_interaccion is not None:
                dias_sin_interaccion = (fecha_actual - fecha_ultima_interaccion).days
                if dias_sin_interaccion >= 30 and estado not in ['cita agendada', 'promesas de pago']:
                    # Cambiar estado a 'inactivo'
                    nuevo_estado = 'inactivo'
                    if es_transicion_valida(estado, nuevo_estado):
                        dbMySQLManager.actualizar_estado_cliente(cliente_id, nuevo_estado)
                        # Finalizar conversaciones activas
                        dbMongoManager.finalizar_conversacion_activa(celular)
                        dbMySQLManager.finalizar_conversacion_activa(cliente_id)

        # Esperar un tiempo antes de la siguiente verificación (ejemplo: 1 hora)
        time.sleep(3600)

def es_transicion_valida(estado_actual, nuevo_estado):
    prioridad_estados = {
        'pendiente de contacto': 1,
        'seguimiento': 2,
        'interesado': 3,
        'promesas de pago': 4,
        'cita agendada': 5,
        'finalizado': 6,
        'no interesado': 0,
        'inactivo': 0
    }
    if estado_actual== 'no interesado' and nuevo_estado == 'no interesado':
        return True

    if nuevo_estado == estado_actual:
        return False  # No hay cambio de estado

    # Permitir avanzar a un estado de mayor prioridad
    if prioridad_estados.get(nuevo_estado, -1) > prioridad_estados.get(estado_actual, -1):
        return True

    # Permitir transiciones específicas desde 'finalizado' a ciertos estados
    if estado_actual == 'finalizado' and nuevo_estado in ['seguimiento', 'interesado']:
        return True  # Permitir volver a 'seguimiento' o 'interesado' desde 'finalizado'

    # Permitir transiciones a 'no interesado' o 'inactivo' solo desde 'seguimiento' o 'interesado'
    if estado_actual in ['seguimiento', 'interesado'] and nuevo_estado in ['no interesado', 'inactivo']:
        return True  # Permitir cambiar a 'no interesado' o 'inactivo' desde 'seguimiento' o 'interesado'

    return False  # No permitir otras transiciones


def obtener_cliente_id_por_charge(charge):
    # Supongamos que usas 'metadata' para guardar el 'cliente_id'
    cliente_id = charge.get('metadata', {}).get('cliente_id')
    return cliente_id

def verificar_citas_pasadas():
    while True:
        print("Verificando citas pasadas...")
        fecha_actual = datetime.now()
        citas_pasadas = dbMySQLManager.obtener_citas_pasadas(fecha_actual)
        for cita in citas_pasadas:
            cita_id = cita['cita_id']
            cliente_id = cita['cliente_id']
            fecha_cita = cita['fecha_cita']
            estado_cita = cita['estado_cita']

            # Por ahora asumimos que la cita se completó
            dbMySQLManager.actualizar_estado_cita(cita_id, 'completada')

            # Actualizar el estado del cliente a 'finalizado'
            nuevo_estado = 'finalizado'
            estado_actual = dbMySQLManager.obtener_estado_cliente(cliente_id)
            if es_transicion_valida(estado_actual, nuevo_estado):
                dbMySQLManager.actualizar_estado_cliente(cliente_id, nuevo_estado)
            else:
                print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")

            # Enviar mensaje de agradecimiento al cliente
            cliente = dbMySQLManager.obtener_cliente(cliente_id)
            response_message = "Esperamos que tu cita haya sido satisfactoria. ¡Gracias por confiar en nosotros!"
            twilio.send_message(cliente['celular'], response_message)
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente['celular'], response_message)
            dbMySQLManager.actualizar_fecha_ultima_interaccion(cliente_id, fecha_actual)
            dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)

        # Esperar antes de la siguiente verificación (ejemplo: cada hora)
        time.sleep(3600)


@app.route('/culqi-webhook', methods=['POST'])
def culqi_webhook():
    try:
        # Obtener el cuerpo de la solicitud y los headers
        request_body = request.data
        signature = request.headers.get('X-Culqi-Signature')
        secret = 'TU_SECRETO_DE_WEBHOOK'  # Reemplaza con tu secreto de webhook de Culqi

        # Verificar la firma de la notificación
        computed_signature = hmac.new(
            bytes(secret, 'utf-8'),
            msg=request_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_signature, signature):
            print("Firma inválida")
            return 'Firma inválida', 400

        # Procesar el contenido de la notificación
        data = request.get_json()
        evento = data.get('type')
        if evento == 'charge.succeeded':
            charge = data.get('data', {}).get('object', {})
            # Obtener el ID del cliente o referencia desde el cargo
            cliente_id = obtener_cliente_id_por_charge(charge)
            if cliente_id:
                # Actualizar el estado del cliente a 'cita agendada'
                dbMySQLManager.actualizar_estado_cliente(cliente_id, 'cita agendada')

                # Opcionalmente, enviar mensaje de confirmación al cliente
                cliente = dbMySQLManager.obtener_cliente(cliente_id)
                response_message = "¡Gracias por tu pago! Tu cita ha sido confirmada. Te esperamos."
                twilio.send_message(cliente['celular'], response_message)

                # Actualizar fechas de última interacción
                fecha_actual = datetime.now()
                dbMySQLManager.actualizar_fecha_ultima_interaccion(cliente_id, fecha_actual)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente['celular'], response_message)
            else:
                print("No se encontró el cliente_id en el cargo")
        else:
            print(f"Evento no manejado: {evento}")

        return '', 200

    except Exception as e:
        print("Error en culqi_webhook:", e)
        return 'Error interno del servidor', 500

@app.route('/health', methods=['GET'])
def health_check():
    return '', 200


def start_background_threads():
    # Iniciar el hilo en segundo plano para iniciar conversaciones automáticamente
    # threading.Thread(target=iniciar_conversacion_leads).start()
    # Iniciar el hilo en segundo plano para verificar conversaciones inactivas
    threading.Thread(target=iniciar_conversacion_leads_zoho).start()
    # Iniciar el hilo en segundo plano para limpiar citas no confirmadas
    # threading.Thread(target=limpiar_citas_no_confirmadas).start()
    # Iniciar otro hilo, si es necesario
    # threading.Thread(target=verificar_estados_clientes).start()

start_background_threads()

if __name__ == '__main__':
    # Iniciar la aplicación Flask
    app.run(host='0.0.0.0',port=5000)
