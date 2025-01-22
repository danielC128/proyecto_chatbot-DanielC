import json
import threading
import time
import os
import hmac
import re
import hashlib
from datetime import datetime, timedelta
from celery_app import celery
from flask import Flask, request, jsonify
from components.twilio_component import TwilioManager
from components.openai_component import OpenAIManager
from components.calendar_component import GoogleCalendarManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from components.leader_csv_component import LeadManager
from components.zoho_component import ZohoCRMManager
from helpers.helpers import format_number, extraer_json,json_a_lista
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho

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

# Función para enviar la respuesta al cliente después del retardo
@celery.task
def enviar_respuesta(celular, cliente_nuevo, profileName):
    print("Enviando respuesta a:", celular)

    # Inicializo los componentes dentro de la tarea
    twilio = TwilioManager()
    openai = OpenAIManager()
    calendar = GoogleCalendarManager()
    dbMongoManager = DataBaseMongoDBManager()
    dbMySQLManager = DataBaseMySQLManager()

    # Recuperar el cliente desde la base de datos dentro de la tarea
    cliente = dbMongoManager.obtener_cliente_por_celular(celular)
    if not cliente:
        # Maneja el caso donde el cliente no existe
        return

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
    if cliente_mysql["nombre"] == "":
        cliente_mysql["nombre"] = profileName
        dbMySQLManager.actualizar_nombre_cliente(cliente_id_mysql, profileName)
    estado_actual = cliente_mysql['estado']
    cliente_nuevo = estado_actual=="nuevo"
    cliente_nuevo_seguimiento = estado_actual == "nuevo"
    campania = ""
    if cliente_nuevo:
        # asociarlo a la nueva campaña
        cliente_mysql["bound"] = True
        cliente_mysql["estado"] = 'seguimiento'
        dbMySQLManager.marcar_bound(cliente_id_mysql,True)
        dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, 'seguimiento')
        dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, 'seguimiento')
        campania_registro = dbMySQLManager.asociar_cliente_a_campana_mas_reciente(cliente_id_mysql) # lo asocia a la campania mas reciente que este activa
        campania = campania_registro["descripcion"] if campania_registro != None else ""  

    cliente_nuevo = cliente_mysql["bound"]
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

    print("Conversación actual:", conversation_actual)
    # Hacemos un mapeo de intenciones para determinar si el chatbot necesita algo específico
    # como agendar, pagar, horarios disponibles
    # regresariamos aqui en caso haya un error <- go to
    max_intentos = 3
    intento_actual = 0

    while intento_actual < max_intentos:
        try:
            intencion = openai.clasificar_intencion(conversation_actual, conversation_history)
            print("Intención detectada antes extraer json:", intencion)
            intencion = extraer_json(intencion)
            if intencion is not None:
                print("Intención detectada:", intencion)
                # Generamos un mensaje de respuesta
                print("Cliente mysql", cliente_mysql)
                #intencion_list = intencion.split(")")
                intencion_list = json_a_lista(intencion)
                print("Intencion lista: ", intencion_list)
                if intencion_list[0] == 1:
                    print("Ingreso a la intencion 1")                  
                    nuevo_estado = 'interesado'
                    if es_transicion_valida(estado_actual, nuevo_estado) and not cliente_nuevo_seguimiento:                           
                        cliente_mysql["estado"] = 'interesado'
                        dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)
                        dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)
                    else:
                        print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")
                    response_message = openai.consulta(cliente_mysql,conversation_actual, conversation_history,cliente_nuevo,campania)
                elif intencion_list[0] == 2:
                    if len(intencion_list) > 1:
                        print("Ingreso a la intencion 2")
                        nuevo_estado = 'interesado'
                        if es_transicion_valida(estado_actual, nuevo_estado) and not cliente_nuevo_seguimiento:
                            cliente_mysql["estado"] = 'interesado'
                            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)  
                            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)      
                        print("Fecha de la cita:", intencion_list[1].strip())
                        try:
                            horarios_disponibles = calendar.listar_horarios_disponibles(intencion_list[1].strip())
                            print("Horarios disponibles:", horarios_disponibles)
                            response_message = openai.consultaHorarios(cliente_mysql,horarios_disponibles,conversation_actual,conversation_history,intencion_list[1],cliente_nuevo,campania)
                        except Exception as e:
                            print("Error al obtener horarios disponibles:", e)
                            horarios_disponibles = []
                            response_message =  f"""{{ "mensaje": "Hubo un error al obtener los horarios disponibles. Por favor, intenta nuevamente." }}"""
                            raise Exception("Fallo en intención 2 al obtener horarios")
                    else:
                        raise Exception("Falta información en la intención 2")
                elif intencion_list[0] == 3:
                    if intencion_list[2] == "":
                        raise Exception("Falta información del nombre en la intención 3")

                    print("Ingreso a la intencion 3")             
                    print("Fecha y hora de la cita:", intencion_list[1].lstrip())
                    reserva_cita = calendar.reservar_cita(intencion_list[1].lstrip(), summary=f"Cita reservada para {cliente_mysql['nombre']}",duration_minutes=30)
                    if not reserva_cita:
                        response_message = f"""{{"mensaje": "Hubo un error al reservar la cita. Por favor, intenta nuevamente."}}"""
                    elif reserva_cita == "Horario no disponible":
                        # Comprobar si esa cita es de el mismo cliente que hace la consulta
                        cita_cliente = dbMySQLManager.buscar_cita_por_fecha_cliente(cliente_id_mysql, intencion_list[1].lstrip())
                        if cita_cliente:
                            print("Cita encontrada:", cita_cliente)
                            response_message = openai.consultaCitaDelCliente(cliente_mysql,cita_cliente,conversation_actual, conversation_history,cliente_nuevo,campania)
                        else:
                            response_message = f"""{{"mensaje": "Lo siento, el horario seleccionado no está disponible. Por favor, selecciona otro horario."}}"""
                    else:
                        nuevo_estado = 'promesas de pago'   
                        if es_transicion_valida(estado_actual, nuevo_estado) :
                            cliente_mysql["estado"] = 'promesas de pago'
                            dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)
                            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)
                        else:
                            print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")

                        print("Cita reservada:", reserva_cita)
                        response_message = openai.consultaCitareservada(cliente_mysql,reserva_cita,conversation_actual, conversation_history,cliente_nuevo,campania)
                
                        fecha_cita = datetime.fromisoformat(reserva_cita["start"]["dateTime"]).strftime('%Y-%m-%d %H:%M:%S')
                        # Registrar la cita en MySQL y vincularla con la conversación activa
                        dbMySQLManager.insertar_cita(
                            cliente_id=cliente_id_mysql,
                            fecha_cita=fecha_cita,
                            motivo="Consulta de cita",
                            estado_cita="agendada",
                            conversacion_id=conversacion_id_mysql
                        )        

                elif intencion_list[0] == 4:
                    print("Ingreso a la intencion 4")
                    # genero link de pago con culqui
                    link_pago = "https://express.culqi.com/pago/HXHKR025JY"
                    
                    nuevo_estado = 'promesas de pago'   
                    if es_transicion_valida(estado_actual, nuevo_estado):
                        cliente_mysql["estado"] = 'promesas de pago'
                        dbMySQLManager.actualizar_estado_cliente(cliente_id_mysql, nuevo_estado)
                        dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, nuevo_estado)
                    else:
                        print(f"No se actualiza el estado desde {estado_actual} a {nuevo_estado}.")
                    response_message = openai.consultaPago(cliente_mysql,link_pago, conversation_actual, conversation_history,cliente_nuevo,campania)

                elif intencion_list[0] == 5:
                    if intencion_list[1] == "":
                        raise Exception("Falta información del nombre en la intención 5")
                    print("Ingreso a la intencion 5")
                    cliente["nombre"] = intencion_list[1].strip()
                    cliente_mysql["nombre"] = intencion_list[1].strip()
                    dbMongoManager.editar_cliente_por_celular(cliente["celular"], cliente["nombre"])
                    dbMySQLManager.actualizar_nombre_cliente(cliente_id_mysql, cliente["nombre"])
                    #dbMySQLManager.
                    response_message = openai.consulta(cliente_mysql,conversation_actual, conversation_history,cliente_nuevo,campania)
                elif intencion_list[0] == 6:
                    if len(intencion_list) > 2:
                        categoria = intencion_list[1].strip()
                        detalle = intencion_list[2].strip()
                        print("Causa de no interés:", categoria)
                        if es_transicion_valida(estado_actual, 'no interesado'):
                            cliente_mysql["estado"] = 'no interesado'
                            dbMySQLManager.actualizar_estado_cliente_no_interes(cliente_id_mysql, 'no interesado', categoria, detalle)
                            dbMySQLManager.actualizar_estado_historico_cliente(cliente_id_mysql, 'no interesado')
                        else:
                            print(f"No se actualiza el estado desde {estado_actual} a no interesado.")
                        response_message = openai.consulta(cliente_mysql, conversation_actual, conversation_history,cliente_nuevo,campania)
                    else:
                        raise Exception("Falta información en la intención 6")
                
                else:
                    raise Exception("Intención no reconocida")

                # Enviar respuesta al cliente
                #if cliente["nombre"] == "":
                #    response_message = openai.consultaNombre(cliente, response_message,conversation_actual)

                print("Response message:", response_message)
                response_message = extraer_json(response_message)
                print("Response message json:", response_message)
                response_message = response_message["mensaje"]
                response_message = response_message.replace("Asesor: ", "").strip('"')
                twilio.send_message(cliente["celular"], response_message)

                # Guardar la respuesta en la conversación actual
                print("Response message:", response_message)
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())

                break
            else:
                response_message = "Lo siento, no pude entender tu mensaje. Por favor, intenta de nuevo."
                twilio.send_message(cliente["celular"], response_message)
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())
                break

        except Exception as e:
            intento_actual += 1
            print(f"Error procesando intenciones (intento {intento_actual}/{max_intentos}): {e}")
            if intento_actual == max_intentos:
                # Si llegamos al máximo de intentos, enviamos un mensaje genérico y salimos
                response_message = "Lo siento, hubo un problema al procesar tu mensaje. Por favor intenta más tarde."
                twilio.send_message(cliente["celular"], response_message)
                dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
                dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())
                break
            else:
                print("Reintentando desde la clasificación de intención...")
                # Continúa el bucle (vuelve al inicio) para intentar de nuevo

