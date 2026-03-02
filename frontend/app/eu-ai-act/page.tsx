import Link from "next/link";

const riskCategories = [
    {
        title: "Unacceptable Risk",
        description:
            "Banned AI systems (e.g., social scoring, manipulative AI). Strazh AI flags these immediately.",
    },
    {
        title: "High Risk",
        description:
            "Strict requirements (e.g., healthcare, law enforcement, critical infrastructure). Strazh AI provides detailed checklists.",
    },
    {
        title: "Limited Risk",
        description:
            "Transparency rules (e.g., chatbots, deepfakes). Strazh AI ensures compliance with minimal effort.",
    },
    {
        title: "Minimal Risk",
        description:
            "No restrictions (e.g., spam filters, recommendation systems). Strazh AI confirms this status.",
    },
];

export default function EUAIActPage() {
    return (
        <div className="min-h-screen w-full flex items-start justify-center pt-24">
            <div className="page-container">
            <Link href="/" className="back-link">
                ← Back to Home
            </Link>

            <div className="section-header">
                <h1>Strazh AI: EU AI Act Risk Classes</h1>
                <p>
                    The EU AI Act classifies AI systems into four risk categories. Strazh
                    AI helps you identify and manage these risks.
                </p>
            </div>

            <hr className="divider" />

            <h2 className="section-title">Risk Categories</h2>

            <ul className="risk-list">
                {riskCategories.map((cat) => (
                    <li key={cat.title} className="risk-item">
                        <div className="risk-item__title">{cat.title}</div>
                        <div className="risk-item__desc">{cat.description}</div>
                    </li>
                ))}
            </ul>
            </div>
        </div>
    );
}
