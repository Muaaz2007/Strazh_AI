import Link from "next/link";
import { AnimatedHero } from "@/components/ui/animated-hero";

export default function HomePage() {
  return (
    <div className="min-h-screen w-full flex flex-col justify-start items-center pt-24">
      <div className="w-full max-w-2xl px-6">
        <div className="flex flex-col items-center">
          <AnimatedHero />

          {/* Action Buttons */}
          <div className="flex flex-col gap-4 mt-4 w-full">
            <button className="hero__btn-secondary w-full">
              <a href="/input-form" className="w-full flex items-center justify-center">
                Start Free Audit →
              </a>
            </button>
            <a href="/blog/why-this" className="w-full">
              <button className="hero__btn-secondary w-full">
                Why This? Learn About AI Governance →
              </button>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
