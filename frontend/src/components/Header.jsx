export default function Header() {
  return (
    <header className="relative overflow-hidden py-16 px-4 text-center">
      {/* Background gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-[#1e3a5f]/40 via-[#0f172a] to-[#0d9488]/20 pointer-events-none" />

      {/* Decorative circles */}
      <div className="absolute -top-20 -left-20 w-72 h-72 bg-[#0d9488]/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-20 -right-20 w-72 h-72 bg-[#1e3a5f]/20 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-3xl mx-auto">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="text-5xl">🏦</div>
          <h1 className="text-5xl md:text-6xl font-extrabold bg-gradient-to-r from-[#60a5fa] via-[#0d9488] to-[#34d399] bg-clip-text text-transparent">
            BankLens
          </h1>
          <div className="text-5xl">🔍</div>
        </div>

        {/* Tagline */}
        <p className="text-lg md:text-xl text-slate-300 mb-6 font-light">
          Parse any bank statement PDF → <span className="text-[#0d9488] font-medium">Instant insights</span>
        </p>

        {/* Privacy badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#1e293b]/80 border border-[#334155] text-sm text-slate-300">
          <span>🔒</span>
          <span>Zero Data Retention — Your data never leaves your browser session</span>
        </div>
      </div>
    </header>
  );
}
