import multiprocessing
from components.database_mysql_component import DataBaseMySQLManager
from components.database_mongodb_component import DataBaseMongoDBManager
from datetime import datetime, timedelta

def procesar_clientes(clientes_chunk):
    """
    Procesa un grupo de clientes para determinar y actualizar su estado basado en interacciones.

    Args:
        clientes_chunk (list): Lista de clientes a procesar.

    Returns:
        int: Número de clientes cambiados a 'interesado'.
    """
    mysqlmanager = DataBaseMySQLManager()
    mongomanager = DataBaseMongoDBManager()

    clientes_interesados = 0

    for cliente in clientes_chunk:
        numero_interacciones = mongomanager.contar_interacciones_ultima_conversacion(cliente['celular'])
        
        if numero_interacciones > 1:
            # Cambiar estado a 'interesado'
            mysqlmanager.actualizar_estado_cliente(cliente['cliente_id'], 'interesado')
            #mysqlmanager.actualizar_estado_historico_cliente(cliente['cliente_id'], 'interesado')
            #clientes_interesados += 1
        elif numero_interacciones == 1:
            # Mantener estado en 'seguimiento'
            mysqlmanager.actualizar_estado_cliente(cliente['cliente_id'], 'seguimiento')
            mysqlmanager.actualizar_estado_historico_cliente(cliente['cliente_id'], 'seguimiento')
            clientes_interesados += 1

    return clientes_interesados

def main():
    mysqlmanager = DataBaseMySQLManager()

    # Obtener clientes de la última semana en estado 'seguimiento' con bound=True
    hace_una_semana = datetime.now() - timedelta(days=7)
    clientes = mysqlmanager.obtener_clientes_filtrados(
        fecha_inicio=hace_una_semana,
        estado='interesado',
        bound=True
    )

    # Dividir los clientes en chunks para procesamiento paralelo
    num_procesos = multiprocessing.cpu_count()  # Número de procesos a usar
    chunk_size = max(1, len(clientes) // num_procesos)  # Tamaño de cada chunk
    clientes_chunks = [clientes[i:i + chunk_size] for i in range(0, len(clientes), chunk_size)]

    # Usar un Pool de procesos
    with multiprocessing.Pool(num_procesos) as pool:
        resultados = pool.map(procesar_clientes, clientes_chunks)

    # Sumar resultados de todos los procesos
    total_interesados = sum(resultados)

    print(f"Total de clientes cambiados a 'seguimiento': {total_interesados}")

if __name__ == "__main__":
    main()
