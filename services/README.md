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

1. **ServiceExtraction**:  
The ServiceExtraction is responsible for extracting entities from requests using a fine-tuned transformer model and cleaning the output using NLP rules.

2. **CreditCheckService**:  
The Credit Check service is responsible for assessing the financial capacity of the customer to repay the loan.

3. **PropertyValuationService**:  
The Property Valuation department is responsible for estimating the market value of the property for which the loan is requested.

4. **ApprovalDecisionService**:  
The Approval Decision service analyzes the data collected during the stages (Credit Check and Property Valuation) to determine if the home loan can be approved.

## ServiceExtraction  
The ServiceExtraction is responsible for extracting entities from requests using a fine-tuned transformer model and cleaning the output using NLP rules.

ServiceExtraction takes in input an unclean text and extracts variables useful to evaluate the loan (contact information, user situation, property information, loan information, etc.).

**How it works:**
- Firstly, it performs preprocessing on the input text (retrieving words based on NLP rules).
- Based on the cleaned text, it calls a fine-tuned **CamemBERT** model to extract entities. The original **CamemBERT** model is a transformer-based language model pre-trained on large amounts of French text data. It is optimized for various NLP tasks, including token classification, and can be fine-tuned for specific tasks such as entity extraction. To see more informations about how I trained my model [see here](https://github.com/mchianale/camemBERT-entities-extraction).
- Applies cleaning functionalities and NLP rules on the extracted entities to obtain the final cleaned entities.
- Based on other rules, it returns an `error` and stops the process if important variables for loan evaluation are missing in the final entities.

## CreditCheckService:
The Credit Check service is responsible for assessing the financial capacity of the customer to repay the loan.
Based on usefull entities to evaluate profile, this service find the debt ratio of the user.

**Debt ration :**

The debt ratio is used to evaluate the borrower's ability to repay a loan based on their monthly income and financial obligations.
- **Debt ratio** = (**Monthly Payments**+**Monthly Charges**)/**Monthly Income** in %
- **Monthly Payments**: This is the monthly debt payments due to the potential loan application.
- **Monthly Charges**: These are additional regular financial obligations, such as rent, utilities, or any other recurring charges.
- **Monthly Income**: This is the gross monthly income before taxes and other deductions.
The resulting ratio is typically expressed as a percentage. A lower ratio indicates a healthier financial situation, while a higher ratio may signal financial strain.


**How it works:**:
- We are supposed toà know **Monthly Charges** and **Monthly Income** based on previous service, but CreditCheckService need to compute **Monthly Payments** based on yearly rate of the future property region (by request [baroemtre regionaux]("https://www.empruntis.com/financement/actualites/barometres_regionaux.php) which are udpated everyday. 

  
