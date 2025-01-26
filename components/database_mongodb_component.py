from pymongo import MongoClient
from datetime import datetime
import pytz

class DataBaseMongoDBManager:
    def __init__(self):
        self.db = self._connect()
        self.lima_tz = pytz.timezone("America/Lima")  # Definir la zona horaria de Lima

    def _connect(self):
        #uri = 'mongodb://localhost:27017/'
        uri = "mongodb+srv://admin:zQumSnUd9MNtjcsK@cluster0.mw4xl.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        return client.chatbot_db

    def _reconnect_if_needed(self):
        """Reconecta si la conexión actual no está activa."""
        try:
            # Verifica la conexión usando un comando simple
            self.db.command("ping")
        except Exception as e:
            print("Reconectando a MongoDB debido a un error:", e)
            self.db = self._connect()  # Vuelve a conectar

    def crear_cliente(self, nombre, celular, id=None, email=""):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Crea un nuevo cliente en la base de datos con su nombre y número de celular.
           Si el ID es proporcionado, lo usa; si no, lo genera automáticamente.
        """
        # Si no se proporciona un ID, generamos uno único basado en el timestamp
        cliente_id = id if id is not None else f"cli_{int(datetime.now(self.lima_tz).timestamp())}"

        # Crear documento del cliente
        cliente = {
            "cliente_id": cliente_id,
            "nombre": nombre,
            "celular": celular,
            "email": email,
            "conversaciones": []
        }
        
        # Insertar cliente en la base de datos
        self.db.clientes.insert_one(cliente)
        print(f"Nuevo cliente creado con celular {celular}.")
        return cliente

    def obtener_conversacion_actual(self, celular):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Obtiene la conversación actual del cliente si está activa."""
        cliente = self.db.clientes.find_one({"celular": celular})
        if cliente:
            for conversacion in cliente.get("conversaciones", []):
                if conversacion.get("estado") == "activa":
                    return conversacion
        return None

    def guardar_interaccion_conversacion_actual(self, cliente_id, mensaje_cliente, mensaje_chatbot):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Guarda una nueva interacción en la conversación actual y actualiza la última interacción."""
        timestamp = datetime.now(self.lima_tz).astimezone(pytz.utc)  # Hora en UTC
        self.db.clientes.update_one(
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
        self._reconnect_if_needed()  # Verifica o reconecta
        """Obtiene todas las conversaciones activas en curso."""
        return list(self.db.clientes.find(
            {"conversaciones.estado": "activa"},
            {"conversaciones.$": 1}
        ))

    def mover_conversacion_a_historial(self, cliente_id):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Mueve la conversación actual al historial y la marca como completada."""
        cliente = self.db.clientes.find_one({"cliente_id": cliente_id})
        if cliente:
            for conversacion in cliente.get("conversaciones", []):
                if conversacion.get("estado") == "activa":
                    # Cambiar el estado de la conversación a completada
                    self.db.clientes.update_one(
                        {"cliente_id": cliente_id, "conversaciones.conversacion_id": conversacion["conversacion_id"]},
                        {"$set": {"conversaciones.$.estado": "completada"}}
                    )
                    break  # Salimos después de encontrar la conversación activa

    def obtener_cliente_por_celular(self, celular):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Obtiene el documento de un cliente utilizando su número de celular."""
        cliente = self.db.clientes.find_one({"celular": celular})
        return cliente

    def obtener_historial_conversaciones(self, celular):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Obtiene hasta tres conversaciones completadas del historial de un cliente, excluyendo las activas."""
        cliente = self.db.clientes.find_one({"celular": celular})
        
        if not cliente:
            return []  # Retorna lista vacía si no encuentra al cliente
        
        # Filtrar conversaciones completadas y limitar a 3
        historial_completado = [
            conversacion for conversacion in cliente.get("conversaciones", [])
            if conversacion.get("estado") == "completada"
        ][:3]  # Limitar a un máximo de 3 conversaciones completadas

        return historial_completado   

    def guardar_respuesta_ultima_interaccion_chatbot(self, celular, respuesta_chatbot):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Guarda la respuesta del chatbot en la última interacción de la última conversación activa."""
        cliente = self.db.clientes.find_one({"celular": celular})
        
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
                        if ultima_interaccion["mensaje_chatbot"] == "" :
                            ultima_interaccion["mensaje_chatbot"] = respuesta_chatbot
                        else:
                            ultima_interaccion["mensaje_chatbot"] += f" | {respuesta_chatbot}"
                    else:
                        # Si no existe respuesta previa, guarda la primera respuesta en mensaje_chatbot
                        ultima_interaccion["mensaje_chatbot"] = respuesta_chatbot
                    
                    # Actualizar la conversación en la base de datos
                    self.db.clientes.update_one(
                        {"celular": celular, "conversaciones.conversacion_id": conversacion["conversacion_id"]},
                        {"$set": {"conversaciones.$.interacciones": conversacion["interacciones"]}}
                    )
                    return "Respuesta guardada en la última interacción"
        
        return "No se encontró una conversación activa"     

    def guardar_mensaje_cliente_ultima_interaccion(self, celular, mensaje_cliente):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Guarda el mensaje del cliente en la última interacción de la última conversación activa."""
        cliente = self.db.clientes.find_one({"celular": celular})
        
        if not cliente:
            return "Cliente no encontrado"
        
        # Buscar la última conversación activa
        for conversacion in reversed(cliente.get("conversaciones", [])):
            if conversacion.get("estado") == "activa":
                # Obtener la última interacción de la conversación activa
                interacciones = conversacion.get("interacciones", [])

                if interacciones:
                    ultima_interaccion = interacciones[-1]
                    
                    # Concatenar el mensaje si ya existe un mensaje del cliente
                    if "mensaje_cliente" in ultima_interaccion:
                        ultima_interaccion["mensaje_cliente"] += f" . {mensaje_cliente}"
                    else:
                        # Si no existe mensaje previo, guarda el mensaje en mensaje_cliente
                        ultima_interaccion["mensaje_cliente"] = mensaje_cliente
                    
                    # Actualizar la conversación en la base de datos
                    self.db.clientes.update_one(
                        {"celular": celular, "conversaciones.conversacion_id": conversacion["conversacion_id"]},
                        {"$set": {"conversaciones.$.interacciones": interacciones}}
                    )
                    return "Mensaje guardado en la última interacción"
                
                self.crear_nueva_interaccion(celular, mensaje_cliente)

                return "Mensaje guardado en una nueva interacción de la conversación activa"
        
        return "No se encontró una conversación activa"    
    
    def crear_nueva_interaccion(self, celular, mensaje_cliente):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Crea una nueva interacción en la conversación activa del cliente."""
        
        # Crear el nuevo registro de interacción
        nueva_interaccion = {
            "fecha": datetime.now(self.lima_tz).astimezone(pytz.utc),  # Hora en UTC
            "mensaje_cliente": mensaje_cliente,
            "mensaje_chatbot": ""  # Se llenará más adelante cuando el chatbot responda
        }

        # Actualizar la conversación activa del cliente con la nueva interacción
        self.db.clientes.update_one(
            {"celular": celular, "conversaciones.estado": "activa"},
            {
                "$push": {
                    "conversaciones.$.interacciones": nueva_interaccion
                },
                "$set": {"conversaciones.$.ultima_interaccion": datetime.now(self.lima_tz).astimezone(pytz.utc)}
            },
            upsert=False
        )
        print(f"Nueva interacción creada para el cliente con celular {celular}.") 

    def crear_nueva_interaccion_vacia(self, celular):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Crea una nueva interacción en la conversación activa del cliente."""
        
        # Crear el nuevo registro de interacción
        nueva_interaccion = {
            "fecha": datetime.now(self.lima_tz).astimezone(pytz.utc),  # Hora en UTC
            "mensaje_cliente": "",
            "mensaje_chatbot": ""  # Se llenará más adelante cuando el chatbot responda
        }

        # Actualizar la conversación activa del cliente con la nueva interacción
        self.db.clientes.update_one(
            {"celular": celular, "conversaciones.estado": "activa"},
            {
                "$push": {
                    "conversaciones.$.interacciones": nueva_interaccion
                },
                "$set": {"conversaciones.$.ultima_interaccion": datetime.now(self.lima_tz).astimezone(pytz.utc)}
            },
            upsert=False
        )
        print(f"Nueva interacción creada para el cliente con celular {celular}.") 


    def hay_conversacion_activa(self, celular):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Verifica si hay una conversación activa para el cliente usando el número de celular."""
        cliente = self.db.clientes.find_one({"celular": celular})
        
        # Comprueba si existe una conversación activa en el campo 'conversaciones'
        if cliente:
            for conversacion in cliente.get("conversaciones", []):
                if conversacion.get("estado") == "activa":
                    return True
        return False    
    
    def crear_conversacion_activa(self, celular):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Crea una nueva conversación activa para el cliente usando el número de celular."""
        nueva_conversacion = {
            "conversacion_id": f"conv_{int(datetime.now(self.lima_tz).timestamp())}",  # ID único basado en timestamp
            "estado": "activa",
            "ultima_interaccion": datetime.now(self.lima_tz).astimezone(pytz.utc),  # Hora en UTC
            "interacciones": []
        }
        
        # Añade la nueva conversación en el array 'conversaciones'
        self.db.clientes.update_one(
            {"celular": celular},
            {"$push": {"conversaciones": nueva_conversacion}}
        )
        print("Nueva conversación activa creada para el cliente con celular:", celular)

    def editar_cliente_por_celular(self, celular, nombre=None, nuevo_celular=None, email=None):
        self._reconnect_if_needed()  # Verifica o reconecta
        """Edita los datos básicos de un cliente: nombre, celular y/o email, buscando por el número de celular actual.
           Solo actualiza los campos que se proporcionan.
        """
        # Crear un diccionario con solo los campos a actualizar
        campos_actualizar = {}
        
        if nombre is not None:
            campos_actualizar["nombre"] = nombre
        if nuevo_celular is not None:
            campos_actualizar["celular"] = nuevo_celular
        if email is not None:
            campos_actualizar["email"] = email

        # Verificar si hay campos para actualizar
        if not campos_actualizar:
            print("No se proporcionaron campos para actualizar.")
            return "No hay cambios que realizar."

        # Actualizar el cliente en la base de datos
        resultado = self.db.clientes.update_one(
            {"celular": celular},
            {"$set": campos_actualizar}
        )

        if resultado.matched_count == 0:
            print(f"No se encontró cliente con celular {celular}.")
            return "Cliente no encontrado."
        
        print(f"Cliente con celular {celular} actualizado con éxito.")
        return "Cliente actualizado correctamente."


    def contar_interacciones_ultima_conversacion(self, celular):
        """
        Cuenta cuántas interacciones tiene la última conversación activa de un cliente.

        Args:
            celular (str): Número de celular del cliente.

        Returns:
            int: Número de interacciones en la última conversación activa, o -1 si no hay una conversación activa.
        """
        self._reconnect_if_needed()  # Verifica o reconecta

        # Buscar el cliente por su celular
        cliente = self.db.clientes.find_one({"celular": celular})

        if not cliente:
            print(f"No se encontró cliente con celular {celular}.")
            return -1  # Retorna -1 si no se encuentra al cliente

        # Buscar la última conversación activa
        for conversacion in reversed(cliente.get("conversaciones", [])):
            if conversacion.get("estado") == "activa":
                interacciones = conversacion.get("interacciones", [])
                return len(interacciones)  # Retorna el número de interacciones

        print(f"No se encontró una conversación activa para el cliente con celular {celular}.")
        return -1  # Retorna -1 si no hay una conversación activa