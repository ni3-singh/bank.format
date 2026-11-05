import { useState, useCallback } from 'react';
import axios from 'axios';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import SummaryCards from './components/SummaryCards';
import BankBadge from './components/BankBadge';
import TransactionsTable from './components/TransactionsTable';
import AnalyticsTable from './components/AnalyticsTable';
import Footer from './components/Footer';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [parsedData, setParsedData] = useState(null);

  const handleFileSelect = useCallback((selectedFile, validationError) => {
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }
    setFile(selectedFile);
    setError(null);
    // Clear previous results when a new file is selected
    setParsedData(null);
  }, []);

  const handleAnalyze = useCallback(async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setParsedData(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await axios.post(`${API_URL}/api/parse`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minute timeout for large files
      });

      setParsedData(response.data);
    } catch (err) {
      let message = 'Something went wrong while analyzing your statement. Please try again.';

      if (err.response) {
        // Server responded with an error
        const status = err.response.status;
        const serverMsg = err.response.data?.detail || err.response.data?.message;

        if (status === 400) {
          message = serverMsg || 'Invalid file. Please upload a valid bank statement PDF.';
        } else if (status === 413) {
          message = 'File is too large. Please upload a smaller PDF.';
        } else if (status === 422) {
          message = serverMsg || 'Could not parse this bank statement. The format may not be supported yet.';
        } else if (status >= 500) {
          message = 'Server error. Please try again later.';
        } else if (serverMsg) {
          message = serverMsg;
        }
      } else if (err.code === 'ECONNABORTED') {
        message = 'Request timed out. The file may be too large or the server is busy.';
      } else if (err.request) {
        message = 'Cannot reach the server. Please check your connection and try again.';
      }

      setError(message);
    } finally {
      setLoading(false);
    }
  }, [file]);

  const summary = parsedData?.analytics?.summary || null;
  const nameFrequency = parsedData?.analytics?.name_frequency || null;
  const transactions = parsedData?.transactions || null;
  const bankDetected = parsedData?.bank_detected || null;

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1">
        <FileUpload
          onFileSelect={handleFileSelect}
          onAnalyze={handleAnalyze}
          file={file}
          loading={loading}
          error={error}
        />

        {parsedData && (
          <div className="animate-fade-in">
            <SummaryCards summary={summary} />
            <BankBadge bank={bankDetected} />
            <TransactionsTable transactions={transactions} />
            <AnalyticsTable nameFrequency={nameFrequency} />
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
