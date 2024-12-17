from components.zoho_component import ZohoCRMManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from datetime import datetime, timedelta
from components.twilio_component import TwilioManager
from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager
from api_keys.api_keys import promesa_pago_interesados
from helpers.helpers import format_number, plantilla_promesa_pago_interesados
import multiprocessing


# --- FUNCIONES AUXILIARES ---

def verificar_celular_en_leads(leads, campo_celular='Mobile'):
    """
    Verifica si todos los leads tienen información en el campo de número de celular.

    Args:
        leads (list): Lista de leads.
        campo_celular (str): Nombre del campo donde se encuentra el número de celular.

    Returns:
        bool: True si todos los leads tienen un número de celular, False en caso contrario.
    """
    for lead in leads:
        if not lead.get(campo_celular):  # Si el campo está vacío o no existe
            return False
    return True


def eliminar_leads_duplicados(leads, campo_celular='Mobile'):
    """
    Elimina leads duplicados basándose en el campo del número de celular.

    Args:
        leads (list): Lista de leads.
        campo_celular (str): Nombre del campo donde se encuentra el número de celular.

    Returns:
        list: Lista de leads sin duplicados.
    """
    seen = set()  # Para almacenar los números de celular únicos
    leads_sin_duplicados = []
    
    for lead in leads:
        numero_celular = lead.get(campo_celular)
        if numero_celular:
            numero_celular = format_number(numero_celular)
        if numero_celular and numero_celular not in seen:
            seen.add(numero_celular)
            leads_sin_duplicados.append(lead)
    
    return leads_sin_duplicados


def procesar_subconjunto(subconjunto_leads):
    """
    Procesa un subconjunto de leads. Por ahora, simplemente imprime los campos Mobile.
    """
    twilio = TwilioManager()
    dbMongoManager = DataBaseMongoDBManager()
    dbMySQLManager = DataBaseMySQLManager()
    for lead in subconjunto_leads:
        print(f"Procesando lead con número: {lead['Mobile']}")
        # crearle 
        if not lead.get("Mobile"):
            continue
        celular = format_number(lead["Mobile"])
        # Buscar en la base de MongoDB usando el numero de telefono del lead
        cliente = dbMongoManager.obtener_cliente_por_celular(celular)
        first_name = lead.get("First_Name") or ""
        last_name = lead.get("Last_Name") or ""

        if not cliente:
            # Si el cliente no existe en Mongo, creamos el cliente
            cliente = dbMongoManager.crear_cliente(f"{first_name} {last_name}".strip(), celular, lead["id"])
            # creamos el cliente en mysql
            cliente_id_mysql = dbMySQLManager.insertar_cliente(
                documento_identidad=None,
                tipo_documento=None,
                nombre=first_name,
                apellido=last_name,
                celular=celular,
                email=lead.get("Email", None),
                estado="contactado"
            )
            dbMySQLManager.marcar_bound(cliente_id_mysql,False) # outbound = False
            print("Cliente creado:", cliente)

            #Crear conversacion activa en MongoDB y Mysql
            dbMongoManager.crear_conversacion_activa(celular)
            conversacion_id_mysql = dbMySQLManager.insertar_conversacion(
                cliente_id=cliente_id_mysql,
                mensaje="Inicio de conversacion por lead, outbound",
                tipo_conversacion="activa",
                resultado=None,
                estado_conversacion="activa"
            )
        else:
            print("Cliente ya existe:", cliente)
            # por ahora 
            print(f"Cliente ya existente, omitiendo procesamiento: {cliente}")
            continue

            cliente_id_mysql = dbMySQLManager.obtener_id_cliente_por_celular(celular)

            #Verificar si ya existe una conversacion activa en Mysql
            if not dbMySQLManager.obtener_conversacion_activa(cliente_id_mysql):
                dbMongoManager.crear_conversacion_activa(celular)
                dbMySQLManager.insertar_conversacion(
                    cliente_id=cliente_id_mysql,
                    mensaje="Inicio de conversacion por lead, outbound",
                    tipo_conversacion="activa",
                    resultado= None,
                    estado_conversacion="activa"
                )
        
        prioridad_lead = lead.get("Prioridad_Lead")
        if prioridad_lead is None:
            prioridad_lead = 1

        lead_id_mysql = dbMySQLManager.insertar_lead_zoho(
            cliente_id=cliente_id_mysql,
            fecha_contacto=datetime.now(),
            prioridad_lead=prioridad_lead,
            lead_source=lead.get("Lead_Source", "Desconocido"),
            campaña=lead.get("Campaing_Name", ""),
            canal_lead=lead.get("Canal_Lead", "Desconocido"),
            estado_lead=lead.get("Lead_Status", "nuevo").lower(),
            notas="Lead generado automáticamente",
            tipo_lead= lead["Tipo_de_Lead"]
        )  

        # Crear una interaccion en MongoDB
        dbMongoManager.crear_nueva_interaccion_vacia(celular)

        #Enviar plantilla al lead usando twilio
        print("Enviando plantilla al lead de numero : ",celular)
        template_content_sid = promesa_pago_interesados
        parameters = f'{{"1": "{first_name}"}}'  # JSON string con parámetros
        print("Parametros de la plantilla:", parameters)
        sid = twilio.send_template_message(
            to_number=celular,
            template_content_sid=template_content_sid,
            parameters=parameters
        )
        mensaje = plantilla_promesa_pago_interesados(first_name)
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(celular, mensaje)
        dbMySQLManager.actualizar_fecha_ultima_interaccion_bot(cliente_id_mysql, datetime.now())
        #print("Estado del lead:", estado_lead)
        print("Mensaje de respuesta:", "Plantilla enviada")

