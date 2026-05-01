# Health-AI - Medical AI Assistant Platform

A comprehensive medical assistance platform that combines AI-powered document processing, medical chatbots, and patient management systems for healthcare professionals.

---

## Table of Contents

- Overview  
- Features  
- Architecture  
- Tech Stack  
- Installation  
- Configuration  
- API Documentation  
- Frontend Components  
- Contributing  

---

## Overview

Health-AI is a full-stack medical AI platform designed to assist healthcare professionals with:

- Document Processing: OCR and Named Entity Recognition for medical documents such as prescriptions and pathology reports  
- AI Chatbot: Medical consultation assistant with Retrieval-Augmented Generation capabilities  
- Patient Management: Intake forms, profiles, and visit tracking  
- Report Analysis: Automated analysis of medical images and documents  
- Admin Dashboard: System management and user administration  

---

## Features

### Document Processing

- OCR pipeline using Google Cloud Vision API  
- Named Entity Recognition for medications, dosages, and conditions  
- Pathology report processing and analysis  
- Medical image segmentation for CT scans, MRI, and X-rays  

### AI Chatbot

- AI-powered medical consultation assistant  
- Retrieval-Augmented Generation for evidence-based responses  
- Persistent conversation memory  
- Patient-specific contextual responses  

### User Management

- Role-based access control for doctors, patients, and administrators  
- Secure authentication using JWT  
- Profile management system  
- Optional Google OAuth integration  

### Patient Management

- Structured intake forms  
- Secure document storage and retrieval  
- Medical history tracking  

---

## Architecture

```
Frontend (React)  <-->  Backend (FastAPI)  <-->  External Services

Frontend:
- React Router
- JavaScript
- Tailwind CSS
- Axios

Backend:
- FastAPI
- LangChain
- JWT Authentication
- OCR and NER modules

External Services:
- MongoDB
- AWS S3
- Google Cloud
- OpenAI APIs
```

### Backend Structure

```
backend/
├── main.py
├── requirements.txt
├── endpoints/
│   ├── auth.py
│   ├── intake.py
│   ├── admin.py
│   └── Mongo_connect.py
├── models/
│   ├── ocr_ner.py
│   ├── patho.py
│   ├── medgemma.py
│   └── report_router.py
├── chatbot/
│   ├── chat_router.py
│   ├── graph_health.py
│   └── logic.py
└── testing/
```

### Frontend Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Navbar.jsx
│   │   ├── Footer.jsx
│   ├── pages/
│   │   ├── Home.jsx
│   │   ├── Login.jsx
│   │   ├── Signup.jsx
│   │   ├── DoctorPanel.jsx
│   │   ├── IntakeForm.jsx
│   │   ├── Report.jsx
│   │   ├── Chatbot.jsx
│   │   └── AdminDashboard.jsx
│   └── App.jsx
├── package.json
└── vite.config.js
```

---

## Tech Stack

### Backend

- FastAPI  
- MongoDB  
- PyMongo / Motor  
- JSON Web Tokens  
- Pydantic  
- OpenAI API  
- Google Cloud Vision API  
- LangChain  
- AWS S3 (optional)  

### Frontend

- React 19  
- Vite  
- React Router  
- Tailwind CSS  
- Axios  

### AI and Machine Learning

- BioClinicalBERT for medical NER  
- OCR and NER pipelines  
- MedGemma medical language model  
- Retrieval-Augmented Generation  

---

## Installation

### Prerequisites

- Python 3.10  
- Node.js 16 or higher  
- MongoDB instance  
- Google Cloud account  
- OpenAI API key  

---

### Backend Setup

```bash
git clone <repository-url>
cd medical/backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file:

```env
MONGODB_KEY=your_mongodb_connection_string
OPENAI_API_KEY=your_openai_api_key
GOOGLE_APPLICATION_CREDENTIALS=path_to_gcp_key.json
JWT_SECRET_KEY=your_jwt_secret
```

Run the backend:

```bash
uvicorn main:app --reload
```

---

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Access:

- Frontend: http://localhost:5173  
- Backend API: http://localhost:8000  
- API Docs: http://localhost:8000/docs  

---

## Configuration

### Environment Variables

```env
MONGODB_KEY=mongodb://localhost:27017/medicotourism

JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

OPENAI_API_KEY=your-openai-key
GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json

AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_S3_BUCKET=your-bucket
```

---

## API Documentation

### Authentication

- POST /auth/login  
- POST /auth/signup  
- GET /auth/me  

### Patient Management

- POST /intake/submit  
- GET /intake/forms/{patient_id}  
- PUT /intake/forms/{form_id}  

### Document Processing

- POST /report/ocr-extract  
- POST /report/pathology-extract  
- POST /report/medgemma-analysis  
- GET /report/reports/{patient_id}  

### Chatbot

- POST /chat/query  
- GET /chat/history/{thread_id}  

### Admin

- GET /admin/users  
- PUT /admin/users/{user_id}  
- DELETE /admin/users/{user_id}  

---

## Frontend Components

### Pages

- Home  
- Login and Signup  
- DoctorPanel  
- IntakeForm  
- Report  
- Chatbot  
- AdminDashboard  

### Features

- Protected routes with role-based access control  
- Real-time updates  
- File upload support  

---

## Contributing

1. Fork the repository  
2. Create a feature branch  
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Commit changes  
   ```bash
   git commit -m "Add your feature"
   ```
4. Push to GitHub  
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a Pull Request  

---

## Support

- Refer to the documentation and API docs  
- Use GitHub Issues for bug reporting  
- Use Discussions for queries  

---

## License

This project is licensed under the MIT License.

---

## Acknowledgements

This project was developed with contributions from:

Abhishek Sharma  
Spandan Kundu  
Jinish Gupta  
Nidhi Mithiya  
Aditya Pratap Singh  
Saket Kumar Singh  
Hemant Pathak  
Arush Sharma  

---

Health-AI is designed to support healthcare professionals with reliable and scalable AI-driven tools.
