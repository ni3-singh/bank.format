import { useState, useMemo } from 'react';
import { formatIndianCurrency, downloadCSV } from '../utils';

export default function AnalyticsTable({ nameFrequency }) {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    if (!nameFrequency) return [];
    const term = search.toLowerCase().trim();
    if (!term) return nameFrequency;
    return nameFrequency.filter(n =>
      n.name && n.name.toLowerCase().includes(term)
    );
  }, [nameFrequency, search]);

  // Already sorted by frequency from API, but let's make sure
  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => (b.frequency || 0) - (a.frequency || 0));
  }, [filtered]);

  const handleDownloadCSV = () => {
    const data = sorted.map(n => ({
      Name: n.name,
      Frequency: n.frequency,
      'Total Debit (₹)': n.total_dr || 0,
      'Total Credit (₹)': n.total_cr || 0,
    }));
    downloadCSV(data, 'banklens_analytics.csv');
  };

  if (!nameFrequency || nameFrequency.length === 0) return null;

  return (
    <section className="max-w-6xl mx-auto px-4 pb-10 animate-slide-up">
      <div className="bg-[#1e293b]/60 border border-[#334155] rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-[#334155]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              📊 Name-wise Summary
              <span className="text-sm font-normal text-slate-400">
                ({sorted.length} unique names)
              </span>
            </h2>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              {/* Search */}
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
                <input
                  type="text"
                  placeholder="Search by name…"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  className="w-full sm:w-56 pl-9 pr-3 py-2 rounded-lg bg-[#0f172a] border border-[#334155] text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#0d9488] transition-colors"
                />
              </div>
              <button
                onClick={handleDownloadCSV}
                className="px-3 py-2 rounded-lg bg-[#0f172a] border border-[#334155] text-sm text-slate-300 hover:border-[#0d9488] hover:text-white transition-colors flex items-center gap-1.5"
              >
                📥 CSV
              </button>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#334155] text-slate-400">
                <th className="text-left px-5 py-3 font-medium">#</th>
                <th className="text-left px-5 py-3 font-medium">Name</th>
                <th className="text-center px-5 py-3 font-medium">Frequency</th>
                <th className="text-right px-5 py-3 font-medium">Total Debit (₹)</th>
                <th className="text-right px-5 py-3 font-medium">Total Credit (₹)</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((n, i) => (
                <tr
                  key={i}
                  className={`border-b border-[#334155]/50 transition-colors hover:bg-[#334155]/30 ${
                    i % 2 === 0 ? 'bg-transparent' : 'bg-[#0f172a]/30'
                  }`}
                >
                  <td className="px-5 py-3 text-slate-500 text-xs">{i + 1}</td>
                  <td className="px-5 py-3 text-white font-medium">{n.name}</td>
                  <td className="px-5 py-3 text-center">
                    <span className="inline-flex items-center justify-center min-w-[28px] px-2 py-0.5 rounded-full bg-[#0d9488]/20 text-[#0d9488] text-xs font-bold">
                      {n.frequency}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right whitespace-nowrap">
                    {n.total_dr ? (
                      <span className="text-rose-400 font-medium">{formatIndianCurrency(n.total_dr)}</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-right whitespace-nowrap">
                    {n.total_cr ? (
                      <span className="text-emerald-400 font-medium">{formatIndianCurrency(n.total_cr)}</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
