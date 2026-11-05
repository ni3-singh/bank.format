# 🏦 BankLens — Bank Statement Analyzer

> Parse any bank statement PDF → Instant insights. Zero data retention.

![Privacy](https://img.shields.io/badge/Privacy-Zero%20Data%20Retention-green)
![License](https://img.shields.io/badge/License-MIT-blue)

## 🚀 What is BankLens?

BankLens is a web application that converts bank statement PDFs into structured, analyzable data. Upload any bank statement PDF and get:

- **Parsed Transactions** — Date, Name, Debit, Credit, Remark
- **Name-wise Analytics** — Frequency of transactions per person/entity with total debits and credits
- **Summary Dashboard** — Total debits, credits, net balance, and transaction count

## 🔒 Privacy First

- **No database** — Zero data storage
- **In-memory processing** — Your PDF is processed and immediately discarded
- **No data retention** — Nothing is saved on our servers
- Your bank statements never leave your browser session (beyond the processing request)

## 🏦 Supported Banks

BankLens intelligently detects and handles different bank statement formats:

| Bank | Description Format | Detection |
|------|-------------------|-----------|
| **IDBI Bank** | `UPI/TxnID/Name` | Auto-detected |
| **Kotak Bank** | `UPI/Name/TxnID/Remark` | Auto-detected |
| **SBI** | `UPI-Name-UPI_ID-Remark` | Auto-detected |
| **HDFC Bank** | `UPI/DR/TxnID/Name/Bank/Remark` | Auto-detected |
| **Others** | Various formats | Smart heuristic parsing |

## 🛠️ Tech Stack

- **Frontend:** React + Vite + Tailwind CSS → Hosted on Netlify
- **Backend:** Python FastAPI + pdfplumber → Hosted on Railway
- **Database:** None! 🎉

## 📦 Project Structure

```
Bank Summary V 2.0/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI application
│   │   ├── pdf_parser.py    # PDF extraction with pdfplumber
│   │   ├── bank_formats.py  # Bank format detection & description cleaning
│   │   └── analyzer.py      # Transaction analytics
│   ├── requirements.txt
│   ├── Procfile
│   └── railway.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── FileUpload.jsx
│   │   │   ├── SummaryCards.jsx
│   │   │   ├── TransactionsTable.jsx
│   │   │   ├── AnalyticsTable.jsx
│   │   │   └── Footer.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── netlify.toml
└── README.md
```

## 🚀 Getting Started

### Backend (Local Development)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend (Local Development)

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

**Frontend** (`.env`):
```
VITE_API_URL=http://localhost:8000
```

## 🌐 Deployment

- **Frontend** → Netlify (auto-deploys from `frontend/` directory)
- **Backend** → Railway (auto-deploys from `backend/` directory)

### Deploy to Netlify
1. Connect your GitHub repo to Netlify
2. Set base directory to `frontend`
3. Build command: `npm run build`
4. Publish directory: `frontend/dist`
5. Add environment variable: `VITE_API_URL=<your-railway-backend-url>`

### Deploy to Railway
1. Connect your GitHub repo to Railway
2. Set root directory to `backend`
3. Railway auto-detects Python and uses the Procfile

## 📄 License

MIT License — Use freely, modify freely.

## 🤝 Contributing

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/new-bank-format`)
3. Commit your changes
4. Push and open a Pull Request

---

**Built with ❤️ for anyone tired of manually parsing bank statements**
