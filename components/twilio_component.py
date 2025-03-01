from twilio.rest import Client
import os
from api_keys.api_keys import account_sid, auth_token


#SI SE USA
#Es el componente de twilio

class TwilioManager:
    def _init_(self):
        self.client = self._authenticate()

    def _authenticate(self):
        return Client(account_sid, auth_token)


    def send_message(self, to_number, message_body):
        to_number = f'whatsapp:{to_number}' if not to_number.startswith('whatsapp:') else to_number

        message = self.client.messages.create(
            body=message_body,
            from_='whatsapp:+51941010026',  # Cambia por tu número de Twilio
            to=to_number
        )
        print(f"Message sent to {to_number}: {message.sid}")
        message_status = self.client.messages(message.sid).fetch()
        print(f"Message status: {message_status.status}")
        return message.sid

    def send_template_message(self, to_number, template_content_sid, parameters=None):
        # Si 'to_number' no viene con el prefijo 'whatsapp:', se lo agregamos
        to_number = f'whatsapp:{to_number}' if not to_number.startswith('whatsapp:') else to_number
        
        # Construimos los argumentos para la creación del mensaje
        message_kwargs = {
            'content_sid': template_content_sid,
            'from_': 'whatsapp:+51944749102',  # Número de Twilio
            'to': to_number
        }

        # Si hay parámetros, los añadimos a 'content_variables'
        if parameters:
            message_kwargs['content_variables'] = parameters

        # Enviamos el mensaje con los argumentos dinámicos
        message = self.client.messages.create(**message_kwargs)

        print("message : ", message)
        print(f"Template message sent to {to_number}: {message.sid}")

        return message.sid