# API Reference

Full API reference for the Conversational Survey Engine.

Base URL: `http://localhost:8000` (development)

---

## Health

### `GET /health`

Returns service health status.

**Response** `200 OK`

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Admin — Surveys

All admin endpoints are prefixed with `/api/v1/admin/surveys`.

### `POST /api/v1/admin/surveys`

Create a new survey.

**Request Body**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `title` | string | Yes | — | Survey display name |
| `context` | string | Yes | — | Background context provided to the AI agent |
| `goal` | string | Yes | — | Research goal the conversation should achieve |
| `constraints` | string[] | No | `[]` | Topics or behaviours to avoid |
| `max_questions` | integer | No | `10` | Maximum questions per session |
| `completion_criteria` | string | No | `""` | Free-text description of when the survey is complete |
| `goal_coverage_threshold` | float | No | `0.85` | Cosine similarity threshold for goal coverage (0–1) |
| `context_similarity_threshold` | float | No | `0.7` | Similarity threshold for context relevance |

**Example Request**

```bash
curl -X POST http://localhost:8000/api/v1/admin/surveys \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Remote Work Satisfaction",
    "context": "We are researching how employees feel about remote work policies at a mid-size tech company.",
    "goal": "Understand employee satisfaction, challenges, and preferences regarding remote work.",
    "constraints": ["Do not ask about salary", "Avoid questions about specific managers"],
    "max_questions": 8
  }'
```

**Response** `201 Created`

```json
{
  "id": "a1b2c3d4-...",
  "title": "Remote Work Satisfaction",
  "context": "We are researching...",
  "goal": "Understand employee satisfaction...",
  "constraints": ["Do not ask about salary", "Avoid questions about specific managers"],
  "max_questions": 8,
  "completion_criteria": "",
  "goal_coverage_threshold": 0.85,
  "context_similarity_threshold": 0.7,
  "is_active": true,
  "created_at": "2026-02-28T12:00:00+00:00",
  "updated_at": "2026-02-28T12:00:00+00:00"
}
```

---

### `GET /api/v1/admin/surveys`

List all surveys with pagination.

**Query Parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | integer | `0` | Offset (≥ 0) |
| `limit` | integer | `20` | Page size (1–100) |

**Example Request**

```bash
curl "http://localhost:8000/api/v1/admin/surveys?skip=0&limit=10"
```

**Response** `200 OK`

```json
{
  "surveys": [ { "id": "...", "title": "...", ... } ],
  "total": 5,
  "skip": 0,
  "limit": 10
}
```

---

### `GET /api/v1/admin/surveys/{survey_id}`

Get a single survey with session statistics.

**Response** `200 OK` — `SurveyDetailResponse`

Includes all `SurveyResponse` fields plus:

| Field | Type | Description |
|-------|------|-------------|
| `total_sessions` | integer | Total sessions started |
| `completed_sessions` | integer | Sessions that finished |
| `avg_questions_per_session` | float | Average Q count per session |

**Errors:** `404` if survey not found.

---

### `PUT /api/v1/admin/surveys/{survey_id}`

Update a survey. Only include the fields you want to change.

**Request Body** — Same fields as `CreateSurveyRequest`, all optional.

**Response** `200 OK` — `SurveyResponse`

**Errors:** `404` if survey not found.

---

### `DELETE /api/v1/admin/surveys/{survey_id}`

Soft-delete a survey (sets `is_active = false`).

**Response** `204 No Content`

**Errors:** `404` if survey not found.

---

### `GET /api/v1/admin/surveys/{survey_id}/responses`

Get all session responses for a survey.

**Query Parameters**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `skip` | integer | `0` | Offset |
| `limit` | integer | `20` | Page size (1–100) |

**Response** `200 OK`

```json
{
  "responses": [
    {
      "session_id": "...",
      "user_id": "...",
      "survey_id": "...",
      "status": "completed",
      "conversation": [
        {
          "question_id": "...",
          "question_text": "How do you feel about remote work?",
          "answer_text": "I really enjoy the flexibility...",
          "question_number": 1,
          "answered_at": "2026-02-28T12:01:00+00:00"
        }
      ],
      "question_count": 5,
      "created_at": "...",
      "completed_at": "..."
    }
  ],
  "total": 12,
  "skip": 0,
  "limit": 20
}
```

**Errors:** `404` if survey not found.

---

### `GET /api/v1/admin/surveys/{survey_id}/stats`

Get aggregated statistics for a survey.

**Response** `200 OK`

```json
{
  "survey_id": "...",
  "total_sessions": 25,
  "completed_sessions": 18,
  "abandoned_sessions": 7,
  "avg_questions_per_session": 6.4,
  "avg_completion_time_seconds": 312.5,
  "top_themes": ["flexibility", "communication", "work-life balance"]
}
```

**Errors:** `404` if survey not found.

---

## Participant — Sessions

Participant endpoints are prefixed with `/api/v1/surveys/{survey_id}/sessions`.

### `POST /api/v1/surveys/{survey_id}/sessions`

