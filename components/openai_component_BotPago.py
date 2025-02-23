from openai import OpenAI
from api_keys.api_keys import openai_api_key

from helpers.helpers import formatear_conversacion
from datetime import datetime
import pytz

class OpenAIManagerBotPagos:
    def __init__(self):
        self.client = OpenAI(api_key=openai_api_key)
    
    def clasificar_intencion(self, conversation_actual):
        #no se usa conversation_history
        conversa_formateada = formatear_conversacion(conversation_actual)
        print("Fecha actual",datetime.now(pytz.timezone("America/Latina")).strftime("%Y-%m-%d"))
        #en la parte siguiente debo usar mi archivo prompt-botPago , mejor dicho, una funcion de ahí, pero no me deja
        #por lo que debo verlo despues, por ahora estamos viendo la base de datos
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": }
            ]
        )