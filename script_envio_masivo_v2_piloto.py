import multiprocessing
from components.database_mysql_component import DataBaseMySQLManager
from components.twilio_component import TwilioManager
from api_keys.api_keys import seguimiento_interesados_ifc_bot_24_01_25  # Este es tu template_content_sid

def main():
    mysqlmanager = DataBaseMySQLManager()

    # Obtener clientes del 2024-12-01 al 2025-01-25 con estados ['seguimiento', 'interesado']
    clientes = mysqlmanager.obtener_clientes_filtrados(
        fecha_inicio='2024-12-01',
        fecha_fin='2025-01-25',
        estado=['seguimiento', 'interesado'],
        limite=2
    )

    if not clientes:
        print("No se encontraron clientes en el rango de fechas y estados especificados.")
        return

    print(clientes)

if __name__ == "__main__":
    main()
