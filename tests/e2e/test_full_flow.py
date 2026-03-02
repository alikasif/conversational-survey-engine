"""
E2E Test Suite for Conversational Survey Engine
Executes all scenarios against the running backend at http://localhost:8000
"""

import requests
import time
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000"
RESULTS = []

# Shared state across scenarios
STATE = {}


def record(scenario_id: str, name: str, result: str, details: str = "", expected: str = "", actual: str = "", bug_fix_hint: str = ""):
    entry = {
        "scenario_id": scenario_id,
        "name": name,
        "result": result,
        "details": details,
        "expected": expected,
        "actual": actual,
        "failure_summary": details if result in ("FAIL", "ERROR") else "",
        "bug_fix_hint": bug_fix_hint,
    }
    RESULTS.append(entry)
    icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️", "SKIP": "⏭️"}.get(result, "?")
    print(f"  {icon} {scenario_id}: {name} -> {result} {details}")


def run_scenario(scenario_id, name, func):
    try:
        func()
    except AssertionError as e:
        record(scenario_id, name, "FAIL", str(e))
    except Exception as e:
        record(scenario_id, name, "ERROR", f"{type(e).__name__}: {e}")


# --- Phase 1: Infrastructure ---

def s001():
    r = requests.get(f"{BASE_URL}/health")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    body = r.json()
    assert body.get("status") == "ok", f"Expected status='ok', got {body}"
    record("S001", "Health check", "PASS")


def s002():
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    body = r.json()
    for field in ("name", "version", "docs"):
        assert field in body, f"Missing field '{field}' in root response: {body}"
    record("S002", "Root endpoint", "PASS")


# --- Phase 2: Admin CRUD - Dynamic Mode ---

def s003():
    payload = {
        "title": "E2E Dynamic Survey",
        "context": "Customer satisfaction for an e-commerce platform",
        "goal": "Understand customer pain points in checkout flow",
        "constraints": ["Keep questions focused on checkout experience", "Avoid leading questions"],
        "max_questions": 5,
        "question_mode": "dynamic",
    }
    r = requests.post(f"{BASE_URL}/api/v1/admin/surveys", json=payload)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("question_mode") == "dynamic", f"Expected question_mode='dynamic', got {body.get('question_mode')}"
    STATE["DYNAMIC_SURVEY_ID"] = body["id"]
    record("S003", "Create dynamic survey", "PASS", f"id={body['id']}")


def s004():
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    body = r.json()
    assert "surveys" in body, f"Missing 'surveys' key: {list(body.keys())}"
    assert isinstance(body["surveys"], list), f"surveys is not a list"
    record("S004", "List surveys", "PASS", f"count={len(body['surveys'])}")


def s005():
    sid = STATE["DYNAMIC_SURVEY_ID"]
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys/{sid}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "total_sessions" in body, f"Missing 'total_sessions' field: {list(body.keys())}"
    record("S005", "Get dynamic survey detail", "PASS")


