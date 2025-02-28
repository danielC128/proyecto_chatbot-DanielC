import json
import threading
import time
import os
import hmac
import re
import hashlib
import redis
from datetime import datetime, timedelta
from celery_app import celery
from flask import Flask, request, jsonify
from components.twilio_component import TwilioManager
from components.openai_component import OpenAIManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from components.database_bigquery_component import DataBaseBigQueryManager
from helpers.helpers import format_number, extraer_json,json_a_lista
#from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from celery_app import celery

r = redis.Redis(host='localhost', port=6379, db=0)

app = Flask(__name__)

# Inicializar Componentes
twilio = TwilioManager()
openai = OpenAIManager()
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()
dbBigQueryManager = DataBaseBigQueryManager()

def get_scheduled_task_id(celular):
    """Devuelve el ID de la tarea pendiente para este celular, o None."""
    return r.get(f"celery_task:{celular}")

def set_scheduled_task_id(celular, task_id):
    """Guarda en Redis el ID de la tarea Celery pendiente para este celular."""
    # ex=300 => expira en 5 minutos si por alguna razón no se limpia
    r.set(f"celery_task:{celular}", task_id, ex=300)

def clear_scheduled_task_id(celular):
    """Elimina la referencia en Redis de la tarea pendiente para este celular. Solo se usa en la función enviar_respuesta"""
    r.delete(f"celery_task:{celular}")

def revoke_task(task_id):
    """Revoca la tarea dado el task_id."""
    try:
        celery.control.revoke(task_id, terminate=True)
        print(f"Tarea {task_id} revocada exitosamente.")
    except Exception as e:
        print(f"Error revocando tarea: {e}")



