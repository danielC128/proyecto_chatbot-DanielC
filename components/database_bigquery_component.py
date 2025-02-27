#debe haber una funcion que , el cliente da su dni y con ese dni lo busco en bigquery , devuelvo los siguientes datos
#documento_identidad, tipo_documento, nombre, apellido, celular, email,estado="nuevo"
#esos datos los paso como parámetro para la funcion insertar_cliente


#FUNCIONES A TENER EN CUENTA
#1 - VALIDAR CLIENTE , es cuando el cliente te pasa su dni o ruc, verificar el campo Estado_Asociado como Activo(LISTO)
#2 - OBTENER DATOS DEL CLIENTE MEDIANTE SU DNI,  es devolver los datos del cliente para luego utilizar la funcion insertar cliente de mysql con los datos que retorne esta(LISTO)
#3 - OBTENER CODIGO DE PAGO(LISTO)
    #ESA FUNCION DEPENDE DE SI REQUIERE CODIGO DE RECAUDACION O CODIGO ESPECIAL
    #ESO SE DETERMINA MEDIANTE LA MOROSIDAD, USA EL CAMPO MORA
    #SI ES MOROSO DE M2 Y/O M3 ES CON CODIGO ESPECIAL Y LO BUSCAS EN LA OTRA TABLA
#4 - CONSULTAR LA CANTIDAD DE CONTRATOS DEL CLIENTE, PARA VER SI VA A LA RAMA SINGULAR DE CONTRATO O VARIOS CONTRATOS (v2 esto último) (LISTO)

from google.cloud import bigquery

