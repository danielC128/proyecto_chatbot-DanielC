import unittest
import os
from twilio.base.exceptions import TwilioRestException
from components.twilio_component import TwilioManager  # Ajusta el import según tu estructura

class TestTwilioManager(unittest.TestCase):

    def setUp(self):
        """ Configura TwilioManager para pruebas """
        self.twilio_manager = TwilioManager()
        self.test_number = "+51941729891"  # Número de prueba real , mi numero personal
        self.test_message = "Este es un mensaje de prueba desde Twilio."

    def test_send_message_success(self):
        """ Prueba que send_message envía correctamente un mensaje de WhatsApp """
        try:
            message_sid = self.twilio_manager.send_message(self.test_number, self.test_message)
            print("Mensaje enviado con SID:", message_sid)
            self.assertIsInstance(message_sid, str)
        except TwilioRestException as e:
            self.fail(f"TwilioRestException: {e}")

#    def test_send_message_invalid_number(self):
#        """ Prueba enviar un mensaje a un número inválido y maneja la excepción """
#        invalid_number = "+00000000000"
#        with self.assertRaises(TwilioRestException):
#            self.twilio_manager.send_message(invalid_number, self.test_message)

    #def test_send_message_empty_body(self):
     #   """ Prueba enviar un mensaje vacío y verifica si Twilio lo permite o falla """
      #  with self.assertRaises(TwilioRestException):
       #     self.twilio_manager.send_message(self.test_number, "")

if __name__ == "__main__":
    unittest.main()