@app.route('/bot', methods=['POST'])
def whatsapp_bot():
    try:
        print("RESPUESTA DE TWILIO: ", request)
        print("RESPUESTA DE TWILIO FORM: ", request.form)
        print("RESPUESTA DE TWILIO BODY: ", request.form.get('Body'))
        print("Profile Name: ", request.form.get('ProfileName'))
        profileName = request.form.get('ProfileName')
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

        # Agrega la interacción del cliente a la conversación actual
        #dbMongoManager.guardar_mensaje_cliente_ultima_interaccion(celular, incoming_msg)
        dbMongoManager.crear_nueva_interaccion(celular, incoming_msg)
        print("Interacción del cliente guardada en la conversación actual.")         

        # Llama a la tarea de Celery con un retraso de 2 segundos
        enviar_respuesta.apply_async(args=[celular, cliente_nuevo,profileName], countdown=2)
        print("Tarea de Celery programada para el cliente:", celular)

        return 'OK', 200

    except Exception as e:
        print("Error en whatsapp_bot:", e)
        return "Error interno del servidor", 500


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

@celery.task
def procesar_culqi_webhook(data):
    try:
        # Procesar el contenido de la notificación
        evento = data.get('type')
        if evento == 'charge.creation.succeeded':  # Verifica si es el evento correcto
            charge = data.get('data', {})
            first_name = charge.get('antifraudDetails', {}).get('firstName')
            last_name = charge.get('antifraudDetails', {}).get('lastName')
            phone_number = charge.get('antifraudDetails', {}).get('phone')
            phone_number = format_number(phone_number) if phone_number else None

            if phone_number:
                cliente_id = dbMySQLManager.obtener_id_cliente_por_celular(phone_number)
                if cliente_id:
                    monto = charge.get('amount', 0) / 100  # Convertir céntimos a unidades
                    metodo_pago = "link de pago"
                    dbMySQLManager.agregar_pago_y_confirmar_cita(cliente_id, monto, metodo_pago,first_name,last_name)

                    # Actualiza Google Calendar y envía confirmación al cliente
                    cita = dbMySQLManager.obtener_cita_mas_cercana(cliente_id)
                    if cita:
                        fecha_cita = datetime.fromisoformat(cita['fecha_cita'])
                        fecha = fecha_cita.strftime("%Y-%m-%d")
                        hora_inicio = fecha_cita.strftime("%H:%M")
                        calendar.actualizar_evento_a_confirmado(fecha, hora_inicio)

                    # Enviar mensaje de confirmación
                    response_message = "¡Gracias por tu pago! Tu cita ha sido confirmada. Te esperamos."
                    twilio.send_message(phone_number, response_message)

                    # Actualizar interacción
                    fecha_actual = datetime.now()
                    dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
                    dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(phone_number, response_message)
                else:
                    print("Cliente no encontrado para el número:", phone_number)
            else:
                print("Número de teléfono no encontrado en antifraudDetails.")
        else:
            print(f"Evento no manejado: {evento}")
    except Exception as e:
        print("Error procesando webhook de Culqi:", e)

