from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from dbMongoManager import obtener_cliente_por_dni, obtener_codigo_pago, guardar_mensaje
from intent_classifier import clasificar_intencion

app = Flask(__name__)

@app.route('/bot', methods=['POST'])
def whatsapp_bot():
    try:
        incoming_msg = request.form.get('Body').lower()
        sender = request.form.get('From')
        celular = sender.split('whatsapp:')[1]
        
        # Analizar la intención del mensaje
        intencion = clasificar_intencion(incoming_msg)
        
        response = MessagingResponse()
        
        if intencion == "obtener_codigo_pago":
            response.message("Por favor, envíame tu número de DNI para validar tu información.")
            guardar_mensaje(celular, incoming_msg, "solicitud de DNI")
        
        elif intencion == "informacion_proceso":
            response.message("El proceso de pago funciona de la siguiente manera: ...")
            guardar_mensaje(celular, incoming_msg, "info proceso")
        
        elif incoming_msg.isdigit() and len(incoming_msg) == 8:  # Si el usuario responde con un DNI
            cliente = obtener_cliente_por_dni(incoming_msg)
            if cliente:
                codigo_pago = obtener_codigo_pago(cliente["dni"])
                response.message(f"Tu código de pago es: {codigo_pago}")
                guardar_mensaje(celular, incoming_msg, "dni recibido, código enviado")
            else:
                response.message("No encontramos tu información. Verifica tu DNI e intenta nuevamente.")
                guardar_mensaje(celular, incoming_msg, "dni no encontrado")
        
        else:
            response.message("Lo siento, no entendí tu solicitud. ¿Puedes reformular tu pregunta?")
            guardar_mensaje(celular, incoming_msg, "mensaje no reconocido")
        
        return str(response)
    except Exception as e:
        print("Error en whatsapp_bot:", e)
        return "Error interno del servidor", 500
