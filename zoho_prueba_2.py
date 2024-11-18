from components.zoho_component import ZohoCRMManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from datetime import datetime, timedelta

zoho_manager = ZohoCRMManager(client_id_zoho, client_secret_zoho, 'http://localhost', refresh_token_zoho)

# Calcula la fecha de hace 6 meses a partir de hoy
hace_seis_meses = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
fecha_fin = datetime.now().strftime('%Y-%m-%d')
fecha = '2024-09-16'

print("Fecha hace 6 meses:", hace_seis_meses)
# Ejemplo de uso: obtener leads de los últimos 6 meses con estado "promesa de pago"
leads_filtrados = zoho_manager.obtener_leads_filtradosv2(
    lead_status="Promesa Pago",
    campaign_name="Experimento 11: Ideas Marco",
    fecha_creacion=fecha,
    limit=10
)

leads_filtrados = zoho_manager.obtener_leads_filtradosv3(
    lead_status="Promesa Pago",
    campaign_name="Experimento 11: Ideas Marco",
    start_date=fecha,
    limit=10
)

# Mostrar los leads obtenidos
for lead in leads_filtrados:
    print(zoho_manager.formatear_lead(lead))
