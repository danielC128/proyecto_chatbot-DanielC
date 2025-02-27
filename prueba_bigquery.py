from google.cloud import bigquery
from components.database_bigquery_component import DataBaseBigQueryManager
from helpers.helpers import agregar_coma_al_dni

# Crear una instancia del administrador de BigQuery
db_manager = DataBaseBigQueryManager()

# Probar la función con un DNI específico
dni_prueba = "09771642"  # Cambia esto por un DNI que exista en la base de datos
dni_coma = agregar_coma_al_dni(dni_prueba)
es_activo = db_manager.cliente_esta_activo(dni_coma)

# Mostrar el resultado
if es_activo:
    print(f"✅ El cliente con DNI {dni_prueba} está ACTIVO en la base de datos.")
else:
    print(f"❌ El cliente con DNI {dni_prueba} NO está ACTIVO en la base de datos.")





dni_a_buscar = "09771642"
dni_coma = agregar_coma_al_dni(dni_a_buscar)
datos_cliente = db_manager.obtener_datos_cliente(dni_coma)
    
if datos_cliente:
    print("✅ Datos del cliente encontrados:")
    print(datos_cliente)
else:
    print(f"❌ No se encontró un cliente con DNI {dni_a_buscar}.")


dni_a_buscar = "09714719"
dni_coma = agregar_coma_al_dni(dni_a_buscar)
cod_bco = db_manager.obtener_codigo_recaudacion_1contrato(dni_coma)

if cod_bco:
    print(f"✅ El cliente con DNI {dni_a_buscar} tiene el Cod_Bco: {cod_bco}")
else:
    print(f"❌ No se encontró un Cod_Bco único para el DNI {dni_a_buscar} o el cliente no está activo.")



dni_a_buscar = "71023115"
dni_coma = agregar_coma_al_dni(dni_a_buscar)
cod_especial = db_manager.obtener_codigo_especial_1contrato(dni_coma)

if cod_especial:
    print(f"✅ El cliente con DNI {dni_a_buscar} tiene el cod_especial: {cod_especial}")
else:
    print(f"❌ No se encontró un cod_especial único para el DNI {dni_a_buscar} o el cliente no está activo.")



dni_a_buscar = "09714719"
dni_coma = agregar_coma_al_dni(dni_a_buscar)
cod_especial = db_manager.obtener_codigo_1contrato(dni_coma)

if cod_especial:
    print(f"✅ El cliente con DNI {dni_a_buscar} tiene el codigo: {cod_especial}")
else:
    print(f"❌ No se encontró un codigo para el DNI {dni_a_buscar} o el cliente no está activo.")



dni_a_buscar = "09714719"
dni_coma = agregar_coma_al_dni(dni_a_buscar)
flag = db_manager.tiene_1_contrato_o_mas(dni_coma)
if(flag == 1):
    print("Tiene solo 1 contrato")
elif(flag == 2):
    print("Tiene más de un contrato")
else:
    print("No aparece en la bd")