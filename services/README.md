# Evaluation Service of real estate loan application

## Overview 
This service is the main component that evaluates a loan application and returns a decision.
### Global Structure 
![global_sch](https://github.com/mchianale/loan_request_application/blob/main/docs/global_sch_composite.png)

**Structure:**
- A main app composed of a **watchdog** and a **composite service**.
- The watchdog and the composite service call the external backend ([see here](https://github.com/mchianale/loan_request_application/edit/main/backend/README.md)).

**How it works:**
- When the watchdog detects new loan applications pending, it calls the service composite's main function `run_loan_application` using a `thread` (to handle multiple user requests simultaneously).
- The service composite calls internal SOAP services and calls the backend depending on the results and the processing state (error, update pending status, add a new valid loan request).

### Service Composite Structure
![sch](https://github.com/mchianale/loan_request_application/blob/main/docs/compo.png)
