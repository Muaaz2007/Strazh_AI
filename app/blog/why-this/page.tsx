import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export default function WhyThisPage() {
  return (
    <div className="min-h-screen w-full py-12 flex items-start justify-center pt-24">
      <div className="w-full max-w-2xl mx-auto px-6">
        {/* Back Link */}
        <Link href="/">
          <div className="back-link">
            <ChevronLeft size={18} />
            Back to home
          </div>
        </Link>

        {/* Blog Post */}
        <article className="w-full">
          <header className="mb-12">
            <h1 className="mb-4">Why AI Governance Matters</h1>
            <p className="text-lg text-gray-600">
              Understanding the 3 core principles of responsible AI development and deployment
            </p>
          </header>

          <div className="prose prose-lg max-w-none space-y-8">
            {/* Introduction */}
            <section>
              <p className="text-gray-700 leading-relaxed">
                As artificial intelligence becomes increasingly integrated into critical business and societal functions,
                the need for strong governance frameworks has never been more important. This guide explains the three
                foundational principles that should guide all AI development and deployment decisions.
              </p>
            </section>

            {/* Principle 1 */}
            <section>
              <h2 className="text-2xl font-bold mb-4">1. Transparency & Accountability</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                The first principle is ensuring that AI systems are transparent and their decisions can be understood and
                explained. This means:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700 ml-4">
                <li><strong>Clear documentation:</strong> Systems should have clear documentation of what they do and how they work</li>
                <li><strong>Explainability:</strong> Users should understand why an AI system made a particular decision</li>
                <li><strong>Accountability:</strong> Organizations must be responsible for their AI systems' outcomes and impacts</li>
                <li><strong>Audit trails:</strong> Systems should maintain logs and records for review and compliance</li>
              </ul>
              <p className="text-gray-700 leading-relaxed mt-4">
                Without transparency, it's impossible to identify when AI systems are making mistakes or causing harm.
                Accountability ensures that organizations take responsibility for their AI decisions.
              </p>
            </section>

            {/* Principle 2 */}
            <section>
              <h2 className="text-2xl font-bold mb-4">2. Fairness & Non-Discrimination</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                The second principle ensures that AI systems treat all users and stakeholders fairly and don't perpetuate
                discrimination or bias. This involves:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700 ml-4">
                <li><strong>Bias detection:</strong> Actively identifying and measuring bias in training data and model outputs</li>
                <li><strong>Fair representation:</strong> Ensuring diverse perspectives in development teams and training data</li>
                <li><strong>Impact assessment:</strong> Understanding how AI decisions affect different groups in society</li>
                <li><strong>Regular audits:</strong> Continuously testing systems for discriminatory outcomes</li>
              </ul>
              <p className="text-gray-700 leading-relaxed mt-4">
                AI systems inherit and amplify biases from their training data and design choices. Fairness ensures that
                AI benefits everyone equally and doesn't marginalize or discriminate against protected groups.
              </p>
            </section>

            {/* Principle 3 */}
            <section>
              <h2 className="text-2xl font-bold mb-4">3. Security & Data Protection</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                The third principle focuses on protecting AI systems and the data they process from threats and misuse:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700 ml-4">
                <li><strong>Data privacy:</strong> Personal and sensitive data must be protected and handled responsibly</li>
                <li><strong>System security:</strong> AI systems should be protected from attacks, manipulation, and unauthorized access</li>
                <li><strong>Robustness:</strong> Systems should continue to work reliably even under unexpected conditions</li>
                <li><strong>Compliance:</strong> Meeting regulations like GDPR, HIPAA, and emerging AI-specific requirements</li>
              </ul>
              <p className="text-gray-700 leading-relaxed mt-4">
                Security breaches in AI systems can expose sensitive data or enable attacks that cause real harm. Robust
                data protection ensures that AI systems are trustworthy and resilient.
              </p>
            </section>

            {/* Conclusion */}
            <section className="bg-blue-50 p-6 rounded-lg border border-blue-200">
              <h2 className="text-2xl font-bold mb-4">Why This Matters for Your Organization</h2>
              <p className="text-gray-700 leading-relaxed mb-4">
                These three principles work together to ensure that AI systems are developed responsibly, deployed ethically,
                and managed with proper oversight. Organizations that follow these principles:
              </p>
              <ul className="list-disc list-inside space-y-2 text-gray-700 ml-4">
                <li>Reduce legal and regulatory risks</li>
                <li>Build trust with stakeholders and users</li>
                <li>Prevent costly failures and security breaches</li>
                <li>Ensure their AI systems deliver fair and reliable results</li>
                <li>Stay ahead of evolving compliance requirements</li>
              </ul>
              <p className="text-gray-700 leading-relaxed mt-4">
                Strazh helps you implement these principles across your AI systems with comprehensive risk assessment,
                security controls, and compliance documentation.
              </p>
            </section>

            {/* CTA */}
            <section className="flex justify-center py-8">
              <Link href="/input-form">
                <button className="hero__btn-primary" style={{ width: "auto", justifyContent: "center" }}>
                  Start Your AI Audit
                </button>
              </Link>
            </section>
          </div>
        </article>
      </div>
    </div>
  );
}
