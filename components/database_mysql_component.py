import mysql.connector
from mysql.connector import Error
from datetime import datetime
import pytz

class DataBaseMySQLManager:
    def __init__(self):
        self.connection = self._connect()

    def _reconnect_if_needed(self):
        """Reconnects if the current connection is not active."""
        if not self.connection.is_connected():
            print("Reconectando a MySQL...")
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
        self._reconnect_if_needed()
        """Obtiene el cliente_id usando el número de celular."""
        cursor = self.connection.cursor()
        query = "SELECT cliente_id FROM clientes WHERE celular = %s"
        cursor.execute(query, (celular,))
        result = cursor.fetchone()
        return result[0] if result else None

    def existe_cliente_por_celular(self, celular):
        self._reconnect_if_needed()
        """Verifica si un cliente ya existe en la base de datos usando el número de celular."""
        return self.obtener_id_cliente_por_celular(celular) is not None

    def insertar_cliente(self, documento_identidad, tipo_documento, nombre, apellido, celular, email,estado="nuevo"):
        self._reconnect_if_needed()
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
        self._reconnect_if_needed()
        """Obtiene los datos de un cliente por su ID."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM clientes WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchone()

    def insertar_lead(self, cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña=None, canal_lead=None, estado_lead="nuevo", notas=None):
        self._reconnect_if_needed()
        """Inserta un nuevo lead para un cliente en la tabla de leads."""
        cursor = self.connection.cursor()
        query = """INSERT INTO leads (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas))
        self.connection.commit()
        return cursor.lastrowid
    
    def insertar_lead_zoho(self, cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña=None, canal_lead=None, estado_lead="nuevo", notas=None, tipo_lead=None):
        self._reconnect_if_needed()
        """Inserta un nuevo lead para un cliente en la tabla de leads."""
        cursor = self.connection.cursor()
        query = """INSERT INTO leads (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas,tipo)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s,%s)"""
        cursor.execute(query, (cliente_id, fecha_contacto, prioridad_lead, lead_source, campaña, canal_lead, estado_lead, notas,tipo_lead))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_leads_cliente(self, cliente_id):
        self._reconnect_if_needed()
        """Obtiene todos los leads de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM leads WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def insertar_cita(self, cliente_id, fecha_cita, motivo, estado_cita="agendada", conversacion_id=None):
        self._reconnect_if_needed()
        """Inserta una nueva cita para un cliente en la tabla de citas."""
        cursor = self.connection.cursor()
        query = """INSERT INTO citas (cliente_id, fecha_cita, motivo, estado_cita, conversacion_id)
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha_cita, motivo, estado_cita, conversacion_id))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_citas_cliente(self, cliente_id):
        self._reconnect_if_needed()
        """Obtiene todas las citas de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM citas WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()
    
    def obtener_citas_por_estado(self, estado_cita):
        self._reconnect_if_needed()
        """Obtiene todas las citas en un estado específico."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM citas WHERE estado_cita = %s"
        cursor.execute(query, (estado_cita,))
        return cursor.fetchall()
    
    def obtener_citas_por_estado_con_numero(self, estado_cita):
        self._reconnect_if_needed()
        """Obtiene todas las citas en un estado específico junto con el celular del cliente asociado."""
        cursor = self.connection.cursor(dictionary=True)
        query = """        
            SELECT c.cita_id, c.fecha_cita, c.estado_cita, c.motivo, c.fecha_creacion, c.aviso, 
               cl.cliente_id, cl.nombre, cl.apellido, cl.celular
            FROM citas c
            JOIN clientes cl ON c.cliente_id = cl.cliente_id
            WHERE c.estado_cita = %s
            """
        cursor.execute(query, (estado_cita,))
        return cursor.fetchall()

    def insertar_pago(self, cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago="pendiente"):
        self._reconnect_if_needed()
        """Inserta un nuevo pago para un cliente en la tabla de pagos."""
        cursor = self.connection.cursor()
        query = """INSERT INTO pagos (cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_pagos_cliente(self, cliente_id):
        self._reconnect_if_needed()
        """Obtiene todos los pagos de un cliente."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM pagos WHERE cliente_id = %s"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchall()

    def insertar_conversacion(self, cliente_id, mensaje, tipo_conversacion, resultado=None, estado_conversacion="activa"):
        self._reconnect_if_needed()
        """Inserta una nueva conversación para un cliente en la tabla de conversaciones."""
        cursor = self.connection.cursor()
        query = """INSERT INTO conversaciones (cliente_id, mensaje, tipo_conversacion, resultado, estado_conversacion, fecha_conversacion)
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, mensaje, tipo_conversacion, resultado, estado_conversacion, datetime.now()))
        self.connection.commit()
        return cursor.lastrowid

    def obtener_conversaciones_cliente(self, cliente_id, estado_conversacion=None):
        self._reconnect_if_needed()
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
        self._reconnect_if_needed()
        """Actualiza el estado de una conversación a 'completada' o 'activa'."""
        cursor = self.connection.cursor()
        query = "UPDATE conversaciones SET estado_conversacion = %s WHERE conversacion_id = %s"
        cursor.execute(query, (nuevo_estado, conversacion_id))
        self.connection.commit()

    def obtener_conversacion_activa(self, cliente_id):
        self._reconnect_if_needed()
        """Obtiene la conversación activa actual de un cliente, si existe."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM conversaciones WHERE cliente_id = %s AND estado_conversacion = 'activa'"
        cursor.execute(query, (cliente_id,))
        return cursor.fetchone()

    def actualizar_estado_lead(self, lead_id, nuevo_estado):
        self._reconnect_if_needed()
        """Actualiza el estado de un lead en la tabla de leads."""
        cursor = self.connection.cursor()
        query = "UPDATE leads SET estado_lead = %s WHERE lead_id = %s"
        cursor.execute(query, (nuevo_estado, lead_id))
        self.connection.commit()
        print(f"Estado del lead {lead_id} actualizado a '{nuevo_estado}'.")

    def actualizar_estado_cliente(self, client_id, nuevo_estado):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        query = "UPDATE clientes SET estado = %s WHERE cliente_id = %s"
        cursor.execute(query,(nuevo_estado,client_id))
        self.connection.commit()
        print(f"Estado del cliente {client_id} actualizado a {nuevo_estado}.")
       
    def actualizar_estado_cliente_no_interes(self, client_id, nuevo_estado,categoria_no_interes,detalle_no_interes):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        query = "UPDATE clientes SET estado = %s, categoria_no_interes = %s, detalle_no_interes = %s WHERE cliente_id = %s"
        cursor.execute(query,(nuevo_estado,categoria_no_interes,detalle_no_interes,client_id))
        self.connection.commit()
        print(f"Estado del cliente {client_id} actualizado a {nuevo_estado}.")        
    
    def actualizar_fecha_ultima_interaccion(self, cliente_id, fecha):
        self._reconnect_if_needed()
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
        self._reconnect_if_needed()
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
        self._reconnect_if_needed()
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
        self._reconnect_if_needed()
        """Obtiene los datos de un cliente por su ID."""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM clientes"
        cursor.execute(query)
        return cursor.fetchall()
    def obtener_citas_pasadas(self, fecha_actual):
        self._reconnect_if_needed()
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
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        sql = "UPDATE citas SET estado_cita = %s WHERE cita_id = %s"
        cursor.execute(sql, (nuevo_estado, cita_id))
        self.connection.commit()
        cursor.close()
    
    def actualizar_aviso_cita(self, cita_id, aviso):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        sql = "UPDATE citas SET aviso = %s WHERE cita_id = %s"
        cursor.execute(sql, (aviso, cita_id))
        self.connection.commit()
        cursor.close()

    def obtener_estado_cliente(self, cliente_id):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        sql = "SELECT estado FROM clientes WHERE cliente_id = %s"
        cursor.execute(sql, (cliente_id,))
        estado = cursor.fetchone()[0]
        cursor.close()
        return estado
    
    def actualizar_nombre_cliente(self, cliente_id, nombre):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        sql = "UPDATE clientes SET nombre = %s WHERE cliente_id = %s"
        cursor.execute(sql, (nombre, cliente_id))
        self.connection.commit()
        cursor.close()

    def actualizar_estado_historico_cliente(self, cliente_id, nuevo_estado):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()

        # Verificar si ya existe un registro en el histórico con el mismo estado para el cliente
        query_check = "SELECT historico_id FROM historico WHERE cliente_id = %s AND estado = %s"
        cursor.execute(query_check, (cliente_id, nuevo_estado))
        result = cursor.fetchone()

        if result:
            # Si existe, actualizar la fecha_estado a la fecha y hora actual
            query_update = "UPDATE historico SET fecha_estado = %s WHERE historico_id = %s"
            cursor.execute(query_update, (datetime.now(), result[0]))
            print(f"Fecha actualizada en el histórico para el estado '{nuevo_estado}' del cliente {cliente_id}.")
        else:
            # Si no existe, insertar un nuevo registro en el histórico
            query_insert = "INSERT INTO historico (cliente_id, estado, fecha_estado) VALUES (%s, %s, %s)"
            cursor.execute(query_insert, (cliente_id, nuevo_estado, datetime.now()))
            print(f"Estado '{nuevo_estado}' añadido al histórico para el cliente {cliente_id}.")

        self.connection.commit()
        cursor.close()

    def agregar_pago_y_confirmar_cita(self, cliente_id, monto, metodo_pago):
        """
        Agrega un pago relacionado a la cita más próxima del cliente en estado 'agendada'
        y cambia el estado de esa cita a 'confirmada'.
        
        Args:
            cliente_id (int): ID del cliente.
            monto (float): Monto del pago.
            metodo_pago (str): Método de pago utilizado.
        
        Returns:
            int: ID del pago insertado o None si no se encontró cita.
        """
        self._reconnect_if_needed()
        cursor = self.connection.cursor(dictionary=True)
        
        # Obtener la cita más próxima en estado 'agendada'
        query_cita = """
            SELECT cita_id, fecha_cita FROM citas
            WHERE cliente_id = %s AND estado_cita = 'agendada'
            ORDER BY fecha_cita ASC LIMIT 1
        """
        cursor.execute(query_cita, (cliente_id,))
        cita = cursor.fetchone()

        if not cita:
            print(f"No se encontró ninguna cita 'agendada' para el cliente con ID {cliente_id}.")
            return None

        cita_id = cita['cita_id']
        fecha_pago = datetime.now()
        
        # Insertar el pago relacionado a la cita encontrada
        query_pago = """
            INSERT INTO pagos (cliente_id, cita_id, fecha_pago, monto, metodo_pago, estado_pago)
            VALUES (%s, %s, %s, %s, %s, 'completado')
        """
        cursor.execute(query_pago, (cliente_id, cita_id, fecha_pago, monto, metodo_pago))
        pago_id = cursor.lastrowid

        # Cambiar el estado de la cita a 'confirmada'
        query_update_cita = "UPDATE citas SET estado_cita = 'confirmada' WHERE cita_id = %s"
        cursor.execute(query_update_cita, (cita_id,))

        # Confirmar cambios en la base de datos
        self.connection.commit()
        cursor.close()
        
        print(f"Pago agregado y cita {cita_id} confirmada para el cliente {cliente_id}.")
        return pago_id
    
    def marcar_bound(self, cliente_id, bound):
        self._reconnect_if_needed()
        cursor = self.connection.cursor()
        query = "UPDATE clientes SET bound = %s WHERE cliente_id = %s"
        cursor.execute(query, (bound, cliente_id))
        self.connection.commit()
        cursor.close()
        print(f"Cliente {cliente_id} marcado como bound={bound}.")


    def obtener_cita_mas_cercana(self, cliente_id):
        """
        Obtiene la cita más cercana para un cliente en estado 'agendada'
        y cuya fecha_cita sea mayor que la fecha actual en la zona horaria de Lima.

        :param cliente_id: ID del cliente.
        :return: La cita más cercana en estado 'agendada' o None si no se encuentra ninguna.
        """
        try:
            # Configurar la zona horaria de Lima
            lima_tz = pytz.timezone("America/Lima")
            ahora = datetime.now(lima_tz)

            self._reconnect_if_needed()
            cursor = self.connection.cursor(dictionary=True)

            # Query para buscar la cita más cercana
            query = """
                SELECT * FROM citas
                WHERE cliente_id = %s AND estado_cita = 'agendada' AND fecha_cita > %s
                ORDER BY fecha_cita ASC
                LIMIT 1
            """
            cursor.execute(query, (cliente_id, ahora))
            cita = cursor.fetchone()
            cursor.close()

            if cita:
                print(f"Cita más cercana encontrada: {cita}")
            else:
                print("No se encontró ninguna cita agendada futura para este cliente.")

            return cita

        except Exception as e:
            print(f"Error al obtener la cita más cercana: {e}")
            return None
    
    def obtener_clientes_por_filtro(self, filtro):
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM clientes WHERE " + filtro
        cursor.execute(query)
        return cursor.fetchall()
    
    def asociar_cliente_a_campana_mas_reciente(self, cliente_id):
        """
        Asocia un cliente a la campaña más reciente que esté activa y devuelve los detalles de la campaña.

        Args:
            cliente_id (int): ID del cliente a asociar.

        Returns:
            dict: Detalles de la campaña asociada o None si no hay campañas activas.
        """
        self._reconnect_if_needed()
        cursor = self.connection.cursor(dictionary=True)

        try:
            # Obtener la campaña activa más reciente
            query_campana = """
                SELECT * FROM campañas
                WHERE estado_campaña = 'activa'
                ORDER BY fecha_creacion DESC
                LIMIT 1
            """
            cursor.execute(query_campana)
            campana = cursor.fetchone()

            if not campana:
                print("No hay campañas activas disponibles.")
                return None

            campana_id = campana['campaña_id']

            # Verificar si ya existe la asociación
            query_check = """
                SELECT * FROM cliente_campaña
                WHERE cliente_id = %s AND campaña_id = %s
            """
            cursor.execute(query_check, (cliente_id, campana_id))
            existe_asociacion = cursor.fetchone()

            if existe_asociacion:
                print("El cliente ya está asociado a la campaña más reciente.")
            else:
                # Insertar la asociación en la tabla intermedia
                query_insert = """
                    INSERT INTO cliente_campaña (cliente_id, campaña_id)
                    VALUES (%s, %s)
                """
                cursor.execute(query_insert, (cliente_id, campana_id))

                # Incrementar el num_clientes de la campaña
                query_update_num_clientes = """
                    UPDATE campañas
                    SET num_clientes = num_clientes + 1
                    WHERE campaña_id = %s
                """
                cursor.execute(query_update_num_clientes, (campana_id,))

                self.connection.commit()
                print(f"Cliente {cliente_id} asociado a la campaña {campana_id} y num_clientes incrementado.")

            return campana

        except Exception as e:
            print(f"Error al asociar cliente a la campaña: {e}")
            return None

        finally:
            cursor.close()
