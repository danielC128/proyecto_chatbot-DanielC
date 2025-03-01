from openai import OpenAI
#from api_keys.api_keys import openai_api_key
from prompt.prompt import prompt_intenciones, prompt_lead_estado, prompt_cliente_nombre, prompt_lead_estado_zoho, prompt_intencionesv2,prompt_consulta_v4, prompt_intencionces_codPago, prompt_cliente_dni_ruc, prompt_obtener_dni, prompt_obtener_dniv2
from helpers.helpers import formatear_conversacion, formatear_historial_conversaciones, formatear_horarios_disponibles
import pytz
import json
import os
import re
from datetime import datetime
from api_keys.api_keys import openai_api_key

class OpenAIManager:
    def _init_(self):
        self.client = OpenAI(api_key=openai_api_key)

    def consulta(self, cliente,conversation_actual, conversation_history,cliente_nuevo,campania):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_consulta_v4(cliente,cliente_nuevo,campania) + formatear_conversacion(conversation_actual)},
            ],
            max_tokens=250,
        )
        return response.choices[0].message.content.strip()
    
    #LA SIGUIENTE FUNCIÓN ANALIZA LA VARIABLE conversation_actual , para determinar la intención, sin embargo
    #conversation_actual tiene TODA LA CONVERSACION del cliente con el bot, no solo la actual,  entonces por eso
    #se limita a max_tokens=100 para que analice solo la última parte ya que rivas no definió eso de que cuándo
    #una conversacion acaba , por lo que no hay conversation_history como tal , solo hay una sola conversacion
    #que está en conversation_actual

    def clasificar_intencion(self, conversation_actual, conversation_history):
        conversacion_actual_formateada = formatear_conversacion(conversation_actual)
        #conversacion_history_formateada = formatear_historial_conversaciones(conversation_history)
        print("Fecha actual",datetime.now(pytz.timezone("America/Lima")).strftime("%Y-%m-%d"))
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_intencionesv2(datetime.now(pytz.timezone("America/Lima")).strftime("%Y-%m-%d")) + conversacion_actual_formateada},
                #{"role": "user", "content": conversacion_actual_formateada}
            ],
            max_tokens=100,
        )
        #print("Conversación actual formateada:", conversacion_actual_formateada)
        #print("Prompt intenciones:", prompt_intenciones(datetime.now(pytz.timezone("America/Lima")).strftime("%Y-%m-%d")) + conversacion_actual_formateada)
        return response.choices[0].message.content.strip()

    def consultaHorarios(self,cliente_mysql, horarios_disponibles, conversation_actual, conversation_history, fecha,cliente_nuevo,campania):
        horarios_disponibles = formatear_horarios_disponibles(horarios_disponibles)
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_consulta_v4(cliente_mysql,cliente_nuevo,campania) + formatear_conversacion(conversation_actual)
                    + f"\n Los horarios disponibles para que le digas al cliente son {horarios_disponibles}"},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    def consultaCitareservada(self,cliente_mysql, reserva_cita, conversation_actual, conversation_history,cliente_nuevo,campania):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_consulta_v4(cliente_mysql,cliente_nuevo,campania) + formatear_conversacion(conversation_actual)
                    + "\n Dile que la cita ha sido reservada para  el ...  y mandale el link pago mencionandole que atraves de este link puede pagar usando yape, plin o tarjetas credito/debito. Recuerda indicarle al cliente que dentro del link no debe ingresar nada donde dice N° Orden y en donde dice celular ingresar el numero de celular desde donde nos esta escribiendo por favor para poder asociar el pago a su cita.  }"},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    
    def consultaCitaDelCliente(self,cliente_mysql, cita, conversation_actual, conversation_history,cliente_nuevo,campania):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_consulta_v4(cliente_mysql,cliente_nuevo,campania) + formatear_conversacion(conversation_actual)
                    + "\n Dile que en esta fecha y horario el cliente ya tiene una cita agendada. Responde adecuadamente. }"},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    
    def consultaPago(self, cliente_mysql,link_pago, conversation_actual, conversation_history,cliente_nuevo,campania):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_consulta_v4(cliente_mysql,cliente_nuevo,campania) + formatear_conversacion(conversation_actual)
                    },
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    def consultaLead(self, lead):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_lead_estado(lead) },
            ],
            max_tokens=100,
        )
        print("Prompt lead :", prompt_lead_estado(lead))
        return response.choices[0].message.content.strip()
    
    def consultaLeadZoho(self, lead):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_lead_estado_zoho(lead) },
            ],
            max_tokens=100,
        )
        #print("Prompt lead :", prompt_lead_estado_zoho(lead))
        return response.choices[0].message.content.strip()
    
    def consultaNombre(self, cliente, response_message,conversation_actual):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_cliente_nombre(cliente, response_message,formatear_conversacion(conversation_actual))},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    def extract_datetime(self, message):
        # Aquí deberías implementar la lógica para extraer la fecha y hora de un mensaje
        # Ejemplo básico:
        date_str = "2024-10-25"
        time_str = "10:00"
        return date_str, time_str



