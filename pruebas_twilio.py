from components.twilio_component import TwilioManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from datetime import datetime
from pymongo import MongoClient

twilio_manager = TwilioManager()
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()


response_message = "Hola! ¿Por qué no reactivas?"
celular = '+51945827800'
cliente_id_mysql = 1

twilio_manager.send_message(celular, response_message)

# Guardar la respuesta en la conversación actual
print("Response message:", response_message)

if not dbMongoManager.hay_conversacion_activa(celular):
    # Se crea una conversacion activa, solo se crea
    print("Creando una nueva conversación activa para el cliente.")
    dbMongoManager.crear_conversacion_activa(celular)
    
    # Agrega la interacción del cliente a la conversación actual
    #dbMongoManager.guardar_mensaje_cliente_ultima_interaccion(celular, incoming_msg)

conversacion_mysql = dbMySQLManager.obtener_conversacion_activa(cliente_id_mysql)
if not conversacion_mysql:
        # Crear conversación activa en MySQL si no existe
    conversacion_id_mysql = dbMySQLManager.insertar_conversacion(
        cliente_id=cliente_id_mysql,
        mensaje="Inicio de conversación",
        resultado=None,
        estado_conversacion="activa"
    )
else:
    conversacion_id_mysql = conversacion_mysql["conversacion_id"]

dbMongoManager.crear_nueva_interaccion_vacia(celular)
dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, response_message)