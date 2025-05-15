import serial
import time
import json
import requests

# Configurar puerto serial y velocidad y url api de flask app
SERIAL_PORT = 'COM7'
BAUD_RATE = 9600
API_URL_SENSORES = 'http://localhost:5000/api/sensores'
API_URL_REGISTRO_COMIDA = 'http://localhost:5000/api/registro_comida'

ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
print("Esperando datos JSON del sensor...")

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        print(f"Recibido: {line}")

        # Convertir la linea a JSON
        data = json.loads(line)

        # Decidir a qué endpoint mandar
        if "evento" in data:
            url = API_URL_REGISTRO_COMIDA
        else:
            url = API_URL_SENSORES

        # Enviar a la API
        response = requests.post(url, json=data)

        if response.status_code == 201:
            print("Datos enviados correctamente")
        else:
            print("Error al enviar:", response.text)

    except json.JSONDecodeError:
        print("Línea recibida no es JSON válido")

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)