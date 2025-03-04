import time  # Importar time para hacer pausas entre intentos

@celery.task
def enviar_respuesta_v4(celular, cliente_nuevo, profileName):
    print("Enviando respuesta a:", celular)

    twilio = TwilioManager()
    openai = OpenAIManager()
    dbMongoManager = DataBaseMongoDBManager()
    dbMySQLManager = DataBaseMySQLManager()
    dbBigQueryManager = DataBaseBigQueryManager()

    cliente = dbMongoManager.obtener_cliente_por_celular(celular)
    if not cliente:
        return  # Cliente no existe en MongoDB, no hay conversación.

    conversation_actual = dbMongoManager.obtener_conversacion_actual(cliente["celular"])
    estado_conversacion = dbMongoManager.obtener_estado_conversacion(cliente["celular"])

    if estado_conversacion == "se_solicito_dni":
        for intento in range(5):  # Intentamos hasta 5 veces obtener el DNI
            try:
                doc_data = openai.obtener_dni_brindado(conversation_actual)
                if doc_data and doc_data["numero"]:  
                    break  # Si encontramos el DNI, salimos del bucle
            except Exception as e:
                print(f"Error obteniendo DNI en intento {intento + 1}: {e}")
            time.sleep(1)  # Esperar 1 segundo antes de reintentar
        
        if not doc_data or not doc_data["numero"]:
            response_message = "El documento ingresado no es válido. Por favor envía un DNI (8 dígitos) o RUC (11 dígitos)."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        dni = doc_data["numero"]
        tipo_documento = doc_data["tipo"]
        print(f"El DNI obtenido es: {dni}")

        if not dbBigQueryManager.cliente_esta_activo(dni):
            response_message = "No encontramos tu información en nuestra base de datos. Verifica tu DNI/RUC e intenta de nuevo."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        datos_cliente = dbBigQueryManager.obtener_datos_cliente(dni)
        if not datos_cliente:
            response_message = "No encontramos tu información en nuestra base de datos. Inténtalo más tarde."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return
        
        nombre, apellido, celular_bq, email = datos_cliente["Nombres"], datos_cliente["Apellido_Paterno"], datos_cliente["Telf_SMS"], datos_cliente["E_mail"]
        dbMySQLManager.insertar_cliente(dni, tipo_documento, nombre, apellido, celular_bq, email)
        id_cliente = dbMySQLManager.obtener_id_cliente_por_dni(dni)

        if dbBigQueryManager.tiene_1_contrato_o_mas(dni) != 1:
            response_message = "Parece ser que tienes más de un contrato activo. Contáctanos para más información."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        codigo_pago, tipo_codigo = dbBigQueryManager.obtener_codigo_1contrato(dni)
        if codigo_pago == -1:
            response_message = "No encontramos un código de pago asociado a tu cuenta. Contáctanos para más información."
            dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
            twilio.send_message(cliente["celular"], response_message)
            return

        dbMySQLManager.insertar_codigoPago(id_cliente, codigo_pago, tipo_codigo, "", datetime.now())
        response_message = f"Tu código {tipo_codigo} es: {codigo_pago}. Puedes utilizarlo para completar tu pago."
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)

        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], None)
        return

    # **Intentos al clasificar intención**
    intencion = None
    for intento in range(5):
        try:
            intencion = openai.clasificar_intencion_botPago(conversation_actual)
            intencion_list = json_a_lista(intencion)
            if intencion_list:
                break  # Si obtenemos una intención válida, salimos del bucle
        except Exception as e:
            print(f"Error clasificando intención en intento {intento + 1}: {e}")
        time.sleep(1)

    if not intencion_list:
        response_message = "Lo siento, no pude entender tu mensaje. Por favor, intenta de nuevo."
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
        response_message = openai.consulta_dni_ruc_botPago(cliente, None, conversation_actual)
        dbMongoManager.guardar_respuesta_ultima_interaccion_chatbot(cliente["celular"], response_message)
        twilio.send_message(cliente["celular"], response_message)
        dbMongoManager.actualizar_estado_conversacion(cliente["celular"], "se_solicito_dni")
        clear_scheduled_task_id(celular)
        print(f"Terminó la tarea de solicitar DNI/RUC para {celular}, limpiando task_id en Redis.")

    else:
        print("Otra intención detectada. No se procesa.")