#FUNCIONES PARA BOT CODIGO PAGO

    #posible error, las verificciones en formato json , si no funciona prueba ponerlo como el clasificar_intencion original
    def clasificar_intencion_botPago(self, conversation_actual):
        try:
            # Formatear la conversación actual
            conversacion_actual_formateada = formatear_conversacion(conversation_actual)

            # Obtener la fecha actual en zona horaria de Lima
            fecha_actual = datetime.now(pytz.timezone("America/Lima")).strftime("%Y-%m-%d")
            print("Fecha actual:", fecha_actual)

            # Generar el mensaje del sistema con el prompt
            prompt_sistema = prompt_intencionces_codPago(fecha_actual) + conversacion_actual_formateada

            # Llamar a la API de OpenAI (GPT-4o)
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt_sistema}],
                max_tokens=100,  #cambiar este dato en caso pruebes con un mensaje largo y openai no lo analice por completo la conversa
            )

            # Obtener la respuesta generada
            respuesta_texto = response.choices[0].message.content.strip()
            print("Respuesta del modelo:", respuesta_texto)  # Log de depuración

            # Intentar cargar la respuesta como JSON
            try:
                #limpiar respuesta_texto
                respuesta_texto = re.sub(r"```json|```", "", respuesta_texto).strip()
                respuesta_json = json.loads(respuesta_texto)
                
                # Validar que la clave "intencion" esté presente en el JSON
                if "intencion" in respuesta_json:
                    return respuesta_json
                else:
                    print("Advertencia: La respuesta no contiene la clave 'intencion'.")
                    return {"error": "Respuesta inválida del modelo"}
            
            except json.JSONDecodeError:
                print("Error: La respuesta del modelo no es un JSON válido.")
                return {"error": "Formato incorrecto de la respuesta"}

        except Exception as e:
            print("Error al clasificar la intención:", str(e))
            return {"error": "Error en la clasificación"}


    def consulta_dni_ruc_botPago(self, cliente, response_message=None, conversation_actual=None):
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt_cliente_dni_ruc(cliente, response_message, formatear_conversacion(conversation_actual))},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    


    def obtener_dni_brindado(self, conversation_actual):
        """
        Usa OpenAI para extraer el DNI o RUC de la conversación actual.
        """
        conversacion_texto = formatear_conversacion(conversation_actual)  # Convertir la conversación a texto
        
        # Generar el prompt para OpenAI
        prompt = prompt_obtener_dniv2(conversacion_texto)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": prompt}],
                max_tokens=50
            )

            respuesta_texto = response.choices[0].message.content.strip()
            print("Respuesta OpenAI:", respuesta_texto)  # Para depuración

            # Intentar parsear la respuesta como JSON
            dni_data = json.loads(respuesta_texto)

            # Validar la estructura del JSON
            if isinstance(dni_data, dict) and "tipo" in dni_data and "numero" in dni_data:
                if dni_data["tipo"] in ["DNI", "RUC"] and dni_data["numero"].isdigit():
                    return dni_data  # Retorna el DNI o RUC detectado
            
            return None  # No se encontró un documento válido

        except Exception as e:
            print("Error al procesar el DNI/RUC:", str(e))
            return None
