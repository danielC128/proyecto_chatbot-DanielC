from helpers.helpers import extraer_json

response_message = '{"mensaje": "¡Genial, Sebastián! Tu cita ha sido agendada para el martes 14 a las 2:30 p.m. 😊 Puedes realizar el pago usando el siguiente link: [https://express.culqi.com/pago/HXHKR025JY], aceptamos Yape, Plin o tarjetas de crédito/débito. Recuerda que hay un"}'


print("Response message:", response_message)
response_message = extraer_json(response_message)
print("Response message despues de extraer json:", response_message)