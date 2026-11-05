import { useState, useMemo } from 'react';
import { downloadCSV, downloadExcel } from '../utils';

export default function ExcelCsvView({ data, onDownloadExcelBackend, onDownloadCsvBackend }) {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const perPage = 50;

  const {
    filename = 'statement',
    total_pages = 1,
    total_rows = 0,
    total_cols = 0,
    headers = [],
    rows = [],
  } = data || {};

  // Search filter across all row cells
  const filteredRows = useMemo(() => {
    if (!rows || rows.length === 0) return [];
    const term = search.toLowerCase().trim();
    if (!term) return rows;
    return rows.filter(row =>
      row.some(cell => String(cell || '').toLowerCase().includes(term))
    );
  }, [rows, search]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / perPage));
  const currentPage = Math.min(page, totalPages);
  const paginatedRows = filteredRows.slice((currentPage - 1) * perPage, currentPage * perPage);

  const baseFilename = filename ? filename.replace(/\.[^/.]+$/, '') : 'bank_statement';

  // Client-side quick download (instant, 0 latency)
  const handleClientDownloadExcel = () => {
    if (onDownloadExcelBackend) {
      onDownloadExcelBackend();
      return;
    }
    const sheetData = rows.map((r) => {
      const obj = {};
      r.forEach((cell, idx) => {
        const colLetter = headers[idx] || `Col_${idx + 1}`;
        obj[colLetter] = cell;
      });
      return obj;
    });
    downloadExcel(sheetData, `${baseFilename}.xlsx`);
  };

  const handleClientDownloadCSV = () => {
    if (onDownloadCsvBackend) {
      onDownloadCsvBackend();
      return;
    }
    const sheetData = rows.map((r) => {
      const obj = {};
      r.forEach((cell, idx) => {
        const colLetter = headers[idx] || `Col_${idx + 1}`;
        obj[colLetter] = cell;
      });
      return obj;
    });
    downloadCSV(sheetData, `${baseFilename}.csv`);
  };

  if (!rows || rows.length === 0) return null;

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Download Action Banner */}
      <div className="bg-gradient-to-r from-emerald-500/15 via-[#1e293b] to-teal-500/15 border border-emerald-500/30 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-2xl">✅</span>
              <h3 className="text-xl font-bold text-white">PDF Converted Successfully!</h3>
            </div>
            <p className="text-sm text-slate-300">
              Extracted <strong className="text-emerald-400 font-semibold">{total_rows.toLocaleString()} rows</strong> across <strong className="text-teal-300 font-semibold">{total_cols} columns</strong> ({total_pages} {total_pages === 1 ? 'page' : 'pages'}).
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <button
              onClick={handleClientDownloadExcel}
              className="flex-1 md:flex-initial px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white font-semibold shadow-lg shadow-emerald-500/25 transition-all duration-200 flex items-center justify-center gap-2 transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="text-lg">📥</span>
              <span>Download Excel (.xlsx)</span>
            </button>
            <button
              onClick={handleClientDownloadCSV}
              className="flex-1 md:flex-initial px-6 py-3 rounded-xl bg-[#1e293b] hover:bg-[#334155] border border-teal-500/40 text-teal-300 hover:text-white font-semibold transition-all duration-200 flex items-center justify-center gap-2 transform hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="text-lg">📄</span>
              <span>Download CSV (.csv)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Spreadsheet Preview Box */}
      <div className="bg-[#1e293b]/70 border border-[#334155] rounded-2xl overflow-hidden shadow-xl">
        {/* Header / Search Controls */}
        <div className="p-4 border-b border-[#334155] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-[#0f172a]/50">
          <div className="flex items-center gap-2">
            <span className="text-lg">📑</span>
            <span className="font-semibold text-white">Spreadsheet Preview</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-300">
              Showing {filteredRows.length} of {total_rows} rows
            </span>
          </div>

          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">🔍</span>
            <input
              type="text"
              placeholder="Search in table..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full sm:w-64 pl-9 pr-3 py-1.5 rounded-lg bg-[#0f172a] border border-[#334155] text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-[#0d9488] transition-colors"
            />
          </div>
        </div>

        {/* Scrollable Table View with Excel Column Letters (A, B, C...) */}
        <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
          <table className="w-full text-xs sm:text-sm border-collapse font-mono">
            <thead className="sticky top-0 bg-[#0f172a] border-b border-[#334155] z-10">
              <tr>
                <th className="px-3 py-2 text-center text-slate-500 bg-[#0b1120] border-r border-[#334155] font-semibold w-12 select-none">
                  #
                </th>
                {headers.map((h, idx) => (
                  <th
                    key={idx}
                    className="px-4 py-2 text-left font-bold text-slate-300 border-r border-[#334155] select-none"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[#0d9488]">{h}</span>
                      <span className="text-[10px] text-slate-600 font-normal">Col {idx + 1}</span>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedRows.map((row, rowIdx) => {
                const globalRowNumber = (currentPage - 1) * perPage + rowIdx + 1;
                return (
                  <tr
                    key={rowIdx}
                    className={`border-b border-[#334155]/40 hover:bg-[#334155]/30 transition-colors ${
                      rowIdx % 2 === 0 ? 'bg-transparent' : 'bg-[#0f172a]/30'
                    }`}
                  >
                    <td className="px-3 py-2 text-center text-slate-500 bg-[#0b1120]/40 border-r border-[#334155] font-mono text-xs select-none">
                      {globalRowNumber}
                    </td>
                    {row.map((cell, colIdx) => (
                      <td
                        key={colIdx}
                        className="px-4 py-2 text-slate-200 border-r border-[#334155]/30 whitespace-nowrap max-w-xs truncate"
                        title={String(cell || '')}
                      >
                        {String(cell || '') || <span className="text-slate-600">—</span>}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-[#334155] flex items-center justify-between bg-[#0f172a]/50 text-xs sm:text-sm">
            <span className="text-slate-400">
              Page <strong className="text-white">{currentPage}</strong> of <strong className="text-white">{totalPages}</strong>
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 rounded bg-[#1e293b] border border-[#334155] text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 rounded bg-[#1e293b] border border-[#334155] text-slate-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