def procesar_leads_en_paralelo(leads, num_procesos=4):
    """
    Divide los leads en partes iguales y los procesa en paralelo usando un pool de procesos.

    Args:
        leads (list): Lista de leads a procesar.
        num_procesos (int): Número de procesos a utilizar.
    """
    # Dividir los leads en subconjuntos
    chunk_size = len(leads) // num_procesos + (len(leads) % num_procesos > 0)
    subconjuntos = [leads[i:i + chunk_size] for i in range(0, len(leads), chunk_size)]

    # Crear pool de procesos y asignar los subconjuntos
    with multiprocessing.Pool(processes=num_procesos) as pool:
        pool.map(procesar_subconjunto, subconjuntos)


# --- CONFIGURACIÓN Y FILTRADO DE LEADS ---

if __name__ == "__main__":
    # Crear instancia del gestor de ZohoCRM
    zoho_manager = ZohoCRMManager(client_id_zoho, client_secret_zoho, 'http://localhost', refresh_token_zoho)

    # Calcular rangos de fechas
    hace_seis_meses = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    hace_dos_meses = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    hace_doces_meses = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    fecha_fin = datetime.now().strftime('%Y-%m-%d')

    # Obtener leads filtrados
    print("Fecha hace 6 meses:", hace_seis_meses)
    leads_filtrados = zoho_manager.obtener_leads_filtrados_vf(
        fecha_creacion=hace_doces_meses,
        lead_status=["Interesado", "Promesa Pago"],
    )

    # Verificar y eliminar duplicados
    if verificar_celular_en_leads(leads_filtrados):
        print("Todos los leads tienen un número de celular.")
    else:
        print("Algunos leads no tienen un número de celular.")

    leads_unicos = eliminar_leads_duplicados(leads_filtrados)
    print(f"Cantidad original de leads: {len(leads_filtrados)}")
    print(f"Cantidad de leads después de eliminar duplicados: {len(leads_unicos)}")

    # Procesar leads en paralelo
    num_procesos = 6  # Ajusta este valor según el número de núcleos disponibles
    print(f"Procesando {len(leads_unicos)} leads en paralelo con {num_procesos} procesos.")
    procesar_leads_en_paralelo(leads_unicos, num_procesos=num_procesos)
