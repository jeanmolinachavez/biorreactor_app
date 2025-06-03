from flask import Blueprint, request, jsonify, current_app
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return jsonify({"message": "API del biorreactor funcionando"})

@main.route('/api/sensores', methods=['POST'])
def recibir_datos():
    data = request.get_json()
    if not data or 'dominio' not in data:
        return jsonify({'error': 'Falta campo dominio'}), 400

    # Añadir timestamp automaticamente
    data['tiempo'] = datetime.utcnow()
    data['id_dispositivo'] = data.get('id_dispositivo', 'desconocido')

    # Insertar en MongoDB
    dominio = data.pop('dominio')  # Usamos este nombre como colección    
    collection = current_app.mongo.db[dominio]
    collection.insert_one(data)

    return jsonify({'message': f'Datos guardados en dominio {dominio}'}), 201

@main.route('/api/datos', methods=['GET'])
def obtener_datos():
    dominio = request.args.get('dominio')
    id_dispositivo = request.args.get('id_dispositivo')
    if not dominio:
        return jsonify({'error': 'Falta parámetro dominio'}), 400

    limit = request.args.get('limit', default=200, type=int)
    if limit <= 0:
        return jsonify({'error': 'El parámetro limit debe ser mayor que 0'}), 400

    colecciones = current_app.mongo.db.list_collection_names()
    if dominio not in colecciones:
        return jsonify({'error': f'No existe la colección {dominio}'}), 404

    collection = current_app.mongo.db[dominio]

    # Armamos el filtro
    filtro = {}
    if id_dispositivo:
        filtro['id_dispositivo'] = id_dispositivo

    # Consulta filtrada
    cursor = collection.find(filtro).sort("tiempo", -1).limit(limit)

    datos = []
    for doc in cursor:
        tiempo = doc.get("tiempo")
        if isinstance(tiempo, datetime):
            tiempo_str = tiempo.isoformat() + "Z"
        else:
            tiempo_str = str(tiempo)

        datos.append({
            'tiempo': tiempo_str,
            'id_dispositivo': doc.get('id_dispositivo'),
            'temperatura': doc.get('temperatura'),
            'ph': doc.get('ph'),
            'oxigeno': doc.get('oxigeno'),
            'turbidez': doc.get('turbidez'),
            'conductividad': doc.get('conductividad')
        })

    return jsonify(list(reversed(datos)))

@main.route('/api/registro_comida', methods=['POST'])
def registrar_comida():
    data = request.get_json()
    if not data or data.get("evento") != "comida":
        return jsonify({'error': 'JSON inválido o evento incorrecto'}), 400

    data['tiempo'] = datetime.utcnow()

    collection = current_app.mongo.db.registro_comida
    collection.insert_one(data)

    return jsonify({'message': 'Registro de comida guardado correctamente'}), 201

@main.route('/api/registro_comida', methods=['GET'])
def obtener_registros_comida():
    collection = current_app.mongo.db.registro_comida
    cursor = collection.find().sort("tiempo", -1).limit(200)
    registros = []
    for doc in cursor:
        tiempo = doc.get("tiempo")
        if isinstance(tiempo, datetime):
            tiempo_str = tiempo.isoformat() + "Z"
        else:
            tiempo_str = str(tiempo)

        registros.append({
            'tiempo': tiempo_str,
            'evento': doc.get('evento')
        })
    return jsonify(list(reversed(registros)))