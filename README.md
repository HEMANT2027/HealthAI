# 🏥 MedicoTourism - Medical AI Assistant Platform

A comprehensive medical assistance platform that combines AI-powered document processing, medical chatbots, and patient management systems for healthcare professionals.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Frontend Components](#frontend-components)
- [Usage](#usage)
- [Deployment](#deployment)
- [Contributing](#contributing)

## 🎯 Overview

MedicoTourism is a full-stack medical AI platform designed to assist healthcare professionals with:

- **Document Processing**: OCR and NER for medical documents (prescriptions, pathology reports)
- **AI Chatbot**: Medical consultation assistant with RAG capabilities
- **Patient Management**: Intake forms, profiles, and visit tracking
- **Report Analysis**: Automated analysis of medical images and documents
- **Admin Dashboard**: System management and user administration

## ✨ Features

### 🔍 Document Processing
- **OCR Pipeline**: Extract text from medical documents using Google Vision API
- **Named Entity Recognition**: Identify medical entities (medications, dosages, conditions)
- **Pathology Analysis**: Process pathology reports and lab results
- **Image Segmentation**: Analyze medical images (CT scans, MRI, X-rays)

### 🤖 AI Chatbot
- **Medical Consultation**: AI-powered health assistant
- **RAG Integration**: Retrieval-Augmented Generation for evidence-based responses
- **Conversation Memory**: Maintains context across chat sessions
- **Patient-Specific Queries**: Tailored responses based on patient data

### 👥 User Management
- **Role-Based Access**: Doctors, patients, and admin roles
- **Authentication**: Secure JWT-based authentication
- **Profile Management**: User profiles and preferences
- **Google OAuth**: Optional Google sign-in integration

### 📊 Patient Management
- **Intake Forms**: Comprehensive patient information collection
- **Report Storage**: Secure document storage and retrieval
- **Medical History**: Track patient medical records

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   External      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   Services      │
│                 │    │                 │    │                 │
│ • React Router  │    │ • FastAPI       │    │ • MongoDB       │
│ • JavaScript    │    │ • Langchain     │    │ • AWS S3        │
│ • Tailwind CSS  │    │ • JWT Auth      │    │ • Google Cloud  │
│ • Axios         │    │ • OCR/NER       │    │ • OpenAI        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Backend Structure
```
backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── endpoints/             # API route handlers
│   ├── auth.py           # Authentication endpoints
│   ├── intake.py         # Patient intake forms
│   ├── admin.py          # Admin management
│   └── Mongo_connect.py  # Database operations
├── models/               # AI models and processing
│   ├── ocr_ner.py        # OCR and NER pipeline
│   ├── patho.py          # Pathology analysis
│   ├── medgemma.py       # Medical AI model
│   └── report_router.py  # Report processing
├── chatbot/              # AI chatbot functionality
│   ├── chat_router.py    # Chat API endpoints
│   ├── graph_health.py   # RAG graph implementation
│   └── logic.py          # Chat logic
└── testing/              # Test files and samples
```

### Frontend Structure
```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── Navbar.jsx   # Navigation component
│   │   ├── Footer.jsx   # Footer component
│   │   
│   ├── pages/           # Page components
│   │   ├── Home.jsx     # Landing page
│   │   ├── Login.jsx    # Authentication
│   │   ├── Signup.jsx   # User registration
│   │   ├── DoctorPanel.jsx # Doctor dashboard
│   │   ├── IntakeForm.jsx  # Patient intake
│   │   ├── Report.jsx      # Report viewing
│   │   ├── Chatbot.jsx     # AI chat interface
│   │   └── Admindashboard.jsx
│   └── App.jsx          # Main application component
├── package.json         # Node.js dependencies
└── vite.config.js      # Vite configuration
```

## 🛠️ Tech Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **MongoDB**: NoSQL database for storing patient data and reports
- **PyMongo/Motor**: MongoDB drivers for Python
- **JWT**: JSON Web Tokens for authentication
- **Pydantic**: Data validation and serialization
- **OpenAI**: AI model integration
- **Google Cloud Vision**: OCR capabilities
- **LangChain**: AI workflow orchestration
- **AWS S3**: File storage (optional)

### Frontend
- **React 19**: Modern React with latest features
- **Vite**: Fast build tool and development server
- **React Router**: Client-side routing
- **Tailwind CSS**: Utility-first CSS framework
- **Axios**: HTTP client for API calls

### AI/ML
- **BioClinicalBERT**: Medical named entity recognition
- **OCR/NER**: For Text Extraction
- **MedGemma**: Medical language model
- **RAG**: Retrieval-Augmented Generation for chatbot


## 🚀 Installation

### Prerequisites
- Python 3.10
- Node.js 16+
- MongoDB instance
- Google Cloud account (for OCR)
- OpenAI API key and Anthropic API Key


### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd medical
   ```

2. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Create .env file in backend directory
   MONGODB_KEY=your_mongodb_connection_string
   OPENAI_API_KEY=your_openai_api_key
   GOOGLE_APPLICATION_CREDENTIALS=path_to_gcp_key.json
   JWT_SECRET_KEY=your_jwt_secret
   ```

5. **Run the backend**
   ```bash
   python main.py
   # or
   uvicorn main:app --reload
   ```

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

4. **Access the application**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Database
MONGODB_KEY=mongodb://localhost:27017/medicotourism

# Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs
OPENAI_API_KEY=sk-your-openai-api-key
GOOGLE_APPLICATION_CREDENTIALS=path/to/gcp-key.json

# AWS (Optional)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_S3_BUCKET=your-s3-bucket-name
```

### Google Cloud Setup

1. **Create a Google Cloud Project**
2. **Enable Vision API**
3. **Create service account credentials**
4. **Download JSON key file**
5. **Set GOOGLE_APPLICATION_CREDENTIALS path**

## 📚 API Documentation

### Authentication Endpoints

- `POST /auth/login` - User login
- `POST /auth/signup` - User registration
- `GET /auth/me` - Get current user info

### Patient Management

- `POST /intake/submit` - Submit patient intake form
- `GET /intake/forms/{patient_id}` - Get patient forms
- `PUT /intake/forms/{form_id}` - Update intake form

### Document Processing

- `POST /report/ocr-extract` - Extract text from images
- `POST /report/pathology-extract` - Process pathology reports
- `POST /report/medgemma-analysis` - AI analysis of medical data
- `GET /report/reports/{patient_id}` - Get patient reports

### Chatbot

- `POST /chat/query` - Send message to AI chatbot
- `GET /chat/history/{thread_id}` - Get chat history

### Admin

- `GET /admin/users` - List all users
- `PUT /admin/users/{user_id}` - Update user
- `DELETE /admin/users/{user_id}` - Delete user

## 🎨 Frontend Components

### Pages

- **Home**: Landing page with feature overview
- **Login/Signup**: Authentication pages
- **DoctorPanel**: Doctor dashboard with patient management
- **IntakeForm**: Patient information collection
- **Report**: Medical report viewing and analysis
- **Chatbot**: AI consultation interface
- **AdminDashboard**: System administration

### Key Features

- **Protected Routes**: Role-based access control
- **Real-time Updates**: Live data synchronization
- **File Upload**: Drag-and-drop document upload


## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Use TypeScript for frontend components
- Write tests for new features
- Update documentation for API changes
- Follow semantic versioning

## 🆘 Support

- **Documentation**: Check this README and API docs
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact the development team


**Built with ❤️ for Healthcare Innovation**
**Special Thanks to Abhishek Sharma, Spandan Kundu, Jinish Gupta, Nidhi Mithiya, Aditya Pratap Singh, Saket Kumar Singh, Hemant Pathak, Arush Sharma"**
*Empowering healthcare professionals with AI-driven tools for better patient care*