@app.route('/culqi-webhook', methods=['POST'])
def culqi_webhook():
    try:
        data = request.get_json()
        print("Notificación recibida:", data)

        # Llama a la tarea Celery para procesar la notificación
        procesar_culqi_webhook.apply_async(args=[data])

        return '', 200
    except Exception as e:
        print("Error en culqi_webhook:", e)
        return 'Error interno del servidor', 500


#@app.route('/culqi-webhook', methods=['POST'])
#def culqi_webhook():
#    try:
#        # Procesar el contenido de la notificación
#        data = request.get_json()
#        evento = data.get('type')
#        print("data : ", data)
#        
#        if evento == 'charge.creation.succeeded':  # Verifica si es el evento correcto
#            # Parsear los datos del objeto `charge` dentro de `data`
#            charge_data = data.get('data', {})
#            charge = charge_data if isinstance(charge_data, dict) else json.loads(charge_data)  # Deserializar si es string
#            
#            # Obtener el número de teléfono desde antifraudDetails
#            phone_number = charge.get('antifraudDetails', {}).get('phone')
#            phone_number = format_number(phone_number) if phone_number else None
#            if phone_number:
#                # Buscar al cliente en la base de datos por número de teléfono
#                cliente_id = dbMySQLManager.obtener_id_cliente_por_celular(phone_number)
#                if cliente_id:
#                    # Actualizar el estado del cliente a 'cita agendada'
#                    dbMySQLManager.actualizar_estado_cliente(cliente_id, 'cita agendada')
#                    
#                    # Registrar el pago y confirmar la cita
#                    monto = charge.get('amount', 0) / 100  # Culqi maneja el monto en céntimos, convertir a unidades monetarias
#                    metodo_pago = "link de pago"
#                    dbMySQLManager.agregar_pago_y_confirmar_cita(cliente_id, monto, metodo_pago)
#                    
#                    # marcar cita en calendar como  "Cita confirmada para {cliente_mysql['nombre']}"
#                    cita = dbMySQLManager.obtener_cita_mas_cercana(cliente_id)
#                    if not cita:
#                        print("No se encontró una cita para el cliente:", phone_number)
#                       # Enviar mensaje de confirmación al cliente
#                        response_message = "¡Gracias por tu pago! Tu cita ha sido confirmada. Te esperamos."
#                        twilio.send_message(phone_number, response_message)

