# Evaluation Service of real estate loan application
## Table of Contents
1. [Overview](#overview)
   - [Global Structure](#global-structure)
2. [Service Composite Structure](#service-composite-structure)
   - [ServiceExtraction](#serviceextraction)
   - [CreditCheckService](#creditcheckservice)
   - [PropertyValuationService](#propertyvaluationservice)
   - [ApprovalDecisionService](#approvaldecisionservice)
3. [Good to know](#good-to-know)
4. [ServiceExtraction](#serviceextraction-1)
5. [CreditCheckService](#creditcheckservice-1)
6. [PropertyValuationService](#propertyvaluationservice-1)
7. [ApprovalDecisionService](#approvaldecisionservice-1)

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

---

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

---

### Good to know

**Threading Management:**  
- Multiple requests from different users can be sent to the composite service simultaneously.  
- **CreditCheckService** and **PropertyValuationService** are executed using `threads`, which helps to save time during the loan evaluation process.

**Cities Data:**  
- I have created a dataset [cities.csv](https://github.com/mchianale/loan_request_application/blob/main/services/features/data/cities.csv) based on several datasets from [french cities informations, on data.gouv](https://www.data.gouv.fr/fr/datasets), to enable the computation of the **CreditCheckService** and **PropertyValuationService** scoring systems.

---

## ServiceExtraction  
The `ServiceExtraction` is responsible for extracting entities from requests using a fine-tuned transformer model and cleaning the output using NLP rules.

ServiceExtraction takes in input an unclean text and extracts variables useful to evaluate the loan (contact information, user situation, property information, loan information, etc.).

**How it works:**
- Firstly, it performs preprocessing on the input text (retrieving words based on NLP rules).
- Based on the cleaned text, it calls a fine-tuned **CamemBERT** model to extract entities. The original **CamemBERT** model is a transformer-based language model pre-trained on large amounts of French text data. It is optimized for various NLP tasks, including token classification, and can be fine-tuned for specific tasks such as entity extraction.
- To see more informations about how I trained my model [see here](https://github.com/mchianale/camemBERT-entities-extraction).
   - **the trained model :** [Camembert-for-Real-Estate-Loan-Entity-Extraction-fr](https://huggingface.co/mchianale/Camembert-for-Real-Estate-Loan-Entity-Extraction-fr/tree/main/3_camembert-base).
   - Download `3_camembert-base` folder, on put it in `./models`.
- Applies cleaning functionalities and NLP rules on the extracted entities to obtain the final cleaned entities.
- Based on other rules, it returns an `error` and stops the process if important variables for loan evaluation are missing in the final entities.

---

## CreditCheckService:

The `CreditCheckService` is responsible for assessing the financial capacity of the customer to repay the loan. Based on useful entities to evaluate the profile, this service calculates the debt ratio of the user.

### Debt Ratio:

The debt ratio is used to evaluate the borrower's ability to repay a loan based on their monthly income and financial obligations.

- **Debt Ratio** = (**Monthly Payments** + **Monthly Charges**) / **Monthly Income** in %

- **Monthly Payments**: This is the monthly debt payment due to the potential loan application.
- **Monthly Charges**: These are additional regular financial obligations, such as rent, utilities, or any other recurring charges.
- **Monthly Income**: This is the gross monthly income before taxes and other deductions.

The resulting ratio is typically expressed as a percentage. A lower ratio indicates a healthier financial situation, while a higher ratio may signal financial strain.

### How it works:

We are supposed to know **Monthly Charges** and **Monthly Income** based on the previous service, but the **CreditCheckService** needs to compute **Monthly Payments** based on the requested loan amount, the loan term, and the annual interest rate of the future property region (using data from [the regional barometer](https://www.empruntis.com/financement/actualites/barometres_regionaux.php) which is updated daily).

---

## PropertyValuationService:

The `PropertyValuationService` is responsible for estimating the market value of the property for which the loan is requested. It helps assess the potential rental yield and the estimated property value based on various parameters like the type of property, its location, and market data.

### How It Works:

1. **Property Type Mapping**:  
   The service maps the property type provided in the request (e.g., house, apartment) to a corresponding type used in the market data. This is done using predefined mappings for different property types (`map_type_logement_v0` and `map_type_logement_v1`).

2. **Surface Area Calculation**:  
   The service calculates the **average surface area** based on the property type and location (using INSEE code). If the surface data isn't available from the market, a fallback method is used, which provides default surface values depending on the property type.

3. **Market Data Retrieval**:  
   Using the French [DVF API (Base des Valeurs Foncières)](https://github.com/cquest/dvf_as_api?tab=readme-ov-file), the service fetches recent property sales data for the specified location. It checks the sale price and the real surface area of properties similar to the one being evaluated. The data is filtered to include only properties within a reasonable range of the loan amount plus down payment.

4. **Rental Yield Calculation**:  
   The rental yield is computed based on the market rent for a similar property and the loan amount. This helps in determining if the property is a profitable investment, particularly for rental purposes.

### Key Calculations:

- **Rental Yield**:  
  The rental yield is calculated as:  
  `Rental Yield = (Annual Rent / (Loan Amount + Down Payment)) * 100`

- **Property Surface Area**:  
  If detailed surface data is available, it is used to calculate the estimated property value per square meter. If not, average values are used based on the type of property.

- **Annual Rent**:  
  The annual rent is calculated based on the **average rent per square meter** for the property type and location, multiplied by the **property surface area**.

- **Potential Property Value**:  
  The potential property value is determined by adding the loan amount and down payment, then applying a threshold ratio to estimate the market value.

---

## ApprovalDecisionService

The `ApprovalDecisionService` class provides a comprehensive service to determine whether a home loan can be approved based on a variety of factors. These factors include the user's financial situation (such as income, debts, etc.), property information (such as valuation, rental yield, etc.), and predefined scoring rules. The service calculates different scores, such as the user score, property score, and global score, to assess whether a loan request is approved or denied.

### Key Components:

1. **Scoring Rules**:
   - Scoring is applied to both the user and property details.
   - The scoring rules are loaded from a JSON file, which determines how much weight each factor carries in the scoring process. For example, professions with more stable income (like civil servants) are given higher scores, while freelance or unstable income professions have lower scores.

2. **Data Processing**:
   - The service processes data provided in three main objects:
     - **`ExtractObj`**: Contains user information and financial details like monthly income, expenses, etc.
     - **`CreditCheckInformation`**: Contains loan-specific data such as debt ratio, region rate, and loan terms.
     - **`PropertyValuationInformation`**: Contains property-specific data like surface area, rental yield, and mean monthly rent.
   
3. **Scoring Calculations**:
   - **User Situation Score**: Based on the user's profession or situation (such as being employed or self-employed), a score is assigned.
   - **Cash Flow Score**: Based on the monthly cash flow (income minus expenses and loan payments), the service assigns a score. Positive cash flow results in a higher score, while negative cash flow results in a lower score.
   - **Confidence Score**: The overall confidence in the loan approval is determined by evaluating various factors like region, debt ratio, rental yield, and cash flow. This score helps to weigh the importance of each factor.

4. **Decision Making**:
   - The `getScoring` method computes the user score, property score, and global score. It then compares these scores against a set of predefined rules to make an approval decision.
   - The final decision (`approve` or `deny`) is determined based on the scoring results and the application of the predefined rules.
   
5. **Approval Messages**:
   - If the loan is approved, the service provides detailed messages about the approval, including feedback on the user's financial situation and the property score. The messages are constructed based on the calculated scores and their respective confidence levels.
   - If the loan is denied, the service provides a message indicating the reason for denial, such as a high debt ratio or low global score.

6. **Error Handling**:
   - The service checks for errors in the calculated scores, ensuring that all values are within expected ranges (e.g., confidence scores between 0 and 100, valid user situation scores).
   - If any errors are detected, an error message is returned with details about the issue.
