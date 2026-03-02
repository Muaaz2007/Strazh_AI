"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AlertTriangle, AlertCircle } from "lucide-react";

// Default mock data structure - replace with real API data
const DEFAULT_REPORT = {
    risk_band: "unacceptable",
    prohibited: true,
    prohibition_reasons: ["EU-AIA-ART5-1E: Emotion recognition in workplace (EU AI Act Article 5(1)(f))"],
    deterministic_score: 100,
    summary: "The Emotion Analyzer system is classified as an unacceptable risk under the EU AI Act due to its use of emotion recognition in the workplace, which is explicitly prohibited by Article 5(1)(f).",
    threats: [
        {
            id: "OWASP-LLM01",
            title: "Prompt Injection",
            severity: "high",
            description: "Attackers manipulate LLM inputs to override instructions, bypass safety controls, or exfiltrate data."
        },
    ],
    checklist: [
        "CANNOT be deployed in the EU under current design",
        "Fundamental redesign required",
        "Legal counsel review required",
        "Notify supervisory authority if deployed",
    ],
    jurisdiction: { country: "DE", ruleset: "EU" },
};

const getRiskBandColor = (risk_band: string) => {
    switch (risk_band) {
        case "unacceptable": return "#E35336";
        case "high": return "#F4A460";
        case "medium": return "#FFD700";
        case "low": return "#52C41A";
        default: return "#A0522D";
    }
};

const getSeverityColor = (severity: string) => {
    switch (severity) {
        case "high": return "#E35336";
        case "medium": return "#F4A460";
        case "low": return "#52C41A";
        default: return "#A0522D";
    }
};

