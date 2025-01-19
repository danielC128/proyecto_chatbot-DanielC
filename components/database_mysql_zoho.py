import mysql.connector
from mysql.connector import Error
from datetime import datetime
import pytz
import json

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
                database='zoho_db',
                user='admin',
                password='zQumSnUd9MNtjcsK'
            )
            if connection.is_connected():
                print("Conectado a MySQL")
            return connection
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            return None
        
    def agregar_lead(self, lead):
        """
        Agrega un lead a la tabla 'zoho_leads' en MySQL.
        Verifica si el lead ya existe basado en su 'id'. Si existe, retorna un error.
        
        :param lead: Diccionario con los datos del lead tal como lo retorna Zoho.
        :return: Tuple (bool, str) indicando éxito o fallo y un mensaje correspondiente.
        """
        self._reconnect_if_needed()
        if not self.connection:
            return (False, 'other', "No hay conexión a la base de datos.")

        try:
            cursor = self.connection.cursor()

            # Verificar si el lead ya existe
            check_query = "SELECT id FROM zoho_leads WHERE id = %s"
            cursor.execute(check_query, (lead.get('id'),))
            result = cursor.fetchone()
            if result:
                cursor.close()
                return (False,'exists', f"El lead con ID {lead.get('id')} ya existe en la base de datos.")

            # Lista completa de columnas a insertar (68 columnas)
            columnas = [
                'id', 'First_Name', 'Last_Name', 'Full_Name', 'Email', 'Mobile',
                'Salutation', 'Referrer', 'Tipo_de_Lead', 'Lead_Status', 'Lead_Source',
                'Campaing_Name', 'Description', 'Prioridad_Lead', 'Owner_Name', 'Owner_Id',
                'Owner_Email', 'Analizado', '`$converted`', '`$process_flow`', '`$approved`',
                '`$editable`', '`$in_merge`', 'Email_Opt_Out', 'Ad_Set_Name', 'Ad_Name',
                'layout_id_name', 'layout_id_id', 'approval_delegate', 'approval_takeover',
                'approval_approve', 'approval_reject', 'approval_resubmit',
                'review_process_approve', 'review_process_reject', 'review_process_resubmit',
                '`$field_states`', '`$review`', '`$converted_detail`', '`$orchestration`',
                'Tag', 'currency_symbol', 'Rama', 'Visitor_Score', 'Days_Visited',
                'Average_Time_Spent_Minutes', '`$state`', 'Unsubscribed_Mode',
                'approval_state', 'Email_Status', 'Solicita_Info_WhatsApp', 'Number_Of_Chats'
            ]

            # Crear la declaración de inserción dinámicamente
            placeholders = ', '.join(['%s'] * len(columnas))
            columnas_formateadas = ', '.join(columnas)
            insert_query = f"INSERT INTO zoho_leads ({columnas_formateadas}) VALUES ({placeholders})"

            # Preparar los datos para la inserción
            data_lead = (
                lead.get('id'),
                lead.get('First_Name'),
                lead.get('Last_Name'),
                lead.get('Full_Name'),
                lead.get('Email'),
                lead.get('Mobile'),
                lead.get('Salutation'),
                lead.get('Referrer'),
                lead.get('Tipo_de_Lead'),
                lead.get('Lead_Status'),
                lead.get('Lead_Source'),
                lead.get('Campaing_Name'),
                lead.get('Description'),
                lead.get('Prioridad_Lead'),
                lead.get('Owner', {}).get('name'),
                lead.get('Owner', {}).get('id'),
                lead.get('Owner', {}).get('email'),
                lead.get('Analizado'),
                lead.get('$converted'),
                lead.get('$process_flow'),
                lead.get('$approved'),
                lead.get('$editable'),
                lead.get('$in_merge'),
                lead.get('Email_Opt_Out'),
                lead.get('Ad_Set_Name'),
                lead.get('Ad_Name'),
                lead.get('$layout_id', {}).get('name'),
                lead.get('$layout_id', {}).get('id'),
                lead.get('$approval', {}).get('delegate'),
                lead.get('$approval', {}).get('takeover'),
                lead.get('$approval', {}).get('approve'),
                lead.get('$approval', {}).get('reject'),
                lead.get('$approval', {}).get('resubmit'),
                lead.get('$review_process', {}).get('approve'),
                lead.get('$review_process', {}).get('reject'),
                lead.get('$review_process', {}).get('resubmit'),
                json.dumps(lead.get('$field_states')) if lead.get('$field_states') else None,
                json.dumps(lead.get('$review')) if lead.get('$review') else None,
                json.dumps(lead.get('$converted_detail')) if lead.get('$converted_detail') else None,
                json.dumps(lead.get('$orchestration')) if lead.get('$orchestration') else None,
                json.dumps(lead.get('Tag')) if lead.get('Tag') else None,
                lead.get('$currency_symbol'),
                lead.get('Rama'),
                lead.get('Visitor_Score'),
                lead.get('Days_Visited'),
                lead.get('Average_Time_Spent_Minutes'),
                lead.get('$state'),
                lead.get('Unsubscribed_Mode'),
                lead.get('approval_state'),
                lead.get('Email_Status'),
                lead.get('Solicita_Info_WhatsApp'),
                lead.get('Number_Of_Chats')
            )

            # Verificar que el número de columnas y datos coincida
            if len(columnas) != len(data_lead):
                cursor.close()
                return (False,'other', f"Discrepancia en el número de columnas y datos: {len(columnas)} columnas, {len(data_lead)} datos.")

            # Ejecutar la inserción
            cursor.execute(insert_query, data_lead)
            self.connection.commit()
            cursor.close()
            return (True,None, f"Lead con ID {lead.get('id')} insertado exitosamente.")

        except mysql.connector.Error as err:
            return (False,'other', f"Error al insertar el lead: {err}")
        
    def agregar_contact(self, contact):
        """
        Agrega un contacto a la tabla 'zoho_contacts' en MySQL.
        Verifica si el contacto ya existe basado en su 'id'. Si existe, retorna un error.
        
        :param contact: Diccionario con los datos del contacto tal como lo retorna Zoho.
        :return: Tuple (bool, str, str) indicando éxito o fallo, tipo de fallo y un mensaje correspondiente.
        """
        self._reconnect_if_needed()
        if not self.connection:
            return (False, 'other', "No hay conexión a la base de datos.")

        try:
            cursor = self.connection.cursor()

            # Verificar si el contacto ya existe
            check_query = "SELECT id FROM zoho_contacts WHERE id = %s"
            cursor.execute(check_query, (contact.get('id'),))
            result = cursor.fetchone()
            if result:
                cursor.close()
                return (False, 'exists', f"El contacto con ID {contact.get('id')} ya existe en la base de datos.")

            # Preparar la consulta de inserción con todas las columnas
            columnas = [
                '`id`', '`Owner_name`', '`Owner_id`', '`Owner_email`', '`Email`', '`$currency_symbol`', '`Visitor_Score`',
                '`$field_states`', '`Fecha_Cita`', '`Mesoterapias_Pagadas`', '`Last_Activity_Time`',
                '`Mesoterapias_Asistidas`', '`$state`', '`Unsubscribed_Mode`', '`$process_flow`', '`Assistant`',
                '`Gestion_Remarketing`', '`Fecha_creacion`', '`Se_gestiono`', '`$locked_for_me`', '`Prioridad_Lead`',
                '`$approved`', '`Tipo_de_Cita`', '`Nro_Agendamientos`', '`$approval_delegate`', '`$approval_takeover`',
                '`$approval_approve`', '`$approval_reject`', '`$approval_resubmit`', '`Medicamentos`',
                '`First_Visited_URL`', '`Days_Visited`', '`$editable`', '`Acepta_Cirug_a`', '`Asistio_a_cita`',
                '`Canal_Lead`', '`Entrego_resultados`', '`Campaing_Name`', '`Recordatorio_Enviado`',
                '`Compro_medicamentos`', '`Volver_a_llamar`', '`Description`', '`Number_Of_Chats`',
                '`$review_process_approve`', '`$review_process_reject`', '`$review_process_resubmit`',
                '`Average_Time_Spent_Minutes`', '`$layout_id_name`', '`$layout_id_id`', '`Ad_Set_Name`', '`Cirug_a`',
                '`Salutation`', '`First_Name`', '`Full_Name`', '`Monto_Cita`', '`Mesoterapia`', '`Nombre_Doctor`',
                '`$review`', '`Nro_Intentos`', '`Fecha_Ult_Compra`', '`Fecha_Ult_Mesoterapia`', '`Ad_Name`',
                '`Ult_Compra_Medicamento_en_Meses`', '`Unsubscribed_Time`', '`Ult_Fec_Gest1`', '`Monto_Cirug_a`',
                '`Ult_Fec_Gest`', '`Mobile`', '`$orchestration`', '`First_Visited_Time`', '`Rpta_Recordatorio`',
                '`Last_Name`', '`$in_merge`', '`Referrer`', '`U_F_s_Diagnosticadas`', '`Lead_Source`',
                '`Fecha_creaci_n_lead`', '`Tag`', '`$approval_state`', '`DNI`','`Ad_ID`'
            ]
            
            insert_query = f"""
                INSERT INTO zoho_contacts ({', '.join(columnas)})
                VALUES ({', '.join(['%s'] * len(columnas))})
            """

            # Preparar los datos para la inserción
            data_contact = (
                contact.get('id'),
                contact.get('Owner', {}).get('name'),
                contact.get('Owner', {}).get('id'),
                contact.get('Owner', {}).get('email'),
                contact.get('Email'),
                contact.get('$currency_symbol'),
                contact.get('Visitor_Score'),
                json.dumps(contact.get('$field_states')) if contact.get('$field_states') else None,
                contact.get('Fecha_Cita'),
                contact.get('Mesoterapias_Pagadas'),
                contact.get('Last_Activity_Time'),
                contact.get('Mesoterapias_Asistidas'),
                contact.get('$state'),
                contact.get('Unsubscribed_Mode'),
                contact.get('$process_flow'),
                contact.get('Assistant'),
                contact.get('Gestion_Remarketing'),
                contact.get('Fecha_creacion'),
                contact.get('Se_gestiono'),
                contact.get('$locked_for_me'),
                contact.get('Prioridad_Lead'),
                contact.get('$approved'),
                contact.get('Tipo_de_Cita'),
                contact.get('Nro_Agendamientos'),
                contact.get('$approval', {}).get('delegate'),
                contact.get('$approval', {}).get('takeover'),
                contact.get('$approval', {}).get('approve'),
                contact.get('$approval', {}).get('reject'),
                contact.get('$approval', {}).get('resubmit'),
                contact.get('Medicamentos'),
                contact.get('First_Visited_URL'),
                contact.get('Days_Visited'),
                contact.get('$editable'),
                contact.get('Acepta_Cirug_a'),
                contact.get('Asistio_a_cita'),
                contact.get('Canal_Lead'),
                contact.get('Entrego_resultados'),
                contact.get('Campaing_Name'),
                contact.get('Recordatorio_Enviado'),
                json.dumps(contact.get('Compro_medicamentos')) if contact.get('Compro_medicamentos') else None,
                contact.get('Volver_a_llamar'),
                contact.get('Description'),
                contact.get('Number_Of_Chats'),
                contact.get('$review_process', {}).get('approve'),
                contact.get('$review_process', {}).get('reject'),
                contact.get('$review_process', {}).get('resubmit'),
                contact.get('Average_Time_Spent_Minutes'),
                contact.get('$layout_id', {}).get('name'),
                contact.get('$layout_id', {}).get('id'),
                contact.get('Ad_Set_Name'),
                contact.get('Cirug_a'),
                contact.get('Salutation'),
                contact.get('First_Name'),
                contact.get('Full_Name'),
                contact.get('Monto_Cita'),
                contact.get('Mesoterapia'),
                contact.get('Nombre_Doctor'),
                json.dumps(contact.get('$review')) if contact.get('$review') else None,
                contact.get('Nro_Intentos'),
                contact.get('Fecha_Ult_Compra'),
                contact.get('Fecha_Ult_Mesoterapia'),
                contact.get('Ad_Name'),
                contact.get('Ult_Compra_Medicamento_en_Meses'),
                contact.get('Unsubscribed_Time'),
                contact.get('Ult_Fec_Gest1'),
                contact.get('Monto_Cirug_a'),
                contact.get('Ult_Fec_Gest'),
                contact.get('Mobile'),
                json.dumps(contact.get('$orchestration')) if contact.get('$orchestration') else None,
                contact.get('First_Visited_Time'),
                contact.get('Rpta_Recordatorio'),
                contact.get('Last_Name'),
                contact.get('$in_merge'),
                contact.get('Referrer'),
                contact.get('U_F_s_Diagnosticadas'),
                contact.get('Lead_Source'),
                contact.get('Fecha_creaci_n_lead'),
                json.dumps(contact.get('Tag')) if contact.get('Tag') else None,
                contact.get('$approval_state'),
                contact.get('DNI'),
                contact.get('Ad_ID')
            )

            # Verificar que el número de columnas y datos coincida
            if len(columnas) != len(data_contact):
                cursor.close()
                return (False,'other', f"Discrepancia en el número de columnas y datos: {len(columnas)} columnas, {len(data_lead)} datos.")

            # Ejecutar la inserción
            cursor.execute(insert_query, data_contact)
            self.connection.commit()
            cursor.close()
            return (True, None, f"Contacto con ID {contact.get('id')} insertado exitosamente.")

        except mysql.connector.Error as err:
            return (False, 'other', f"Error al insertar el contacto con ID {contact.get('id')}: {err}")
        
    def cerrar_conexion(self):
        """Cierra la conexión a la base de datos."""
        if self.connection.is_connected():
            self.connection.close()
            print("Conexión a MySQL cerrada.")