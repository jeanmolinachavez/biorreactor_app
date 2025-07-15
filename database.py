from pymongo import MongoClient
from config import MONGO_URI
import pytz

# Conversión centralizada a horario chileno
def convertir_a_chile(fecha_utc):
    if fecha_utc is None:
        return None
    chile_tz = pytz.timezone("America/Santiago")
    if fecha_utc.tzinfo is None:
        fecha_utc = fecha_utc.replace(tzinfo=pytz.utc)
    return fecha_utc.astimezone(chile_tz)

def obtener_datos(dominio='dominio_ucn', limit=5000):
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

def obtener_registro_comida(limit=5000):
    client = MongoClient(MONGO_URI)
    db = client["biorreactor_app"]
    collection = db["registro_comida"]
    cursor = collection.find().sort("tiempo", -1).limit(limit)
    
    registros = []
    for doc in cursor:
        tiempo = convertir_a_chile(doc.get("tiempo"))
        id_dispositivo = doc.get("id_dispositivo", "Desconocido")  # por si falta el campo
        registros.append({
            'tiempo': tiempo.strftime('%Y-%m-%d %H:%M:%S') if tiempo else "Sin tiempo",
            'id_dispositivo': id_dispositivo
        })

    client.close()
    return list(reversed(registros))
