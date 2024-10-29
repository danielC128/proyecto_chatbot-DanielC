import requests
import datetime as dt

class CulqiPaymentManager:
    def __init__(self, public_key, private_key):
        self.public_key = public_key
        self.private_key = private_key
        self.base_url = "https://secure.culqi.com/v2/"
        
    def _headers(self):
        return {
            "Authorization": f"Bearer {self.private_key}",
            "Content-Type": "application/json"
        }

    def create_payment_link(self, amount, currency_code="PEN", description="Pago en Culqi", email=None):
        """
        Genera un enlace de pago con el monto y detalles específicos.
        """
        data = {
            "amount": int(amount * 100),  # Enviar en céntimos
            "currency_code": currency_code,
            "description": description,
            "payment_code": f"code-{dt.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "metadata": {
                "email": email or "cliente@example.com"
            }
        }

        response = requests.post(self.base_url + "charges", headers=self._headers(), json=data)
        if response.status_code == 201:
            print("Enlace de pago generado con éxito.")
            return response.json()
        else:
            print("Error al crear el enlace de pago:", response.json())
            return None

    def get_charge_status(self, charge_id):
        """
        Obtiene el estado de un cargo dado su ID.
        """
        response = requests.get(self.base_url + f"charges/{charge_id}", headers=self._headers())
        if response.status_code == 200:
            print("Estado del cargo obtenido con éxito.")
            return response.json()
        else:
            print("Error al obtener el estado del cargo:", response.json())
            return None