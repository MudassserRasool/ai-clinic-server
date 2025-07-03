# Doctor Assistant Backend

FastAPI backend for the AI-powered medical assistant system with Bio_ClinicalBERT embeddings.

## Features

- JWT Authentication with role-based access (Admin/Doctor)
- MongoDB integration for scalable data storage
- Bio_ClinicalBERT embeddings for clinical text analysis
- Vector similarity search for case recommendations
- Chatbot interface for querying similar cases
- Comprehensive API endpoints for patient and visit management

## Setup

### Prerequisites

- Python 3.8+
- MongoDB (local or cloud instance)

### Installation

1. Navigate to the server directory:

```bash
cd server
```

2. Create a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate.bat
  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create environment file:

```bash
cp .env.example .env
```

5. Update the `.env` file with your MongoDB connection string and other settings.

### Running the Application

```bash
python main.py
```

The API will be available at `http://localhost:8000`

### API Documentation

Interactive API documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## API Endpoints

### Authentication

- `POST /login` - Login for doctors and admin
- `POST /token` - OAuth2 compatible token endpoint

### Admin Endpoints (require admin role)

- `POST /admin/doctors` - Create new doctor account
- `GET /admin/doctors` - List all doctors
- `PATCH /admin/doctors/{doctor_id}` - Update doctor information
- `PATCH /admin/doctors/{doctor_id}/block` - Block/unblock doctor
- `GET /admin/stats` - Get admin dashboard statistics

### Doctor Endpoints (require doctor role)

- `GET /doctors/me` - Get current doctor's profile
- `PATCH /doctors/me` - Update doctor's profile
- `POST /doctors/patients` - Create or get patient by phone
- `POST /doctors/visits` - Create new patient visit
- `POST /doctors/chat` - Chat with AI assistant for case recommendations

## Default Credentials

- **Admin**: `admin123` / `admin123`
- **Sample Doctor**: Create via admin interface

## Technologies Used

- FastAPI - Modern Python web framework
- MongoDB - Document database
- Bio_ClinicalBERT - Medical text embeddings
- JWT - Authentication tokens
- PyTorch - Deep learning framework
- Scikit-learn - Machine learning utilities

## Project Structure

```
server/
├── app/
│   ├── routes/          # API route definitions
│   ├── models.py        # Pydantic data models
│   ├── auth.py          # Authentication utilities
│   ├── database.py      # MongoDB connection
│   ├── embedding_service.py  # Bio_ClinicalBERT integration
│   └── config.py        # Application configuration
├── main.py              # FastAPI application entry point
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Embedding Service

The system uses Bio_ClinicalBERT to generate embeddings for clinical cases:

1. **Text Processing**: Combines vitals, clinical tests, observations, and medications
2. **Embedding Generation**: Uses BERT [CLS] token for 768-dimensional vectors
3. **Similarity Search**: Cosine similarity for finding related cases
4. **Chatbot Integration**: Natural language queries against case database

## Database Schema

### Collections:

- `doctors` - Doctor profiles and credentials
- `patients` - Patient demographic information
- `visits` - Clinical visit records with embeddings
- Indexes optimized for common queries

## Security

- Passwords hashed with bcrypt
- JWT tokens for stateless authentication
- Role-based access control
- CORS configuration for frontend integration
