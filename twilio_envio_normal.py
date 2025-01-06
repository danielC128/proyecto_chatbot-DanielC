from components.twilio_component import TwilioManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from datetime import datetime, timedelta

twilio_manager = TwilioManager()
dbMongoManager = DataBaseMongoDBManager()
dbMySQLManager = DataBaseMySQLManager()


response_message = "¡Genial, Sebastián! Tu cita ha sido agendada para el martes 14 a las 2:30 p.m. 😊 Puedes realizar el pago usando el siguiente link: [https://express.culqi.com/pago/HXHKR025JY], aceptamos Yape, Plin o tarjetas de crédito/débito."
celular = '+51996542672'
cliente_id_mysql = 621

twilio_manager.send_message(celular, response_message)

# Guardar la respuesta en la conversación actual
print("Response message:", response_message)
dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, response_message)
dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())