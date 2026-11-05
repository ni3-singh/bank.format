import { useCallback, useState } from 'react';

export default function FileUpload({ onFileSelect, onAnalyze, file, loading, error }) {
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  }, []);

  const validateFile = useCallback((f) => {
    if (!f) return null;
    const isPdf = (f.type && f.type === 'application/pdf') || (f.name && f.name.toLowerCase().endsWith('.pdf'));
    if (!isPdf) {
      return 'Only PDF files are allowed.';
    }
    if (f.size > 30 * 1024 * 1024) {
      return 'File size must be less than 30 MB.';
    }
    return null;
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    const err = validateFile(droppedFile);
    if (err) {
      onFileSelect(null, err);
    } else {
      onFileSelect(droppedFile, null);
    }
  }, [onFileSelect, validateFile]);

  const handleFileChange = useCallback((e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    const err = validateFile(selectedFile);
    if (err) {
      onFileSelect(null, err);
    } else {
      onFileSelect(selectedFile, null);
    }
    // Reset input so same file can be re-selected
    e.target.value = '';
  }, [onFileSelect, validateFile]);

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <section className="max-w-2xl mx-auto px-4 pb-10 animate-fade-in">
      {/* Drop zone */}
      <label
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative flex flex-col items-center justify-center gap-4 p-10 rounded-2xl cursor-pointer
          border-2 border-dashed transition-all duration-300
          ${dragOver
            ? 'border-[#0d9488] bg-[#0d9488]/10 scale-[1.02]'
            : file
              ? 'border-[#0d9488]/50 bg-[#1e293b]/60'
              : 'border-[#334155] bg-[#1e293b]/40 hover:border-[#475569] hover:bg-[#1e293b]/60'
          }
        `}
      >
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={loading}
        />

        {/* Icon */}
        <div className={`text-5xl transition-transform duration-300 ${dragOver ? 'scale-110' : ''}`}>
          {file ? '📄' : '📤'}
        </div>

        {file ? (
          <div className="text-center">
            <p className="text-lg font-medium text-white">{file.name}</p>
            <p className="text-sm text-slate-400 mt-1">{formatSize(file.size)}</p>
            <p className="text-xs text-slate-500 mt-2">Click or drag to replace</p>
          </div>
        ) : (
          <div className="text-center">
            <p className="text-lg text-slate-300">
              <span className="text-[#0d9488] font-medium">Drop your PDF</span> here or click to browse
            </p>
            <p className="text-sm text-slate-500 mt-1">Bank statement PDF files · Max 30 MB</p>
          </div>
        )}
      </label>

      {/* Error message */}
      {error && (
        <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-center gap-2 animate-fade-in">
          <span>⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Convert button */}
      <button
        onClick={onAnalyze}
        disabled={!file || loading}
        className={`
          mt-6 w-full py-4 rounded-xl font-bold text-lg transition-all duration-300
          flex items-center justify-center gap-3 shadow-lg
          ${!file || loading
            ? 'bg-[#334155] text-slate-500 cursor-not-allowed'
            : 'bg-gradient-to-r from-emerald-500 via-teal-600 to-[#1e3a5f] text-white hover:shadow-emerald-500/25 hover:scale-[1.01] active:scale-[0.99]'
          }
        `}
      >
        {loading ? (
          <>
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <span>Converting PDF to Excel & CSV…</span>
          </>
        ) : (
          <>
            <span className="text-xl">⚡</span>
            <span>Convert PDF to Excel & CSV</span>
          </>
        )}
      </button>
    </section>
  );
}
