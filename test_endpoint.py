import requests
import json

BASE = "http://localhost:8000/api/v1"

# Step 1: Create a preset-mode survey
print("Creating preset survey...")
payload = {
    "title": "Preset Test Survey",
    "context": "Gathering feedback on remote work policies at a tech company",
    "goal": "Understand employee preferences for remote vs hybrid work",
    "constraints": ["Keep questions professional"],
    "max_questions": 5,
    "question_mode": "preset"
}
r = requests.post(f"{BASE}/admin/surveys", json=payload)
print(f"CREATE STATUS: {r.status_code}")
print(f"CREATE BODY: {r.text[:500]}")
if r.status_code >= 300:
    print("FAILED to create survey")
    exit(1)

data = r.json()
sid = data["id"]
print(f"Survey ID: {sid}, mode: {data.get('question_mode')}")

# Step 2: Generate preset questions
print(f"\nGenerating preset questions...")
r2 = requests.post(f"{BASE}/admin/surveys/{sid}/generate-questions", timeout=120)
print(f"GENERATE STATUS: {r2.status_code}")
print(f"GENERATE BODY: {r2.text[:3000]}")
