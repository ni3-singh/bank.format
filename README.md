# 📄 PDF to Excel & CSV Converter (Bank Statements)

> Instantly convert any Bank Statement PDF into clean Excel (.xlsx) and CSV (.csv) files. Zero data retention.

[![Privacy](https://img.shields.io/badge/Privacy-Zero%20Data%20Retention-green)](https://github.com/ni3-singh/bank.format)
[![License](https://img.shields.io/badge/License-MIT-blue)](https://github.com/ni3-singh/bank.format)
[![Railway](https://img.shields.io/badge/Railway-Live%20Backend-0B0D0E?logo=railway)](https://backend-api-production-9746.up.railway.app)
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/ni3-singh/bank.format)

## 🌐 Live URLs

- **Backend API (Railway):** [`https://backend-api-production-9746.up.railway.app`](https://backend-api-production-9746.up.railway.app)
  - Health check: [`https://backend-api-production-9746.up.railway.app/api/health`](https://backend-api-production-9746.up.railway.app/api/health)
- **Frontend App (Netlify):** [`https://banklens-app.netlify.app`](https://banklens-app.netlify.app)
- **GitHub Repository:** [`https://github.com/ni3-singh/bank.format`](https://github.com/ni3-singh/bank.format)

---

## ⚡ What does this app do?

1. **Upload any Bank Statement PDF**
2. **Extracts all tables across all pages** using `pdfplumber` (reproducing your Google Colab workflow)
3. **Download with 1 Click**:
   - 📥 **Download Excel (`.xlsx`)**
   - 📄 **Download CSV (`.csv`)**
4. **Interactive Spreadsheet Preview**:
   - Displays all columns (A, B, C, D...) and row numbers directly in your browser.
5. **Cleaned Bank Summary & Analytics (Optional Tab)**:
   - Formats Date, Name, Debit, Credit, and Remark.
   - Calculates unique counterparty frequency and sums total Debits & Credits per name (IDBI, Kotak, SBI, HDFC).

---

## 🔒 100% Privacy & Zero Data Retention

- **No database** — Zero data storage
- **In-memory processing** — The PDF is processed in RAM and immediately released
- **No file persistence** — Your financial records never stay on our servers

---

## 🛠️ Tech Stack

- **Frontend:** React + Vite + Tailwind CSS (Hosted on Netlify)
- **Backend:** Python FastAPI + pdfplumber + pandas + openpyxl (Hosted on Railway)
- **Database:** None 🎉
