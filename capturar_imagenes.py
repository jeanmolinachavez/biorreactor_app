import cv2
import base64
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_URI

# Conexión con MongoDB
client = MongoClient(MONGO_URI)
db = client["biorreactor_app"]
collection = db["imagenes_webcam"]

def capturar_y_guardar():
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    if not ret:
        print("Error al capturar imagen")
        return

    _, buffer = cv2.imencode('.jpg', frame)
    imagen_base64 = base64.b64encode(buffer).decode('utf-8')

    doc = {
        "tiempo": datetime.utcnow(),
        "imagen": imagen_base64
    }
    collection.insert_one(doc)
    cap.release()
    print("Imagen guardada correctamente")

if __name__ == "__main__":
    capturar_y_guardar()