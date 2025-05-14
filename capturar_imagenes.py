import cv2
import base64
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_URI
import pytz

# Conexión con MongoDB
client = MongoClient(MONGO_URI)
db = client["biorreactor_app"]
collection = db["imagenes_webcam"]

def capturar_y_guardar():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    ret, frame = cap.read()
    if not ret:
        print("Error al capturar imagen")
        return

    _, buffer = cv2.imencode('.jpg', frame)
    imagen_base64 = base64.b64encode(buffer).decode('utf-8')

    # Convertir hora UTC a hora de Chile
    chile_tz = pytz.timezone('America/Santiago')
    tiempo_chile = datetime.now(pytz.utc).astimezone(chile_tz)

    doc = {
        "tiempo": tiempo_chile,
        "imagen": imagen_base64
    }
    collection.insert_one(doc)
    cap.release()
    print(f"Imagen guardada correctamente a las {tiempo_chile.strftime('%Y-%m-%d %H:%M:%S')} (hora Chile)")

if __name__ == "__main__":
    capturar_y_guardar()