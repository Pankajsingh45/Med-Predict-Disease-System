import json
with open("models/symptom_list.json") as f:
    symptoms = json.load(f)
print("✅ Total known symptoms:", len(symptoms))
print("\n🩺 Sample of known symptoms:", symptoms[:50])