export default function ReportPage() {
    const router = useRouter();
    const [reportData, setReportData] = useState(DEFAULT_REPORT);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // TODO: Fetch report data from your backend API
        // Example:
        // const fetchReport = async () => {
        //     try {
        //         const response = await fetch('/api/compliance-report', {
        //             method: 'GET',
        //             // or POST with payload if needed
        //         });
        //         const data = await response.json();
        //         setReportData(data);
        //     } catch (error) {
        //         console.error('Failed to fetch report:', error);
        //         // Keep using default data or show error
        //     } finally {
        //         setIsLoading(false);
        //     }
        // };

        // For now, use mock data
        setIsLoading(false);
    }, []);

    const riskColor = getRiskBandColor(reportData.risk_band);

    if (isLoading) {
        return (
            <div className="min-h-screen w-full flex items-center justify-center">
                <div className="text-center">
                    <div className="loading-spinner mb-4" />
                    <p className="text-[#8B6F5E]">Loading report...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen w-full py-12 flex items-start justify-center pt-24">
            <div className="w-full max-w-4xl mx-auto px-6 flex flex-col">
                {/* Close button */}
                <div className="flex justify-end mb-6">
                    <button
                        className="text-2xl text-[#A0522D] hover:text-[#8d4726] transition-colors"
                        onClick={() => router.push("/")}
                        aria-label="Close report"
                    >
                        ✕
                    </button>
                </div>

                {/* Header */}
                <div className="mb-12">
                    <h1 className="text-4xl font-bold text-[#3B2314] mb-2">AI Compliance Report</h1>
                    <p className="text-lg text-[#8B6F5E]">System Assessment</p>
                </div>

                {/* Risk Classification */}
                <div className="mb-12 p-8 rounded-2xl border-2" style={{ borderColor: riskColor, backgroundColor: `${riskColor}15` }}>
                    <div className="flex items-center gap-6">
                        <div className="text-4xl" style={{ color: riskColor }}>
                            <AlertTriangle size={48} />
                        </div>
                        <div>
                            <div className="text-sm font-bold uppercase tracking-wide" style={{ color: riskColor }}>
                                Risk Classification
                            </div>
                            <div className="text-3xl font-bold text-[#3B2314] mt-1 capitalize">
                                {reportData.risk_band} Risk
                            </div>
                            {reportData.prohibited && (
                                <div className="text-base font-semibold mt-2" style={{ color: riskColor }}>
                                    ⛔ Prohibited under EU AI Act
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Prohibition Reasons */}
                {reportData.prohibited && reportData.prohibition_reasons?.length > 0 && (
                    <div className="mb-12">
                        <div className="text-lg font-bold text-[#3B2314] mb-4">Prohibition Reasons</div>
                        <div className="space-y-3">
                            {reportData.prohibition_reasons.map((reason, idx) => (
                                <div key={idx} className="p-4 bg-[#FFF9F2] border-l-4 border-[#E35336] rounded">
                                    <p className="text-[#3B2314] font-semibold">{reason}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Risk Score */}
                <div className="mb-12">
                    <div className="text-lg font-bold text-[#3B2314] mb-4">Risk Score</div>
                    <div className="p-6 bg-[#FFF9F2] rounded-xl">
                        <div className="flex items-center gap-8">
                            <div className="flex-1">
                                <div className="w-full bg-[#E8D5C4] rounded-full h-4 overflow-hidden">
                                    <div
                                        className="h-full transition-all duration-500"
                                        style={{ width: `${reportData.deterministic_score}%`, backgroundColor: riskColor }}
                                    />
                                </div>
                            </div>
                            <div className="text-4xl font-bold" style={{ color: riskColor }}>
                                {reportData.deterministic_score}
                                <span className="text-lg text-[#8B6F5E]">/100</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Summary */}
                <div className="mb-12">
                    <div className="text-lg font-bold text-[#3B2314] mb-4">Summary</div>
                    <div className="p-6 bg-[#F5EDE4] rounded-xl border border-[#E8D5C4]">
                        <p className="text-[#3B2314] leading-relaxed text-base">
                            {reportData.summary}
                        </p>
                    </div>
                </div>

                {/* Threats & Vulnerabilities */}
                {reportData.threats && reportData.threats.length > 0 && (
                    <div className="mb-12">
                        <div className="text-lg font-bold text-[#3B2314] mb-4">Security Threats & Vulnerabilities</div>
                        <div className="space-y-4">
                            {reportData.threats.map((threat) => (
                                <div key={threat.id} className="p-4 border border-[#E8D5C4] rounded-xl hover:shadow-md transition-shadow">
                                    <div className="flex items-start gap-4">
                                        <div
                                            className="px-3 py-1 rounded text-sm font-bold text-white whitespace-nowrap mt-1"
                                            style={{ backgroundColor: getSeverityColor(threat.severity) }}
                                        >
                                            {threat.severity.toUpperCase()}
                                        </div>
                                        <div className="flex-1">
                                            <div className="font-bold text-[#3B2314]">{threat.title}</div>
                                            <p className="text-[#8B6F5E] mt-1">{threat.description}</p>
                                            <div className="text-xs text-[#A0522D] font-semibold mt-2">{threat.id}</div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Compliance Checklist */}
                {reportData.checklist && reportData.checklist.length > 0 && (
                    <div className="mb-12">
                        <div className="text-lg font-bold text-[#3B2314] mb-4">Action Items & Checklist</div>
                        <div className="space-y-3">
                            {reportData.checklist.map((item, idx) => (
                                <div key={idx} className="flex items-start gap-3 p-4 bg-[#FFF9F2] rounded-lg border border-[#E8D5C4]">
                                    <div className="text-[#E35336] mt-1">
                                        <AlertCircle size={20} />
                                    </div>
                                    <p className="text-[#3B2314] font-medium">{item}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Jurisdiction */}
                {reportData.jurisdiction && (
                    <div className="mb-12 p-6 bg-[#F5EDE4] rounded-xl">
                        <div className="grid grid-cols-2 gap-8">
                            <div>
                                <div className="text-sm font-bold text-[#A0522D] uppercase tracking-wide">Country</div>
                                <div className="text-2xl font-bold text-[#3B2314] mt-1">{reportData.jurisdiction.country}</div>
                            </div>
                            <div>
                                <div className="text-sm font-bold text-[#A0522D] uppercase tracking-wide">Regulatory Framework</div>
                                <div className="text-2xl font-bold text-[#3B2314] mt-1">{reportData.jurisdiction.ruleset}</div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-4 mb-8">
                    <button
                        onClick={() => window.print()}
                        className="hero__btn-primary"
                        style={{ flex: 1 }}
                    >
                        Download Report
                    </button>
                    <Link href="/report-complete" className="hero__btn-secondary" style={{ flex: 1 }}>
                        Next Steps
                    </Link>
                </div>
            </div>
        </div>
    );
}