#Falta agregar los datos a la tabla conversacion (hacerlo en los returns)
#Falta un prompt y una funcion de openai para brindar informacion (al ultimo)
@celery.task
def enviar_respuesta_v3(celular, cliente_nuevo, profileName):
    print("Enviando respuesta a:", celular)

    twilio = TwilioManager()
    openai = OpenAIManager()
    dbMongoManager = DataBaseMongoDBManager()
    dbMySQLManager = DataBaseMySQLManager()
    dbBigQueryManager = DataBaseBigQueryManager()

    #Obtener cliente mediante el celular que escribió
    cliente = dbMongoManager.obtener_cliente_por_celular(celular)
    if not cliente:
        return  # Cliente no existe en MongoDB, no hay conversación.

    #Obtener la conversacion del cliente (por como está diseñado obtiene TODA la conversacion, todo el historial mejor dicho)
    conversation_actual = dbMongoManager.obtener_conversacion_actual(cliente["celular"])

    # Verificamos si el cliente ya está en proceso de enviar su DNI/RUC
    estado_conversacion = dbMongoManager.obtener_estado_conversacion(cliente["celular"])

    # Si el estado es "se_solicito_dni" busca obtener el DNI que supuestamente escribio el cliente, si no lo obtiene hace return
    # y si lo obtiene , procesa adecuadamente todo y devuelve el código , haciendo de igual forma return

    if estado_conversacion == "se_solicito_dni":

        #OBTENER EL DNI
        doc_data = openai.obtener_dni_brindado(conversation_actual)
        dni = doc_data["numero"] if doc_data else None  #la variable deberia ser dni_ruc
        tipo_documento = doc_data["tipo"] if doc_data else None

        #verificar doc_data
        if doc_data is None:
            #el siguiente response también puede ser un prompt para openai, de momento es así
            response_message = "El documento ingresado no es válido. Por favor envía un DNI (8 dígitos) o RUC (11 dígitos)."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        print(f"El dni obtenido es: {dni}")
        #FIN OBTENER DNI

        #UNA VEZ OBTENIDO EL DNI

        #PROCEDE VALIDAR DATOS DEL CLIENTE
        # Verificar si el cliente está activo
        if not dbBigQueryManager.cliente_esta_activo(dni):
            #lo siguiente podría ser un prompt
            response_message = "No encontramos tu información en nuestra base de datos. Verifica tu DNI/RUC e intenta de nuevo."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        # Obtener datos del cliente
        datos_cliente = dbBigQueryManager.obtener_datos_cliente(dni)

        # Verificar datos
        if not datos_cliente:
            #lo siguiente podría ser un prompt
            response_message = "No encontramos tu información en nuestra base de datos. Inténtalo más tarde."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        nombre, apellido, celular_bq, email = datos_cliente["Nombres"], datos_cliente["Apellido_Paterno"], datos_cliente["Telf_SMS"], datos_cliente["E_mail"]

        # Insertar cliente en MySQL si no existe
        #si no funciona prueba poner estado tambien al final de los parametros
        dbMySQLManager.insertar_cliente(dni, tipo_documento, nombre, apellido, celular_bq, email)

        # Obtener el ID del cliente en MySQL
        id_cliente = dbMySQLManager.obtener_id_cliente_por_dni(dni)

        # Verificar si el cliente tiene solo 1 contrato
        if dbBigQueryManager.tiene_1_contrato_o_mas(dni) != 1:
            response_message = "Parece ser que tienes más de un contrato activo. Contáctanos para más información."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        # Obtener el código de pago
        codigo_pago, tipo_codigo = dbBigQueryManager.obtener_codigo_1contrato(dni)
        if codigo_pago == -1:
            response_message = "No encontramos un código de pago asociado a tu cuenta. Contáctanos para más información."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        # Insertar código en MySQL
        dbMySQLManager.insertar_codigoPago(id_cliente, codigo_pago, tipo_codigo, "", datetime.now())

        # Enviar código al cliente
        #Hacer un prompt para enviar el código y ponerlo en response_message
        response_message = f"Tu código {tipo_codigo} es: {codigo_pago}. Puedes utilizarlo para completar tu pago."
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)

        # IMPORTANTE Resetear estado de conversación , lo pone como None , pero se puede poner como "activa" para seguir la logica de Rivas
        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], None)
        return




    # ESTA ZONA DE ACÁ ABAJO es si no nos encontramos en proceso de analizar el dni
    # y brindarle el código de pago


    # Si no está en espera de DNI, clasificamos la intención del mensaje , esto es si el estado de la conversacion es
    # cualquiera menos "se_solicito_dni"
    intencion = openai.clasificar_intencion_botPago(conversation_actual)
    intencion_list = json_a_lista(intencion)

    if "informacion" in intencion_list:
        #Generar mediante chatgpt texto explicativo del proceso
        response_message = "Existen 3 tipos de códigos de pago: Recaudación, Extranet y Especial. ¿Necesitas más detalles?"
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        #agregar fecha de interaccion a la tabla conversacion (creo) de mysql
        twilio.send_message(cliente["celular"], response_message)


        clear_scheduled_task_id(celular) #probar eliminar esto si no funciona
        print(f"Terminó la tarea de dar informacion para {celular}, limpiando task_id en Redis.")

    elif "pago" in intencion_list:
        #usar consulta dni ruc
        response_message = openai.consulta_dni_ruc_botPago(cliente, None , conversation_actual)
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        #agregar fecha de interaccion a la tabla conversacion (creo) de mysql
        twilio.send_message(cliente["celular"], response_message)

        # Guardamos en MongoDB que esperamos el DNI , servirá para la siguiente iteración
        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], "se_solicito_dni")

        clear_scheduled_task_id(celular) #probar eliminar esto si no funciona
        print(f"Terminó la tarea solicitar dni o ruc para {celular}, limpiando task_id en Redis.")
    else:
        print("Otra intención detectada. No se procesa.")