Start a new survey session. A user record is created automatically and the first AI-generated question is returned.

**Request Body** (optional)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `participant_name` | string | No | `null` | Display name |
| `metadata` | object | No | `{}` | Arbitrary key-value metadata |

**Example Request**

```bash
curl -X POST http://localhost:8000/api/v1/surveys/SURVEY_ID/sessions \
  -H "Content-Type: application/json" \
  -d '{"participant_name": "Alice"}'
```

**Response** `201 Created`

```json
{
  "session_id": "...",
  "user_id": "...",
  "survey_id": "...",
  "status": "active",
  "current_question": {
    "question_id": "...",
    "text": "What aspects of remote work do you find most valuable?",
    "question_number": 1
  },
  "question_number": 1,
  "max_questions": 8,
  "created_at": "2026-02-28T12:00:00+00:00"
}
```

**Errors:** `404` if survey not found.

---

### `POST /api/v1/surveys/{survey_id}/sessions/{session_id}/respond`

Submit an answer to the current question and receive the next question (or completion).

**Request Body**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `answer` | string | Yes | The participant's answer |
| `question_id` | string | No | ID of the question being answered |
| `question_text` | string | No | Text of the question being answered |

**Example Request**

```bash
curl -X POST http://localhost:8000/api/v1/surveys/SURVEY_ID/sessions/SESSION_ID/respond \
  -H "Content-Type: application/json" \
  -d '{
    "answer": "I really enjoy the flexibility to manage my own schedule.",
    "question_id": "q-abc-123",
    "question_text": "What aspects of remote work do you find most valuable?"
  }'
```

**Response** `200 OK` — active session

```json
{
  "session_id": "...",
  "status": "active",
  "question": {
    "question_id": "...",
    "text": "Can you describe a specific situation where that flexibility helped you?",
    "question_number": 2
  },
  "completion_reason": null,
  "question_number": 2,
  "max_questions": 8
}
```

**Response** `200 OK` — session completed

```json
{
  "session_id": "...",
  "status": "completed",
  "question": null,
  "completion_reason": "goal_coverage_met",
  "question_number": 6,
  "max_questions": 8
}
```

**Errors:**
- `404` — Session not found
- `409` — Session is not active (already completed or exited)
- `400` — Processing error

---

### `GET /api/v1/surveys/{survey_id}/sessions/{session_id}`

Get the current state of a session including full conversation history.

**Response** `200 OK`

```json
{
  "session_id": "...",
  "user_id": "...",
  "survey_id": "...",
  "status": "active",
  "conversation": [
    {
      "question_id": "...",
      "question_text": "What aspects of remote work do you find most valuable?",
      "answer_text": "I really enjoy the flexibility...",
      "question_number": 1,
      "answered_at": "2026-02-28T12:01:00+00:00"
    }
  ],
  "question_count": 1,
  "created_at": "...",
  "completed_at": null
}
```

**Errors:** `404` if session not found.

---

### `POST /api/v1/surveys/{survey_id}/sessions/{session_id}/exit`

Exit a session early. The session status is set to `exited`.

**Response** `200 OK`

```json
{
  "session_id": "...",
  "status": "exited",
  "question_count": 3,
  "message": "Session exited successfully. Thank you for your participation!"
}
```

**Errors:**
- `404` — Session not found
- `409` — Session is not active

---

## Schemas Reference

### `SurveyResponse`

```
id                          string    UUID
title                       string
context                     string
goal                        string
constraints                 string[]
max_questions               integer
completion_criteria         string
goal_coverage_threshold     float
context_similarity_threshold float
is_active                   boolean
created_at                  string    ISO 8601
updated_at                  string    ISO 8601
```

### `SurveyDetailResponse` (extends SurveyResponse)

```
total_sessions              integer
completed_sessions          integer
avg_questions_per_session   float
```

### `SurveyStatsResponse`

```
survey_id                       string
total_sessions                  integer
completed_sessions              integer
abandoned_sessions              integer
avg_questions_per_session       float
avg_completion_time_seconds     float
top_themes                      string[]
```

### `SessionResponse`

```
session_id                  string
user_id                     string
survey_id                   string
status                      string    "active" | "completed" | "exited"
current_question            QuestionPayload
question_number             integer
max_questions               integer
created_at                  string
```

### `QuestionPayload`

```
question_id                 string
text                        string
question_number             integer
```

### `NextQuestionResponse`

```
session_id                  string
status                      string
question                    QuestionPayload | null
completion_reason           string | null
question_number             integer
max_questions               integer
```

### `SessionDetailResponse`

```
session_id                  string
user_id                     string
survey_id                   string
status                      string
conversation                ConversationEntry[]
question_count              integer
created_at                  string
completed_at                string | null
```

### `ConversationEntry`

```
question_id                 string
question_text               string
answer_text                 string
question_number             integer
answered_at                 string
```

### `SessionCompleteResponse`

```
session_id                  string
status                      string
question_count              integer
message                     string
```

### `SubmitAnswerRequest`

```
answer                      string    required
question_id                 string    optional
question_text               string    optional
```
