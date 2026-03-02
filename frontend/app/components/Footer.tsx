'use client';

import Link from 'next/link';

export default function Footer() {
    return (
        <footer className="site-footer">
            <div className="site-footer__inner">
                <div className="site-footer__links">
                    <Link href="#" className="site-footer__link">About</Link>
                    <Link href="#" className="site-footer__link">Contact</Link>
                    <Link href="#" className="site-footer__link">Blog</Link>
                </div>
                <span className="site-footer__copy">© 2026 Strazh AI</span>
            </div>
        </footer>
    );
}
