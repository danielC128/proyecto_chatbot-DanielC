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

#leads_filtrados = zoho_manager.obtener_todos_leads()
contacts = zoho_manager.obtener_todos_contacts(
    limit=1
)
print("Contact ejemplo : ",contacts[0])

#agregado, mensaje_agregrado = dbmysql_manager.agregar_lead(leads_filtrados[0])
#print(f"Lead agregado: {agregado}, mensaje: {mensaje_agregrado}")

agregado, error, mensaje_agregado = dbmysql_manager.agregar_contact(contacts[0])

print(f"Contact agregado: {agregado}, mensaje: {mensaje_agregado}")

print(f"Cantidad original de contacts: {len(contacts)}")

