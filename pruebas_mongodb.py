from components.database_mongodb_component import DataBaseMongoDBManager
from pymongo import MongoClient
from datetime import datetime
import pytz


dbMongoManager = DataBaseMongoDBManager()


celular = "+51941729891"

cliente = dbMongoManager.obtener_cliente_por_celular(celular)



response_message = "Prueba para ver conversacion en mongodb"
dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)