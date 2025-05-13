from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime
import pytz

def obtener_datos(limit=100):
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    collection = db["datos"]

    chile_tz = pytz.timezone('America/Santiago')

    cursor = collection.find().sort("tiempo", -1).limit(limit)
    datos = []
    for doc in cursor:

        # Convertir tiempo a zona horaria de Chile
        tiempo_utc = doc.get("tiempo")
        if tiempo_utc:
            # Asegúrate de que tenga zona UTC, y luego conviértelo
            tiempo_utc = tiempo_utc.replace(tzinfo=pytz.utc)
            tiempo_chile = tiempo_utc.astimezone(chile_tz)
        else:
            tiempo_chile = datetime.now(chile_tz)

        datos.append({
            'tiempo': tiempo_chile.strftime('%Y-%m-%d %H:%M:%S'),
            'temperatura': doc.get('temperatura'),
            'ph': doc.get('ph'),
            'oxigeno': doc.get('oxigeno'),
            'turbidez': doc.get('turbidez'),
            'conductividad': doc.get('conductividad')
        })

    client.close()
    return list(reversed(datos))