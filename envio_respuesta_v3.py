
#Falta agregar los datos a la tabla conversacion (hacerlo en los returns)
#Falta un prompt y una funcion de openai para brindar informacion (al ultimo)
@celery.task
def enviar_respuesta_v3(celular, cliente_nuevo, profileName):
    print("Enviando respuesta a:", celular)

    twilio = TwilioManager()
    openai = OpenAIManager()
    dbMongoManager = DataBaseMongoDBManager()
    dbMySQLManager = DataBaseMySQLManager()
    dbBigQueryManager = DataBaseBigQueryManager()

    #Obtener cliente mediante el celular que escribió
    cliente = dbMongoManager.obtener_cliente_por_celular(celular)
    if not cliente:
        return  # Cliente no existe en MongoDB, no hay conversación.

    #Obtener la conversacion del cliente (por como está diseñado obtiene TODA la conversacion, todo el historial mejor dicho)
    conversation_actual = dbMongoManager.obtener_conversacion_actual(cliente["celular"])

    # Verificamos si el cliente ya está en proceso de enviar su DNI/RUC
    estado_conversacion = dbMongoManager.obtener_estado_conversacion(cliente["celular"])

    # Si el estado es "se_solicito_dni" busca obtener el DNI que supuestamente escribio el cliente, si no lo obtiene hace return
    # y si lo obtiene , procesa adecuadamente todo y devuelve el código , haciendo de igual forma return

    if estado_conversacion == "se_solicito_dni":

        #OBTENER EL DNI
        doc_data = openai.obtener_dni_brindado(conversation_actual)
        dni = doc_data["numero"] if doc_data else None  #la variable deberia ser dni_ruc
        tipo_documento = doc_data["tipo"] if doc_data else None

        #verificar doc_data
        if doc_data is None:
            #el siguiente response también puede ser un prompt para openai, de momento es así
            response_message = "El documento ingresado no es válido. Por favor envía un DNI (8 dígitos) o RUC (11 dígitos)."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        print(f"El dni obtenido es: {dni}")
        #FIN OBTENER DNI

        #UNA VEZ OBTENIDO EL DNI

        #PROCEDE VALIDAR DATOS DEL CLIENTE
        # Verificar si el cliente está activo
        if not dbBigQueryManager.cliente_esta_activo(dni):
            #lo siguiente podría ser un prompt
            response_message = "No encontramos tu información en nuestra base de datos. Verifica tu DNI/RUC e intenta de nuevo."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        # Obtener datos del cliente
        datos_cliente = dbBigQueryManager.obtener_datos_cliente(dni)

        # Verificar datos
        if not datos_cliente:
            #lo siguiente podría ser un prompt
            response_message = "No encontramos tu información en nuestra base de datos. Inténtalo más tarde."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        nombre, apellido, celular_bq, email = datos_cliente["Nombres"], datos_cliente["Apellido_Paterno"], datos_cliente["Telf_SMS"], datos_cliente["E_mail"]

        # Insertar cliente en MySQL si no existe
        #si no funciona prueba poner estado tambien al final de los parametros
        dbMySQLManager.insertar_cliente(dni, tipo_documento, nombre, apellido, celular_bq, email)

        # Obtener el ID del cliente en MySQL
        id_cliente = dbMySQLManager.obtener_id_cliente_por_dni(dni)

        # Verificar si el cliente tiene solo 1 contrato
        if dbBigQueryManager.tiene_1_contrato_o_mas(dni) != 1:
            response_message = "Parece ser que tienes más de un contrato activo. Contáctanos para más información."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        # Obtener el código de pago
        codigo_pago, tipo_codigo = dbBigQueryManager.obtener_codigo_1contrato(dni)
        if codigo_pago == -1:
            response_message = "No encontramos un código de pago asociado a tu cuenta. Contáctanos para más información."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        # Insertar código en MySQL
        dbMySQLManager.insertar_codigoPago(id_cliente, codigo_pago, tipo_codigo, "", datetime.now())

        # Enviar código al cliente
        #Hacer un prompt para enviar el código y ponerlo en response_message
        response_message = f"Tu código {tipo_codigo} es: {codigo_pago}. Puedes utilizarlo para completar tu pago."
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)

        # IMPORTANTE Resetear estado de conversación , lo pone como None , pero se puede poner como "activa" para seguir la logica de Rivas
        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], None)
        return




    # ESTA ZONA DE ACÁ ABAJO es si no nos encontramos en proceso de analizar el dni
    # y brindarle el código de pago


    # Si no está en espera de DNI, clasificamos la intención del mensaje , esto es si el estado de la conversacion es
    # cualquiera menos "se_solicito_dni"
    intencion = openai.clasificar_intencion_botPago(conversation_actual)
    intencion_list = json_a_lista(intencion)

    if "informacion" in intencion_list:
        #Generar mediante chatgpt texto explicativo del proceso
        response_message = "Existen 3 tipos de códigos de pago: Recaudación, Extranet y Especial. ¿Necesitas más detalles?"
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        #agregar fecha de interaccion a la tabla conversacion (creo) de mysql
        twilio.send_message(cliente["celular"], response_message)


        clear_scheduled_task_id(celular) #probar eliminar esto si no funciona
        print(f"Terminó la tarea de dar informacion para {celular}, limpiando task_id en Redis.")

    elif "pago" in intencion_list:
        #usar consulta dni ruc
        response_message = openai.consulta_dni_ruc_botPago(cliente, None , conversation_actual)
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        #agregar fecha de interaccion a la tabla conversacion (creo) de mysql
        twilio.send_message(cliente["celular"], response_message)

        # Guardamos en MongoDB que esperamos el DNI , servirá para la siguiente iteración
        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], "se_solicito_dni")

        clear_scheduled_task_id(celular) #probar eliminar esto si no funciona
        print(f"Terminó la tarea solicitar dni o ruc para {celular}, limpiando task_id en Redis.")
    else:
        print("Otra intención detectada. No se procesa.")


