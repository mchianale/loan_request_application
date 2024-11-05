from flask import Flask, render_template,request, jsonify,  redirect, url_for
import json
import requests
import time  

CONFIG_PATH = 'config.json'
# Initialize UserService with the configuration
config = json.load(open(CONFIG_PATH))
url_root = f"http://backend_service:{config['backend_service']['port']}/api/"

process = {
                1 : {"title" : "Chargement de la demande", "description" : "Évaluation textuelle de votre demande..."},
                2 : {"title" : "Evaluation de la demande", "description" : "Évaluation de votre profil et du projet immobilier..."},
                3 : {"title" : "Prise de décision", "description" : "Évaluation finale de la demande..."}
            }

session = {
    "user_id" : None, 
    "session_id" : None, 
    "current_request_step" : None,
    "pending_id" : None,
    "last_input" : "",
}

app = Flask(__name__)
@app.route('/')
def home():
    global session 
    if session['pending_id']:
        return render_template('process.html', process=process, step=session['current_request_step'])
    if not session['user_id'] or not session['session_id']:
        session['user_id'], session['session_id'], session['current_request_step'], session['pending_id'] = None, None, None, None
        return render_template('home.html')
    else:
        return render_template('home_log.html', user_id=session['user_id'])

# login
@app.route('/login', methods=['GET', 'POST'])
def login():
    global session 
    if session['pending_id']:
        return render_template('process.html', process=process, step=session['current_request_step'])
    if session['user_id'] is not None and session['session_id'] is not None:
        return render_template('home_log.html', user_id=session['user_id'])
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # login
        try:        
            # Define the payload (data) you want to send
            url = url_root + 'user/login'
            payload = {
                "user_id": username,
                "password": password
            }

            # Make the POST request
            response = requests.post(url, json=payload)
            if response.status_code == 201:
                session['user_id'] = username
                # get session['session_id']
                session['session_id'] = response.json()['session_id']
                return render_template('home_log.html', user_id=session['user_id'])
            else:
                return render_template('login.html', error=response.json()['error'])
        except Exception as e:
            render_template('login.html', error="Une erreur est survenue lors de la connexion.")
    return render_template('login.html')

# sign up
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    global session 
    if session['pending_id']:
        return render_template('process.html', process=process, step=session['current_request_step'])
    if session['user_id'] is not None and session['session_id'] is not None:
        return render_template('home_log.html', user_id=session['user_id'])
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        # register
         
        url = url_root + 'user/signup'
        payload = {
            "user_id": username,
            "password": password,
            "confirm_password" : confirm_password
        }

        # Make the POST request
        response = requests.post(url, json=payload)
    
        if response.status_code == 201:
            session['user_id'] = username  # Enregistre le nom d'utilisateur
            # get session['session_id']
            session['session_id'] = response.json()['session_id']
            return render_template('home_log.html', user_id=session['user_id'])
        else:
            return render_template('signup.html', error=response.json()['error'])
    
    return render_template('signup.html')


