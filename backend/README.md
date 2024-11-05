# Loan Management API

This API is designed to handle loan requests and manage user authentication and session control, using a MongoDB database for persistence. The API provides endpoints to submit, update, retrieve, and delete loan requests, and includes user signup, login, and logout functionalities. Below, you'll find detailed instructions for setup, endpoint usage, and ideas for potential improvements.

---

## Table of Contents
- [Documentation](#api-documentation)
  - [Test API](#test-api)
  - [User Endpoints](#user-endpoints)
  - [Loan Pending Endpoints](#loan-pending-endpoints)
  - [Loan Request Endpoints](#loan-request-endpoints)
- [Improvements](#improvements)


---

# API Documentation

## Test API
### `/api/test`
- **Method:** `GET`
- **Description:** Checks if the API is running.
- **Response:**
    ```json
    {
        "message": "ok"
    }
    ```
---

## User Endpoints

### `/api/user/signup`
- **Method:** `POST`
- **Description:** Registers a new user.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "password": "string",
        "confirm_password": "string"
    }
    ```
- **Response:**
    - `201 Created`: Returns session ID on success.
    - `401`: If passwords do not match or the user ID is invalid.
    - `409`: If user ID is already taken.

### `/api/user/login`
- **Method:** `POST`
- **Description:** Logs in an existing user.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "password": "string"
    }
    ```
- **Response:**
    - `201 Created`: Returns session ID on success.
    - `404`: If user ID is not found.
    - `401`: If password is incorrect.

### `/api/user/logout`
- **Method:** `POST`
- **Description:** Logs out a user.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "session_id": "string"
    }
    ```
- **Response:**
    - `201 Created`: Confirms logout.
    - `404`: If user ID or session ID is missing or invalid.

### `/api/user/all_users`
- **Method:** `GET`
- **Description:** Retrieves all registered users.
- **Response:**
    - `200 OK`: Returns a list of users.

---

## Loan Pending Endpoints

### `/api/pending/all_pendings`
- **Method:** `GET`
- **Description:** Retrieve all pending loan requests.
- **Response:**
    - `200 OK`: Returns all loan pending entries.

### `/api/pending/new_request`
- **Method:** `POST`
- **Description:** Initiates a new loan request pending process.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "session_id": "string",
        "input": "string"
    }
    ```
- **Response:**
    - `201 Created`: Returns `pending_id`.
    - `401`: If an existing unprocessed request is already present.
    - `404`: If `user_id` or `session_id` is missing or invalid.

### `/api/pending/get_process_step`
- **Method:** `POST`
- **Description:** Retrieves the current step of a specific loan process.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "session_id": "string",
        "pending_id": "string"
    }
    ```
- **Response:**
    - `201 Created`: Returns the current step of the process or relevant error message.
    - `404`: If `user_id` or `session_id` is missing or invalid.

### `/api/pending/update_status`
- **Method:** `POST`
- **Description:** Updates the status of an existing loan request.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "pending_id": "string",
        "status": "string",
        "error": "string (optional)"
    }
    ```
- **Response:**
    - `201 Created`: Confirms successful update.
    - `404`: If `user_id` or `pending_id` is missing or invalid.
    - `401`: If the pending request does not exist.

### `/api/pending/delete`
- **Method:** `POST`
- **Description:** Deletes a loan pending request if the status is `Finished` or `Pending`.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "pending_id": "string",
        "forced": "boolean"
    }
    ```
- **Response:**
    - `201 Created`: Confirms deletion.
    - `404`: If deletion is restricted due to request status.

---

## Loan Request Endpoints

### `/api/request/requests`
- **Method:** `POST`
- **Description:** Retrieve all loan requests associated with a specific user.
- **Payload:**
    ```json
    {
        "user_id": "string"
    }
    ```
- **Response:**
    - `201 Created`: Returns all loan requests for the user.

### `/api/request/add`
- **Method:** `POST`
- **Description:** Adds a new loan request to the system.
- **Payload:**
    ```json
    {
        "loan_request": {
            "_id": "string",
            "user_id": "string",
            "date": "string"
        }
    }
    ```
- **Response:**
    - `201 Created`: Confirms the addition of the loan request.
    - `401`: If the loan request already exists.

### `/api/request/delete`
- **Method:** `POST`
- **Description:** Deletes a loan request identified by its ID.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "request_id": "string"
    }
    ```
- **Response:**
    - `201 Created`: Confirms successful deletion of the loan request.
    - `404`: If `user_id` or `request_id` is missing or invalid.

### `/api/request/by_id`
- **Method:** `POST`
- **Description:** Retrieves details of a loan request using its ID.
- **Payload:**
    ```json
    {
        "user_id": "string",
        "request_id": "string"
    }
    ```
- **Response:**
    - `201 Created`: Returns the details of the loan request.

---

## Improvements

### Security Enhancements
- **Session Management:** 
  - Implement session timeout to secure the application further. This will prevent stale sessions from being reused indefinitely.
  
- **Password Security:** 
  - Consider adding stricter password policies (e.g., minimum length, special characters) to improve account security.
  
- **Enhanced Validation:** 
  - Further sanitize all user inputs and response data to prevent injection and similar attacks.

### Logical Enhancements
- **Data Consistency:** 
  - Implement MongoDB transactions for complex, multi-step operations across collections, ensuring that database changes are atomic.
  
- **Rate Limiting:** 
  - Add rate limiting to prevent abuse of sensitive endpoints like login and signup.
  
- **Extended Error Handling:** 
  - Provide more specific error messages and codes to enhance debugging and development processes.

### Persistence and Scaling
- **Database Indexing:** 
  - Add indexes to fields like `user_id` and `_id` in MongoDB collections to improve lookup speed and query performance.
  
- **Data Archiving:** 
  - For completed loan requests, consider implementing a scheduled archival system to remove or archive older, processed requests and improve performance for active queries.

### Troubleshooting
- **MongoDB Connection Issues:** 
  - Ensure MongoDB is running and reachable. If MongoDB is running in a Docker container, verify network settings to allow access from the Flask app.
