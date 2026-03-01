"""
AegisAI - Comprehensive Rule-Based Risk Engine
================================================
All risk classification decisions are made here deterministically.
The LLM only generates natural language explanations for what the rules decided.

Rule sources:
    - EU AI Act 2024 (Articles 5, 6, 7, 13, 14, 15, Annexes I-III)
    - NIST AI RMF 1.0 (Govern, Map, Measure, Manage)
    - OWASP Top 10 for LLM Applications 2025
    - OECD AI Principles 2024
    - ISO/IEC 42001:2023
    - GDPR 2016/679
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

EU_COUNTRIES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT",
    "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RiskEngineResult:
    score: int
    risk_band: str
    prohibited: bool
    prohibition_reasons: list[str]
    score_breakdown: list[dict[str, Any]]
    minimum_band_applied: str | None
    threats: list[dict[str, Any]]
    compliance_requirements: list[str]
    nist_functions: list[str]
    override_reason: str
    ruleset: str  # "EU" or "NIST"


# ---------------------------------------------------------------------------
# EU AI Act Article 5 - PROHIBITED PRACTICES
# Any single match forces risk_band = unacceptable, score = 100
# ---------------------------------------------------------------------------

_PROHIBITIONS: list[dict[str, Any]] = [
    {
        "rule_id": "EU-AIA-ART5-1A",
        "rule_name": "Subliminal manipulation of behaviour",
        "source": "EU AI Act Article 5(1)(a)",
        "description": "AI deploying subliminal techniques beyond consciousness to materially distort behaviour causing harm.",
        "required_flags": ["subliminal_manipulation"],
    },
    {
        "rule_id": "EU-AIA-ART5-1B",
        "rule_name": "Exploitation of vulnerabilities of specific groups",
        "source": "EU AI Act Article 5(1)(b)",
        "description": "AI exploiting vulnerabilities of persons due to age, disability or social situation to distort behaviour causing harm.",
        "required_flags": ["exploits_vulnerability", "targets_vulnerable_groups"],
    },
    {
        "rule_id": "EU-AIA-ART5-1C",
        "rule_name": "Social scoring by public authorities",
        "source": "EU AI Act Article 5(1)(c)",
        "description": "AI evaluating or classifying persons based on social behaviour or inferred personal characteristics by public authorities.",
        "required_flags": ["social_scoring"],
    },
    {
        "rule_id": "EU-AIA-ART5-1D",
        "rule_name": "Real-time biometric ID in public spaces for law enforcement",
        "source": "EU AI Act Article 5(1)(d)",
        "description": "Real-time remote biometric identification in public spaces by law enforcement (with narrow legal exceptions).",
        "required_flags": ["real_time_biometric", "public_spaces", "law_enforcement"],
    },
    {
        "rule_id": "EU-AIA-ART5-1E",
        "rule_name": "Emotion recognition in workplace",
        "source": "EU AI Act Article 5(1)(f)",
        "description": "AI systems inferring emotions of persons in workplace contexts.",
        "required_flags": ["emotion_recognition", "employment_decision"],
    },
    {
        "rule_id": "EU-AIA-ART5-1E-EDU",
        "rule_name": "Emotion recognition in educational institutions",
        "source": "EU AI Act Article 5(1)(f)",
        "description": "AI systems inferring emotions of persons in educational institution contexts.",
        "required_flags": ["emotion_recognition", "education"],
    },
    {
        "rule_id": "EU-AIA-ART5-1F",
        "rule_name": "Biometric categorisation by protected characteristics",
        "source": "EU AI Act Article 5(1)(g)",
        "description": "AI categorising individuals by biometric data to infer race, political opinion, religion, sexual orientation or trade union membership.",
        "required_flags": ["biometric_categorisation_protected"],
    },
    {
        "rule_id": "EU-AIA-ART5-1G",
        "rule_name": "Predictive policing based solely on profiling",
        "source": "EU AI Act Article 5(1)(e)",
        "description": "AI assessing individual criminal risk based solely on profiling without objective verifiable facts.",
        "required_flags": ["predictive_policing", "profiling_only"],
    },
    {
        "rule_id": "EU-AIA-ART5-MASS",
        "rule_name": "Mass surveillance of population",
        "source": "EU AI Act Article 5 + ECHR Article 8",
        "description": "AI conducting indiscriminate mass surveillance without specific legal basis.",
        "required_flags": ["mass_surveillance"],
    },
]

# ---------------------------------------------------------------------------
# EU AI Act Annex III - HIGH RISK classification rules
# Each triggered rule: adds points, enforces min_band = high, adds compliance items
# ---------------------------------------------------------------------------

_HIGH_RISK_RULES: list[dict[str, Any]] = [
    # --- Biometric ---
    {
        "rule_id": "EU-AIII-1A",
        "rule_name": "Remote biometric identification system",
        "source": "EU AI Act Annex III (1)(a)",
        "points": 40,
        "trigger_flags": ["biometric", "remote_identification"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Registration in EU AI database (Art. 49)",
            "Fundamental rights impact assessment (Art. 27)",
        ],
    },
    {
        "rule_id": "EU-AIII-1B",
        "rule_name": "Biometric categorisation system",
        "source": "EU AI Act Annex III (1)(b)",
        "points": 35,
        "trigger_flags": ["biometric_categorisation"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Technical documentation required (Art. 11)",
            "Transparency to affected persons (Art. 50)",
        ],
    },
    {
        "rule_id": "EU-AIII-1C",
        "rule_name": "Emotion recognition system",
        "source": "EU AI Act Annex III (1)(c)",
        "points": 30,
        "trigger_flags": ["emotion_recognition"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Transparency obligation to affected persons (Art. 50)",
            "Human oversight measures required (Art. 14)",
            "Strict legal basis required for deployment",
        ],
    },

    # --- Critical infrastructure ---
    {
        "rule_id": "EU-AIII-2A",
        "rule_name": "Critical infrastructure safety component",
        "source": "EU AI Act Annex III (2)",
        "points": 40,
        "trigger_flags": ["critical_infrastructure"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Cybersecurity robustness measures required (Art. 15)",
            "Incident reporting to national supervisory authority",
            "Post-market monitoring plan required (Art. 72)",
        ],
    },
    {
        "rule_id": "EU-AIII-2B",
        "rule_name": "Energy grid management AI",
        "source": "EU AI Act Annex III (2)",
        "points": 40,
        "trigger_flags": ["energy_grid"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Resilience and failsafe mechanisms required",
        ],
    },
    {
        "rule_id": "EU-AIII-2C",
        "rule_name": "Transport safety AI",
        "source": "EU AI Act Annex III (2)",
        "points": 40,
        "trigger_flags": ["transport_safety"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Sector-specific safety certification required",
        ],
    },

    # --- Education ---
    {
        "rule_id": "EU-AIII-3A",
        "rule_name": "AI determining access to educational institutions",
        "source": "EU AI Act Annex III (3)(a)",
        "points": 25,
        "trigger_flags": ["education", "admission"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Human oversight required (Art. 14)",
            "Transparency to affected persons (Art. 13)",
            "Logging and audit trail required (Art. 12)",
            "Non-discrimination testing required",
        ],
    },
    {
        "rule_id": "EU-AIII-3B",
        "rule_name": "AI assessing students in educational institutions",
        "source": "EU AI Act Annex III (3)(b)",
        "points": 25,
        "trigger_flags": ["education", "assessment"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Human oversight required (Art. 14)",
            "Right of explanation for assessed persons",
            "Audit trail required (Art. 12)",
        ],
    },

    # --- Employment ---
    {
        "rule_id": "EU-AIII-4A",
        "rule_name": "Recruitment and selection of persons",
        "source": "EU AI Act Annex III (4)(a)",
        "points": 35,
        "trigger_flags": ["employment_decision", "recruitment"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Non-discrimination bias audit required",
            "Right to explanation for rejected candidates",
            "Transparency to applicants (Art. 13)",
        ],
    },
    {
        "rule_id": "EU-AIII-4B",
        "rule_name": "AI for hiring decisions",
        "source": "EU AI Act Annex III (4)(a)",
        "points": 35,
        "trigger_flags": ["employment_decision", "hiring"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Human oversight of final decisions required",
            "Non-discrimination audit required",
        ],
    },
    {
        "rule_id": "EU-AIII-4C",
        "rule_name": "AI for promotion and termination decisions",
        "source": "EU AI Act Annex III (4)(c)",
        "points": 30,
        "trigger_flags": ["employment_decision", "termination"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Right to human review of decisions",
            "Non-discrimination audit required",
            "Documentation of decision criteria required",
        ],
    },
    {
        "rule_id": "EU-AIII-4D",
        "rule_name": "AI for performance evaluation",
        "source": "EU AI Act Annex III (4)(c)",
        "points": 25,
        "trigger_flags": ["employment_decision", "performance_evaluation"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Transparency to evaluated employees (Art. 13)",
            "Human oversight of automated evaluations",
        ],
    },
    {
        "rule_id": "EU-AIII-4E",
        "rule_name": "AI for worker monitoring and surveillance",
        "source": "EU AI Act Annex III (4)(b)",
        "points": 25,
        "trigger_flags": ["employment_monitoring"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map"],
        "compliance": [
            "Transparency to monitored workers required",
            "Works council / union consultation required where applicable",
            "Legal basis for monitoring required",
        ],
    },

    # --- Essential services ---
    {
        "rule_id": "EU-AIII-5A",
        "rule_name": "Creditworthiness and credit scoring AI",
        "source": "EU AI Act Annex III (5)(a)",
        "points": 30,
        "trigger_flags": ["credit_scoring"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Right to explanation under GDPR Art. 22",
            "Non-discrimination testing required",
            "Audit trail of all credit decisions required",
            "Human review available to applicants",
        ],
    },
    {
        "rule_id": "EU-AIII-5B",
        "rule_name": "Loan decision AI",
        "source": "EU AI Act Annex III (5)(a)",
        "points": 30,
        "trigger_flags": ["loan_decision"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Right to explanation required",
            "Human review mechanism required",
        ],
    },
    {
        "rule_id": "EU-AIII-5C",
        "rule_name": "Public benefits and social services AI",
        "source": "EU AI Act Annex III (5)(b)",
        "points": 30,
        "trigger_flags": ["public_benefits"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Human oversight mandatory for all benefit decisions",
            "Appeal mechanism required for affected persons",
            "Non-discrimination audit required",
        ],
    },
    {
        "rule_id": "EU-AIII-5D",
        "rule_name": "Emergency services dispatch AI",
        "source": "EU AI Act Annex III (5)(c)",
        "points": 35,
        "trigger_flags": ["emergency_services"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Human operator oversight mandatory",
            "Failsafe and redundancy mechanisms required",
        ],
    },

    # --- Law enforcement ---
    {
        "rule_id": "EU-AIII-6A",
        "rule_name": "Individual risk assessment for crime likelihood",
        "source": "EU AI Act Annex III (6)(a)",
        "points": 40,
        "trigger_flags": ["law_enforcement", "risk_assessment_crime"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Fundamental rights impact assessment required (Art. 27)",
            "Human oversight at all decision points",
            "Audit trail and logging required (Art. 12)",
            "Non-discrimination validation required",
        ],
    },
    {
        "rule_id": "EU-AIII-6B",
        "rule_name": "Polygraph and emotional state detection in law enforcement",
        "source": "EU AI Act Annex III (6)(b)",
        "points": 35,
        "trigger_flags": ["law_enforcement", "emotion_detection"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Strict legal basis required",
            "Human review of all outputs mandatory",
            "Scientific validity evidence required",
        ],
    },
    {
        "rule_id": "EU-AIII-6C",
        "rule_name": "Crime analytics and crime prediction",
        "source": "EU AI Act Annex III (6)(d)",
        "points": 35,
        "trigger_flags": ["law_enforcement", "crime_analytics"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Fundamental rights impact assessment required",
            "Non-discrimination and bias validation required",
            "Human oversight of all operational decisions",
        ],
    },
    {
        "rule_id": "EU-AIII-6D",
        "rule_name": "AI used to analyse criminal evidence",
        "source": "EU AI Act Annex III (6)(e)",
        "points": 35,
        "trigger_flags": ["law_enforcement", "evidence_analysis"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure"],
        "compliance": [
            "Scientific validation of methodology required",
            "Human expert review of all outputs",
        ],
    },

    # --- Migration / asylum ---
    {
        "rule_id": "EU-AIII-7A",
        "rule_name": "Lie detector and reliability assessment in migration context",
        "source": "EU AI Act Annex III (7)(a)",
        "points": 40,
        "trigger_flags": ["migration", "emotion_detection"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Fundamental rights impact assessment required",
            "Human decision-maker oversight mandatory",
        ],
    },
    {
        "rule_id": "EU-AIII-7B",
        "rule_name": "AI in asylum, visa and border control decisions",
        "source": "EU AI Act Annex III (7)(b)",
        "points": 40,
        "trigger_flags": ["asylum"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Fundamental rights impact assessment required",
            "Conformity assessment required (Art. 43)",
            "Human oversight mandatory for all decisions",
        ],
    },
    {
        "rule_id": "EU-AIII-7C",
        "rule_name": "Border control AI",
        "source": "EU AI Act Annex III (7)",
        "points": 40,
        "trigger_flags": ["border_control"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Conformity assessment required (Art. 43)",
            "Fundamental rights compliance verified",
        ],
    },

    # --- Justice and democracy ---
    {
        "rule_id": "EU-AIII-8A",
        "rule_name": "AI assisting in judicial decision-making",
        "source": "EU AI Act Annex III (8)(a)",
        "points": 40,
        "trigger_flags": ["judicial_decision"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Human judge oversight mandatory - AI is decision-support only",
            "Full explainability of all outputs required",
            "Audit trail required (Art. 12)",
            "Conformity assessment required (Art. 43)",
        ],
    },
    {
        "rule_id": "EU-AIII-8B",
        "rule_name": "AI influencing elections and democratic processes",
        "source": "EU AI Act Annex III (8)(b)",
        "points": 40,
        "trigger_flags": ["election_influence"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Transparency on AI-generated electoral content required",
            "Independent audit required",
            "Prohibited from voter manipulation",
        ],
    },

    # --- Healthcare ---
    {
        "rule_id": "HEALTH-MDR",
        "rule_name": "Medical device or clinical decision support AI",
        "source": "EU AI Act + EU MDR 2017/745 + IVDR 2017/746",
        "points": 35,
        "trigger_flags": ["medical_device_context"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Medical Device Regulation (MDR) or IVDR compliance required",
            "Clinical evaluation and validation required",
            "Post-market surveillance plan required",
            "Human clinician oversight mandatory",
            "Quality management system (ISO 13485) required",
        ],
    },
    {
        "rule_id": "HEALTH-DIAG",
        "rule_name": "Diagnostic assistance AI in healthcare",
        "source": "EU AI Act Annex III + MDR",
        "points": 30,
        "trigger_flags": ["diagnostic_assistance"],
        "min_band": "high",
        "nist_functions": ["Govern", "Map", "Measure", "Manage"],
        "compliance": [
            "Clinical validation required",
            "Clinician-in-the-loop for all diagnostic outputs",
            "Performance monitoring in production required",
            "Uncertainty quantification required in outputs",
        ],
    },
]

# ---------------------------------------------------------------------------
# General scoring rules (add points, no band enforcement)
# ---------------------------------------------------------------------------

_SCORING_RULES: list[dict[str, Any]] = [
    # Data sensitivity
    {"rule_id": "D-BIO",         "points": 20, "flag": "biometric",                  "label": "Biometric data processed"},
    {"rule_id": "D-HEALTH",      "points": 20, "flag": "health_data",                "label": "Health / medical data processed"},
    {"rule_id": "D-GENETIC",     "points": 20, "flag": "genetic_data",               "label": "Genetic data processed"},
    {"rule_id": "D-LOCATION",    "points": 10, "flag": "location_tracking",          "label": "Location data tracked"},
    {"rule_id": "D-FINANCIAL",   "points": 10, "flag": "financial_data",             "label": "Financial data processed"},
    {"rule_id": "D-MINORS",      "points": 20, "flag": "minors_involved",            "label": "Data of minors involved"},
    {"rule_id": "D-SENSITIVE",   "points": 15, "flag": "sensitive_data",             "label": "Sensitive personal data processed"},
    {"rule_id": "D-PERSONAL",    "points": 10, "flag": "processes_personal_data",    "label": "Personal data processed"},
    {"rule_id": "D-PROFILING",   "points": 15, "flag": "profiling",                  "label": "Individual profiling"},

    # Automation
    {"rule_id": "A-AUTO",        "points": 15, "flag": "automated_decision_making",  "label": "Automated decision-making"},
    {"rule_id": "A-SCORE",       "points": 10, "flag": "automated_scoring",          "label": "Automated scoring"},
    {"rule_id": "A-NOHUMAN",     "points": 15, "flag": "no_human_oversight",         "label": "No human oversight in loop"},
    {"rule_id": "A-AUTONOMOUS",  "points": 15, "flag": "autonomous_operation",       "label": "Autonomous operation"},
    {"rule_id": "A-AGENTIC",     "points": 10, "flag": "agentic_ai",                 "label": "Agentic AI with tool access"},

    # Deployment context
    {"rule_id": "C-PUBLIC-AUTH", "points": 10, "flag": "public_authority",           "label": "Deployed by public authority"},
    {"rule_id": "C-EU",          "points": 10, "flag": "eu_jurisdiction",            "label": "EU jurisdiction"},
    {"rule_id": "C-PUBLIC",      "points":  5, "flag": "public_exposure",            "label": "Public-facing deployment"},
    {"rule_id": "C-MULTIREGION", "points":  5, "flag": "multi_region",               "label": "Multi-region deployment"},
    {"rule_id": "C-HIGHVOLUME",  "points": 10, "flag": "high_volume",                "label": "High-volume deployment"},

    # Impact
    {"rule_id": "I-IRREVERSIBLE","points": 20, "flag": "irreversible_impact",        "label": "Potential irreversible harm"},
    {"rule_id": "I-PHYSICAL",    "points": 20, "flag": "physical_harm_possible",     "label": "Physical harm possible"},
    {"rule_id": "I-FUNDAMENTAL", "points": 20, "flag": "fundamental_rights",         "label": "Affects fundamental rights"},
    {"rule_id": "I-FINANCIAL",   "points": 10, "flag": "financial_harm_possible",    "label": "Financial harm possible"},

    # Model characteristics
    {"rule_id": "M-GENERATIVE",  "points":  5, "flag": "generative_ai",              "label": "Generative AI / LLM"},
    {"rule_id": "M-OPAQUE",      "points": 10, "flag": "black_box_model",            "label": "Black-box / opaque model"},
    {"rule_id": "M-SELFLEARN",   "points": 10, "flag": "continuous_learning",        "label": "Continuous / online learning"},
    {"rule_id": "M-THIRDPARTY",  "points":  5, "flag": "third_party_model",          "label": "Third-party model dependency"},
    {"rule_id": "M-FINETUNED",   "points":  5, "flag": "fine_tuned_model",           "label": "Fine-tuned model"},
]

# ---------------------------------------------------------------------------
# OWASP LLM Top 10 (2025) + domain threat rules
# ---------------------------------------------------------------------------

_THREATS: list[dict[str, Any]] = [
    {
        "threat_id": "OWASP-LLM01",
        "title": "Prompt Injection",
        "source": "OWASP LLM Top 10 - LLM01:2025",
        "description": "Attackers manipulate LLM inputs to override instructions, bypass safety controls, or exfiltrate data.",
        "severity": "high", "likelihood": "high",
        "trigger_flags": ["generative_ai", "conversational_agent", "llm_system"],
        "mitigations": [
            "Implement prompt firewalling and input sanitization",
            "Separate system instructions from user inputs architecturally",
            "Use structured output schemas and validate all LLM outputs",
            "Apply least-privilege to all LLM tool access",
        ],
    },
    {
        "threat_id": "OWASP-LLM02",
        "title": "Insecure Output Handling",
        "source": "OWASP LLM Top 10 - LLM02:2025",
        "description": "LLM outputs passed downstream without validation enabling XSS, SSRF, privilege escalation or code injection.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["generative_ai", "llm_system"],
        "mitigations": [
            "Validate and sanitize all LLM outputs before downstream use",
            "Apply context-aware output encoding",
            "Never execute LLM-generated code without sandbox isolation",
        ],
    },
    {
        "threat_id": "OWASP-LLM03",
        "title": "Training Data Poisoning",
        "source": "OWASP LLM Top 10 - LLM03:2025",
        "description": "Malicious data injected into training sets introduces backdoors, biases or vulnerabilities.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["custom_trained_model", "fine_tuned_model", "continuous_learning"],
        "mitigations": [
            "Audit and validate all training data sources",
            "Implement data provenance and lineage tracking",
            "Use adversarial testing to detect backdoors before deployment",
            "Apply differential privacy where feasible",
        ],
    },
    {
        "threat_id": "OWASP-LLM04",
        "title": "Model Denial of Service",
        "source": "OWASP LLM Top 10 - LLM04:2025",
        "description": "Adversaries send computationally expensive queries to degrade availability and inflate costs.",
        "severity": "medium", "likelihood": "medium",
        "trigger_flags": ["public_exposure", "api_access", "generative_ai"],
        "mitigations": [
            "Implement rate limiting and query complexity caps",
            "Monitor token consumption per user and session",
            "Use caching for repeated query patterns",
        ],
    },
    {
        "threat_id": "OWASP-LLM05",
        "title": "Supply Chain Vulnerabilities",
        "source": "OWASP LLM Top 10 - LLM05:2025",
        "description": "Vulnerabilities in third-party models, datasets or plugins compromise system integrity.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["third_party_model", "external_plugins", "third_party_data"],
        "mitigations": [
            "Maintain AI/ML bill of materials (AI-BOM)",
            "Verify integrity of all third-party components before integration",
            "Continuously monitor CVEs across all AI dependencies",
        ],
    },
    {
        "threat_id": "OWASP-LLM06",
        "title": "Sensitive Information Disclosure",
        "source": "OWASP LLM Top 10 - LLM06:2025",
        "description": "LLM inadvertently reveals confidential data, PII, or system internals in outputs.",
        "severity": "high", "likelihood": "high",
        "trigger_flags": ["processes_personal_data", "sensitive_data", "biometric", "health_data"],
        "mitigations": [
            "Implement output filtering for PII and sensitive data patterns",
            "Apply strict data minimization in context windows",
            "Conduct red-team data extraction attack exercises",
            "Use differential privacy in training pipelines",
        ],
    },
    {
        "threat_id": "OWASP-LLM07",
        "title": "Insecure Plugin and Tool Design",
        "source": "OWASP LLM Top 10 - LLM07:2025",
        "description": "Overprivileged LLM plugins enable data exfiltration, remote code execution or lateral movement.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["agentic_ai", "tool_access", "external_plugins"],
        "mitigations": [
            "Apply least-privilege to all plugin and tool permissions",
            "Validate all plugin inputs and outputs",
            "Require explicit user confirmation for high-impact actions",
        ],
    },
    {
        "threat_id": "OWASP-LLM08",
        "title": "Excessive Agency",
        "source": "OWASP LLM Top 10 - LLM08:2025",
        "description": "LLM granted excessive autonomy enables unintended harmful real-world actions.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["agentic_ai", "autonomous_operation", "automated_decision_making"],
        "mitigations": [
            "Define strict boundaries for autonomous action scope",
            "Require human-in-the-loop for all high-impact decisions",
            "Implement reversibility mechanisms for autonomous actions",
            "Log and audit all autonomous actions taken",
        ],
    },
    {
        "threat_id": "OWASP-LLM09",
        "title": "Overreliance and Misinformation",
        "source": "OWASP LLM Top 10 - LLM09:2025",
        "description": "Users or downstream systems over-rely on LLM outputs that may be hallucinated or incorrect.",
        "severity": "medium", "likelihood": "high",
        "trigger_flags": ["diagnostic_assistance", "legal_decision_making", "financial", "healthcare"],
        "mitigations": [
            "Add uncertainty quantification to all outputs",
            "Require expert human review for high-stakes decisions",
            "Implement RAG for factual grounding",
            "Display confidence levels and source citations to users",
        ],
    },
    {
        "threat_id": "OWASP-LLM10",
        "title": "Model Theft and Extraction",
        "source": "OWASP LLM Top 10 - LLM10:2025",
        "description": "Adversaries replicate proprietary model behaviour through systematic API querying.",
        "severity": "medium", "likelihood": "low",
        "trigger_flags": ["api_access", "public_exposure", "custom_trained_model"],
        "mitigations": [
            "Implement query rate limiting and behavioural anomaly detection",
            "Add output perturbation to resist model extraction",
            "Monitor for systematic probing patterns",
        ],
    },
    {
        "threat_id": "DOMAIN-BIAS",
        "title": "Algorithmic Bias and Discrimination",
        "source": "NIST AI RMF + EU AI Act Art. 9 + EU Equal Treatment Directives",
        "description": "Model outputs reflect or amplify historical biases causing discriminatory outcomes against protected groups.",
        "severity": "high", "likelihood": "high",
        "trigger_flags": ["employment_decision", "credit_scoring", "healthcare", "law_enforcement", "biometric"],
        "mitigations": [
            "Conduct pre-deployment bias audit across all protected characteristics",
            "Use representative and balanced training datasets",
            "Implement production fairness metrics monitoring",
            "Establish human review for all flagged decisions",
        ],
    },
    {
        "threat_id": "DOMAIN-PRIVACY",
        "title": "Privacy Violation and Unlawful Data Processing",
        "source": "GDPR 2016/679 + EU AI Act",
        "description": "System collects, processes or exposes personal data beyond stated and lawful purpose.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["processes_personal_data", "health_data", "location_tracking", "minors_involved"],
        "mitigations": [
            "Conduct DPIA under GDPR Article 35",
            "Implement data minimization and purpose limitation",
            "Establish data retention, deletion and breach response policies",
            "Encrypt all personal data at rest and in transit",
        ],
    },
    {
        "threat_id": "DOMAIN-ADVERSARIAL",
        "title": "Adversarial Attacks on Model",
        "source": "NIST AI RMF MG-2.2 + MITRE ATLAS",
        "description": "Malicious inputs crafted to cause misclassification or unexpected behaviour in safety-critical applications.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["diagnostic_assistance", "critical_infrastructure", "autonomous_operation", "law_enforcement"],
        "mitigations": [
            "Apply adversarial training and input validation",
            "Implement anomaly detection on model inputs in production",
            "Conduct regular adversarial red-team exercises",
            "Monitor for input distribution shift",
        ],
    },
    {
        "threat_id": "DOMAIN-SURVEILLANCE",
        "title": "Disproportionate Surveillance and Civil Liberty Violation",
        "source": "EU AI Act Art. 5 + ECHR Art. 8 + GDPR",
        "description": "System enables monitoring at a scale or intrusiveness that violates fundamental rights to privacy and freedom.",
        "severity": "high", "likelihood": "high",
        "trigger_flags": ["mass_surveillance", "location_tracking", "biometric", "public_authority"],
        "mitigations": [
            "Establish strict legal basis and proportionality review",
            "Implement data minimization and strict retention limits",
            "Ensure independent oversight and audit mechanisms",
            "Publish transparency reports to affected populations",
        ],
    },
    {
        "threat_id": "DOMAIN-MINORS",
        "title": "Harm to Minors",
        "source": "EU AI Act + UNCRC + GDPR Art. 8 + COPPA",
        "description": "Processing data of minors without appropriate safeguards creates elevated exploitation and privacy risks.",
        "severity": "high", "likelihood": "medium",
        "trigger_flags": ["minors_involved"],
        "mitigations": [
            "Obtain verifiable parental consent where required",
            "Apply age-appropriate design standards",
            "Minimize all data collection from minors",
            "Conduct child rights impact assessment",
        ],
    },
]

# ---------------------------------------------------------------------------
# NIST AI RMF function assignment
# ---------------------------------------------------------------------------

_NIST_RULES: list[tuple[str, list[str]]] = [
    ("automated_decision_making",   ["Govern", "Map", "Measure", "Manage"]),
    ("biometric",                   ["Govern", "Map", "Measure", "Manage"]),
    ("healthcare",                  ["Govern", "Map", "Measure", "Manage"]),
    ("law_enforcement",             ["Govern", "Map", "Measure", "Manage"]),
    ("critical_infrastructure",     ["Govern", "Map", "Measure", "Manage"]),
    ("employment_decision",         ["Govern", "Map", "Measure"]),
    ("processes_personal_data",     ["Govern", "Map"]),
    ("generative_ai",               ["Map", "Measure"]),
    ("continuous_learning",         ["Measure", "Manage"]),
    ("public_exposure",             ["Map", "Measure"]),
    ("agentic_ai",                  ["Govern", "Map", "Measure", "Manage"]),
]

_BAND_ORDER = ["minimal", "limited", "high", "unacceptable"]


def _more_severe(a: str, b: str) -> str:
    return a if _BAND_ORDER.index(a) >= _BAND_ORDER.index(b) else b


def _score_to_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 30:
        return "limited"
    return "minimal"


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def compute_risk(
    audit_request: dict[str, Any],
    normalization_flags: dict[str, Any],
    country: str = "",
) -> RiskEngineResult:
    """
    Run the full deterministic risk assessment.
    Returns a RiskEngineResult containing every decision and its source rule.
    """
    cc = country.strip().upper()
    ruleset = "EU" if cc in EU_COUNTRIES else "NIST"

    if ruleset == "EU":
        return _compute_risk_eu(audit_request, normalization_flags, country=cc)
    return _compute_risk_nist(audit_request, normalization_flags, country=cc)


def _compute_risk_eu(audit_request, normalization_flags, country="") -> RiskEngineResult:
    flags: dict[str, bool] = {k: bool(v) for k, v in normalization_flags.items()}

    # Step 1: Prohibitions
    prohibition_reasons: list[str] = []
    for rule in _PROHIBITIONS:
        if all(flags.get(f, False) for f in rule["required_flags"]):
            prohibition_reasons.append(
                f"{rule['rule_id']}: {rule['rule_name']} ({rule['source']})"
            )
            logger.warning("PROHIBITED triggered: %s", rule["rule_id"])

    if prohibition_reasons:
        return RiskEngineResult(
            score=100,
            risk_band="unacceptable",
            prohibited=True,
            prohibition_reasons=prohibition_reasons,
            score_breakdown=[{
                "rule_id": "PROHIBITED",
                "points": 100,
                "label": "; ".join(prohibition_reasons)
            }],
            minimum_band_applied=None,
            threats=_collect_threats(flags),
            compliance_requirements=[
                "CANNOT be deployed in the EU under current design (EU AI Act Art. 5)",
                "Fundamental redesign required to remove prohibited features",
                "Legal counsel review required before any deployment",
                "Notify national supervisory authority if already deployed",
            ],
            nist_functions=["Govern"],
            override_reason="Hard prohibition - EU AI Act Article 5",
            ruleset="EU",
        )

    # Step 2: High-risk rule scoring
    total = 0
    breakdown: list[dict[str, Any]] = []
    current_min_band = "minimal"
    compliance_set: set[str] = set()
    nist_set: set[str] = set()

    for rule in _HIGH_RISK_RULES:
        req = rule["trigger_flags"]
        if all(flags.get(f, False) for f in req):
            pts = rule["points"]
            total += pts
            current_min_band = _more_severe(current_min_band, rule.get("min_band", "minimal"))
            breakdown.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["rule_name"],
                "source": rule["source"],
                "points": pts,
            })
            for c in rule.get("compliance", []):
                compliance_set.add(c)
            for fn in rule.get("nist_functions", []):
                nist_set.add(fn)

    # Step 3: Additional scoring
    for rule in _SCORING_RULES:
        if flags.get(rule["flag"], False):
            pts = rule["points"]
            total += pts
            breakdown.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["label"],
                "source": "Scoring matrix",
                "points": pts,
            })

    # Step 4: NIST functions
    for flag_key, functions in _NIST_RULES:
        if flags.get(flag_key, False):
            for fn in functions:
                nist_set.add(fn)

    # Step 5: Cap and derive band
    total = min(total, 100)
    score_band = _score_to_band(total)
    final_band = _more_severe(current_min_band, score_band)

    # Step 6: Base compliance by band
    if final_band == "high":
        compliance_set.update([
            "Technical documentation required (EU AI Act Art. 11)",
            "Conformity assessment required (EU AI Act Art. 43)",
            "Register in EU AI systems database (EU AI Act Art. 49)",
            "Human oversight mechanisms required (EU AI Act Art. 14)",
            "Logging and audit trail required (EU AI Act Art. 12)",
            "Accuracy, robustness and cybersecurity required (EU AI Act Art. 15)",
            "Post-market monitoring plan required (EU AI Act Art. 72)",
            "Quality management system required (EU AI Act Art. 17)",
        ])
    elif final_band == "limited":
        compliance_set.update([
            "Transparency: users must know they interact with AI (EU AI Act Art. 50)",
            "Clear AI disclosure in all user-facing outputs",
            "Deepfake disclosure required if applicable (EU AI Act Art. 50(4))",
        ])
    else:
        compliance_set.update([
            "Voluntary codes of conduct recommended (EU AI Act Art. 95)",
            "Basic AI governance documentation recommended",
        ])

    # GDPR compliance
    if flags.get("processes_personal_data") or flags.get("sensitive_data") or flags.get("health_data"):
        compliance_set.update([
            "GDPR lawful basis for processing required (Art. 6)",
            "Data Protection Impact Assessment (DPIA) required (GDPR Art. 35)",
            "Data subject rights mechanism required (GDPR Art. 15-22)",
            "Data Processing Agreement with processors required (GDPR Art. 28)",
            "Data Protection Officer (DPO) appointment may be required (GDPR Art. 37)",
        ])

    nist_ordered = [fn for fn in ["Govern", "Map", "Measure", "Manage"] if fn in nist_set]

    return RiskEngineResult(
        score=total,
        risk_band=final_band,
        prohibited=False,
        prohibition_reasons=[],
        score_breakdown=breakdown,
        minimum_band_applied=current_min_band if current_min_band != "minimal" else None,
        threats=_collect_threats(flags),
        compliance_requirements=sorted(compliance_set),
        nist_functions=nist_ordered,
        override_reason="Deterministic rule engine (EU)",
        ruleset="EU",
    )


def _compute_risk_nist(audit_request, normalization_flags, country="") -> RiskEngineResult:
    """
    Non-EU mode: NIST-first deterministic scoring.
    No EU Art.5 prohibitions and no Annex III minimum-band forcing.
    """
    flags: dict[str, bool] = {k: bool(v) for k, v in normalization_flags.items()}

    total = 0
    breakdown: list[dict[str, Any]] = []
    compliance_set: set[str] = set()
    nist_set: set[str] = set()

    # Step 1: Score using the general scoring matrix
    for rule in _SCORING_RULES:
        if flags.get(rule["flag"], False):
            pts = rule["points"]
            total += pts
            breakdown.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["label"],
                "source": "NIST scoring matrix",
                "points": pts,
            })

    # Step 2: Threat surface bonus (keeps band sensitive to LLM/security risks)
    threats = _collect_threats(flags)
    triggered = [t for t in threats if t.get("id") != "GENERAL-01"]
    if triggered:
        bonus = min(20, 5 * len(triggered))
        total += bonus
        breakdown.append({
            "rule_id": "NIST-THREAT-SURFACE",
            "rule_name": "Triggered threat surface",
            "source": "OWASP LLM + domain threats",
            "points": bonus,
        })

    # Step 3: NIST function mapping
    for flag_key, functions in _NIST_RULES:
        if flags.get(flag_key, False):
            for fn in functions:
                nist_set.add(fn)

    total = min(total, 100)
    final_band = _score_to_band(total)

    # Step 4: NIST-style compliance guidance
    compliance_set.update([
        "Establish AI governance roles, policies, and accountability (NIST AI RMF: Govern)",
        "Document context, intended use, stakeholders, and impacts (NIST AI RMF: Map)",
        "Define evaluation metrics and test for bias, robustness, and security (NIST AI RMF: Measure)",
        "Implement monitoring, incident response, and continuous risk treatment (NIST AI RMF: Manage)",
    ])

    if final_band == "high":
        compliance_set.update([
            "Require human review for high-impact decisions where feasible",
            "Perform red-team testing and adversarial evaluations",
            "Implement strong access control, audit logging, and change management",
        ])
    elif final_band == "limited":
        compliance_set.update([
            "Provide user-facing transparency and limitations",
            "Monitor drift and performance in production",
        ])
    else:
        compliance_set.update([
            "Maintain basic documentation and monitor for unexpected behavior",
        ])

    nist_ordered = [fn for fn in ["Govern", "Map", "Measure", "Manage"] if fn in nist_set]
    if not nist_ordered:
        nist_ordered = ["Govern", "Map", "Measure", "Manage"] if total >= 30 else ["Govern", "Map"]

    return RiskEngineResult(
        score=total,
        risk_band=final_band,
        prohibited=False,
        prohibition_reasons=[],
        score_breakdown=breakdown,
        minimum_band_applied=None,
        threats=threats,
        compliance_requirements=sorted(compliance_set),
        nist_functions=nist_ordered,
        override_reason=f"Deterministic rule engine (NIST), country={country or 'unknown'}",
        ruleset="NIST",
    )


def _collect_threats(flags: dict[str, bool]) -> list[dict[str, Any]]:
    """Return all threats whose trigger flags are satisfied."""
    out: list[dict[str, Any]] = []
    for t in _THREATS:
        if any(flags.get(f, False) for f in t["trigger_flags"]):
            out.append({
                "id": t["threat_id"],
                "title": t["title"],
                "description": t["description"],
                "severity": t["severity"],
                "likelihood": t["likelihood"],
                "mitigations": t["mitigations"],
                "source": t["source"],
            })
    if not out:
        out.append({
            "id": "GENERAL-01",
            "title": "General AI System Risk",
            "description": "All AI systems carry inherent risks of error, bias and unexpected behaviour.",
            "severity": "low",
            "likelihood": "low",
            "mitigations": [
                "Document system limitations clearly",
                "Monitor performance in production",
                "Establish incident response process",
            ],
            "source": "NIST AI RMF",
        })
    return out


def apply_hybrid_override(
    llm_band: str,
    engine_result: RiskEngineResult,
) -> tuple[str, str]:
    """
    The engine always wins on classification.
    The LLM result is only elevated, never used to reduce the engine's decision.
    """
    if engine_result.prohibited:
        return "unacceptable", f"PROHIBITED - {'; '.join(engine_result.prohibition_reasons)}"

    final = _more_severe(llm_band, engine_result.risk_band)

    if final != engine_result.risk_band:
        return final, f"LLM elevated band from engine '{engine_result.risk_band}' to '{llm_band}'"
    if final != llm_band:
        return final, f"Engine override: score {engine_result.score}/100 enforces '{engine_result.risk_band}' over LLM '{llm_band}'"
    return final, "LLM and engine agree"