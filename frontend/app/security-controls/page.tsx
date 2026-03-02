import Link from "next/link";

const threats = [
    {
        threat: "Prompt Injection",
        description:
            "Attackers manipulate AI inputs to extract data or alter behavior. Strazh AI detects and mitigates this threat.",
        framework: "OWASP AI Top 10",
    },
    {
        threat: "Data Poisoning",
        description:
            "Training data is corrupted to degrade model performance. Strazh AI identifies vulnerabilities.",
        framework: "NIST AI RMF",
    },
    {
        threat: "Model Inversion",
        description:
            "Attackers reverse-engineer model outputs to reconstruct private training data. Strazh AI monitors exposure risks.",
        framework: "MITRE ATLAS",
    },
    {
        threat: "Supply Chain Compromise",
        description:
            "Third-party components or pre-trained models introduce hidden vulnerabilities. Strazh AI audits dependencies.",
        framework: "OWASP AI Top 10",
    },
    {
        threat: "Insecure Output Handling",
        description:
            "AI outputs are used without validation, enabling downstream injection attacks. Strazh AI recommends output sanitisation.",
        framework: "OWASP AI Top 10",
    },
];

export default function SecurityControlsPage() {
    return (
        <div className="min-h-screen w-full flex items-start justify-center pt-24">
            <div className="page-container">
            <Link href="/" className="back-link">
                ← Back to Home
            </Link>

            <div className="section-header">
                <h1>Strazh AI: Security Controls Library</h1>
                <p>
                    Strazh AI traces security and governance requirements across your AI
                    estate.
                </p>
            </div>

            <table className="data-table">
                <thead>
                    <tr>
                        <th>Threat</th>
                        <th>Description</th>
                        <th>Framework</th>
                    </tr>
                </thead>
                <tbody>
                    {threats.map((t) => (
                        <tr key={t.threat}>
                            <td style={{ fontWeight: 700 }}>{t.threat}</td>
                            <td>{t.description}</td>
                            <td>
                                <span className="data-table__framework">{t.framework}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            </div>
        </div>
    );
}
