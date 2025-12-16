# FMECA-HWATM Integrations

FastAPI Backend + React Frontend

A production-ready system for visualizing, filtering, and validating **FMECA (Failure Mode, Effects, and Criticality Analysis)** data across multiple hardware boards.
The application loads Excel-based FMECA sheets, cross-checks ATM coverage, and provides an interactive UI to perform board-level analysis.

---

## 🚀 Features

### **Backend (FastAPI)**

- Dynamic board configuration with automatic image loading or placeholder generation
- Excel processing for FMECA data and ATM coverage
- Intelligent extraction of CRD / reference designators using regex
- RPN-based severity filtering (Red, Orange, Yellow, Green)
- ATM gap analysis to find missing components between FMECA and coverage
- Fully typed API responses using Pydantic models
- CORS-ready for local frontend integration
- Clean service logs & error handling

### **Frontend (ReactJS)**

- Modern dashboard displaying all available boards
- Auto-fetches board list and images from the API
- Interactive FMECA analysis page for each board
- Color-based filtering and structured table displays
- Smooth navigation between dashboard ↔ analysis

---

## 📁 Project Structure

```
project/
│
├── backend/
│   ├── main.py                # FastAPI application
│   ├── boards/                # Folder containing Excel files & optional images
│   └── ...
│
└── frontend/
    ├── App.jsx                # Main React application
    ├── components/
    │   ├── MainDashboard.jsx
    │   └── FMECAAnalysis.jsx
    └── ...
```

---

## ⚙️ Installation & Setup

### **1. Backend Setup (FastAPI)**

#### Install dependencies

```bash
pip install fastapi uvicorn pandas openpyxl pillow
```

#### Run the server

```bash
uvicorn main:app --reload --port 8000
```

#### Backend will run at:

```
http://localhost:8000
```

Ensure Excel files are placed correctly:

```
boards/<BOARD_NAME>/fmeca.xlsx
boards/<BOARD_NAME>/coverage.xlsx
```

---

### **2. Frontend Setup (React)**

Inside the frontend folder:

```bash
npm install
npm start
```

Frontend runs at:

```
http://localhost:3000
```

---

## 📊 Excel Processing Logic

- Automatically detects sheet names (`DFMECA`, `Sheet1`, `Coverage`, etc.)
- Extracts designators using robust regex patterns
- Maps CRD → ATM Coverage
- Determines missing components using designator matching
- Supports inconsistent Excel structures through fallback logic

---

## 🧪 Running in Development

**Backend**

```
uvicorn main:app --reload
```

**Frontend**

```
npm start
```

Both must be running simultaneously.
