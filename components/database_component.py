class DatabaseManager:
    def __init__(self):
        self.db = self._connect()

    def _connect(self):
        client = MongoClient('mongodb://localhost:27017/')
        return client.chatbot_db

    def obtener_conversacion_actual(self, cliente_id):
        """Obtiene la conversación actual del cliente."""
        cliente = self.db.clientes.find_one({"_id": cliente_id})
        if cliente and "conversacion_actual" in cliente:
            return cliente["conversacion_actual"]
        return []

    def guardar_interaccion_conversacion_actual(self, cliente_id, mensaje_cliente, mensaje_chatbot):
        """Guarda una nueva interacción en la conversación actual."""
        self.db.clientes.update_one(
            {"_id": cliente_id},
            {
                "$push": {
                    "conversacion_actual": {
                        "cliente": mensaje_cliente,
                        "chatbot": mensaje_chatbot,
                        "timestamp": datetime.utcnow()
                    }
                },
                "$set": {"ultima_interaccion": datetime.utcnow()}
            },
            upsert=True
        )

    def obtener_conversaciones_activas(self):
        """Obtiene todas las conversaciones activas que tienen interacciones en curso."""
        return list(self.db.clientes.find({"ultima_interaccion": {"$exists": True}}))

    def mover_conversacion_a_historial(self, cliente_id):
        """Mueve la conversación actual al historial y la marca como completada."""
        cliente = self.db.clientes.find_one({"_id": cliente_id})
        if cliente and "conversacion_actual" in cliente:
            conversacion_completa = cliente["conversacion_actual"]
            self.db.clientes.update_one(
                {"_id": cliente_id},
                {
                    "$push": {"historial_conversaciones": conversacion_completa},
                    "$unset": {"conversacion_actual": "", "ultima_interaccion": ""}
                }
            )
