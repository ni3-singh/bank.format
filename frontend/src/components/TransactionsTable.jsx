import { useState, useMemo } from 'react';
import { formatIndianCurrency, downloadCSV, downloadExcel } from '../utils';

export default function TransactionsTable({ transactions }) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [sortCol, setSortCol] = useState(null);
  const [sortDir, setSortDir] = useState('asc');
  const perPage = 25;

  const filtered = useMemo(() => {
    if (!transactions) return [];
    const term = search.toLowerCase().trim();
    if (!term) return transactions;
    return transactions.filter(t =>
      (t.name && t.name.toLowerCase().includes(term)) ||
      (t.remark && t.remark.toLowerCase().includes(term)) ||
      (t.date && t.date.toLowerCase().includes(term))
    );
  }, [transactions, search]);

  const sorted = useMemo(() => {
    if (!sortCol) return filtered;
    return [...filtered].sort((a, b) => {
      let aVal = a[sortCol];
      let bVal = b[sortCol];
      if (sortCol === 'dr' || sortCol === 'cr') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      } else {
        aVal = String(aVal || '').toLowerCase();
        bVal = String(bVal || '').toLowerCase();
      }
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }, [filtered, sortCol, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const paginated = sorted.slice((currentPage - 1) * perPage, currentPage * perPage);

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortCol(col);
      setSortDir('asc');
    }
    setPage(1);
  };

  const SortIcon = ({ col }) => {
    if (sortCol !== col) return <span className="text-slate-600 ml-1">↕</span>;
    return <span className="text-[#0d9488] ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const handleDownloadCSV = () => {
    const data = filtered.map(t => ({
      Date: t.date,
      Name: t.name,
      'Debit (₹)': t.dr || 0,
      'Credit (₹)': t.cr || 0,
      Remark: t.remark || '',
    }));
    downloadCSV(data, 'banklens_transactions.csv');
  };

  const handleDownloadExcel = () => {
    const data = filtered.map(t => ({
      Date: t.date,
      Name: t.name,
      'Debit (₹)': t.dr || 0,
      'Credit (₹)': t.cr || 0,
      Remark: t.remark || '',
    }));
    downloadExcel(data, 'banklens_transactions.xlsx');
  };

  if (!transactions || transactions.length === 0) return null;

  return (
    <section className="max-w-6xl mx-auto px-4 pb-10 animate-slide-up">
      <div className="bg-[#1e293b]/60 border border-[#334155] rounded-2xl overflow-hidden">
        {/* Header */}
        <div className="p-5 border-b border-[#334155]">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                📋 Transactions
                <span className="text-sm font-normal text-slate-400">
                  ({filtered.length} of {transactions.length})
                </span>
              </h2>
            </div>
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
              {/* Search */}
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
                <input
                  type="text"
                  placeholder="Search by name, date, remark…"
                  value={search}
                  onChange={e => { setSearch(e.target.value); setPage(1); }}
                  className="w-full sm:w-64 pl-9 pr-3 py-2 rounded-lg bg-[#0f172a] border border-[#334155] text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#0d9488] transition-colors"
                />
              </div>
              {/* Download buttons */}
              <div className="flex gap-2">
                <button
                  onClick={handleDownloadCSV}
                  className="px-3 py-2 rounded-lg bg-[#0f172a] border border-[#334155] text-sm text-slate-300 hover:border-[#0d9488] hover:text-white transition-colors flex items-center gap-1.5"
                >
                  📥 CSV
                </button>
                <button
                  onClick={handleDownloadExcel}
                  className="px-3 py-2 rounded-lg bg-[#0f172a] border border-[#334155] text-sm text-slate-300 hover:border-emerald-500 hover:text-white transition-colors flex items-center gap-1.5"
                >
                  📥 Excel
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#334155] text-slate-400">
                <th
                  onClick={() => handleSort('date')}
                  className="text-left px-5 py-3 font-medium cursor-pointer hover:text-white transition-colors select-none"
                >
                  Date <SortIcon col="date" />
                </th>
                <th
                  onClick={() => handleSort('name')}
                  className="text-left px-5 py-3 font-medium cursor-pointer hover:text-white transition-colors select-none"
                >
                  Name <SortIcon col="name" />
                </th>
                <th
                  onClick={() => handleSort('dr')}
                  className="text-right px-5 py-3 font-medium cursor-pointer hover:text-white transition-colors select-none"
                >
                  Debit (₹) <SortIcon col="dr" />
                </th>
                <th
                  onClick={() => handleSort('cr')}
                  className="text-right px-5 py-3 font-medium cursor-pointer hover:text-white transition-colors select-none"
                >
                  Credit (₹) <SortIcon col="cr" />
                </th>
                <th className="text-left px-5 py-3 font-medium">Remark</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map((t, i) => (
                <tr
                  key={i}
                  className={`border-b border-[#334155]/50 transition-colors hover:bg-[#334155]/30 ${
                    i % 2 === 0 ? 'bg-transparent' : 'bg-[#0f172a]/30'
                  }`}
                >
                  <td className="px-5 py-3 text-slate-300 whitespace-nowrap">{t.date}</td>
                  <td className="px-5 py-3 text-white font-medium max-w-[200px] truncate" title={t.name}>{t.name}</td>
                  <td className="px-5 py-3 text-right whitespace-nowrap">
                    {t.dr ? (
                      <span className="text-rose-400 font-medium">{formatIndianCurrency(t.dr)}</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-right whitespace-nowrap">
                    {t.cr ? (
                      <span className="text-emerald-400 font-medium">{formatIndianCurrency(t.cr)}</span>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>
                  <td className="px-5 py-3 text-slate-400 max-w-[250px] truncate" title={t.remark}>{t.remark || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-4 border-t border-[#334155]">
            <p className="text-sm text-slate-400">
              Showing {(currentPage - 1) * perPage + 1}–{Math.min(currentPage * perPage, sorted.length)} of {sorted.length}
            </p>
            <div className="flex gap-1">
              <button
                onClick={() => setPage(1)}
                disabled={currentPage === 1}
                className="px-2.5 py-1.5 rounded-md text-sm disabled:text-slate-600 text-slate-300 hover:bg-[#334155] transition-colors disabled:cursor-not-allowed"
              >
                ««
              </button>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-2.5 py-1.5 rounded-md text-sm disabled:text-slate-600 text-slate-300 hover:bg-[#334155] transition-colors disabled:cursor-not-allowed"
              >
                ‹
              </button>
              {/* Page numbers */}
              {(() => {
                const pages = [];
                let start = Math.max(1, currentPage - 2);
                let end = Math.min(totalPages, start + 4);
                start = Math.max(1, end - 4);
                for (let i = start; i <= end; i++) {
                  pages.push(
                    <button
                      key={i}
                      onClick={() => setPage(i)}
                      className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
                        i === currentPage
                          ? 'bg-[#0d9488] text-white'
                          : 'text-slate-300 hover:bg-[#334155]'
                      }`}
                    >
                      {i}
                    </button>
                  );
                }
                return pages;
              })()}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-2.5 py-1.5 rounded-md text-sm disabled:text-slate-600 text-slate-300 hover:bg-[#334155] transition-colors disabled:cursor-not-allowed"
              >
                ›
              </button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={currentPage === totalPages}
                className="px-2.5 py-1.5 rounded-md text-sm disabled:text-slate-600 text-slate-300 hover:bg-[#334155] transition-colors disabled:cursor-not-allowed"
              >
                »»
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