def s006():
    sid = STATE["DYNAMIC_SURVEY_ID"]
    r = requests.put(f"{BASE_URL}/api/v1/admin/surveys/{sid}", json={"title": "E2E Dynamic Survey Updated"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("title") == "E2E Dynamic Survey Updated", f"Title not updated: {body.get('title')}"
    record("S006", "Update dynamic survey", "PASS")


def s007():
    sid = STATE["DYNAMIC_SURVEY_ID"]
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys/{sid}/stats")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert "survey_id" in body, f"Missing 'survey_id' field: {list(body.keys())}"
    record("S007", "Get survey stats", "PASS")


def s008():
    sid = STATE["DYNAMIC_SURVEY_ID"]
    r = requests.delete(f"{BASE_URL}/api/v1/admin/surveys/{sid}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text}"
    record("S008", "Delete dynamic survey", "PASS")


# --- Phase 3: Admin CRUD - Preset Mode ---

def s009():
    payload = {
        "title": "E2E Preset Survey",
        "context": "Employee engagement at a tech company",
        "goal": "Measure team morale and identify improvement areas",
        "constraints": ["Keep questions professional", "Avoid personal questions"],
        "max_questions": 3,
        "question_mode": "preset",
    }
    r = requests.post(f"{BASE_URL}/api/v1/admin/surveys", json=payload)
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("question_mode") == "preset", f"Expected question_mode='preset', got {body.get('question_mode')}"
    STATE["PRESET_SURVEY_ID"] = body["id"]
    record("S009", "Create preset survey", "PASS", f"id={body['id']}")


def s010():
    sid = STATE["PRESET_SURVEY_ID"]
    payload = {
        "questions": [
            {"question_number": 1, "question_id": "pq1", "text": "How satisfied are you with your current team collaboration?"},
            {"question_number": 2, "question_id": "pq2", "text": "What is the biggest challenge you face in your daily work?"},
            {"question_number": 3, "question_id": "pq3", "text": "How would you rate management communication?"},
        ]
    }
    r = requests.put(f"{BASE_URL}/api/v1/admin/surveys/{sid}/preset-questions", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    record("S010", "Set preset questions", "PASS")


def s011():
    sid = STATE["PRESET_SURVEY_ID"]
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys/{sid}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    pq = body.get("preset_questions", [])
    assert len(pq) == 3, f"Expected 3 preset questions, got {len(pq)}"
    record("S011", "Verify preset questions", "PASS")


def s012():
    # Create a dynamic survey for error testing
    payload = {
        "title": "E2E Dynamic For Error Test",
        "context": "Test",
        "goal": "Test",
        "max_questions": 3,
        "question_mode": "dynamic",
    }
    r = requests.post(f"{BASE_URL}/api/v1/admin/surveys", json=payload)
    assert r.status_code == 201, f"Expected 201 for survey creation, got {r.status_code}: {r.text}"
    body = r.json()
    STATE["ERROR_TEST_SURVEY_ID"] = body["id"]

    # Try generate-questions on a dynamic survey - should fail with 400
    r2 = requests.post(f"{BASE_URL}/api/v1/admin/surveys/{body['id']}/generate-questions")
    assert r2.status_code == 400, f"Expected 400 for generate-questions on dynamic survey, got {r2.status_code}: {r2.text}"
    record("S012", "Generate questions on dynamic survey (expect 400)", "PASS")


# --- Phase 4: Participant Flow - Preset Mode ---

def s013():
    sid = STATE["PRESET_SURVEY_ID"]
    r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions", json={})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    STATE["PRESET_SESSION_ID"] = body["session_id"]
    cq = body.get("current_question", {})
    STATE["current_question_id"] = cq.get("question_id", "")
    STATE["current_question_text"] = cq.get("text", "")
    assert "How satisfied are you with your current team collaboration?" in cq.get("text", ""), \
        f"First question mismatch: {cq.get('text', '')}"
    record("S013", "Start preset session, verify Q1", "PASS", f"session_id={body['session_id']}")


def s014():
    sid = STATE["PRESET_SURVEY_ID"]
    sess_id = STATE["PRESET_SESSION_ID"]
    time.sleep(2.5)
    payload = {
        "answer": "I think collaboration is generally good but could be improved with better tools",
        "question_id": STATE["current_question_id"],
        "question_text": STATE["current_question_text"],
    }
    r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("status") == "active", f"Expected status='active', got {body.get('status')}"
    q = body.get("question", {})
    STATE["current_question_id"] = q.get("question_id", "")
    STATE["current_question_text"] = q.get("text", "")
    assert "biggest challenge" in q.get("text", "").lower(), \
        f"Q2 mismatch: {q.get('text', '')}"
    record("S014", "Answer Q1, verify Q2 returned", "PASS")


def s015():
    sid = STATE["PRESET_SURVEY_ID"]
    sess_id = STATE["PRESET_SESSION_ID"]

    # Answer Q2
    time.sleep(2.5)
    payload_q2 = {
        "answer": "The biggest challenge is managing multiple deadlines simultaneously",
        "question_id": STATE["current_question_id"],
        "question_text": STATE["current_question_text"],
    }
    r2 = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload_q2)
    assert r2.status_code == 200, f"Expected 200 for Q2 answer, got {r2.status_code}: {r2.text}"
    body2 = r2.json()
    q3 = body2.get("question", {})
    q3_id = q3.get("question_id", "")
    q3_text = q3.get("text", "")
    assert "management communication" in q3_text.lower(), f"Q3 mismatch: {q3_text}"

    # Answer Q3
    time.sleep(2.5)
    payload_q3 = {
        "answer": "Management communication is decent but could be more transparent",
        "question_id": q3_id,
        "question_text": q3_text,
    }
    r3 = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload_q3)
    assert r3.status_code == 200, f"Expected 200 for Q3 answer, got {r3.status_code}: {r3.text}"
    body3 = r3.json()
    assert body3.get("status") == "completed", f"Expected status='completed' after Q3, got {body3.get('status')}"
    record("S015", "Answer Q2 & Q3, session completed", "PASS")


def s016():
    sid = STATE["PRESET_SURVEY_ID"]
    sess_id = STATE["PRESET_SESSION_ID"]
    r = requests.get(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    conv = body.get("conversation", [])
    assert len(conv) >= 3, f"Expected >= 3 conversation entries, got {len(conv)}"
    record("S016", "Get session detail, verify conversation", "PASS", f"conversation_len={len(conv)}")


def s017():
    sid = STATE["PRESET_SURVEY_ID"]
    sess_id = STATE["PRESET_SESSION_ID"]
    time.sleep(2.5)
    payload = {
        "answer": "This should fail",
        "question_id": "pq1",
        "question_text": "any",
    }
    r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload)
    assert r.status_code == 409, f"Expected 409 for respond on completed session, got {r.status_code}: {r.text}"
    record("S017", "Respond on completed session (expect 409)", "PASS")


# --- Phase 5: Participant Flow - Dynamic Mode (LLM-dependent) ---

def s018():
    sid = STATE["ERROR_TEST_SURVEY_ID"]
    try:
        r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions", json={}, timeout=30)
    except requests.Timeout:
        record("S018", "Start dynamic session", "SKIP", "Request timed out (LLM issue)")
        return
    if r.status_code in (400, 500, 502, 503):
        record("S018", "Start dynamic session", "SKIP", f"LLM unavailable: {r.status_code} {r.text[:200]}")
        return
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text}"
    body = r.json()
    cq = body.get("current_question", {})
    assert cq.get("text"), f"No current_question text: {body}"
    STATE["DYNAMIC_SESSION_ID"] = body["session_id"]
    STATE["dynamic_question_id"] = cq.get("question_id", "")
    STATE["dynamic_question_text"] = cq.get("text", "")
    record("S018", "Start dynamic session", "PASS", f"session_id={body['session_id']}")


def s019():
    if "DYNAMIC_SESSION_ID" not in STATE:
        record("S019", "Respond in dynamic session", "SKIP", "S018 was skipped")
        return
    sid = STATE["ERROR_TEST_SURVEY_ID"]
    sess_id = STATE["DYNAMIC_SESSION_ID"]
    time.sleep(2.5)
    payload = {
        "answer": "The checkout process takes too long and has too many steps",
        "question_id": STATE.get("dynamic_question_id", ""),
        "question_text": STATE.get("dynamic_question_text", ""),
    }
    try:
        r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload, timeout=30)
    except requests.Timeout:
        record("S019", "Respond in dynamic session", "SKIP", "Request timed out (LLM issue)")
        return
    if r.status_code in (500, 502, 503):
        record("S019", "Respond in dynamic session", "SKIP", f"LLM unavailable: {r.status_code}")
        return
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    record("S019", "Respond in dynamic session", "PASS")


