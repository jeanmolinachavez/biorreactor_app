from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({"message": "API del biorreactor funcionando"})

@main.route('/api/sensores', methods=['POST'])
def recibir_datos():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No se recibió JSON'}), 400

    # Añadir timestamp automaticamente
    data['tiempo'] = datetime.utcnow()

    # Insertar en MongoDB
    collection = current_app.mongo.db.datos
    collection.insert_one(data)

    return jsonify({'message': 'Datos guardados correctamente'}), 201

@main.route('/api/datos', methods=['GET'])
def obtener_datos():
    collection = current_app.mongo.db.datos
    cursor = collection.find().sort("tiempo", -1).limit(100)
    datos = []
    for doc in cursor:
        # Formatear el campo tiempo a string ISO 8601 plano para ser leido por grafana
        tiempo = doc.get("tiempo")
        if isinstance(tiempo, datetime):
            tiempo_str = tiempo.isoformat() + "Z"
        else:
            tiempo_str = str(tiempo)  # fallback por si acaso

        datos.append({
            'tiempo': tiempo_str,
            'temperatura': doc.get('temperatura'),
            'ph': doc.get('ph'),
            'oxigeno': doc.get('oxigeno'),
            'turbidez': doc.get('turbidez'),
            'conductividad': doc.get('conductividad')
        })
    return jsonify(list(reversed(datos)))

@main.route('/api/clear', methods=['POST'])
def clear_data():
    collection = current_app.mongo.db.datos
    result = collection.delete_many({})
    return jsonify({'message': f'{result.deleted_count} documentos eliminados'}), 200