# logout
@app.route('/logout', methods=['GET'])
def logout():
    # dans tout les cas je retourne vers home, mais peux ajouter des systemes de secruites en focntion des conditions
    global session 
    if session['pending_id']:
        return render_template('process.html', process=process, step=session['current_request_step'])
    if not session['user_id']:
        return render_template('home.html')
    # logout
    url = url_root + 'user/logout'
    payload = {
        "user_id": session['user_id'],
        "session_id" : session['session_id']
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        session['user_id'], session['session_id'] = None, None # logout
        return render_template('home.html')
    # il a un session['user_id'] qui n'existe pas ou une session['session_id'] qui n'est pas fiable
    return render_template('home.html')


@app.route('/new_request', methods=['GET', 'POST'])
def new_request():
    global session 
    if session['pending_id']:
        return render_template('process.html', process=process, step=session['current_request_step'])
    if session['user_id'] is None or session['session_id'] is None:
        return render_template('home.html')
    if request.method == 'POST':
        input =  request.form['request']
        session['last_input'] = input
        url = url_root + 'pending/new_request'
        payload = {
            "user_id": session['user_id'],
            "session_id" : session['session_id'],
            "input" : input
        }
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            session['pending_id']  = response.json()['pending_id']
            session['current_request_step'] = 1
            return render_template('process.html', process=process, step=session['current_request_step'])
        if response.status_code != 401:
           return render_template('home.html')
            
        # des requetes sont actuellemnt evaluer
        return render_template('new_loan_request.html', error=response.json()['error'])
    return render_template('new_loan_request.html')


@app.route('/get_process_step')
def get_process_step():
    global session 
    if not session['pending_id']: 
        if session['user_id'] is None or session['session_id'] is None:
            return render_template('home.html')
        return jsonify({'redirect': 'home_log', 'user_id': session['user_id']})

    # Update the session['current_request_step'] from the service
    url = url_root + 'pending/get_process_step'
    payload = {
        "user_id": session['user_id'],
        "session_id" : session['session_id'],
        "pending_id" : session['pending_id']
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        session['current_request_step'] = response.json()['step']
        # If process is complete, reset the step and provide a redirect
        if session['current_request_step'] == 4:
            temp_pending_id = session['pending_id']
            session['current_request_step'], session['pending_id'] = None, None
            return jsonify({'redirect': 'see_request', 'pending_id': temp_pending_id})

        # If ongoing, return JSON response with the current step data
        return jsonify({
            'step': session['current_request_step'],
            'process': {
                'title': process[session['current_request_step']]['title'],
                'description': process[session['current_request_step']]['description']
            }
    })
   
    return jsonify({'message_error' : response.json()['error']})

@app.route('/retry')
def retry():
    global session 
    if not session['pending_id']: 
        if session['user_id'] is None or session['session_id'] is None:
            return render_template('home.html')
        return jsonify({'redirect': 'home_log', 'user_id': session['user_id']})
    
    url = url_root + '/pending/delete'
    payload = {
        "user_id": session['user_id'],
        'pending_id' : session['pending_id'],
        'forced' : True
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        session['current_request_step'], session['pending_id'] = None, None
        return render_template('new_loan_request.html', input=session['last_input'])
    return render_template('home.html')

@app.route('/user_requests', methods=['GET'])
def user_requests():
    if session['pending_id']:
        return render_template('process.html', process=process, step=session['current_request_step'])
    if session['user_id'] is None or session['session_id'] is None:
        return render_template('home.html')
    
    page = int(request.args.get('page', 1))
    items_per_page = 4
    # Fetch loan requests for the user (replace this with your database call)
    url = url_root + 'request/requests'
    payload = {
        "user_id": session['user_id']
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        loan_requests = response.json()['loan_requests']
        total_requests = len(loan_requests)
        total_pages = max((total_requests + items_per_page - 1) // items_per_page, 1)
        start = (page - 1) * items_per_page
        end = start + items_per_page
        loan_requests_paginated = loan_requests[start:end]

        return render_template(
            'user_requests.html',
            loan_requests=loan_requests_paginated,
            page=page,
            total_pages=total_pages
        )
    return render_template('home.html')

@app.route('/delete_request/<string:id>', methods=['POST'])
def delete_request(id): 
    # Convert the string ID to an ObjectId
    url = url_root + '/request/delete'
    payload = {
        "user_id": session['user_id'],
        'request_id' : id
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        return redirect(url_for('user_requests'))
    return render_template('home.html')
    
@app.route('/see_request/<string:id>', methods=['GET', 'POST'])
def see_request(id):
    # Convert the string ID to an ObjectId
    url = url_root + '/request/by_id'
    payload = {
        "user_id": session['user_id'],
        'request_id' : id
    }
    response = requests.post(url, json=payload)
    if response.status_code == 201:
        loan_request = response.json()['loan_request']
        if not loan_request:
            if session['user_id'] is not None and session['session_id'] is not None:
                return redirect(url_for('user_requests')) 
            else:
                return redirect(url_for('home'))
        loan_request['property_score'] = loan_request.get('property_score', 0)
        loan_request['user_score'] = loan_request.get('user_score', 0)
        loan_request['global_score'] = loan_request.get('global_score', 0)
        return render_template("loan_request.html", id=id, request=loan_request['approvalDecisionInformation'],date=loan_request['date'], input_text=loan_request['request'] )
    return redirect(url_for('home'))

if __name__ == '__main__':
    
    url = url_root + '/test'
    while True:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                break 
            time.sleep(1)
        except:
            time.sleep(1)
 
    port = config['flask_frontend']['port']
    app.run(host='0.0.0.0', port=port)
