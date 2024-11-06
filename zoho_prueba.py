from components.zoho_component import ZohoCRMManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho

# Datos de autenticación
client_id = client_id_zoho
client_secret = client_secret_zoho
redirect_uri = 'http://localhost'
refresh_token = refresh_token_zoho

# Inicializa el ZohoCRMManager
zoho_manager = ZohoCRMManager(client_id, client_secret, redirect_uri, refresh_token)

# Obtener todos los clientes
leads_formateados = zoho_manager.obtener_leads_formateados(limit=5)
for lead in leads_formateados:
    print(lead)

print(zoho_manager.obtener_todos_los_leads(limit=2))