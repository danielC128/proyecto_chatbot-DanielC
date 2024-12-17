from components.twilio_component import TwilioManager
from api_keys.api_keys import promesa_pago_interesados, promesa_pago

twilio_manager = TwilioManager()
template_content_sid = promesa_pago_interesados
parameters = '{"1": "John"}'  # JSON string con parámetros

sid = twilio_manager.send_template_message(
    to_number='+51932709296',
    template_content_sid=template_content_sid,
    parameters=parameters
)

