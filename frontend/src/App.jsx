import { useState, useCallback } from 'react';
import axios from 'axios';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import ExcelCsvView from './components/ExcelCsvView';
import SummaryCards from './components/SummaryCards';
import BankBadge from './components/BankBadge';
import TransactionsTable from './components/TransactionsTable';
import AnalyticsTable from './components/AnalyticsTable';
import Footer from './components/Footer';

const API_URL = import.meta.env.VITE_API_URL || 'https://backend-api-production-9746.up.railway.app';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [parsedData, setParsedData] = useState(null);
  const [activeTab, setActiveTab] = useState('raw'); // 'raw' | 'summary'

  const handleFileSelect = useCallback((selectedFile, validationError) => {
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }
    setFile(selectedFile);
    setError(null);
    setParsedData(null);
  }, []);

  const handleConvert = useCallback(async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setParsedData(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_URL}/api/convert`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 180000, // 3 minute timeout
      });

      setParsedData(response.data);
      setActiveTab('raw'); // default to raw converted spreadsheet view
    } catch (err) {
      let message = 'Something went wrong while converting your PDF. Please try again.';

      if (err.response) {
        const status = err.response.status;
        const serverMsg = err.response.data?.detail || err.response.data?.message;

        if (status === 400) {
          message = serverMsg || 'Invalid file. Please upload a valid bank statement PDF.';
        } else if (status === 413) {
          message = 'File is too large. Maximum size is 30 MB.';
        } else if (status === 422) {
          message = serverMsg || 'Could not find any tables in this PDF. Please ensure it is not an image scan.';
        } else if (status >= 500) {
          message = serverMsg || 'Server error. Please try again.';
        } else if (serverMsg) {
          message = serverMsg;
        }
      } else if (err.code === 'ECONNABORTED') {
        message = 'Request timed out. The file may be large or taking longer to process.';
      } else if (err.request) {
        message = 'Cannot connect to backend server. Please verify your internet connection.';
      }

      setError(message);
    } finally {
      setLoading(false);
    }
  }, [file]);

  // Backend streaming download handlers
  const handleDownloadExcelBackend = useCallback(async () => {
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await axios.post(`${API_URL}/api/download/excel`, formData, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const baseName = file.name.replace(/\.[^/.]+$/, '');
      link.setAttribute('download', `${baseName}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      // Fallback handled inside ExcelCsvView
    }
  }, [file]);

  const handleDownloadCsvBackend = useCallback(async () => {
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await axios.post(`${API_URL}/api/download/csv`, formData, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      const baseName = file.name.replace(/\.[^/.]+$/, '');
      link.setAttribute('download', `${baseName}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      // Fallback handled inside ExcelCsvView
    }
  }, [file]);

  const hasSummary = Boolean(
    parsedData?.cleaned_summary ||
    (parsedData?.transactions && parsedData.transactions.length > 0)
  );

  const summary = parsedData?.cleaned_summary?.analytics?.summary || parsedData?.analytics?.summary || null;
  const nameFrequency = parsedData?.cleaned_summary?.analytics?.name_frequency || parsedData?.analytics?.name_frequency || null;
  const transactions = parsedData?.cleaned_summary?.transactions || parsedData?.transactions || null;
  const bankDetected = parsedData?.cleaned_summary?.bank_detected || parsedData?.bank_detected || null;

  return (
    <div className="min-h-screen flex flex-col bg-[#0f172a] text-slate-100">
      <Header />

      <main className="flex-1 max-w-6xl w-full mx-auto px-4 pb-16">
        <FileUpload
          onFileSelect={handleFileSelect}
          onAnalyze={handleConvert}
          file={file}
          loading={loading}
          error={error}
        />

        {parsedData && (
          <div className="mt-8 space-y-6 animate-fade-in">
            {/* View Switcher Tabs (when cleaned summary is also available) */}
            {hasSummary && (
              <div className="flex items-center justify-center gap-2 p-1 bg-[#1e293b] rounded-xl border border-[#334155] max-w-md mx-auto">
                <button
                  onClick={() => setActiveTab('raw')}
                  className={`flex-1 py-2 px-4 rounded-lg font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2 ${
                    activeTab === 'raw'
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <span>📑</span>
                  <span>Excel / CSV View</span>
                </button>
                <button
                  onClick={() => setActiveTab('summary')}
                  className={`flex-1 py-2 px-4 rounded-lg font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2 ${
                    activeTab === 'summary'
                      ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  <span>📊</span>
                  <span>Bank Analytics</span>
                </button>
              </div>
            )}

            {/* TAB 1: Raw Excel / CSV Conversion View */}
            {activeTab === 'raw' && (
              <ExcelCsvView
                data={parsedData}
                onDownloadExcelBackend={handleDownloadExcelBackend}
                onDownloadCsvBackend={handleDownloadCsvBackend}
              />
            )}

            {/* TAB 2: Cleaned Bank Summary & Analytics */}
            {activeTab === 'summary' && hasSummary && (
              <div className="space-y-6 animate-fade-in">
                <SummaryCards summary={summary} />
                <BankBadge bank={bankDetected} />
                <TransactionsTable transactions={transactions} />
                <AnalyticsTable nameFrequency={nameFrequency} />
              </div>
            )}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
