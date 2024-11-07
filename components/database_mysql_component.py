import mysql.connector
from mysql.connector import Error
from datetime import datetime

class DataBaseMySQLManager:
    def __init__(self):
        self.connection = self._connect()

    def _connect(self):
        try:
            connection = mysql.connector.connect(
                #host='localhost',
                #user='danielrp551',
                #database='chatbot_db',
                #password='26deJULIO@'
                host='chatbot-mysql.c5yiocg6aj0e.us-east-2.rds.amazonaws.com',
                database='chatbot_db',
                user='admin',
                password='zQumSnUd9MNtjcsK'
            )
            if connection.is_connected():
                print("Conectado a MySQL")
            return connection
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            return None

    def obtener_id_cliente_por_celular(self, celular):
        """Obtiene el cliente_id usando el número de celular."""
        cursor = self.connection.cursor()
        query = "SELECT cliente_id FROM clientes WHERE celular = %s"
        cursor.execute(query, (celular,))
        result = cursor.fetchone()
        return result[0] if result else None

    def existe_cliente_por_celular(self, celular):
        """Verifica si un cliente ya existe en la base de datos usando el número de celular."""
        return self.obtener_id_cliente_por_celular(celular) is not None

    def insertar_cliente(self, documento_identidad, tipo_documento, nombre, apellido, celular, email,estado="activo"):
        """Inserta un nuevo cliente en la tabla de clientes si no existe ya."""
        if not self.existe_cliente_por_celular(celular):
            cursor = self.connection.cursor()
            query = """INSERT INTO clientes (documento_identidad, tipo_documento, nombre, apellido, celular, email,estado)
                       VALUES (%s, %s, %s, %s, %s, %s,%s)"""
            cursor.execute(query, (documento_identidad, tipo_documento, nombre, apellido, celular, email,estado))
            self.connection.commit()
            print("Cliente insertado en MySQL.")
            return cursor.lastrowid
        else:
            print("El cliente ya existe en MySQL.")
            return self.obtener_id_cliente_por_celular(celular)

    def obtener_cliente(self, cliente_id):
        """Obtiene los datos de un cliente por su ID."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM clientes WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchone()

    def insertar_lead(self, cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña=None, canal_lead=None, estado_lead="nuevo", notas=None):
        """Inserta un nuevo lead para un cliente en la tabla de leads."""
        cursor = self.connection.cursor()
        query = """INSERT INTO leads (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas))
        self.connection.commit()
        return cursor.lastrowid
    
    def insertar_lead_zoho(self, cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña=None, canal_lead=None, estado_lead="nuevo", notas=None, tipo_lead=None):
        """Inserta un nuevo lead para un cliente en la tabla de leads."""
        cursor = self.connection.cursor()
        query = """INSERT INTO leads (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas,tipo)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)"""
        cursor.execute(query, (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas,tipo_lead))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_leads_cliente(self, cliente_id):
        """Obtiene todos los leads de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM leads WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def insertar_cita(self, cliente_id, fecha_cita, motivo, estado_cita="agendada", conversacion_id=None):
        """Inserta una nueva cita para un cliente en la tabla de citas."""
        cursor = self.connection.cursor()
        query = """INSERT INTO citas (cliente_id, fecha_cita, motivo, estado_cita, conversacion_id)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha_cita, motivo, estado_cita, conversacion_id))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_citas_cliente(self, cliente_id):
        """Obtiene todas las citas de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM citas WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def insertar_pago(self, cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago="pendiente"):
        """Inserta un nuevo pago para un cliente en la tabla de pagos."""
        cursor = self.connection.cursor()
        query = """INSERT INTO pagos (cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_pagos_cliente(self, cliente_id):
        """Obtiene todos los pagos de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM pagos WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def insertar_conversacion(self, cliente_id, mensaje, tipo_conversacion, resultado=None, estado_conversacion="activa"):
        """Inserta una nueva conversación para un cliente en la tabla de conversaciones."""
        cursor = self.connection.cursor()
        query = """INSERT INTO conversaciones (cliente_id, mensaje, tipo_conversacion, resultado, estado_conversacion, fecha_conversacion)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, mensaje, tipo_conversacion, resultado, estado_conversacion, datetime.now()))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_conversaciones_cliente(self, cliente_id, estado_conversacion=None):
        """Obtiene todas las conversaciones de un cliente, filtrando opcionalmente por estado."""
        cursor = self.connection.cursor(dictionary=True)
        if estado_conversacion:
            query = "SELECT * FROM conversaciones WHERE cliente_id = %s AND estado_conversacion = %s"
            cursor.execute(query, (cliente_id, estado_conversacion))
        else:
            query = "SELECT * FROM conversaciones WHERE cliente_id = %s"
            cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def actualizar_estado_conversacion(self, conversacion_id, nuevo_estado):
        """Actualiza el estado de una conversación a 'completada' o 'activa'."""
        cursor = self.connection.cursor()
        query = "UPDATE conversaciones SET estado_conversacion = %s WHERE conversacion_id = %s"
        cursor.execute(query, (nuevo_estado, conversacion_id))
        self.connection.commit()

    def obtener_conversacion_activa(self, cliente_id):
        """Obtiene la conversación activa actual de un cliente, si existe."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM conversaciones WHERE cliente_id = %s AND estado_conversacion = 'activa'"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchone()

    def actualizar_estado_lead(self, lead_id, nuevo_estado):
        """Actualiza el estado de un lead en la tabla de leads."""
        cursor = self.connection.cursor()
        query = "UPDATE leads SET estado_lead = %s WHERE lead_id = %s"
        cursor.execute(query, (nuevo_estado, lead_id))
        self.connection.commit()
        print(f"Estado del lead {lead_id} actualizado a '{nuevo_estado}'.")

    def actualizar_estado_cliente(self, client_id, nuevo_estado):
        cursor = self.connection.cursor()
        query = "UPDATE clientes SET estado = %s WHERE cliente_id = %s"
        cursor.execute(query,(nuevo_estado,client_id))
        self.connection.commit()
        print(f"Estado del cliente {client_id} actualizado a {nuevo_estado}.")
       
    def actualizar_estado_cliente_no_interes(self, client_id, nuevo_estado,categoria_no_interes,detalle_no_interes):
        cursor = self.connection.cursor()
        query = "UPDATE clientes SET estado = %s, categoria_no_interes = %s, detalle_no_interes = %s WHERE cliente_id = %s"
        cursor.execute(query,(nuevo_estado,categoria_no_interes,detalle_no_interes,client_id))
        self.connection.commit()
        print(f"Estado del cliente {client_id} actualizado a {nuevo_estado}.")        
    
    def actualizar_fecha_ultima_interaccion(self, cliente_id, fecha):
        cursor = self.connection.cursor()
        sql = "UPDATE clientes SET fecha_ultima_interaccion = %s WHERE cliente_id = %s"
        cursor.execute(sql, (fecha, cliente_id))

        # Actualiza la fecha en la conversación activa
        sql_conversacion = """
            UPDATE conversaciones 
            SET fecha_ultima_interaccion = %s 
            WHERE cliente_id = %s AND estado_conversacion = 'activa'
        """
        cursor.execute(sql_conversacion, (fecha, cliente_id))

        self.connection.commit()
        cursor.close()

    def actualizar_fecha_ultima_interaccion_bot(self, cliente_id, fecha):
        cursor = self.connection.cursor()
        sql = "UPDATE clientes SET fecha_ultima_interaccion_bot = %s WHERE cliente_id = %s"
        cursor.execute(sql, (fecha, cliente_id))
        
        # Actualiza la fecha en la conversación activa
        sql_conversacion = """
            UPDATE conversaciones 
            SET fecha_ultima_interaccion = %s 
            WHERE cliente_id = %s AND estado_conversacion = 'activa'
        """
        cursor.execute(sql_conversacion, (fecha, cliente_id))    
        
        self.connection.commit()
        cursor.close()

    
    def obtener_citas_pendientes(self):
        cursor = self.connection.cursor(dictionary=True)
        sql = """
            SELECT c.*, p.estado_pago FROM citas c
            LEFT JOIN pagos p ON c.cita_id = p.cita_id
            WHERE c.estado_cita = 'agendada' AND (p.estado_pago IS NULL OR p.estado_pago != 'completado')
        """
        cursor.execute(sql)
        citas = cursor.fetchall()
        cursor.close()
        return citas
    
    def obtener_todos_los_clientes(self):
        """Obtiene los datos de un cliente por su ID."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM clientes"
        cursor.execute(query)
        return cursor.fetchall()
    def obtener_citas_pasadas(self, fecha_actual):
        cursor = self.connection.cursor(dictionary=True)
        sql = """
            SELECT * FROM citas
            WHERE estado_cita = 'agendada' AND fecha_cita <= %s
        """
        cursor.execute(sql, (fecha_actual,))
        citas = cursor.fetchall()
        cursor.close()
        return citas
    
    def actualizar_estado_cita(self, cita_id, nuevo_estado):
        cursor = self.connection.cursor()
        sql = "UPDATE citas SET estado_cita = %s WHERE cita_id = %s"
        cursor.execute(sql, (nuevo_estado, cita_id))
        self.connection.commit()
        cursor.close()

    def obtener_estado_cliente(self, cliente_id):
        cursor = self.connection.cursor()
        sql = "SELECT estado FROM clientes WHERE cliente_id = %s"
        cursor.execute(sql, (cliente_id,))
        estado = cursor.fetchone()[0]
        cursor.close()
        return estado
    
    def actualizar_nombre_cliente(self, cliente_id, nombre):
        cursor = self.connection.cursor()
        sql = "UPDATE clientes SET nombre = %s WHERE cliente_id = %s"
        cursor.execute(sql, (nombre, cliente_id))
        self.connection.commit()
        cursor.close()