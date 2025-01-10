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
    y retorna dos listas de IDs de leads que fallaron al insertarse.
    
    :param leads_chunk: Lista de leads a procesar.
    :param process_number: Número identificador del proceso.
    :return: Tuple (list, list) con IDs de leads que fallaron por existir y por otros errores.
    """
    # Instanciar un gestor de base de datos para este proceso
    dbmysql_manager = DataBaseMySQLManager()
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
    
    
    # Obtener todos los leads desde Zoho CRM con un límite opcional
    # Puedes cambiar 'limit' según tus necesidades o eliminarlo para obtener todos los leads
    leads_filtrados = zoho_manager.obtener_todos_leads()  # Cambia 'limit' según requieras
    print(f"Cantidad de leads obtenidos: {len(leads_filtrados)}")
    
    # Verificar que se hayan obtenido leads
    if not leads_filtrados:
        print("No se obtuvieron leads para procesar.")
        return
    
    # Definir el número de procesos (puedes ajustarlo según tu CPU)
    num_processes = multiprocessing.cpu_count()  # O define un número fijo, e.g., 4
    
    # Definir el tamaño del chunk
    chunk_size = 100  # Por ejemplo, 100 leads por chunk
    
    # Crear chunks de leads
    chunks = [leads_filtrados[i:i + chunk_size] for i in range(0, len(leads_filtrados), chunk_size)]
    print(f"Total de chunks a procesar: {len(chunks)}")
    
    # Crear una lista de argumentos para cada chunk (cada argumento es un tuple: (leads_chunk, process_number))
    # Aquí, 'process_number' se asigna de manera cíclica para identificar fácilmente los procesos
    process_args = [(chunk, (i % num_processes) + 1) for i, chunk in enumerate(chunks)]
    
    # Crear un Pool de procesos
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Utilizar imap_unordered para asignación dinámica de tareas
        # Esto permite que los procesos tomen nuevos chunks tan pronto como terminen los anteriores
        results = pool.starmap(process_leads_chunk, process_args)
    
    # Recopilar todos los IDs que fallaron
    failed_exists_leads = []
    failed_other_leads = []
    
    for exists_ids, other_ids in results:
        failed_exists_leads.extend(exists_ids)
        failed_other_leads.extend(other_ids)
    
    # Imprimir los resultados finales
    if failed_exists_leads or failed_other_leads:
        if failed_exists_leads:
            print(f"Leads que ya existían y no se pudieron insertar ({len(failed_exists_leads)}):")
            #print(failed_exists_leads)  # Puedes comentar esto si tienes demasiados leads
        if failed_other_leads:
            print(f"Leads que fallaron por otros motivos ({len(failed_other_leads)}):")
            #print(failed_other_leads)  # Puedes comentar esto si tienes demasiados leads
    else:
        print("Todos los leads se insertaron correctamente.")
    
    print(f"Cantidad original de leads: {len(leads_filtrados)}")
    print(f"Cantidad de leads exitosos: {len(leads_filtrados) - len(failed_exists_leads) - len(failed_other_leads)}")

if __name__ == "__main__":
    main()
