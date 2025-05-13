import serial
import time
import json
import requests

# Configurar puerto serial y velocidad y url api de flask app
SERIAL_PORT = 'COM7'
BAUD_RATE = 9600
API_URL = 'http://localhost:5000/api/sensores'

ser = serial.Serial(SERIAL_PORT, BAUD_RATE)
print("Esperando datos JSON del sensor...")

while True:
    try:
        line = ser.readline().decode('utf-8').strip()
        print(f"Recibido: {line}")

        # Convertir la linea a JSON
        data = json.loads(line)

        # Enviar a la API
        response = requests.post(API_URL, json=data)

        if response.status_code == 201:
            print("Datos enviados correctamente")
        else:
            print("Error al enviar:", response.text)

        time.sleep(1800)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(2)