@app.route('/bot_pago', methods=['POST'])  #RUTA 3 (código bot pago)
def whatsapp_bot_codigopago():
    try:
        #VER el contenido del mensaje, enviado por el cliente, 
        #a procesar
        print("RESPUESTA DE TWILIO: ", request)
        print("RESPUESTA DE TWILIO FORM: ", request.form)
        print("RESPUESTA DE TWILIO BODY: ", request.form.get('Body'))
        print("Profile Name: ", request.form.get('ProfileName'))

        #asignar el contenido a las variables
        profileName = request.form.get('ProfileName') #esta linea se puede eliminar
        incoming_msg = request.form.get('Body').lower()
        sender = request.form.get('From')
        celular = sender.split('whatsapp:')[1]

        #revisar el contenido asignado
        print("Mensaje recibido: ", incoming_msg)
        print("Remitente: ", celular)



        #Parte de MONGODB , donde se analiza si el cliente ya existe
        #o si no existe y se crea ahí en la bd de mongo
        #tambien ve el tema de si hay una conversacion activa o no
        #tambien agrega la interaccion del cliente a la conversacion actual (?)

        #de la linea 318 a la linea 335 de la ruta 1
        cliente = dbMongoManager.obtener_cliente_por_celular(celular)
        cliente_nuevo = False
        if not cliente:
            cliente_nuevo = True
            cliente = dbMongoManager.crear_cliente(nombre="", celular=celular)
            print("Cliente creado:", cliente)
        print("Cliente encontrado en la base de datos: ", cliente["nombre"])

        if not dbMongoManager.hay_conversacion_activa(celular):
            #crear conversacion activa
            print("Creando una nueva conversacion activa para el cliente.")
            dbMongoManager.crear_conversacion_activa(celular)

        #Se agrega la interacción del cliente a la conversacion actual
        #IMPORTANTE, el código de rivas hace que cada mensaje del cliente
        #se coloca en una interaccion distinta (por el crear_nueva_interaccion)
        #esto hace que varias interacciones queden con el mensaje del bot
        #vacio ya que no se responden , sin embargo
        #al bot se le pasa toda la conversacion (max 100 tokens) por lo que
        #en cierta medida sí analiza los mensajes anteriores
        #solo que la respuesta del bot la guarda en la ultima interaccion
        dbMongoManager.crear_nueva_interaccion(celular, incoming_msg)
        print("Interaccion del cliente guardada en la conversacion actual")

        #fin MONGODB



        #PROBAR ELIMINAR ESTO SI HAY UN ERROR
        #Revisa si hay una tarea pendiente para este celular y de ser
        #necesario, eliminarla para tratar la nueva tarea
        old_task_id = get_scheduled_task_id(celular)
        if old_task_id:
            #revocar la tarea anterior para reiniciar el countdown
            revoke_task(old_task_id.decode('utf-8'))

        #MUY IMPORTANTE ESTO siguiente
        #Llama a la tarea de Celery con un retraso de 45 segundos
        #Es decir, esperará 45 segundos por posibles mensajes extras
        #del usuario y en base a eso determinar la intencion.
        #Determinar la intencion sera esa tarea de Celery.
        #La lógica antes de usar la función enviar respuesta v2 es
        #el mensaje que escribió se une al historial de ese número y se
        #junta con los otros mensajes, si llega a pasar 45 segundos sin
        #recibir nuevos mensajes, ahí recién se usa la función
        #enviar_respuesta_v2 , por lo que es importante tener esas
        #funciones de mongodb

        new_task = enviar_respuesta_v3.apply_async(
            args=[celular, cliente_nuevo, profileName],
            countdown=45
        )


        #Una vez obtenido el new_task, lo guarda en la caché (Redis)
        set_scheduled_task_id(celular, new_task.id)

        #Verifica que se asignó correctamente
        print(f"Tarea programada {new_task.id} para {celular}")

        return 'OK', 200
    
    except Exception as e:
        print("Error en whatsapp_bot_codigopago: ", e)
        return "Error interno del servidor", 500
    



if __name__ == '__main__':
    # Iniciar la aplicación Flask
    app.run(host='0.0.0.0',port=5000)
