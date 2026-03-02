const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface AuditRequest {
    name: string;
    domain: string;
    description: string;
    intended_users: string;
    outputs: string;
    deployment: string;
    data_types: string;
    country?: string;
}

export interface Threat {
    name: string;
    severity: string;
    description: string;
}

export interface AuditReport {
    system_name: string;
    compliance_score: number;
    risk_band: string;
    confidence_score: number;
    threats: Threat[];
    compliance_checklist: string[];
    reasoning_summary: string;
    warnings: string[];
    prohibited_flags: string[];
    retrieval_sources: string[];
}

export async function runAudit(request: AuditRequest): Promise<AuditReport> {
    const response = await fetch(`${API_BASE_URL}/audit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
    });

    if (!response.ok) {
        throw new Error(`Audit request failed: ${response.statusText}`);
    }

    return response.json();
}