class DataBaseBigQueryManager:
    def __init__(self):
        """Inicializa el cliente de BigQuery."""
        self.client = bigquery.Client()


    #dni_coma = agregar_coma_al_dni(dni_prueba) USAR SIEMPRE ESTO ANTES DE LLAMAR A ESTA FUNCION
    def cliente_esta_activo(self, dni):
        """
        Verifica si un cliente con el DNI dado tiene el Estado_Asociado en 'ACTIVO'.
        """

        query = """
            SELECT COUNT(*) as total
            FROM `peak-emitter-350713.FR_general.bd_fondos`
            WHERE N_Doc = @dni AND Estado_Asociado = 'ACTIVO'
        """

        # Configurar los parámetros de la consulta (es más que nada por seguridad este paso)
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("dni", "STRING", dni)
            ]
        )

        # Ejecutar la consulta
        query_job = self.client.query(query, job_config=job_config)
        result = query_job.result()

        # Obtener el resultado
        for row in result:
            return row.total > 0  # Si total > 0, el cliente está activo, si no, no

        return False  # En caso de que no se obtenga ningún resultado , es decir si el cliente no tiene ninguna fila con contrato ACTIVO







    #dni_coma = agregar_coma_al_dni(dni_prueba) USAR SIEMPRE ESTO ANTES DE LLAMAR A ESTA FUNCION
    def obtener_datos_cliente(self, dni):
        """
        Obtiene los datos de un cliente usando su DNI.
        """
        query = """
            SELECT Nombres, Apellido_Paterno, Apellido_Materno, Telf_SMS, E_mail
            FROM `peak-emitter-350713.FR_general.bd_fondos`
            WHERE N_Doc = @dni
        """

        # Configurar los parámetros de la consulta
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("dni", "STRING", dni)]
        )

        # Ejecutar la consulta
        query_job = self.client.query(query, job_config=job_config)
        result = query_job.result()

        # Obtener los datos del primer resultado (si existe)
        for row in result:
            return {
                "Nombres": row.Nombres,
                "Apellido_Paterno": row.Apellido_Paterno,
                "Apellido_Materno": row.Apellido_Materno,
                "Telf_SMS": row.Telf_SMS,
                "E_mail": row.E_mail,
            }

        return None  # Si no se encuentra el cliente





    #dni_coma = agregar_coma_al_dni(dni_prueba) USAR SIEMPRE ESTO ANTES DE LLAMAR A ESTA FUNCION
    def obtener_codigo_recaudacion_1contrato(self, dni):
        """
        Obtiene el Cod_Bco de un cliente si el DNI aparece solo una vez con Estado_Asociado en 'ACTIVO'.
        """
        query = """
            WITH clientes_activos AS (
                SELECT N_Doc, Cod_Bco
                FROM `peak-emitter-350713.FR_general.bd_fondos`
                WHERE N_Doc = @dni AND Estado_Asociado = 'ACTIVO' AND Mora IN (0, 1)
            )
            SELECT Cod_Bco
            FROM clientes_activos
            GROUP BY N_Doc, Cod_Bco
            HAVING COUNT(*) = 1;
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("dni", "STRING", dni)
            ]
        )

        query_job = self.client.query(query, job_config=job_config)
        result = query_job.result()

        row = next(result, None)  # Obtener la primera fila si existe
        return row.Cod_Bco if row else None  # Retorna el Cod_Bco si existe, de lo contrario None


    #dni_coma = agregar_coma_al_dni(dni_prueba) USAR SIEMPRE ESTO ANTES DE LLAMAR A ESTA FUNCION
    #solo funciona con 82 de los 1310 casos que están en cobranzas_m2 , eso ya es tema de la base de datos
    #obs : en la tabla cobranzas_m2 , cada cliente solo aparece 1 sola vez
    def obtener_codigo_especial_1contrato(self, dni):
        """
        Obtiene el codigo_especial de un cliente si el DNI aparece solo una vez con Estado_Asociado en 'ACTIVO'
        y si el campo Mora es 2 o 3 en la tabla `bd_fondos`. Luego, busca el codigo_especial en `envios_cobranzas_m2`
        con la misma condición de Mora.
        """
        query = """
            WITH clientes_validos AS (
                SELECT N_Doc
                FROM `peak-emitter-350713.FR_general.bd_fondos`
                WHERE N_Doc = @dni AND Estado_Asociado = 'ACTIVO' AND Mora IN (2, 3)
                GROUP BY N_Doc
                HAVING COUNT(*) = 1
            )
            SELECT e.codigo_especial
            FROM `peak-emitter-350713.FR_general.envios_cobranzas_m2` e
            JOIN clientes_validos c ON e.N_Doc = c.N_Doc
            WHERE e.Mora IN (2, 3);
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("dni", "STRING", dni)
            ]
        )

        query_job = self.client.query(query, job_config=job_config)
        result = query_job.result()

        row = next(result, None)  # Obtener la primera fila si existe
        return row.codigo_especial if row else None  # Retorna el codigo_especial si existe, de lo contrario None



    def obtener_codigo_1contrato(self, dni):
        """
        Retorna un código basado en la condición de Mora:
        - Si Mora es 0 o 1, retorna el código de obtener_codigo_recaudacion_1contrato.
        - Si Mora es 2 o 3, retorna el código de obtener_codigo_especial_1contrato.
        - Si Mora tiene cualquier otro valor o el cliente no cumple las condiciones, retorna -1.
        """

        # Verificar si el cliente aparece solo una vez con Estado_Asociado "ACTIVO"
        query = """
            SELECT Mora
            FROM `peak-emitter-350713.FR_general.bd_fondos`
            WHERE N_Doc = @dni AND Estado_Asociado = 'ACTIVO'
            GROUP BY N_Doc, Mora
            HAVING COUNT(*) = 1;
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("dni", "STRING", dni)]
        )

        query_job = self.client.query(query, job_config=job_config)
        result = query_job.result()

        row = next(result, None)  # Obtener la primera fila si existe

        if row:
            mora = row.Mora
            if mora in (0, 1):
                return self.obtener_codigo_recaudacion_1contrato(dni) , "de recaudacion"
            elif mora in (2, 3):
                return self.obtener_codigo_especial_1contrato(dni) , "especial"
        
        return -1  # Si no cumple ninguna condición, retorna -1




    def tiene_1_contrato_o_mas(self, dni):
        """
        Verifica si un cliente con el DNI dado aparece solo una vez en la tabla `bd_fondos`
        con Estado_Asociado en 'ACTIVO'. Retorna True si aparece una vez, False si aparece más de una vez,
        y None si no aparece en la tabla.
        """

        query = """
            SELECT COUNT(*) as total
            FROM `peak-emitter-350713.FR_general.bd_fondos`
            WHERE N_Doc = @dni AND Estado_Asociado = 'ACTIVO'
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("dni", "STRING", dni)]
        )

        query_job = self.client.query(query, job_config=job_config)
        result = query_job.result()

        row = next(result, None)  # Obtener el resultado si existe

        if row:
            if row.total == 1:
                return 1  # Cliente aparece solo una vez
            elif row.total > 1:
                return 2  # Cliente aparece más de una vez

        return 3  # Cliente no aparece en la tabla


