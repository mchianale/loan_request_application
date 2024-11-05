# Frontend for Real Estate Loan Application Service

## Overview
This frontend application is built using Flask and serves as the user interface for the Real Estate Loan Application Service. It enables users to manage their loan applications seamlessly by providing functionalities such as user registration, login, and tracking the status of loan requests. The frontend communicates with the backend services to facilitate loan evaluation processes and displays relevant information to the users.

## Features
- **User Registration and Login**: Allows users to create an account and securely log in.
- **Submission of New Loan Requests**: Users can submit new loan requests for evaluation.
- **Real-Time Tracking of Loan Application Status**: Keeps users updated on the progress of their loan requests.
- **User-Friendly Interface**: Clean and simple design for managing loan requests and account details.
- **Secure Communication with Backend Services**: Ensures all user and loan data are securely transmitted between the frontend and backend.

## Structure Information

### Templates
The `templates` directory contains all the HTML files used by the Flask application. Each file corresponds to a specific route in the application, allowing users to navigate through various functionalities seamlessly. Key templates include:
- `home.html`: The landing page for the application.
- `login.html`: The user login page.
- `signup.html`: The user registration page.
- `process.html`: Displays the current status of loan application processing.
- `new_loan_request.html`: The form to submit a new loan request.
- `user_requests.html`: Displays a list of loan requests made by the user.
- `loan_request.html`: Displays detailed information about a specific loan request.

### Static Files
The `static` directory holds static files such as stylesheets and JavaScript files. Currently, it contains the `styles.css` file that styles the frontend pages. You can modify the styles as necessary to match the branding or design requirements of the application.

---

## Improvements

### Database Isolation
In the current implementation, the frontend does not directly interact with any database, as all user-related data and loan requests are handled by the backend service. However, to improve the isolation and scalability of the system, it's recommended that:

- The backend service should be responsible for managing the database interactions, keeping the frontend application focused solely on user interaction and presenting data.
- Ensure that sensitive information, such as user passwords and financial data, is encrypted and stored securely in the backend database.
- The frontend can simply interact with the backend API endpoints for managing users and loan requests. This ensures that the frontend remains independent of direct database operations.

This isolation enhances security, scalability, and maintainability of the application, as the database management and application logic remain decoupled.

### Loan Application Timeout Handling
Currently, the system does not have a built-in mechanism to automatically handle failed or expired loan applications. The following improvements can be made to handle timeouts and automatic deletion of failed loan applications:

- **Timeout Timer**: Implement a background timer or scheduled task in the backend service to track the duration of each loan request. If a request has been in the processing state for too long (for example, more than a certain threshold like 24 hours), it can be flagged as failed.
- **Backend Solution**: Create a scheduled task or cron job that runs at regular intervals (e.g., every 15 minutes) to check for failed loan requests that have been in the system for an excessive period. If the loan request is in a "failed" or "timed-out" state, the backend can send a request to the frontend to notify the user or automatically delete the loan request.

This will improve user experience by preventing the frontend from showing loan applications that are no longer valid or have been abandoned due to technical issues.

---
