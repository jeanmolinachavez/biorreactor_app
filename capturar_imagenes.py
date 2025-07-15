import cv2
import base64
from datetime import datetime
from pymongo import MongoClient
from config import MONGO_URI
import pytz

# Función para conexión con MongoDB
def obtener_db():
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    return db["imagenes_webcam"]

def capturar_y_guardar():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print("No se pudo acceder a la cámara.")
        return

    try:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar imagen.")
            return

        # Codificar imagen como base64
        _, buffer = cv2.imencode('.jpg', frame)
        imagen_base64 = base64.b64encode(buffer).decode('utf-8')

        # Tiempo actual en hora de Chile
        chile_tz = pytz.timezone('America/Santiago')
        tiempo_chile = datetime.now(pytz.utc).astimezone(chile_tz)

        doc = {
            "tiempo": tiempo_chile,
            "imagen": imagen_base64
        }

        # Insertar en MongoDB
        collection = obtener_db()
        collection.insert_one(doc)

        print(f"Imagen guardada correctamente a las {tiempo_chile.strftime('%Y-%m-%d %H:%M:%S')} (hora Chile)")

    except Exception as e:
        print(f"Error durante la captura o guardado: {e}")
    
    finally:
        cap.release()

if __name__ == "__main__":
    capturar_y_guardar()