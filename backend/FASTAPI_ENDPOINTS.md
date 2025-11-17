# FastAPI Endpoints Documentation

## Overview
This FastAPI application implements an asynchronous processing system with background tasks to execute CrewAI crews without timeouts.

## Architecture

### Workflow
1. Client calls `POST /crew/start`
2. A unique UUID is generated
3. A database record is created with status `PROCESSING`
4. The crew is launched in a background task
5. The ID is returned immediately
6. Client polls `GET /crew/status/{id}`
7. When the crew finishes, the status changes to `COMPLETED` or `ERROR`

## Endpoints

### 1. Start Crew Execution

```http
POST /crew/start
```

**Description**: Starts a new crew execution in the background and immediately returns an execution ID.

**Response**:
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "message": "Crew execution started successfully"
}
```

**Status Codes**:
- `200 OK`: Execution started successfully
- `500 Internal Server Error`: Error starting the execution

**Example with curl**:
```bash
curl -X POST http://localhost:8081/crew/start
```

**Example with fetch**:
```javascript
const response = await fetch('http://localhost:8081/crew/start', {
  method: 'POST'
});
const data = await response.json();
console.log('Execution ID:', data.execution_id);
```

---

### 2. Check Execution Status (Polling)

```http
GET /crew/status/{execution_id}
```

**Description**: Checks the current status of a crew execution.

**Path Parameters**:
- `execution_id` (string, required): Execution UUID

**Response - Processing**:
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "result": null,
  "error": null
}
```

**Response - Completed**:
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "result": {
    "raw": "Crew execution results here...",
    "data": { ... }
  },
  "error": null
}
```

**Response - Error**:
```json
{
  "execution_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ERROR",
  "result": null,
  "error": "Error message here"
}
```

**Status Codes**:
- `200 OK`: Status retrieved successfully
- `404 Not Found`: Execution ID does not exist
- `500 Internal Server Error`: Error querying the status

**Example with curl**:
```bash
curl http://localhost:8081/crew/status/550e8400-e29b-41d4-a716-446655440000
```

**Polling Example with JavaScript**:
```javascript
async function pollCrewStatus(executionId) {
  const maxAttempts = 60; // 5 minutes (5 seconds * 60)
  let attempts = 0;

  while (attempts < maxAttempts) {
    const response = await fetch(`http://localhost:8081/crew/status/${executionId}`);
    const data = await response.json();

    if (data.status === 'COMPLETED') {
      console.log('Crew completed!', data.result);
      return data;
    } else if (data.status === 'ERROR') {
      console.error('Crew failed:', data.error);
      throw new Error(data.error);
    }

    console.log('Still processing...');
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait 5 seconds
    attempts++;
  }

  throw new Error('Polling timeout after 5 minutes');
}

// Usage
const startResponse = await fetch('http://localhost:8081/crew/start', { method: 'POST' });
const { execution_id } = await startResponse.json();
const result = await pollCrewStatus(execution_id);
```

---

### 3. List Executions

```http
GET /crew/executions?limit=10
```

**Description**: Lists the latest crew executions (useful for debugging).

**Query Parameters**:
- `limit` (integer, optional): Maximum number of executions to return. Default: 10

**Response**:
```json
{
  "executions": [
    {
      "execution_id": "550e8400-e29b-41d4-a716-446655440000",
      "crew_name": "YourCrewName",
      "status": "COMPLETED",
      "created_at": "2025-11-17T10:30:00",
      "updated_at": "2025-11-17T10:32:15"
    },
    {
      "execution_id": "660e8400-e29b-41d4-a716-446655440001",
      "crew_name": "YourCrewName",
      "status": "PROCESSING",
      "created_at": "2025-11-17T10:35:00",
      "updated_at": "2025-11-17T10:35:00"
    }
  ]
}
```

**Example with curl**:
```bash
curl "http://localhost:8081/crew/executions?limit=5"
```

---

### 4. Health Check

```http
GET /health
```

**Description**: Checks the application status and Snowflake connection.

**Response**:
```json
{
  "status": "ok",
  "environment": "DEVELOPMENT",
  "snowflake_authmethod": "oauth",
  "snowflake_account": "account.region",
  "oauth_token_exists": true,
  "oauth_token_length": 1234
}
```

---

## Execution States

| State | Description |
|--------|-------------|
| `PROCESSING` | The crew is running in the background |
| `COMPLETED` | The crew finished successfully |
| `ERROR` | The crew failed with an error |

## Database Schema

The `crew_execution_results` table has the following structure:

```sql
CREATE TABLE crew_execution_results (
    id VARCHAR PRIMARY KEY,
    crew_name VARCHAR,
    raw_output VARIANT,
    result_text TEXT,
    status VARCHAR,
    metadata VARIANT,
    created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);
```

## Migration from Flask

To migrate from the previous Flask endpoint:

1. **Install dependencies**:
```bash
pip install fastapi uvicorn
```

2. **Run database migration**:
```bash
snowsql -f backend/migrations/add_updated_at_column.sql
```

3. **Change startup command**:

Before:
```bash
python backend/src/app.py
```

After:
```bash
python backend/src/fastapi_app.py
```

Or with uvicorn:
```bash
uvicorn fastapi_app:app --host 0.0.0.0 --port 8081
```

## Important Notes

- Background tasks run in the same process as the FastAPI application
- For heavier loads, consider using Celery or similar
- Polling should be implemented on the client with an appropriate interval (e.g., 5 seconds)
- A maximum polling timeout is recommended on the client side (e.g., 5-10 minutes)
