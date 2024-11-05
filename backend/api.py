from flask import Flask, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
import bcrypt
import json
import re
import time
from datetime import datetime

CONFIG_PATH = 'config.json'

# Load configuration
config = json.load(open(CONFIG_PATH, encoding='utf-8'))

# Initialize Flask app
app = Flask(__name__)
# wait for db mongo load and connect
while True:
    try:
        client = MongoClient('mongodb', 27017)
        break
    except:
        time.sleep(5)

# Get db & collections
db = client[config["db"]["name"]]
db_loan_pendings = db[config["db"]["loan_pendings"]]
db_loan_requests = db[config["db"]["loan_requests"]]
db_users = db[config["db"]["users"]]

# Clear pendings collections 
db_loan_pendings.delete_many({})

# end point test
@app.route('/api/test', methods=['GET'])
def get_test():
    return jsonify({"message" : "ok"}), 200
# for pendings
@app.route('/api/pending/all_pendings', methods=['GET'])
def all_pendings():
    loan_pendings = list(db_loan_pendings.find({"status": "Pending"}))
    return jsonify({'loan_pendings' : loan_pendings})


@app.route('/api/pending/update_status', methods=['POST'])
def update_status():
        data = request.json
        if not data or 'user_id' not in data or 'pending_id' not in data:
            return jsonify({"error": "Identifiant utilisateur ou pending_id manquant"}), 404
        
        db_loan_pending = db_loan_pendings.find_one({"user_id": data['user_id'], "_id": data['pending_id']})
        if not db_loan_pending:
            return jsonify({"error" : "La loan pending n'existe pas"}), 401
        if 'error' not in data:
            db_loan_pendings.update_one(
                                        {"_id": data['pending_id']},
                                        {
                                            "$set": {
                                                "status": data['status']
                                            }
                                        }
                                    )
        elif data['error']:
            db_loan_pendings.update_one(
                                    {"_id": data['pending_id']},
                                    {
                                        "$set": {
                                            "status": data['status'],
                                            "error" : data['error']
                                        }
                                    }
                            )
        return jsonify({"message" : "succes to update"}), 201

@app.route('/api/pending/delete', methods=['POST'])
def delete_pending():
    data = request.json
    if not data or 'user_id' not in data or 'pending_id' not in data:
        return jsonify({"error": "Identifiant utilisateur ou pending_id manquant"}), 404
    db_loan_pending = db_loan_pendings.find_one({"user_id": data['user_id'], "_id": data['pending_id']})
    if not db_loan_pending:
        return jsonify({"error" : "La loan pending n'existe pas"}), 401
    if not data['forced'] and db_loan_pending['status'] != 'Finished' and db_loan_pending['status'] != 'Pending':
        return jsonify({"error" : "interdiction de supprimer"}), 404
    db_loan_pendings.delete_one({"_id": data['pending_id']})
    return jsonify({"message" : "succes to delete"}), 201

@app.route('/api/pending/new_request', methods=['POST'])
def new_request():
    data = request.json
    if not data or 'user_id' not in data or 'session_id' not in data or 'input' not in  data:
        return jsonify({"error": "Identifiant utilisateur ou session_id manquant"}), 404

    db_user = db_users.find_one({"user_id": data['user_id'], "session_id": data["session_id"]})
    if not db_user:
        return jsonify({"error": "L'identifiant utilisateur n'existe pas !"}), 404
    loan_pending = {
                    "_id": str(ObjectId()),  # Unique ID for the request
                    "user_id": data['user_id'],
                    "request" : data['input'],
                    "status": "Pending"
    }
    # push it to pending
    # insert True if not multiple request at the same time of the same user
    db_loan_pending = db_loan_pendings.find_one({"user_id" : data['user_id']})
    if not db_loan_pending:
        db_loan_pendings.insert_one(loan_pending)
        return jsonify({'pending_id' : loan_pending["_id"]}), 201
        
    return jsonify({"error": "Attendez que toutes vos demandes soient traitées."}), 401

@app.route('/api/pending/get_process_step', methods=['POST'])
def get_process_step():
    data = request.json
    if not data or 'user_id' not in data or 'session_id' not in data or 'pending_id' not in  data:
        return jsonify({"error": "Identifiant utilisateur ou session_id manquant"}), 404

    db_user = db_users.find_one({"user_id": data['user_id'], "session_id": data["session_id"]})
    if not db_user:
        return jsonify({"error": "L'identifiant utilisateur n'existe pas !"}), 404
    
    db_loan_pending = db_loan_pendings.find_one({"user_id" : data['user_id'], "_id" : data['pending_id']})
    if not db_loan_pending or db_loan_pending['status'] == 'Finished':
        if db_loan_pending and 'error' in db_loan_pending and db_loan_pending['error'] is not None:
            return jsonify({"error": "Un souci a été rencontré pendant le processus d'évaluation, veuillez dès maintenant nous excuser"}), 401   
        return jsonify({"step" : 4}), 201
    if db_loan_pending['status'] == 'Load':
        if 'error' in db_loan_pending and db_loan_pending['error'] == 'Doc too long !':
            return jsonify({"error": "Si vous plaît veuillez raccourcir la taille de votre demande."}), 401   
        if 'error' in db_loan_pending and db_loan_pending['error'] is not None:
            return jsonify({"error": "Veuillez faire part de la manière la plus claire possible, les informations requises pour évaluer votre demande (vos coordonnées, informations de revenus et charges mensuels, le montant du prêt souhaité et sa durée...)"}), 401
            
        return jsonify({"step" : 2}), 201
    if db_loan_pending['status'] == 'Evaluation':
        if 'error' in db_loan_pending:
           return jsonify({"error": "Un souci a été rencontré pendant le processus d'évaluation, veuillez dès maintenant nous excuser"}), 401   
        return jsonify({"step" : 3}), 201
    return jsonify({"step" : 1}), 201


