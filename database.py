from pymongo import MongoClient
from config import MONGO_URI
from datetime import datetime
import pytz

# Zona horaria de Chile definida una vez
chile_tz = pytz.timezone('America/Santiago')

# Conversión centralizada a horario chileno
def convertir_a_chile(utc_dt):
    if utc_dt:
        utc_dt = utc_dt.replace(tzinfo=pytz.utc)
        return utc_dt.astimezone(chile_tz)
    else:
        return datetime.now(chile_tz)

def obtener_datos(dominio='dominio_ucn', limit=2000):
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    collection = db[dominio]
    cursor = collection.find().sort("tiempo", -1).limit(limit)
    datos = []
    for doc in cursor:
        tiempo_chile = convertir_a_chile(doc.get("tiempo"))
        datos.append({
            'tiempo': tiempo_chile.strftime('%Y-%m-%d %H:%M:%S'),
            'id_dispositivo': doc.get('id_dispositivo'),
            'temperatura': doc.get('temperatura'),
            'ph': doc.get('ph'),
            'oxigeno': doc.get('oxigeno'),
            'turbidez': doc.get('turbidez'),
            'conductividad': doc.get('conductividad')
        })

    client.close()
    return list(reversed(datos))

def obtener_registro_comida(limit=2000):
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    collection = db["registro_comida"]
    cursor = collection.find().sort("tiempo", -1).limit(limit)
    registros = []
    for doc in cursor:
        tiempo_chile = convertir_a_chile(doc.get("tiempo"))
        registros.append({
            'tiempo': tiempo_chile.strftime('%Y-%m-%d %H:%M:%S')
        })

    client.close()
    return list(reversed(registros))