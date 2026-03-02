from dotenv import load_dotenv
load_dotenv()

from intelligence.pipeline import run_ai

audit_request = {
    "name": "TestBot",
    "domain": "healthcare",
    "description": "A chatbot that answers patient questions.",
    "intended_users": "Patients",
    "outputs": "Text responses",
    "deployment": "Web app",
    "data_types": "Medical history",
}

normalization_flags = {
    "high_risk_domain": True,
    "processes_personal_data": True,
}

result = run_ai(audit_request, normalization_flags)
print("Risk band:", result["risk_band"])
print("Confidence:", result["confidence"])
print("Summary:", result["summary"])