# for request
@app.route('/api/request/requests', methods=['POST'])
def get_requests():    
    data = request.json
    if not data or 'user_id' not in data:
        return jsonify({"error": "Identifiant utilisateur manquant"}), 404
    loan_requests = list(db_loan_requests.find({"user_id": data['user_id']}))
    loan_requests = sorted(loan_requests, key=lambda x: datetime.strptime(x['date'], "%d/%m/%Y %H:%M:%S"), reverse=True)
    return jsonify({'loan_requests' : loan_requests}), 201

@app.route('/api/request/add', methods=['POST'])
def add_request():
    data = request.json
    db_loan_request = db_loan_requests.find_one({"_id": data['loan_request']["_id"]})
    if db_loan_request:
        return jsonify({"error" : "La loan request existe deja"}), 401
    db_loan_requests.insert_one(data['loan_request'])
    return jsonify({"message" : "succes to add"}), 201

@app.route('/api/request/delete', methods=['POST'])
def delete_request():
    data = request.json
    if not data or 'user_id' not in data or 'request_id' not in data:
        return jsonify({"error": "Identifiant utilisateur ou request_id manquant"}), 404
    db_loan_request = db_loan_requests.find_one({"user_id": data['user_id'], "_id": data['request_id']})
    if not db_loan_request:
        return jsonify({"error" : "La loan request n'existe pas"}), 401
    db_loan_requests.delete_one({"_id": data['request_id']})
    return jsonify({"message" : "succes to delete"}), 201

@app.route('/api/request/by_id', methods=['POST'])
def get_request():
    data = request.json
    if not data or 'user_id' not in data:
        return jsonify({"error": "Identifiant utilisateur manquant"}), 404
    loan_request = db_loan_requests.find_one({"user_id": data['user_id'], "_id" : data['request_id']})
    if loan_request:
        return jsonify({'loan_request' : loan_request}), 201
    return jsonify({'loan_request' : None}), 401

# for user
@app.route('/api/user/signup', methods=['POST'])
def signup():
    """Handle user signup."""
    data = request.json
    print(data)
    # Validate input
    if not data or 'user_id' not in data or 'password' not in data or 'confirm_password' not in data:
        return jsonify({"error": "Identifiant utilisateur ou mot de passe manquant"}), 404

    if data['password'] != data['confirm_password']:
        return jsonify({"error": "Les mots de passes ne correspondent pas !"}), 401

    if not re.match(r'^[a-zA-Z0-9_-]+$', data['user_id']):
        return jsonify({"error": "L'identifiant utilisateur n'est pas valide ! Il ne doit contenir que des lettres, des chiffres, des underscores (_) ou des tirets (-)."}), 401

    # Check if user exists
    db_user = db_users.find_one({"user_id": data['user_id']})
    if db_user:
        return jsonify({"error": "Cet identifiant utilisateur est déjà pris. Veuillez en choisir un autre."}), 409  # 409 Conflict

    # Hash password and create new user
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    session_id = str(ObjectId())
    new_user = {
        "user_id": data['user_id'],
        "password": hashed_password,
        "session_id": session_id
    }
    db_users.insert_one(new_user)
    return jsonify({'session_id': session_id}), 201  # 201 Created

@app.route('/api/user/login', methods=['POST'])
def login():
    """Handle user login."""
    data = request.json
    
    # Validate input
    if not data or 'user_id' not in data or 'password' not in data:
        return jsonify({"error": "Identifiant utilisateur ou mot de passe manquant"}), 404

    # Find user in the database
    db_user = db_users.find_one({"user_id": data['user_id']})
    if not db_user:
        return jsonify({"error": "L'identifiant utilisateur n'existe pas !"}), 404

    # Check password
    if not bcrypt.checkpw(data['password'].encode('utf-8'), db_user['password']):
        return jsonify({"error": "Mot de passe incorrect"}), 401

    # check if not pending
    if db_user['session_id']:
        db_loan_pending = db_loan_pendings.find_one({"user_id" : data['user_id']})
        if db_loan_pending:
            return jsonify({"error": "Un autre utilisateur est connecté, et une requête est actuellement en cours."}), 404
    # Update session ID
    session_id = str(ObjectId())
    db_users.update_one({"user_id": data['user_id']}, {"$set": {"session_id": session_id}})
    
    return jsonify({'session_id': session_id}), 201

@app.route('/api/user/logout', methods=['POST'])
def logout():
    data = request.json
    if not data or 'user_id' not in data or 'session_id' not in data:
        return jsonify({"error": "Identifiant utilisateur ou session_id manquant"}), 404
    # Find user in the database
    db_user = db_users.find_one({"user_id": data['user_id']})
    if not db_user:
        return jsonify({"error": "L'identifiant utilisateur n'existe pas !"}), 404
    db_user = db_users.find_one({"user_id": data['user_id'], "session_id": data["session_id"]})
    db_users.update_one({"user_id": data['user_id']},
                                {
                                    "$set": {
                                        "session_id" : None
                                    }
                                }
                            )
    return jsonify({'session_id':  data["session_id"]}), 201

@app.route('/api/user/all_users', methods=['GET'])
def get_all_users():
    return jsonify({'users' : list(db_users.find({}))}), 200

@app.route('/shutdown', methods=['POST'])
def shutdown_server():
    """Shutdown the Flask server."""
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()
    return jsonify({'status': 'Server shutting down...'}), 201

if __name__ == "__main__":
    # Run the app
    port = config['backend_service']['port']
    app.run(host="0.0.0.0", port=port)
