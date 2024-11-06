# Real estate loan application Service
This project is a containerized application designed to manage new loan applications, automatically evaluating each request based on multiple integrated services. The application leverages Docker to streamline service deployment and orchestration, ensuring a modular, scalable setup.

---

## Table of Contents
- [Demo](#demo)
- [Introduction](#introduction)
- [Security](#security)
- [Reuse](#reuse)
  - [Config for all](#config-for-all)
  - [To edit](#to-edit)
  - [Using Docker](#using-docker)
- [Improvements](#improvements)
- [Citation](#citation)
  
## Demo
[![GitHub Logo](https://github.com/mchianale/loan_request_application/blob/main/docs/play.png)](https://youtu.be/JTdvEErmetI)

--- 

## Introduction 
![global_sch](https://github.com/mchianale/loan_request_application/blob/main/docs/global_sch.png)

**The system comprises four main services, all interconnected within a Docker bridge network (`app-network`) for secure, isolated communication:**

--- 

1. **MongoDB**:
   - A NoSQL database used to store user and loan data persistently. It serves as the primary data repository, maintaining crucial records for the backend to query and update as needed.

--- 

2. **[Backend Service](https://github.com/mchianale/loan_request_application/blob/main/backend/README.md)**:
   - Acts as the core processing unit, handling requests, managing loan applications, and coordinating data with MongoDB.
   - This service also interfaces with the loan evaluation service and is foundational to the application’s operation.

--- 

3.  **[Loan Service](https://github.com/mchianale/loan_request_application/blob/main/services/README.md)**:
     - This service is responsible for executing loan evaluation processes. It determines applicant eligibility and assesses risk based on predefined business rules and provided application data. Triggered by a watchdog system, the service analyzes input text to evaluate loan applications and make approval or rejection decisions.
     - The service is built with [Spyne](https://spyne.io/), a Python framework for creating SOAP-based web services.
     - Using SOAP (Simple Object Access Protocol), the Loan Service enables structured and reliable messaging that follows a well-defined XML schema. This approach ensures data integrity and supports complex operations between the Loan Service and other parts of the application, like the Backend Service.
     - The Loan Service operates on multiple ports, facilitating concurrent evaluation workflows and ensuring that multiple requests can be processed simultaneously.
     - By using SOAP, the Loan Service can communicate with other applications in a secure and standardized way, making it a robust solution for handling sensitive loan data and evaluations.

--- 

4.  **[Flask Frontend](https://github.com/mchianale/loan_request_application/blob/main/frontend/README.md)**:
    - A user-facing interface built with Flask, allowing applicants and staff to interact with the system. It provides endpoints for submitting loan applications and viewing their evaluation status.

--- 

## Security

- **Isolate Database from Frontend and Loan Services**:  
  Ensure that the database is not directly exposed to the frontend or loan services. Use secure APIs and backend logic to interact with the database.

- **Apply Logical Routes in Frontend**:  
  Implement logic in the frontend to block certain components for malicious or unauthorized users. This prevents access to sensitive features based on the user's role or authentication status.

- **Managing User Sessions**:  
  Create a sign-in and login system in the backend that generates a `session_id` for each user. User passwords are hashed and salted to increase security and prevent unauthorized access.

- **Prevent Multiple Requests from the Same User**:  
  To avoid multiple requests from the same user simultaneously, implement a management system that handles session states and limits duplicate submissions. This  is achieved through both backend and frontend logic.

---

## Reuse
To use the model I had trained to extract loan information entities [see here](https://github.com/mchianale/camemBERT-entities-extraction) :
- **the trained model :** [Camembert-for-Real-Estate-Loan-Entity-Extraction-fr](https://huggingface.co/mchianale/Camembert-for-Real-Estate-Loan-Entity-Extraction-fr/tree/main/3_camembert-base).
- Download `3_camembert-base` folder, on put it in `./models`.
### Config for all
**[config.json](https://github.com/mchianale/loan_request_application/blob/main/config.json) :**
```json
{
    "tns_name" : "spyne.loan.application.service",
    "db" : {
      "name" : "loan_service_db",
      "loan_pendings" : "loan_pendings",
      "loan_requests" : "loan_requests",
      "users" : "users"
    },
    "backend_service" : {
      "port" : 5001
    },
    "flask_frontend" : {
      "port" : 5002
    },
    "services" : {
        "ServiceExtraction" : {
            "port" : 8001,
            "description" : "Extract entities from requests using finetuned transformers model and clean output using nlp rules.",
            "improvement" : "finish"
        },
        "CreditCheckService" : {
            "port" : 8002,
            "description" : "The Credit Check service is responsible for assessing the financial capacity of the customer to repay the loan.",
            "improvement" : "finish"
        },
        "PropertyValuationService" : {
            "port" : 8003,
            "description" : "The Property Valuation department is responsible for estimating the market value of the property for which the loan is requested",
            "improvement" : "finish"
        },
        "ApprovalDecisionService" : {
            "port" : 8004,
            "description" : "The Approval Decision service analyzes the data collected during the stages (Credit Check and Property Valuation) to determine if the home loan can be approved",
            "improvement" : "to make"
        }
    },
    "camembert_model" : {
        "model_path" : "models/3_camembert-base",
        "max_length" : 512,
        "improvement" : "finish"
    }
}
```
See the file directly for more details, there are also rules for composite service decision prices.

### To edit
**Install the dependencies :**
```bash
pip install -r backend/requirements.txt
pip install -r services/requirements.txt
pip install -r frontend/requirements.txt
```
**Warning:** For all dependent applications that call other services, ensure that the host is set to `localhost`. Currently, the hosts are configured using container names, as each service container is on the same Docker network expect for `mongodb`, which is isolate based on docker-compose netwokds implementation.

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
  public:
    driver: bridge
  internal:
    driver: bridge
    internal: true  # isolation

services:
  mongodb:
    container_name: mongodb
    image: mongo:latest
    volumes:
      - ./data:/data/db    
    networks:
      - internal # isolated from all except from backend

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
      - internal   
      - public     

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
      - public   

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
      - public   
```

## Improvements
- **Optimization of the various Dockerfiles for faster containerization**: A review of the Dockerfiles is recommended to reduce build time and improve the efficiency of containerization. This could include removing unnecessary dependencies and utilizing caching when installing packages.


## Citation

---

- [CamemBERT](https://arxiv.org/pdf/1911.03894)

---

**For data :**
- [DVF API](https://github.com/cquest/dvf_as_api?tab=readme-ov-file)
- [french yearly rates](https://www.empruntis.com/financement/actualites/barometres_regionaux.php)
- [french cities informations, on data.gouv](https://www.data.gouv.fr/fr/datasets)