# --- Phase 6: Error Handling ---

def s020():
    r = requests.post(f"{BASE_URL}/api/v1/surveys/nonexistent-id-12345/sessions", json={})
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
    record("S020", "Session on non-existent survey (404)", "PASS")


def s021():
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys/nonexistent-id-12345")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"
    record("S021", "Get non-existent survey (404)", "PASS")


def s022():
    payload = {"title": "Bad", "context": "x", "goal": "x", "question_mode": "invalid_mode"}
    r = requests.post(f"{BASE_URL}/api/v1/admin/surveys", json=payload)
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"
    record("S022", "Invalid question_mode (422)", "PASS")


def s023():
    sid = STATE["PRESET_SURVEY_ID"]
    sess_id = STATE["PRESET_SESSION_ID"]
    payload = {"answer": ""}
    r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload)
    # Accept 422 (validation error) or 409 (session completed) - both are correct
    assert r.status_code in (422, 409), f"Expected 422 or 409, got {r.status_code}: {r.text}"
    record("S023", "Empty answer (422 or 409)", "PASS", f"status={r.status_code}")


def s024():
    sid = STATE["PRESET_SURVEY_ID"]
    # Create a new session
    r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions", json={})
    assert r.status_code == 201, f"Expected 201 for new session, got {r.status_code}: {r.text}"
    body = r.json()
    new_sess_id = body["session_id"]
    STATE["EXIT_SESSION_ID"] = new_sess_id

    time.sleep(2.5)

    # Exit the session
    r2 = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{new_sess_id}/exit")
    assert r2.status_code == 200, f"Expected 200 for exit, got {r2.status_code}: {r2.text}"
    body2 = r2.json()
    assert body2.get("status") == "exited", f"Expected status='exited', got {body2.get('status')}"
    record("S024", "Exit session early", "PASS")


def s025():
    sid = STATE["PRESET_SURVEY_ID"]
    sess_id = STATE["EXIT_SESSION_ID"]
    time.sleep(2.5)
    payload = {
        "answer": "This should fail on exited session",
        "question_id": "pq1",
        "question_text": "any",
    }
    r = requests.post(f"{BASE_URL}/api/v1/surveys/{sid}/sessions/{sess_id}/respond", json=payload)
    assert r.status_code == 409, f"Expected 409 for respond on exited session, got {r.status_code}: {r.text}"
    record("S025", "Respond on exited session (409)", "PASS")


