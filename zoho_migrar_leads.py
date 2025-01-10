from components.zoho_component import ZohoCRMManager
from components.database_mysql_zoho import DataBaseMySQLManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from datetime import datetime, timedelta
from helpers.helpers import format_number
import multiprocessing


zoho_manager = ZohoCRMManager(client_id_zoho, client_secret_zoho, 'http://localhost', refresh_token_zoho)
dbmysql_manager = DataBaseMySQLManager()

# Calcula la fecha de hace 6 meses a partir de hoy
hace_seis_meses = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
hace_dos_meses = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
hace_doces_meses = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
fecha_fin = datetime.now().strftime('%Y-%m-%d')
fecha = '2024-09-16'

print("Fecha hace 6 meses:", hace_seis_meses)
#leads_filtrados = zoho_manager.obtener_todos_leads()
leads_filtrados = zoho_manager.obtener_todos_los_leads(
    limit=5
)
#print("Lead ejemplo : ",leads_filtrados[0])

#agregado, mensaje_agregrado = dbmysql_manager.agregar_lead(leads_filtrados[0])
#print(f"Lead agregado: {agregado}, mensaje: {mensaje_agregrado}")

# Verificar que se hayan obtenido leads
if not leads_filtrados:
    print("No se obtuvieron leads para procesar.")
else:
    # Iterar sobre cada lead y agregarlos a la base de datos
    for lead in leads_filtrados:
        try:
            agregado, mensaje_agregado = dbmysql_manager.agregar_lead(lead)
            if agregado:
                print(f"Lead con ID {lead.get('id')} agregado exitosamente.")
            else:
                print(f"Error al agregar el lead con ID {lead.get('id')}: {mensaje_agregado}")
        except Exception as e:
            print(f"Excepción al agregar el lead con ID {lead.get('id')}: {e}")

print(f"Cantidad original de leads: {len(leads_filtrados)}")

