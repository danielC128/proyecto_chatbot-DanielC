from components.openai_component import OpenAIManager  # Importa correctamente tu componente OpenAI
import json

# Inicializar OpenAIManager
openai_manager = OpenAIManager()

# 🔹 **Conversación 1** - Cliente quiere saber su código de pago
conversation_cod_pago = {
    "conversacion_id": "conv_1712345678",
    "estado": "activa",
    "ultima_interaccion": "2025-03-04T07:05:00Z",
    "interacciones": [
        {
            "fecha": "2025-03-04T07:00:00Z",
            "mensaje_cliente": "Hola, quiero saber mi código de pago.",
            "mensaje_chatbot": ""  # OpenAI generará la respuesta
        }
    ]
}

# 🔹 **Conversación 2** - Cliente proporciona su DNI
conversation_dni = {
    "conversacion_id": "conv_1712345679",
    "estado": "activa",
    "ultima_interaccion": "2025-03-04T07:06:00Z",
    "interacciones": [
        {
            "fecha": "2025-03-04T07:02:00Z",
            "mensaje_cliente": "Mi DNI es 12345678",
            "mensaje_chatbot": ""  # OpenAI generará la respuesta
        }
    ]
}

# 🔹 **Cliente** - Para la prueba de consulta_dni_ruc_botPago
cliente = {
    "cliente_id": "cli_001",
    "nombre": "Daniel Castillo",
    "celular": "+51941729891",
    "email": "daniel@example.com",
    "conversaciones": []  # No se necesita en esta prueba
}

print("\n--- Conversación 1: Código de Pago ---")
print(json.dumps(conversation_cod_pago, indent=2, default=str))

print("\n--- Conversación 2: DNI ---")
print(json.dumps(conversation_dni, indent=2, default=str))

print("\n--- Cliente para prueba de consulta_dni_ruc_botPago ---")
print(json.dumps(cliente, indent=2, default=str))

# 🔍 Probar **clasificar_intencion_botPago** con la primera conversación
print("\n🔍 Probando clasificar_intencion_botPago...")
resultado_intencion = openai_manager.clasificar_intencion_botPago(conversation_cod_pago)
print("🔹 Resultado:", resultado_intencion)

# 🔍 Probar **obtener_dni_brindado** con la segunda conversación
print("\n🔍 Probando obtener_dni_brindado...")
dni_brindado = openai_manager.obtener_dni_brindado(conversation_dni)
print("🔹 DNI/RUC Extraído:", dni_brindado)

# 🔍 Probar **consulta_dni_ruc_botPago** con el cliente
print("\n🔍 Probando consulta_dni_ruc_botPago...")
respuesta_dni_ruc = openai_manager.consulta_dni_ruc_botPago(cliente=cliente, response_message=None, conversation_actual=None)
print("🔹 Respuesta:", respuesta_dni_ruc)
