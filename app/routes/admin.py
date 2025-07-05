from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
from bson import ObjectId
from datetime import datetime
from ..models import DoctorCreate, Doctor, DoctorUpdate, AdminCreate
from ..auth import get_current_admin, get_password_hash
from ..preprocessors.database import get_database

router = APIRouter()

@router.post("/setup", response_model=dict)
async def setup_initial_admin(admin_data: AdminCreate):
    """Create the first admin account (only works when no admins exist)"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    # Check if any admin already exists
    admin_count = await db.admins.count_documents({})
    if admin_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Admin setup already completed. Use the regular admin creation endpoint."
        )
    
    # Hash the password
    hashed_password = get_password_hash(admin_data.password)
    
    # Create first admin (automatically becomes super admin)
    admin_dict = admin_data.model_dump(exclude={"password"})
    admin_dict["password"] = hashed_password
    admin_dict["isSuperAdmin"] = True
    admin_dict["createdAt"] = datetime.utcnow()
    admin_dict["updatedAt"] = datetime.utcnow()
    
    # Insert admin
    result = await db.admins.insert_one(admin_dict)
    
    return {
        "message": "Initial admin setup completed successfully",
        "admin_id": str(result.inserted_id),
        "isSuperAdmin": True
    }

@router.post("/create", response_model=dict)
async def create_admin(
    admin_data: AdminCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """Create a new admin account (requires super admin privileges)"""
    db = get_database()
    if db is None:
        raise HTTPException(
            status_code=500,
            detail="Database connection not available"
        )
    
    # Check if current admin is super admin or if this is the first admin
    admin_count = await db.admins.count_documents({})
    if admin_count > 0 and not current_admin.get("isSuperAdmin", False):
        raise HTTPException(
            status_code=403,
            detail="Only super admin can create new admin accounts"
        )
    
    # Check if admin with this phone already exists
    existing_admin = await db.admins.find_one({"phone": admin_data.phone})
    if existing_admin:
        raise HTTPException(
            status_code=400,
            detail="Admin with this phone number already exists"
        )
    
    # Hash the password
    hashed_password = get_password_hash(admin_data.password)
    
    # Create admin document
    admin_dict = admin_data.model_dump(exclude={"password"})
    admin_dict["password"] = hashed_password
    admin_dict["isSuperAdmin"] = admin_count == 0  # First admin becomes super admin
    admin_dict["createdAt"] = datetime.utcnow()
    admin_dict["updatedAt"] = datetime.utcnow()
    
    # Insert admin
    result = await db.admins.insert_one(admin_dict)
    
    return {
        "message": "Admin created successfully",
        "admin_id": str(result.inserted_id),
        "isSuperAdmin": admin_dict["isSuperAdmin"]
    }

@router.post("/doctors", response_model=dict)
async def create_doctor(
    doctor_data: DoctorCreate,
    current_admin: dict = Depends(get_current_admin)
):
    """Create a new doctor account"""
    db = get_database()
    
    # Check if doctor with this phone already exists
    existing_doctor = await db.doctors.find_one({"phone": doctor_data.phone})
    if existing_doctor:
        raise HTTPException(
            status_code=400,
            detail="Doctor with this phone number already exists"
        )
    
    # Hash the password
    hashed_password = get_password_hash(doctor_data.password)
    
    # Create doctor document
    doctor_dict = doctor_data.model_dump(exclude={"password"})
    doctor_dict["password"] = hashed_password
    doctor_dict["isBlocked"] = False
    doctor_dict["totalPatients"] = 0
    doctor_dict["createdAt"] = datetime.utcnow()
    doctor_dict["updatedAt"] = datetime.utcnow()
    
    # Insert doctor
    result = await db.doctors.insert_one(doctor_dict)
    
    return {
        "message": "Doctor created successfully",
        "doctor_id": str(result.inserted_id)
    }

@router.get("/doctors")
async def get_all_doctors(
    current_admin: dict = Depends(get_current_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(None, description="Search by name or clinical domain")
):
    """Get all doctors with optional search and pagination"""
    db = get_database()
    
    # Build query
    query = {}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"clinicalDomain": {"$regex": search, "$options": "i"}}
        ]
    
    # Get doctors (exclude password field)
    doctors_cursor = db.doctors.find(
        query,
        {"password": 0}  # Exclude password field
    ).sort("name", 1).skip(skip).limit(limit)
    
    doctors = []
    async for doctor in doctors_cursor:
        doctor["id"] = str(doctor["_id"])
        del doctor["_id"]
        doctors.append(doctor)
    
    # Get total count
    total_count = await db.doctors.count_documents(query)
    
    return {
        "doctors": doctors,
        "total": total_count,
        "skip": skip,
        "limit": limit
    }

@router.patch("/doctors/{doctor_id}")
async def update_doctor(
    doctor_id: str,
    doctor_update: DoctorUpdate,
    current_admin: dict = Depends(get_current_admin)
):
    """Update doctor information or block/unblock doctor"""
    db = get_database()
    
    # Validate ObjectId
    try:
        doc_object_id = ObjectId(doctor_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid doctor ID")
    
    # Check if doctor exists
    doctor = await db.doctors.find_one({"_id": doc_object_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Build update data
    update_data = doctor_update.model_dump(exclude_unset=True)
    if update_data:
        update_data["updatedAt"] = datetime.utcnow()
        
        result = await db.doctors.update_one(
            {"_id": doc_object_id},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            return {"message": "No changes made"}
    
    return {"message": "Doctor updated successfully"}

@router.patch("/doctors/{doctor_id}/block")
async def toggle_doctor_block_status(
    doctor_id: str,
    current_admin: dict = Depends(get_current_admin)
):
    """Block or unblock a doctor"""
    db = get_database()
    
    # Validate ObjectId
    try:
        doc_object_id = ObjectId(doctor_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid doctor ID")
    
    # Get current doctor
    doctor = await db.doctors.find_one({"_id": doc_object_id})
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Toggle block status
    new_blocked_status = not doctor.get("isBlocked", False)
    
    await db.doctors.update_one(
        {"_id": doc_object_id},
        {
            "$set": {
                "isBlocked": new_blocked_status,
                "updatedAt": datetime.utcnow()
            }
        }
    )
    
    action = "blocked" if new_blocked_status else "unblocked"
    return {
        "message": f"Doctor {action} successfully",
        "isBlocked": new_blocked_status
    }

@router.get("/stats")
async def get_admin_stats(current_admin: dict = Depends(get_current_admin)):
    """Get admin dashboard statistics"""
    db = get_database()
    
    # Get doctor statistics
    total_doctors = await db.doctors.count_documents({})
    active_doctors = await db.doctors.count_documents({"isBlocked": False})
    blocked_doctors = await db.doctors.count_documents({"isBlocked": True})
    
    # Get patient and visit statistics
    total_patients = await db.patients.count_documents({})
    total_visits = await db.visits.count_documents({})
    
    # Get visits from last 30 days
    from datetime import timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_visits = await db.visits.count_documents({
        "createdAt": {"$gte": thirty_days_ago}
    })
    
    return {
        "doctors": {
            "total": total_doctors,
            "active": active_doctors,
            "blocked": blocked_doctors
        },
        "patients": {
            "total": total_patients
        },
        "visits": {
            "total": total_visits,
            "last_30_days": recent_visits
        }
    } 