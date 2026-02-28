# Admin Guide

Guide for administrators to create and manage surveys.

---

## Creating a Survey

Navigate to the **Admin Dashboard** and click **Create Survey**, or use the API directly.

### Required Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Title** | A short, descriptive name for the survey. Shown in the admin dashboard. | "Remote Work Satisfaction Q1 2026" |
| **Context** | Background information provided to the AI agent. This shapes what the AI knows about the topic. Be specific — the richer the context, the better the questions. | "We are a 200-person tech company that went fully remote in 2023. We want to understand how employees feel about our current remote work policy, including flexibility, collaboration tools, and work-life balance." |
| **Goal** | The research objective. The AI will aim to generate questions that collectively satisfy this goal. The goal coverage check uses this field. | "Understand employee satisfaction with remote work, identify key challenges, and discover what changes would improve their experience." |

### Optional Fields

| Field | Default | Description |
|-------|---------|-------------|
| **Constraints** | `[]` | A list of topics or behaviours the AI must avoid. Each constraint is respected absolutely. | 
| **Max Questions** | `10` | Upper limit on questions per session. Sessions end when this is reached. |
| **Completion Criteria** | `""` | Free-text description of completion conditions (informational). |
| **Goal Coverage Threshold** | `0.85` | When the cosine similarity between all Q&A content and the goal exceeds this value, the session completes early. Range: 0.0–1.0. |
| **Context Similarity Threshold** | `0.7` | Similarity threshold for context relevance checks. Range: 0.0–1.0. |

### Example: Creating via API

```bash
curl -X POST http://localhost:8000/api/v1/admin/surveys \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Remote Work Satisfaction Q1 2026",
    "context": "We are a 200-person tech company that went fully remote in 2023. We want to understand how employees feel about our current remote work policy.",
    "goal": "Understand employee satisfaction with remote work, identify key challenges, and discover improvement opportunities.",
    "constraints": [
      "Do not ask about individual salaries or compensation",
      "Avoid naming specific managers or teams"
    ],
    "max_questions": 8,
    "goal_coverage_threshold": 0.80
  }'
```

---

## Managing Surveys

### Listing Surveys

**Dashboard:** The admin dashboard shows all surveys with their status and session counts.

**API:**

```bash
curl "http://localhost:8000/api/v1/admin/surveys?skip=0&limit=20"
```

### Viewing Survey Details

Click a survey in the dashboard to see:
- Full configuration
- Session statistics (total, completed, average questions)
- All responses with conversation histories

**API:**

```bash
curl "http://localhost:8000/api/v1/admin/surveys/{survey_id}"
```

### Editing a Survey

Update any field — only include the fields you want to change.

```bash
curl -X PUT http://localhost:8000/api/v1/admin/surveys/{survey_id} \
  -H "Content-Type: application/json" \
  -d '{"max_questions": 12, "goal_coverage_threshold": 0.9}'
```

> **Tip:** Editing a survey does not affect sessions already in progress. New sessions will use the updated configuration.

### Deleting a Survey

Deletion is a soft delete — the survey is marked as inactive.

```bash
curl -X DELETE http://localhost:8000/api/v1/admin/surveys/{survey_id}
```

---

## Viewing Responses and Stats

### Responses

Get all session responses for a survey:

```bash
curl "http://localhost:8000/api/v1/admin/surveys/{survey_id}/responses?skip=0&limit=50"
```

Each response includes:
- Session metadata (user ID, status, timestamps)
- Full conversation history (every question + answer, in order)

### Statistics

```bash
curl "http://localhost:8000/api/v1/admin/surveys/{survey_id}/stats"
```

Returns:
- `total_sessions` — How many participants started the survey
- `completed_sessions` — How many reached completion
- `abandoned_sessions` — How many exited early
- `avg_questions_per_session` — Average number of questions asked
- `avg_completion_time_seconds` — Average session duration
- `top_themes` — Most common themes extracted from responses

---

## Understanding Survey Configuration

### Context

The **context** field is the most important input. It tells the AI agent what the survey is about, who the audience is, and what background information is relevant. Think of it as a briefing document for a human interviewer.

**Good context includes:**
- Organization / product / situation description
- Target audience
- Relevant background events or changes
- Scope boundaries

### Goal

The **goal** drives the AI's question strategy and determines when a session can end early (via goal coverage). Write it as a clear research objective.

### Constraints

Constraints are hard rules the AI must follow. Use them to:
- Exclude sensitive topics (salary, health, personal relationships)
- Avoid naming specific individuals
- Keep questions within a certain scope
- Enforce tone (e.g., "Keep questions professional and respectful")

### Max Questions

Sets the hard upper limit. The session *may* end earlier if goal coverage is reached. Choose a number that balances thoroughness with participant fatigue:
- **5–6** for quick pulse surveys
- **8–10** for standard research surveys
- **12–15** for in-depth interviews

### Goal Coverage Threshold

Controls how aggressively the system ends sessions early. A value of **0.85** means the session ends when the combined Q&A content has 85% semantic similarity to the goal.

- **Lower (0.6–0.7):** Sessions end sooner, fewer questions
- **Higher (0.85–0.95):** Sessions go deeper, more thorough coverage

---

## Best Practices

### Writing Effective Context

1. **Be specific**, not generic. "Mid-size tech company with 200 employees that went remote in 2023" is better than "a company."
2. **Include relevant events.** "We recently changed our PTO policy" gives the AI something to probe.
3. **Define the audience.** "Software engineers on the platform team" generates more targeted questions than "employees."
4. **Set scope.** "Focus on day-to-day productivity, not company strategy" prevents off-topic drift.

### Writing Effective Goals

1. **Use action verbs.** "Understand", "Identify", "Discover", "Evaluate".
2. **Be multi-faceted.** "Understand satisfaction AND identify challenges AND discover improvement opportunities" encourages diverse questions.
3. **Be measurable.** Goals that have concrete sub-topics help the coverage estimator.

### Constraint Tips

- Write constraints as clear prohibitions: "Do not ask about X".
- Use constraints sparingly — too many constraints limit the AI's ability to explore.
- Test your survey with a short session first to verify constraints are respected.
