import time  # Importar time para hacer pausas entre intentos

@celery.task
def enviar_respuesta_v3(celular, cliente_nuevo, profileName):
    print("Enviando respuesta a:", celular)

    twilio = TwilioManager()
    openai = OpenAIManager()
    dbMongoManager = DataBaseMongoDBManager()
    dbMySQLManager = DataBaseMySQLManager()
    dbBigQueryManager = DataBaseBigQueryManager()

    # Obtener cliente mediante el celular que escribió
    cliente = dbMongoManager.obtener_cliente_por_celular(celular)
    if not cliente:
        return  # Cliente no existe en MongoDB, no hay conversación.

    # Obtener la conversación actual del cliente
    conversation_actual = dbMongoManager.obtener_conversacion_actual(cliente["celular"])

    # Verificamos si el cliente ya está en proceso de enviar su DNI/RUC
    estado_conversacion = dbMongoManager.obtener_estado_conversacion(cliente["celular"])

    # Si el estado es "se_solicito_dni", buscar el DNI brindado por el cliente
    if estado_conversacion == "se_solicito_dni":
        doc_data = None
        for intento in range(5):
            try:
                doc_data = openai.obtener_dni_brindado(conversation_actual)
                if doc_data:
                    break  # Si obtenemos el DNI correctamente, salimos del bucle
            except Exception as e:
                print(f"Error al obtener DNI en intento {intento + 1}: {e}")
            time.sleep(1)

        dni = doc_data["numero"] if doc_data else None
        tipo_documento = doc_data["tipo"] if doc_data else None

        if doc_data is None:
            response_message = "El documento ingresado no es válido. Por favor envía un DNI (8 dígitos) o RUC (11 dígitos)."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        print(f"El DNI obtenido es: {dni}")

        # Verificar si el cliente está activo en BigQuery
        if not dbBigQueryManager.cliente_esta_activo(dni):
            response_message = "No encontramos tu información en nuestra base de datos. Verifica tu DNI/RUC e intenta de nuevo."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        # Obtener datos del cliente
        datos_cliente = dbBigQueryManager.obtener_datos_cliente(dni)
        if not datos_cliente:
            response_message = "No encontramos tu información en nuestra base de datos. Inténtalo más tarde."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        nombre, apellido, celular_bq, email = datos_cliente["Nombres"], datos_cliente["Apellido_Paterno"], datos_cliente["Telf_SMS"], datos_cliente["E_mail"]

        # Insertar cliente en MySQL si no existe
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
        response_message = f"Tu código {tipo_codigo} es: {codigo_pago}. Puedes utilizarlo para completar tu pago."
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)

        # Resetear estado de conversación
        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], None)
        return

    # Si no está en espera de DNI, clasificamos la intención del mensaje
    intencion = None
    for intento in range(5):
        try:
            intencion = openai.clasificar_intencion_botPago(conversation_actual)
            intencion_list = json_a_lista(intencion)
            if intencion_list:
                break  # Si obtenemos la intención correctamente, salimos del bucle
        except Exception as e:
            print(f"Error al clasificar intención en intento {intento + 1}: {e}")
        time.sleep(1)

    if not intencion_list:
        response_message = "Lo siento, no pude entender tu mensaje. Por favor intenta de nuevo."
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)
        return

    if "informacion" in intencion_list:
        response_message = "Existen 3 tipos de códigos de pago: Recaudación, Extranet y Especial. ¿Necesitas más detalles?"
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)

        clear_scheduled_task_id(celular)
        print(f"Terminó la tarea de dar información para {celular}, limpiando task_id en Redis.")

    elif "pago" in intencion_list:
        response_message = None
        for intento in range(5):
            try:
                response_message = openai.consulta_dni_ruc_botPago(cliente, None, conversation_actual)
                if response_message:
                    break  # Si obtenemos una respuesta válida, salimos del bucle
            except Exception as e:
                print(f"Error en consulta_dni_ruc_botPago en intento {intento + 1}: {e}")
            time.sleep(1)

        if not response_message:
            response_message = "Hubo un problema al procesar tu solicitud. Inténtalo de nuevo más tarde."

        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)

        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], "se_solicito_dni")

        clear_scheduled_task_id(celular)
        print(f"Terminó la tarea de solicitar DNI/RUC para {celular}, limpiando task_id en Redis.")
    else:
        print("Otra intención detectada. No se procesa.")
