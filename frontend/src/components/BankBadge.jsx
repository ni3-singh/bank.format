export default function BankBadge({ bank }) {
  if (!bank) return null;

  const bankColors = {
    sbi: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    hdfc: 'bg-red-500/20 text-red-300 border-red-500/30',
    icici: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    axis: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    kotak: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    idbi: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    pnb: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    bob: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
    canara: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    union: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    yes: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
    indusind: 'bg-teal-500/20 text-teal-300 border-teal-500/30',
    federal: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
  };

  const colorClass = bankColors[bank.toLowerCase()] || 'bg-slate-500/20 text-slate-300 border-slate-500/30';

  return (
    <div className="max-w-6xl mx-auto px-4 pb-8 animate-fade-in">
      <div className="flex items-center justify-center gap-2">
        <span className="text-sm text-slate-400">Bank Detected:</span>
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-sm font-medium uppercase tracking-wide ${colorClass}`}>
          🏛️ {bank}
        </span>
      </div>
    </div>
  );
}
