#!/usr/bin/env python3
"""
Database seeding script for Doctor Assistant System
Creates initial admin, sample doctors, patients, and visits with embeddings
"""

import asyncio
import logging
from datetime import datetime, timedelta
from bson import ObjectId

from app.database import connect_to_mongo, get_database
from app.auth import get_password_hash
from app.embedding_service import embedding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample clinical domains
CLINICAL_DOMAINS = [
    "Cardiology", "Neurology", "Pediatrics", "Orthopedics", "Dermatology",
    "Gastroenterology", "Endocrinology", "Pulmonology", "Psychiatry", "Oncology"
]

# Sample doctors data
SAMPLE_DOCTORS = [
    {
        "name": "Dr. Alice Johnson",
        "phone": "doc123",
        "password": "doc123",
        "qualification": "MD Cardiology",
        "clinicalDomain": "Cardiology",
        "yearsOfExperience": 10,
        "gender": "Female"
    },
    {
        "name": "Dr. Bob Smith", 
        "phone": "doc456",
        "password": "doc456",
        "qualification": "MD Neurology",
        "clinicalDomain": "Neurology",
        "yearsOfExperience": 8,
        "gender": "Male"
    },
    {
        "name": "Dr. Carol Davis",
        "phone": "doc789",
        "password": "doc789",
        "qualification": "MD Pediatrics",
        "clinicalDomain": "Pediatrics",
        "yearsOfExperience": 12,
        "gender": "Female"
    }
]

# Sample patients data
SAMPLE_PATIENTS = [
    {
        "name": "John Doe",
        "age": 45,
        "gender": "Male",
        "phone": "555-5678",
        "address": "123 Main St, City"
    },
    {
        "name": "Jane Smith",
        "age": 32,
        "gender": "Female", 
        "phone": "555-9876",
        "address": "456 Oak Ave, Town"
    },
    {
        "name": "Mike Johnson",
        "age": 28,
        "gender": "Male",
        "phone": "555-4321",
        "address": "789 Pine St, Village"
    },
    {
        "name": "Sarah Wilson",
        "age": 55,
        "gender": "Female",
        "phone": "555-1111",
        "address": "321 Elm St, City"
    },
    {
        "name": "Robert Brown",
        "age": 38,
        "gender": "Male",
        "phone": "555-2222",
        "address": "654 Maple Ave, Town"
    }
]

# Sample visits data
SAMPLE_VISITS = [
    {
        "patient_phone": "555-5678",
        "doctor_phone": "doc123",
        "vitals": {
            "bloodPressure": "120/80",
            "oxygen": "98%",
            "weight": "75kg",
            "didRecover": False
        },
        "clinicalTests": "CBC normal, ECG shows minor anomaly",
        "doctorNoticed": "Patient reports fatigue and mild chest discomfort",
        "prescribedMedications": "Iron supplement 1x daily, follow-up in 2 weeks",
        "days_ago": 5
    },
    {
        "patient_phone": "555-9876",
        "doctor_phone": "doc123",
        "vitals": {
            "bloodPressure": "110/70",
            "oxygen": "99%",
            "weight": "62kg",
            "didRecover": True
        },
        "clinicalTests": "Blood work normal, X-ray clear",
        "doctorNoticed": "Patient recovered well from respiratory infection",
        "prescribedMedications": "Completed antibiotic course",
        "days_ago": 10
    },
    {
        "patient_phone": "555-4321",
        "doctor_phone": "doc456",
        "vitals": {
            "bloodPressure": "125/85",
            "oxygen": "97%",
            "weight": "80kg",
            "didRecover": False
        },
        "clinicalTests": "Stress test scheduled, lipid panel elevated",
        "doctorNoticed": "High stress levels, needs lifestyle changes",
        "prescribedMedications": "Statin therapy, exercise program",
        "days_ago": 3
    },
    {
        "patient_phone": "555-1111",
        "doctor_phone": "doc789",
        "vitals": {
            "bloodPressure": "115/75",
            "oxygen": "98%",
            "weight": "58kg",
            "didRecover": True
        },
        "clinicalTests": "Mammogram normal, blood sugar stable",
        "doctorNoticed": "Regular checkup, patient maintaining good health",
        "prescribedMedications": "Continue current vitamins, annual follow-up",
        "days_ago": 1
    },
    {
        "patient_phone": "555-2222",
        "doctor_phone": "doc456",
        "vitals": {
            "bloodPressure": "140/90",
            "oxygen": "96%",
            "weight": "85kg",
            "didRecover": False
        },
        "clinicalTests": "MRI shows mild disc herniation, muscle tension",
        "doctorNoticed": "Chronic back pain, limited mobility",
        "prescribedMedications": "Physical therapy, anti-inflammatory medication",
        "days_ago": 7
    }
]

