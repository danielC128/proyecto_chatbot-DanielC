from components.zoho_component import ZohoCRMManager
from components.database_mysql_zoho import DataBaseMySQLManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from datetime import datetime, timedelta
import multiprocessing
import json

def process_leads_chunk(leads_chunk, process_number):
    """
    Procesa una lista de leads: inserta cada lead en la base de datos,
    imprime mensajes de éxito o error con el número de proceso,
    y retorna una lista de IDs de leads que fallaron al insertarse.
    
    :param leads_chunk: Lista de leads a procesar.
    :param process_number: Número identificador del proceso.
    :return: Lista de IDs de leads que fallaron al insertarse.
    """
    # Instanciar un gestor de base de datos para este proceso
    dbmysql_manager = DataBaseMySQLManager()
    failed_ids = []
    failed_exists_ids = []
    failed_other_ids = []    
    
    for lead in leads_chunk:
        try:
            agregado, error_type, mensaje_agregado = dbmysql_manager.agregar_lead(lead)
            if agregado:
                print(f"Proceso {process_number}: Lead con ID {lead.get('id')} agregado exitosamente.")
            else:
                if error_type == 'exists':
                    print(f"Proceso {process_number}: El lead con ID {lead.get('id')} ya existe.")
                    failed_exists_ids.append(lead.get('id'))
                else:
                    print(f"Proceso {process_number}: Error al agregar el lead con ID {lead.get('id')}: {mensaje_agregado}")
                    failed_other_ids.append(lead.get('id'))
        except Exception as e:
            print(f"Proceso {process_number}: Excepción al agregar el lead con ID {lead.get('id')}: {e}")
            failed_other_ids.append(lead.get('id'))
    
    # Cerrar la conexión a la base de datos en este proceso
    dbmysql_manager.cerrar_conexion()
    
    return (failed_exists_ids, failed_other_ids)

def main():
    # Instanciar el gestor de Zoho CRM
    zoho_manager = ZohoCRMManager(client_id_zoho, client_secret_zoho, 'http://localhost', refresh_token_zoho)
    
    # Obtener todos los leads desde Zoho CRM (ajusta el límite según tus necesidades)
    leads_filtrados = zoho_manager.obtener_todos_leads(limit=8000)  # Cambia 'limit' según requieras
    print(f"Cantidad de leads obtenidos: {len(leads_filtrados)}")
    
    # Verificar que se hayan obtenido leads
    if not leads_filtrados:
        print("No se obtuvieron leads para procesar.")
        return
    
    # Definir el número de procesos (puedes ajustarlo según tu CPU)
    num_processes = multiprocessing.cpu_count()  # O define un número fijo, e.g., 4
    
    # Dividir los leads en chunks para cada proceso
    chunk_size = len(leads_filtrados) // num_processes
    chunks = [leads_filtrados[i * chunk_size : (i + 1) * chunk_size] for i in range(num_processes)]
    
    # Si hay leads restantes, agrégalas al último chunk
    if len(leads_filtrados) % num_processes != 0:
        chunks[-1].extend(leads_filtrados[num_processes * chunk_size:])
    
    # Crear una lista de argumentos para cada proceso (cada argumento es un tuple: (leads_chunk, process_number))
    process_args = [(chunk, i+1) for i, chunk in enumerate(chunks)]
    
    # Crear un Pool de procesos
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Mapear las tareas a los procesos
        results = pool.starmap(process_leads_chunk, process_args)

    # Recopilar todos los IDs que fallaron
    failed_exists_leads = []
    failed_other_leads = []
    
    for exists_ids, other_ids in results:
        failed_exists_leads.extend(exists_ids)
        failed_other_leads.extend(other_ids)
    
    # Imprimir los IDs de los leads que tuvieron errores
    if failed_exists_leads or failed_other_leads:
        if failed_exists_leads:
            #print(f"Leads que ya existían y no se pudieron insertar ({len(failed_exists_leads)}): {failed_exists_leads}")
            print(f"Leads que ya existían y no se pudieron insertar ({len(failed_exists_leads)})")
        if failed_other_leads:
            #print(f"Leads que fallaron por otros motivos ({len(failed_other_leads)}): {failed_other_leads}")
            print(f"Leads que fallaron por otros motivos ({len(failed_other_leads)})")
    else:
        print("Todos los leads se insertaron correctamente.")
    
    print(f"Cantidad de leads exitosos: {len(leads_filtrados) - len(failed_exists_leads) - len(failed_other_leads)}")
    print(f"Cantidad original de leads: {len(leads_filtrados)}")

if __name__ == "__main__":
    main()
