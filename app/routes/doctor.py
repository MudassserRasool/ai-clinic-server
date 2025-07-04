from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
from ..models import (
    DoctorUpdate, Patient, PatientBase, VisitCreate, Visit, 
    ChatQuery, ChatResponse, SimilarCase
)
from ..auth import get_current_doctor
from ..database import get_database
from ..embedding_service import embedding_service

router = APIRouter()

@router.get("/me")
async def get_doctor_profile(current_doctor: dict = Depends(get_current_doctor)):
    """Get current doctor's profile"""
    return {
        "id": current_doctor["id"],
        "name": current_doctor["name"],
        "phone": current_doctor["phone"],
        "qualification": current_doctor.get("qualification"),
        "clinicalDomain": current_doctor.get("clinicalDomain"),
        "yearsOfExperience": current_doctor.get("yearsOfExperience"),
        "gender": current_doctor.get("gender"),
        "totalPatients": current_doctor.get("totalPatients", 0)
    }

@router.patch("/me")
async def update_doctor_profile(
    doctor_update: DoctorUpdate,
    current_doctor: dict = Depends(get_current_doctor)
):
    """Update current doctor's profile"""
    db = get_database()
    
    update_data = doctor_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        
        result = await db.doctors.update_one(
            {"_id": ObjectId(current_doctor["id"])},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Doctor not found")
    
    return {"message": "Profile updated successfully"}

@router.post("/patients", response_model=dict)
async def create_or_get_patient(
    patient_data: PatientBase,
    current_doctor: dict = Depends(get_current_doctor)
):
    """Create new patient or get existing patient by phone"""
    db = get_database()
    
    # Check if patient already exists
    existing_patient = await db.patients.find_one({"phone": patient_data.phone})
    
    if existing_patient:
        existing_patient["id"] = str(existing_patient["_id"])
        return existing_patient
    
    # Create new patient
    patient_dict = patient_data.model_dump()
    patient_dict["createdAt"] = datetime.utcnow()
    patient_dict["updatedAt"] = datetime.utcnow()
    
    result = await db.patients.insert_one(patient_dict)
    
    # Return created patient
    new_patient = await db.patients.find_one({"_id": result.inserted_id})
    new_patient["id"] = str(new_patient["_id"])
    
    return new_patient

@router.post("/visits")
async def create_visit(
    visit_data: VisitCreate,
    current_doctor: dict = Depends(get_current_doctor)
):
    """Create a new patient visit and generate embedding"""
    db = get_database()
    
    try:
        # Create or get patient
        patient_info = PatientBase(
            name=visit_data.patientName,
            age=visit_data.patientAge,
            gender=visit_data.patientGender,
            phone=visit_data.patientPhone,
            address=visit_data.patientAddress
        )
        
        # Check if patient exists
        patient = await db.patients.find_one({"phone": visit_data.patientPhone})
        
        if not patient:
            # Create new patient
            patient_dict = patient_info.model_dump()
            patient_dict["createdAt"] = datetime.utcnow()
            patient_dict["updatedAt"] = datetime.utcnow()
            result = await db.patients.insert_one(patient_dict)
            patient_id = result.inserted_id
        else:
            patient_id = patient["_id"]
        
        # Create visit data
        visit_dict = {
            "patientId": patient_id,
            "doctorId": ObjectId(current_doctor["id"]),
            "vitals": {
                "bloodPressure": visit_data.bloodPressure,
                "oxygen": visit_data.oxygen,
                "weight": visit_data.weight,
                "didRecover": visit_data.didRecover
            },
            "clinicalTests": visit_data.clinicalTests,
            "doctorNoticed": visit_data.doctorNoticed,
            "prescribedMedications": visit_data.prescribedMedications,
            "date": datetime.utcnow(),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        # Insert visit without embedding first
        result = await db.visits.insert_one(visit_dict)
        visit_id = result.inserted_id
        
        # Generate embedding after visit is created (as per requirement)
        if visit_data.prescribedMedications:
            try:
                embedding = embedding_service.generate_visit_embedding(visit_dict)
                # Update visit with embedding
                await db.visits.update_one(
                    {"_id": visit_id},
                    {"$set": {"embedding": embedding}}
                )
            except Exception as e:
                # Log error but don't fail the visit creation
                print(f"Warning: Could not generate embedding: {e}")
        
        # Update doctor's total patients count
        await db.doctors.update_one(
            {"_id": ObjectId(current_doctor["id"])},
            {"$inc": {"totalPatients": 1}}
        )
        
        return {
            "message": "Visit created successfully",
            "visit_id": str(visit_id),
            "patient_id": str(patient_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating visit: {str(e)}")

@router.get("/visits")
async def get_doctor_visits(
    current_doctor: dict = Depends(get_current_doctor),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get all visits created by the current doctor"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    try:
        # Build aggregation pipeline to get visits with patient info
        pipeline = [
            {"$match": {"doctorId": ObjectId(current_doctor["id"])}},
            {
                "$lookup": {
                    "from": "patients",
                    "localField": "patientId", 
                    "foreignField": "_id",
                    "as": "patient"
                }
            },
            {"$unwind": "$patient"},
            {"$sort": {"createdAt": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        visits = []
        async for visit in db.visits.aggregate(pipeline):
            visit_data = {
                "id": str(visit["_id"]),
                "patient": {
                    "id": str(visit["patient"]["_id"]),
                    "name": visit["patient"]["name"],
                    "age": visit["patient"]["age"],
                    "gender": visit["patient"]["gender"],
                    "phone": visit["patient"]["phone"],
                    "address": visit["patient"].get("address", "")
                },
                "vitals": visit.get("vitals", {}),
                "clinicalTests": visit.get("clinicalTests", ""),
                "doctorNoticed": visit.get("doctorNoticed", ""),
                "prescribedMedications": visit.get("prescribedMedications", ""),
                "date": visit["date"].isoformat() if visit.get("date") else visit["createdAt"].isoformat()
            }
            visits.append(visit_data)
        
        # Get total count for pagination
        total_count = await db.visits.count_documents({"doctorId": ObjectId(current_doctor["id"])})
        
        return {
            "visits": visits,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching visits: {str(e)}")

@router.post("/chat", response_model=dict)
async def chat_with_assistant(
    chat_query: ChatQuery,
    current_doctor: dict = Depends(get_current_doctor)
):
    """Chat endpoint for querying similar cases using natural language"""
    db = get_database()
    
    try:
        # Get relevant embeddings from all doctors
        pipeline = [
            {"$match": {"embedding": {"$exists": True, "$ne": None}}},
            {
                "$lookup": {
                    "from": "patients",
                    "localField": "patientId",
                    "foreignField": "_id", 
                    "as": "patient"
                }
            },
            {"$unwind": "$patient"}
        ]
        
        stored_embeddings = []
        async for visit in db.visits.aggregate(pipeline):
            if visit.get("embedding"):
                stored_embeddings.append({
                    "visit_id": str(visit["_id"]),
                    "embedding": visit["embedding"],
                    "patient": visit["patient"],
                    "clinical_data": {
                        "clinicalTests": visit.get("clinicalTests", ""),
                        "doctorNoticed": visit.get("doctorNoticed", ""),
                        "prescribedMedications": visit.get("prescribedMedications", ""),
                        "vitals": visit.get("vitals", {}),
                    }
                })
        
        # Query similar cases
        similar_cases = embedding_service.query_similar_cases(
            chat_query.message, stored_embeddings, top_k=3
        )
        
        # Format response
        if similar_cases:
            response_text = f"Based on your query '{chat_query.message}', I found {len(similar_cases)} similar cases:\n\n"
            
            case_summaries = []
            for i, (case_data, score) in enumerate(similar_cases, 1):
                case_summary = {
                    "case_number": i,
                    "similarity_score": round(score, 3),
                    "patient_age": case_data["patient"]["age"],
                    "patient_gender": case_data["patient"]["gender"],
                    "clinical_observations": case_data["clinical_data"]["doctorNoticed"],
                    "prescribed_medications": case_data["clinical_data"]["prescribedMedications"],
                    "outcome": "Recovered" if case_data["clinical_data"]["vitals"].get("didRecover") else "In Treatment"
                }
                case_summaries.append(case_summary)
                
                response_text += f"Case {i} (Similarity: {score:.3f}):\n"
                response_text += f"- Patient: {case_data['patient']['age']}yr {case_data['patient']['gender']}\n"
                response_text += f"- Observations: {case_data['clinical_data']['doctorNoticed']}\n"
                response_text += f"- Treatment: {case_data['clinical_data']['prescribedMedications']}\n"
                response_text += f"- Outcome: {'Recovered' if case_data['clinical_data']['vitals'].get('didRecover') else 'In Treatment'}\n\n"
        else:
            response_text = "I couldn't find any similar cases matching your query. This might be a unique case that requires careful consideration."
            case_summaries = []
        
        return {
            "response": response_text,
            "similar_cases": case_summaries,
            "query": chat_query.message,
            "context": chat_query.context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat assistant: {str(e)}") 