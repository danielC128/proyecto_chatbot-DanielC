from components.zoho_component import ZohoCRMManager
from components.database_mysql_zoho import DataBaseMySQLManager
from api_keys.api_keys import client_id_zoho, client_secret_zoho, refresh_token_zoho
from datetime import datetime, timedelta
import multiprocessing
import json

def process_contacts_chunk(contacts_chunk, process_number):
    """
    Procesa una lista de contactos: inserta cada contacto en la base de datos,
    imprime mensajes de éxito o error con el número de proceso,
    y retorna dos listas de IDs de contactos que fallaron al insertarse.
    
    :param contacts_chunk: Lista de contactos a procesar.
    :param process_number: Número identificador del proceso.
    :return: Tuple (list, list) con IDs de contactos que fallaron por existir y por otros errores.
    """
    # Instanciar un gestor de base de datos para este proceso
    dbmysql_manager = DataBaseMySQLManager()
    failed_exists_ids = []
    failed_other_ids = []
    
    for contact in contacts_chunk:
        try:
            agregado, error_type, mensaje_agregado = dbmysql_manager.agregar_contact(contact)
            if agregado:
                print(f"Proceso {process_number}: Contacto con ID {contact.get('id')} agregado exitosamente.")
            else:
                if error_type == 'exists':
                    print(f"Proceso {process_number}: El contacto con ID {contact.get('id')} ya existe.")
                    failed_exists_ids.append(contact.get('id'))
                else:
                    print(f"Proceso {process_number}: Error al agregar el contacto con ID {contact.get('id')}: {mensaje_agregado}")
                    failed_other_ids.append(contact.get('id'))
        except Exception as e:
            print(f"Proceso {process_number}: Excepción al agregar el contacto con ID {contact.get('id')}: {e}")
            failed_other_ids.append(contact.get('id'))
    
    # Cerrar la conexión a la base de datos en este proceso
    dbmysql_manager.cerrar_conexion()
    
    return (failed_exists_ids, failed_other_ids)

def main():
    # Instanciar el gestor de Zoho CRM
    zoho_manager = ZohoCRMManager(
        client_id=client_id_zoho,
        client_secret=client_secret_zoho,
        redirect_uri='http://localhost',
        refresh_token=refresh_token_zoho
    )
    
    # Obtener todos los contactos desde Zoho CRM con un límite opcional
    # Puedes cambiar 'limit' según tus necesidades o eliminarlo para obtener todos los contactos
    contacts_filtrados = zoho_manager.obtener_todos_contacts()  # Cambia 'limit' según requieras
    print(f"Cantidad de contactos obtenidos: {len(contacts_filtrados)}")
    
    # Verificar que se hayan obtenido contactos
    if not contacts_filtrados:
        print("No se obtuvieron contactos para procesar.")
        return
    
    # Definir el número de procesos (puedes ajustarlo según tu CPU)
    num_processes = multiprocessing.cpu_count()  # O define un número fijo, e.g., 4
    print(f"Número de procesos a utilizar: {num_processes}")
    
    # Definir el tamaño del chunk
    chunk_size = 15  # Por ejemplo, 100 contactos por chunk
    
    # Crear chunks de contactos
    chunks = [contacts_filtrados[i:i + chunk_size] for i in range(0, len(contacts_filtrados), chunk_size)]
    print(f"Total de chunks a procesar: {len(chunks)}")
    
    # Crear una lista de argumentos para cada chunk (cada argumento es un tuple: (contacts_chunk, process_number))
    # Aquí, 'process_number' se asigna de manera cíclica para identificar fácilmente los procesos
    process_args = [(chunk, (i % num_processes) + 1) for i, chunk in enumerate(chunks)]
    
    # Crear un Pool de procesos
    with multiprocessing.Pool(processes=num_processes) as pool:
        # Utilizar starmap para asignación dinámica de tareas
        # Esto permite que los procesos tomen nuevos chunks tan pronto como terminen los anteriores
        results = pool.starmap(process_contacts_chunk, process_args)
    
    # Recopilar todos los IDs que fallaron
    failed_exists_contacts = []
    failed_other_contacts = []
    
    for exists_ids, other_ids in results:
        failed_exists_contacts.extend(exists_ids)
        failed_other_contacts.extend(other_ids)
    
    # Imprimir los resultados finales
    if failed_exists_contacts or failed_other_contacts:
        if failed_exists_contacts:
            print(f"Contactos que ya existían y no se pudieron insertar ({len(failed_exists_contacts)}):")
            # Limitar la impresión si hay demasiados contactos
            if len(failed_exists_contacts) <= 20:
                print(failed_exists_contacts)
            else:
                print(failed_exists_contacts[:20] + ['...'])
        if failed_other_contacts:
            print(f"Contactos que fallaron por otros motivos ({len(failed_other_contacts)}):")
            if len(failed_other_contacts) <= 20:
                print(failed_other_contacts)
            else:
                print(failed_other_contacts[:20] + ['...'])
    else:
        print("Todos los contactos se insertaron correctamente.")
    
    print(f"Cantidad original de contactos: {len(contacts_filtrados)}")
    exitosos = len(contacts_filtrados) - len(failed_exists_contacts) - len(failed_other_contacts)
    print(f"Cantidad de contactos exitosos: {exitosos}")

if __name__ == "__main__":
    main()
