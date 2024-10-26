from pymongo import MongoClient
from datetime import datetime

class DataBaseMongoDBManager:
    def __init__(self):
        self.db = self._connect()

    def _connect(self):
        client = MongoClient('mongodb://localhost:27017/')
        return client.chatbot_db

    def obtener_conversacion_actual(self, cliente_id):
        """Obtiene la conversación actual del cliente si está activa."""
        cliente = self.db.clientes_conversaciones.find_one({"cliente_id": cliente_id})
        if cliente:
            for conversacion in cliente.get("conversaciones", []):
                if conversacion.get("estado") == "activa":
                    return conversacion
        return None

    def guardar_interaccion_conversacion_actual(self, cliente_id, mensaje_cliente, mensaje_chatbot):
        """Guarda una nueva interacción en la conversación actual y actualiza la última interacción."""
        timestamp = datetime.utcnow()
        self.db.clientes_conversaciones.update_one(
            {"cliente_id": cliente_id, "conversaciones.estado": "activa"},
            {
                "$push": {
                    "conversaciones.$.interacciones": {
                        "fecha": timestamp,
                        "mensaje_cliente": mensaje_cliente,
                        "mensaje_chatbot": mensaje_chatbot
                    }
                },
                "$set": {"conversaciones.$.ultima_interaccion": timestamp}
            },
            upsert=False
        )

    def obtener_conversaciones_activas(self):
        """Obtiene todas las conversaciones activas en curso."""
        return list(self.db.clientes_conversaciones.find(
            {"conversaciones.estado": "activa"},
            {"conversaciones.$": 1}
        ))

    def mover_conversacion_a_historial(self, cliente_id):
        """Mueve la conversación actual al historial y la marca como completada."""
        cliente = self.db.clientes_conversaciones.find_one({"cliente_id": cliente_id})
        if cliente:
            for conversacion in cliente.get("conversaciones", []):
                if conversacion.get("estado") == "activa":
                    # Cambiar el estado de la conversación a completada
                    self.db.clientes_conversaciones.update_one(
                        {"cliente_id": cliente_id, "conversaciones.conversacion_id": conversacion["conversacion_id"]},
                        {"$set": {"conversaciones.$.estado": "completada"}}
                    )
                    break  # Salimos después de encontrar la conversación activa

    def obtener_cliente_por_celular(self, celular):
        """Obtiene el documento de un cliente utilizando su número de celular."""
        cliente = self.db.clientes_conversaciones.find_one({"celular": celular})
        return cliente
    

    def obtener_historial_conversaciones(self, celular):
        """Obtiene hasta tres conversaciones completadas del historial de un cliente, excluyendo las activas."""
        cliente = self.db.clientes_conversaciones.find_one({"celular": celular})
        
        if not cliente:
            return []  # Retorna lista vacía si no encuentra al cliente
        
        # Filtrar conversaciones completadas y limitar a 3
        historial_completado = [
            conversacion for conversacion in cliente.get("conversaciones", [])
            if conversacion.get("estado") == "completada"
        ][:3]  # Limitar a un máximo de 3 conversaciones completadas

        return historial_completado   

    def guardar_respuesta_ultima_interaccion_chatbot(self, celular, respuesta_chatbot):
        """Guarda la respuesta del chatbot en la última interacción de la última conversación activa."""
        cliente = self.db.clientes_conversaciones.find_one({"celular": celular})
        
        if not cliente:
            return "Cliente no encontrado"
        
        # Buscar la última conversación activa
        for conversacion in reversed(cliente.get("conversaciones", [])):
            if conversacion.get("estado") == "activa":
                # Obtener la última interacción de la conversación activa
                if conversacion.get("interacciones"):
                    ultima_interaccion = conversacion["interacciones"][-1]
                    
                    # Concatenar la respuesta si ya existe una respuesta del chatbot
                    if "mensaje_chatbot" in ultima_interaccion:
                        ultima_interaccion["mensaje_chatbot"] += f" | {respuesta_chatbot}"
                    else:
                        # Si no existe respuesta previa, guarda la primera respuesta en mensaje_chatbot
                        ultima_interaccion["mensaje_chatbot"] = respuesta_chatbot
                    
                    # Actualizar la conversación en la base de datos
                    self.db.clientes_conversaciones.update_one(
                        {"celular": celular, "conversaciones.conversacion_id": conversacion["conversacion_id"]},
                        {"$set": {"conversaciones.$.interacciones": conversacion["interacciones"]}}
                    )
                    return "Respuesta guardada en la última interacción"
        
        return "No se encontró una conversación activa"     
    

    def guardar_mensaje_cliente_ultima_interaccion(self, celular, mensaje_cliente):
        """Guarda el mensaje del cliente en la última interacción de la última conversación activa."""
        cliente = self.db.clientes_conversaciones.find_one({"celular": celular})
        
        if not cliente:
            return "Cliente no encontrado"
        
        # Buscar la última conversación activa
        for conversacion in reversed(cliente.get("conversaciones", [])):
            if conversacion.get("estado") == "activa":
                # Obtener la última interacción de la conversación activa
                if conversacion.get("interacciones"):
                    ultima_interaccion = conversacion["interacciones"][-1]
                    
                    # Concatenar el mensaje si ya existe un mensaje del cliente
                    if "mensaje_cliente" in ultima_interaccion:
                        ultima_interaccion["mensaje_cliente"] += f" | {mensaje_cliente}"
                    else:
                        # Si no existe mensaje previo, guarda el mensaje en mensaje_cliente
                        ultima_interaccion["mensaje_cliente"] = mensaje_cliente
                    
                    # Actualizar la conversación en la base de datos
                    self.db.clientes_conversaciones.update_one(
                        {"celular": celular, "conversaciones.conversacion_id": conversacion["conversacion_id"]},
                        {"$set": {"conversaciones.$.interacciones": conversacion["interacciones"]}}
                    )
                    return "Mensaje guardado en la última interacción"
        
        return "No se encontró una conversación activa"    