# Real estate loan application Service
This project is a containerized application designed to manage new loan applications, automatically evaluating each request based on multiple integrated services. The application leverages Docker to streamline service deployment and orchestration, ensuring a modular, scalable setup.

**demo here**

## Introduction 
![global_sch](https://github.com/mchianale/loan_request_application/blob/main/docs/global_sch.png)

The system comprises four main services, all interconnected within a Docker bridge network (`app-network`) for secure, isolated communication:

--- 

- **MongoDB**: A NoSQL database used to store user and loan data persistently. It serves as the primary data repository, maintaining crucial records for the backend to query and update as needed.

--- 

- **[Backend Service](https://github.com/mchianale/loan_request_application/edit/main/backend/README.md)**: Acts as the core processing unit, handling requests, managing loan applications, and coordinating data with MongoDB. This service also interfaces with the loan evaluation service and is foundational to the application’s operation.

--- 

- **Loan Service**: This service is responsible for running loan evaluation processes, determining eligibility and assessing risk based on predefined business rules and application data. The service is built with [Spyne](https://spyne.io/), a Python framework for creating SOAP-based web services. 
Using SOAP (Simple Object Access Protocol), the Loan Service enables structured and reliable messaging that follows a well-defined XML schema. This approach ensures data integrity and supports complex operations between the Loan Service and other parts of the application, like the Backend Service. The Loan Service operates on multiple ports, facilitating concurrent evaluation workflows and ensuring that multiple requests can be processed simultaneously. 
By using SOAP, the Loan Service can communicate with other applications in a secure and standardized way, making it a robust solution for handling sensitive loan data and evaluations.

--- 

- **Flask Frontend**: A user-facing interface built with Flask, allowing applicants and staff to interact with the system. It provides endpoints for submitting loan applications and viewing their evaluation status.

--- 

## Reuse
### To edit
**Install the dependencies :**
```bash
pip install -r backend/requirements.txt
pip install -r services/requirements.txt
pip install -r frontend/requirements.txt
```
**Warning:** For all dependent applications that call other services, ensure that the host is set to `localhost`. Currently, the hosts are configured using container names, as each service container is on the same Docker network.

### Using Docker
**Containerization :**
```bash
docker-compose up --build
```

**Warning:** If containers stop immediately after starting, it may be because some applications attempted to call other services before they were fully initialized. Don't hesitate to manually restart the affected containers to ensure all services are running correctly.

**More details :**
```yml
version: '3.8'
networks:
  app-network:
    driver: bridge

services:
  mongodb:
    container_name: mongodb
    image: mongo:latest
    ports:
      - "27017:27017"
    volumes:
      - ./data:/data/db  # Persist MongoDB data
    networks:
      - app-network

  backend_service:
    container_name: backend_service
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "5001:5001"   
    depends_on:
      - mongodb
    networks:
      - app-network

  loan_service:
    container_name: loan_service
    build:
        context: .
        dockerfile: Dockerfile.services
    ports:
        - "8001:8001"
        - "8002:8002"
        - "8003:8003"
        - "8004:8004"
    depends_on:
        - backend_service
    networks:
        - app-network

  flask_frontend:
    container_name: flask_frontend
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "5002:5002"  
    depends_on:
      - backend_service
      - loan_service
    networks:
      - app-network
```


https://github.com/cquest/dvf_as_api?tab=readme-ov-file => api dvf
https://www.data.gouv.fr/fr/datasets/regions-departements-villes-et-villages-de-france-et-doutre-mer/ => data cities
https://www.empruntis.com/financement/actualites/barometres_regionaux.php => rate
code insee => https://www.data.gouv.fr/fr/datasets/base-officielle-des-codes-postaux/
loyer m2 => https://www.seloger.com/prix-de-l-immo/location/ile-de-france/paris/paris-20eme/750120.htm