# --- Phase 7: Cross-Layer Verification ---

def s026():
    sid = STATE["PRESET_SURVEY_ID"]
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys/{sid}/responses")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    responses = body.get("responses", [])
    assert len(responses) >= 1, f"Expected >= 1 responses, got {len(responses)}"
    record("S026", "Survey responses exist", "PASS", f"responses_count={len(responses)}")


def s027():
    sid = STATE["PRESET_SURVEY_ID"]
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys/{sid}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    ts = body.get("total_sessions", 0)
    cs = body.get("completed_sessions", 0)
    assert ts >= 1, f"Expected total_sessions >= 1, got {ts}"
    assert cs >= 1, f"Expected completed_sessions >= 1, got {cs}"
    record("S027", "Survey stats reflect sessions", "PASS", f"total={ts}, completed={cs}")


def s028():
    r = requests.get(f"{BASE_URL}/api/v1/admin/surveys", params={"skip": 0, "limit": 1})
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    surveys = body.get("surveys", [])
    assert len(surveys) == 1, f"Expected exactly 1 survey with limit=1, got {len(surveys)}"
    total = body.get("total", 0)
    assert total >= 1, f"Expected total >= 1, got {total}"
    record("S028", "Pagination works", "PASS", f"total={total}, returned={len(surveys)}")


# --- Main ---

SCENARIOS = [
    ("S001", "Health check", s001),
    ("S002", "Root endpoint", s002),
    ("S003", "Create dynamic survey", s003),
    ("S004", "List surveys", s004),
    ("S005", "Get dynamic survey detail", s005),
    ("S006", "Update dynamic survey", s006),
    ("S007", "Get survey stats", s007),
    ("S008", "Delete dynamic survey", s008),
    ("S009", "Create preset survey", s009),
    ("S010", "Set preset questions", s010),
    ("S011", "Verify preset questions", s011),
    ("S012", "Generate questions on dynamic survey (expect 400)", s012),
    ("S013", "Start preset session, verify Q1", s013),
    ("S014", "Answer Q1, verify Q2 returned", s014),
    ("S015", "Answer Q2 & Q3, session completed", s015),
    ("S016", "Get session detail, verify conversation", s016),
    ("S017", "Respond on completed session (expect 409)", s017),
    ("S018", "Start dynamic session", s018),
    ("S019", "Respond in dynamic session", s019),
    ("S020", "Session on non-existent survey (404)", s020),
    ("S021", "Get non-existent survey (404)", s021),
    ("S022", "Invalid question_mode (422)", s022),
    ("S023", "Empty answer (422 or 409)", s023),
    ("S024", "Exit session early", s024),
    ("S025", "Respond on exited session (409)", s025),
    ("S026", "Survey responses exist", s026),
    ("S027", "Survey stats reflect sessions", s027),
    ("S028", "Pagination works", s028),
]


def main():
    print(f"\n{'='*60}")
    print(f" E2E Test Suite - Conversational Survey Engine")
    print(f" Target: {BASE_URL}")
    print(f" Started: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

    for sid, name, func in SCENARIOS:
        run_scenario(sid, name, func)

    # Summary
    pass_count = sum(1 for r in RESULTS if r["result"] == "PASS")
    fail_count = sum(1 for r in RESULTS if r["result"] == "FAIL")
    error_count = sum(1 for r in RESULTS if r["result"] == "ERROR")
    skip_count = sum(1 for r in RESULTS if r["result"] == "SKIP")
    total = len(RESULTS)

    print(f"\n{'='*60}")
    print(f" SUMMARY: {pass_count} PASS | {fail_count} FAIL | {error_count} ERROR | {skip_count} SKIP | {total} TOTAL")
    print(f"{'='*60}")

    if fail_count > 0 or error_count > 0:
        print(f"\n FAILURES & ERRORS:")
        for r in RESULTS:
            if r["result"] in ("FAIL", "ERROR"):
                print(f"   {r['scenario_id']}: {r['name']} -> {r['result']}: {r['details']}")

    # Write results to shared/e2e_scenarios.json
    output = {
        "run_timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "error": error_count,
            "skip": skip_count,
        },
        "scenarios": RESULTS,
    }
    output_path = "d:/GitHub/conversational-survey-engine/shared/e2e_scenarios.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n Results written to {output_path}")

    # Exit code: 0 if all pass/skip, 1 if any fail/error
    sys.exit(1 if (fail_count + error_count) > 0 else 0)


if __name__ == "__main__":
    main()