#                        # Actualizar fechas de última interacción
#                        fecha_actual = datetime.now()
#                        dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
#                        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(phone_number, response_message)
#
#                    fecha_cita = cita['fecha_cita']  # Formato 'YYYY-MM-DD HH:MM:SS'
#
#                    # Formatear la fecha y hora para el método de confirmacion
#                    fecha = fecha_cita.strftime("%Y-%m-%d")
#                    hora_inicio = fecha_cita.strftime("%H:%M")
#
#                    print(f"Procesando cita agendada: {fecha} {hora_inicio} del cliente {cita["cliente_id"]}")
#
#                    # Llamar al método para editar el evento
#                    evento_editado = calendar.actualizar_evento_a_confirmado(fecha, hora_inicio)
#                    if evento_editado:
#                        print("Evento confirmado exitosamente.")
#                    else:
#                        print("No se encontró ningún evento en el rango especificado.")                    
#
#                    # Enviar mensaje de confirmación al cliente
#                    response_message = "¡Gracias por tu pago! Tu cita ha sido confirmada. Te esperamos."
#                    twilio.send_message(phone_number, response_message)
#
#                    # Actualizar fechas de última interacción
#                    fecha_actual = datetime.now()
#                    dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id, fecha_actual)
#                    dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(phone_number, response_message)
#                else:
#                    print("No se encontró un cliente con el número de teléfono:", phone_number)
#            else:
#                print("No se encontró el número de teléfono en antifraudDetails")
#
#        else:
#            print(f"Evento no manejado: {evento}")
#
#        return '', 200
#
#    except Exception as e:
#        print("Error en culqi_webhook:", e)
#        return 'Error interno del servidor', 500



if __name__ == '__main__':
    # Iniciar la aplicación Flask
    app.run(host='0.0.0.0',port=5000)