async def create_doctors(db):
    """Create sample doctors in the database"""
    logger.info("Creating sample doctors...")
    
    doctors_collection = db.doctors
    doctor_ids = {}
    
    for doctor_data in SAMPLE_DOCTORS:
        # Check if doctor already exists
        existing = await doctors_collection.find_one({"phone": doctor_data["phone"]})
        if existing:
            logger.info(f"Doctor {doctor_data['name']} already exists")
            doctor_ids[doctor_data["phone"]] = existing["_id"]
            continue
        
        # Hash password and create doctor
        hashed_password = get_password_hash(doctor_data["password"])
        doctor_doc = {
            "name": doctor_data["name"],
            "phone": doctor_data["phone"],
            "password": hashed_password,
            "qualification": doctor_data["qualification"],
            "clinicalDomain": doctor_data["clinicalDomain"],
            "yearsOfExperience": doctor_data["yearsOfExperience"],
            "gender": doctor_data["gender"],
            "isBlocked": False,
            "totalPatients": 0,
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = await doctors_collection.insert_one(doctor_doc)
        doctor_ids[doctor_data["phone"]] = result.inserted_id
        logger.info(f"Created doctor: {doctor_data['name']}")
    
    return doctor_ids

async def create_patients(db):
    """Create sample patients in the database"""
    logger.info("Creating sample patients...")
    
    patients_collection = db.patients
    patient_ids = {}
    
    for patient_data in SAMPLE_PATIENTS:
        # Check if patient already exists
        existing = await patients_collection.find_one({"phone": patient_data["phone"]})
        if existing:
            logger.info(f"Patient {patient_data['name']} already exists")
            patient_ids[patient_data["phone"]] = existing["_id"]
            continue
        
        # Create patient
        patient_doc = {
            "name": patient_data["name"],
            "age": patient_data["age"],
            "gender": patient_data["gender"],
            "phone": patient_data["phone"],
            "address": patient_data["address"],
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = await patients_collection.insert_one(patient_doc)
        patient_ids[patient_data["phone"]] = result.inserted_id
        logger.info(f"Created patient: {patient_data['name']}")
    
    return patient_ids

async def create_visits_with_embeddings(db, doctor_ids, patient_ids):
    """Create sample visits and generate embeddings"""
    logger.info("Creating sample visits with embeddings...")
    
    visits_collection = db.visits
    doctors_collection = db.doctors
    
    for visit_data in SAMPLE_VISITS:
        # Get IDs
        doctor_id = doctor_ids.get(visit_data["doctor_phone"])
        patient_id = patient_ids.get(visit_data["patient_phone"])
        
        if not doctor_id or not patient_id:
            logger.warning(f"Skipping visit - missing doctor or patient")
            continue
        
        # Check if visit already exists (basic check)
        existing = await visits_collection.find_one({
            "patientId": patient_id,
            "doctorId": doctor_id,
            "prescribedMedications": visit_data["prescribedMedications"]
        })
        if existing:
            logger.info(f"Visit already exists for patient {visit_data['patient_phone']}")
            continue
        
        # Create visit document
        visit_date = datetime.utcnow() - timedelta(days=visit_data["days_ago"])
        visit_doc = {
            "patientId": patient_id,
            "doctorId": doctor_id,
            "vitals": visit_data["vitals"],
            "clinicalTests": visit_data["clinicalTests"],
            "doctorNoticed": visit_data["doctorNoticed"],
            "prescribedMedications": visit_data["prescribedMedications"],
            "date": visit_date,
            "createdAt": visit_date,
            "updatedAt": visit_date
        }
        
        # Insert visit first
        result = await visits_collection.insert_one(visit_doc)
        visit_id = result.inserted_id
        
        # Generate embedding for the visit
        try:
            embedding = embedding_service.generate_visit_embedding(visit_doc)
            
            # Update visit with embedding
            await visits_collection.update_one(
                {"_id": visit_id},
                {"$set": {"embedding": embedding}}
            )
            
            logger.info(f"Created visit with embedding for patient {visit_data['patient_phone']}")
        except Exception as e:
            logger.warning(f"Could not generate embedding for visit: {e}")
            logger.info(f"Created visit without embedding for patient {visit_data['patient_phone']}")
        
        # Update doctor's patient count
        await doctors_collection.update_one(
            {"_id": doctor_id},
            {"$inc": {"totalPatients": 1}}
        )

async def seed_database():
    """Main seeding function"""
    logger.info("Starting database seeding...")
    
    # Connect to database
    await connect_to_mongo()
    db = get_database()
    
    try:
        # Initialize embedding service
        try:
            await embedding_service.initialize()
            logger.info("Embedding service initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize embedding service: {e}")
            logger.warning("Visits will be created without embeddings")
        
        # Create doctors and patients
        doctor_ids = await create_doctors(db)
        patient_ids = await create_patients(db)
        
        # Create visits with embeddings
        await create_visits_with_embeddings(db, doctor_ids, patient_ids)
        
        logger.info("Database seeding completed successfully!")
        
        # Print summary
        if db:
            total_doctors = await db.doctors.count_documents({})
            total_patients = await db.patients.count_documents({})
            total_visits = await db.visits.count_documents({})
            visits_with_embeddings = await db.visits.count_documents({"embedding": {"$exists": True}})
            
            logger.info(f"Summary:")
            logger.info(f"- Doctors: {total_doctors}")
            logger.info(f"- Patients: {total_patients}")
            logger.info(f"- Visits: {total_visits}")
            logger.info(f"- Visits with embeddings: {visits_with_embeddings}")
        else:
            logger.error("Database connection not available for summary")
        
    except Exception as e:
        logger.error(f"Error during seeding: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(seed_database()) 