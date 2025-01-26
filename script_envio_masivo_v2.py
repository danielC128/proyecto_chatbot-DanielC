import multiprocessing
from components.database_mysql_component import DataBaseMySQLManager
from components.twilio_component import TwilioManager
from api_keys.api_keys import seguimiento_interesados_ifc_bot_24_01_25  # Este es tu template_content_sid

def procesar_clientes(clientes_chunk):
    """
    Procesa un grupo de clientes:
      - Si bound == True, actualiza el campo in_out a True.
      - Envía el template Twilio (sin parámetros).
    
    Retorna una tupla (num_enviados, num_in_out_actualizados).
    """
    # Crear instancias dentro de cada proceso
    mysqlmanager = DataBaseMySQLManager()
    twilio = TwilioManager()
    template_content_sid = seguimiento_interesados_ifc_bot_24_01_25

    num_enviados = 0
    num_in_out_actualizados = 0

    for cliente in clientes_chunk:
        cliente_id = cliente['cliente_id']
        bound_val = cliente.get('bound', False)
        celular = cliente.get('celular', None)

        print(f"Procesando cliente {cliente_id} con bound={bound_val} y celular={celular}")
        # 1. Si bound == True, actualizar in_out a True
        if bound_val == True:
            mysqlmanager.actualizar_in_out_cliente(cliente_id, True)
            num_in_out_actualizados += 1

        # 2. Enviar plantilla (si tiene número de celular)
        if celular:
            # No se requieren parámetros en esta plantilla
            twilio.send_template_message(
                to_number=celular,
                template_content_sid=template_content_sid
            )
            num_enviados += 1

    return (num_enviados, num_in_out_actualizados)

def main():
    mysqlmanager = DataBaseMySQLManager()

    # Obtener clientes del 2024-12-01 al 2025-01-25 con estados ['seguimiento', 'interesado']
    clientes = mysqlmanager.obtener_clientes_filtrados(
        fecha_inicio='2024-12-01',
        fecha_fin='2025-01-25',
        estado=['seguimiento', 'interesado'],
    )

    if not clientes:
        print("No se encontraron clientes en el rango de fechas y estados especificados.")
        return

    # Dividir la lista de clientes en chunks para procesamiento en paralelo
    num_procesos = multiprocessing.cpu_count()  # Se pueden usar menos si se desea
    chunk_size = max(1, len(clientes) // num_procesos)
    clientes_chunks = [clientes[i:i + chunk_size] for i in range(0, len(clientes), chunk_size)]

    # Crear un pool de procesos y mapear la función
    with multiprocessing.Pool(num_procesos) as pool:
        resultados = pool.map(procesar_clientes, clientes_chunks)

    # Sumar resultados de todos los procesos
    total_enviados = sum(r[0] for r in resultados)
    total_in_out = sum(r[1] for r in resultados)

    print(f"Total de clientes procesados: {len(clientes)}")
    print(f"Total de plantillas enviadas: {total_enviados}")
    print(f"Total de clientes con in_out actualizado a True: {total_in_out}")

if __name__ == "__main__":
    main()
