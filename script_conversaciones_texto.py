from components.database_mongodb_component import DataBaseMongoDBManager
from components.database_mysql_component import DataBaseMySQLManager

# Función para formatear conversaciones
def formatear_conversacion(conversacion):
    if not conversacion:
        return "No hay conversación activa."

    interacciones = conversacion.get("interacciones", [])
    formatted = "\n".join(
        [
            f"{i + 1}. Cliente: {inter['mensaje_cliente']}\n   Chatbot: {inter['mensaje_chatbot']}"
            for i, inter in enumerate(interacciones)
        ]
    )
    return formatted if formatted else "No hay interacciones registradas."

# Función para ordenar clientes por estado
def ordenar_clientes_por_estado(clientes):
    prioridad_estados = {
        "cita agendada": 1,
        "promesas de pago": 2,
        "interesado": 3,
        "seguimiento": 4,
        "activo": 5,
        "no interesado": 6,
        "pendiente de contacto": 7,
        "nuevo": 8
    }
    return sorted(clientes, key=lambda cliente: prioridad_estados.get(cliente.get("estado", "nuevo"), 8))

# Escritura del archivo de texto
def escribir_archivo(clientes, mongodb_manager):
    output_file = "clientes_conversaciones.txt"

    with open(output_file, "w", encoding="utf-8") as file:
        for cliente in clientes:
            nombre = cliente.get("nombre", "Desconocido")
            celular = cliente.get("celular", "No especificado")
            estado = cliente.get("estado", "Desconocido")

            conversacion = mongodb_manager.obtener_conversacion_actual(celular)
            conversacion_formateada = formatear_conversacion(conversacion)

            file.write(f"Cliente: {nombre}\n")
            file.write(f"Celular: {celular}\n")
            file.write(f"Estado: {estado}\n")
            file.write("Conversación:\n")
            file.write(f"{conversacion_formateada}\n")
            file.write("-" * 50 + "\n")

    print(f"Archivo generado: {output_file}")


# Ejecución principal
def main():
    mysql_manager = DataBaseMySQLManager()
    mongodb_manager = DataBaseMongoDBManager()

    # Definir filtro para clientes
    #filtro = "bound = 1 and nombre not like 'prueba%' and DATE(DATE_SUB(fecha_creacion, INTERVAL 5 HOUR)) = CURDATE();"
    filtro = "bound = 1 and nombre not like 'prueba%'"

    # Obtener todos los clientes de MySQL
    clientes = mysql_manager.obtener_clientes_por_filtro(filtro)

    # Ordenar clientes por estado
    clientes_ordenados = ordenar_clientes_por_estado(clientes)

    # Generar archivo de texto
    escribir_archivo(clientes_ordenados, mongodb_manager)

if __name__ == "__main__":
    main()