import mysql.connector
from mysql.connector import Error
from datetime import datetime

class DataBaseMySQLManager:
    def __init__(self):
        self.connection = self._connect()

    def _connect(self):
        try:
            connection = mysql.connector.connect(
                host='localhost',
                database='chatbot_db',
                user='danielrp551',
                password='26deJULIO@'
            )
            if connection.is_connected():
                print("Conectado a MySQL")
            return connection
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            return None

    def insertar_cliente(self, documento_identidad, tipo_documento, nombre, celular, email):
        """Inserta un nuevo cliente en la tabla de clientes."""
        cursor = self.connection.cursor()
        query = """INSERT INTO clientes (documento_identidad, tipo_documento, nombre, celular, email)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (documento_identidad, tipo_documento, nombre, celular, email))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_cliente(self, cliente_id):
        """Obtiene los datos de un cliente por su ID."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM clientes WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchone()

    def insertar_lead(self, cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña=None, canal_lead=None, agendo_cita=False, estado="nuevo"):
        """Inserta un nuevo lead para un cliente en la tabla de leads."""
        cursor = self.connection.cursor()
        query = """INSERT INTO leads (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, agendo_cita, estado, fecha_creacion)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, agendo_cita, estado, datetime.now().date()))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_leads_cliente(self, cliente_id):
        """Obtiene todos los leads de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM leads WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def insertar_cita_confirmada(self, cliente_id, fecha, hora, servicio):
        """Inserta una nueva cita confirmada para un cliente."""
        cursor = self.connection.cursor()
        query = """INSERT INTO citas_confirmadas (cliente_id, fecha, hora, servicio, confirmado)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha, hora, servicio, True))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_citas_confirmadas_cliente(self, cliente_id):
        """Obtiene todas las citas confirmadas de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM citas_confirmadas WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()
