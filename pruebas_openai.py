import unittest
import json
import os
from openai import OpenAI
from components.openai_component import OpenAIManager  # Asegúrate de que el nombre del archivo sea correcto

class TestOpenAIManagerWithAPI(unittest.TestCase):

    def setUp(self):
        """Configura OpenAI con una clave real"""
        self.openai_manager = OpenAIManager()
        
        # Asegurarse de que la clave API esté configurada
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  

    def test_clasificar_intencion_botPago(self):
        """Prueba clasificar_intencion_botPago con la API real"""
        conversation_actual = {
            "interacciones": [
                {"mensaje_cliente": "Hola, quiero saber mi código de pago."}
            ]
        }
        
        resultado = self.openai_manager.clasificar_intencion_botPago(conversation_actual)
        print("Resultado prueba 1 -> \n", resultado)
        print("FIN Resultado prueba 1 \n")
        
        # Asegurar que la respuesta tiene el formato esperado
        self.assertIn("intencion", resultado)
    
    def test_consulta_dni_ruc_botPago(self):
        """Prueba consulta_dni_ruc_botPago con la API real"""
        cliente = {
            "nombre": "Juan Perez",
            "celular": "987654321"  # Ahora es un diccionario con el campo celular
        }
        response_message = {
            "interacciones": [
                {"mensaje_cliente": "Mi DNI es 12345678"}
            ]
        }
        conversation_actual = {
            "interacciones": [
                {"mensaje_cliente": "Hola, necesito mi código de pago."}
            ]
        }

        resultado = self.openai_manager.consulta_dni_ruc_botPago(cliente, None, conversation_actual)
        print("Resultado prueba 2 -> \n", resultado)
        print("FIN Resultado prueba 2 \n")

        self.assertIsInstance(resultado, str)  # Asegurar que devuelve un string


    def test_obtener_dni_brindado(self):
        """Prueba obtener_dni_brindado con la API real"""
        conversation_actual = {
            "interacciones": [
                {"mensaje_cliente": "Hola, mi DNI es 87654321."}
            ]
        }

        resultado = self.openai_manager.obtener_dni_brindado(conversation_actual)
        print("Resultado prueba 3 -> \n", resultado)
        print("FIN Resultado prueba 3\n")
        self.assertIsInstance(resultado, dict)  # Debe devolver un diccionario con el DNI
        self.assertIn("tipo", resultado)
        self.assertIn("numero", resultado)

if __name__ == "__main__":
    unittest.main()
