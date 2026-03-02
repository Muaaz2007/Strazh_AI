"use client";

import Link from "next/link";
import { useState } from "react";

export default function ReportCompletePage() {
    const [rating, setRating] = useState(0);
    const [hoveredStar, setHoveredStar] = useState(0);

    return (
        <div className="min-h-screen w-full py-12 flex items-start justify-center pt-24">
            <div className="w-full max-w-2xl mx-auto px-6 flex flex-col">
                <div className="success-screen">
                    {/* Success Icon */}
                    <div className="success-icon">✓</div>

                    <h2>Your Report is Ready!</h2>
                    <p>Need help improving your compliance? Contact our team.</p>

                    <div className="success-actions">
                        <Link href="/input-form" className="btn-primary">
                            Download Another Report
                        </Link>
                        <Link href="#" className="btn-secondary">
                            Contact Us
                        </Link>
                    </div>

                    {/* Feedback Section */}
                    <div className="feedback-section">
                        <label>How was your experience?</label>
                        <div className="star-rating">
                            {[1, 2, 3, 4, 5].map((star) => (
                                <span
                                    key={star}
                                    className={`star-rating__star ${star <= (hoveredStar || rating)
                                            ? "star-rating__star--active"
                                            : ""
                                        }`}
                                    onClick={() => setRating(star)}
                                    onMouseEnter={() => setHoveredStar(star)}
                                    onMouseLeave={() => setHoveredStar(0)}
                                >
                                    ★
                                </span>
                            ))}
                        </div>

                        <label>Any suggestions?</label>
                        <textarea
                            className="feedback-textarea"
                            placeholder="Write your suggestions..."
                        />
                    </div>
                </div>
            </div>
        </div>
    );
}
