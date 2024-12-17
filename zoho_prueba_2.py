from components.zoho_component import ZohoCRMManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from datetime import datetime, timedelta
from helpers.helpers import format_number
import multiprocessing

# Función para verificar si todos los leads tienen el campo de número de celular
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

# Función para eliminar leads duplicados por número de celular
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

zoho_manager = ZohoCRMManager(client_id_zoho, client_secret_zoho, 'http://localhost', refresh_token_zoho)

# Calcula la fecha de hace 6 meses a partir de hoy
hace_seis_meses = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
hace_dos_meses = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
hace_doces_meses = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
fecha_fin = datetime.now().strftime('%Y-%m-%d')
fecha = '2024-09-16'


# Ejemplo de uso: obtener leads de los últimos 6 meses con estado "promesa de pago"
#leads_filtrados = zoho_manager.obtener_leads_filtradosv2(
#    lead_status="Interesado",
#    limit=10
#    )

#leads_filtrados = zoho_manager.obtener_leads_filtradosv3(
#    lead_status="Promesa Pago",
#    campaign_name="Experimento 11: Ideas Marco",
#    start_date=fecha,
#    limit=10
#)#

#Promesa Pago
#Interesado

print("Fecha hace 6 meses:", hace_seis_meses)
leads_filtrados = zoho_manager.obtener_leads_filtrados_vf(
    fecha_creacion=hace_doces_meses,
    lead_status=["Interesado", "Promesa Pago"],
)

# Verificar si todos los leads tienen número de celular
if verificar_celular_en_leads(leads_filtrados):
    print("Todos los leads tienen un número de celular.")
else:
    print("Algunos leads no tienen un número de celular.")

# Eliminar duplicados basándose en el número de celular
leads_unicos = eliminar_leads_duplicados(leads_filtrados)
print(f"Cantidad original de leads: {len(leads_filtrados)}")
print(f"Cantidad de leads después de eliminar duplicados: {len(leads_unicos)}")

# Mostrar los leads obtenidos
#for lead in leads_filtrados:
#    print(zoho_manager.formatear_lead(lead))
