#!/bin/bash
gunicorn -c gunicorn_config.py app:app

    # Intencion "dudas, consultas, etc" -> pasamos el mensaje del cliente, conversacion actual, conversacion historica del cliente para que chat nos devuelva una respuesta.
    # Intencion "obtener horarios libres" -> chatgpt nos debe dar la fecha de cuando desea los horarios disponibles en formato AAAA-MM-DD HH:MM
    # Intencion "agendar cita" -> chatgpt nos debe decir el dia y hora en formato AAAA-MM-DD HH:MM, agendamos esta cita en una base de datos podria ser donde esten las citas no confirmadas y cada cierto tiempo limpiamos estas citas no confirmadas como por cada 2 horas.
    # Intencion "generar link de pago" -> generamos el link de pago con los datos del cliente y mandamos a chat esa informacion para que responda adecuadamente
    # Proceso interno -> "confirmar pago" -> nos llega la confirmación del pago, informamos al cliente y lo añadimos a la conversacion actual en la parte de respuesta del chatbot y agendamos ahora si la cita.