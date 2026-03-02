'use client';

import Link from 'next/link';

export default function Header() {
  return (
    <header className="site-header">
      <div className="site-header__left">
        <Link href="/" className="site-header__logo">
          <span className="site-header__icon">◯</span>
          Strazh AI
        </Link>
      </div>
      <nav className="site-header__nav">
        <Link href="/eu-ai-act" className="site-header__link">Use cases</Link>
        <Link href="/security-controls" className="site-header__link">Features</Link>
      </nav>
      <div className="site-header__right">
        <Link href="#" className="site-header__link">Sign in</Link>
        <Link href="/input-form" className="site-header__cta">Start free audit</Link>
      </div>
    </header>
  );
}
