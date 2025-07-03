from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid objectid')
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string"}

# User Models
class UserBase(BaseModel):
    phone: str
    name: str

class UserLogin(BaseModel):
    username: str  # phone number
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

# Admin Models
class AdminBase(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None

class AdminCreate(AdminBase):
    password: str

class AdminUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

class Admin(AdminBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    isSuperAdmin: bool = False
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Doctor Models
class DoctorBase(BaseModel):
    name: str
    phone: str
    qualification: str
    clinicalDomain: str
    yearsOfExperience: int
    gender: str

class DoctorCreate(DoctorBase):
    password: str

class DoctorUpdate(BaseModel):
    name: Optional[str] = None
    qualification: Optional[str] = None
    clinicalDomain: Optional[str] = None
    yearsOfExperience: Optional[int] = None
    gender: Optional[str] = None

class Doctor(DoctorBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    isBlocked: bool = False
    totalPatients: int = 0
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Patient Models
class PatientBase(BaseModel):
    name: str
    age: int
    gender: str
    phone: str
    address: Optional[str] = None

class Patient(PatientBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Visit Models
class VitalsBase(BaseModel):
    bloodPressure: str
    oxygen: str
    weight: str
    didRecover: bool = False

class VisitBase(BaseModel):
    clinicalTests: Optional[str] = None
    doctorNoticed: Optional[str] = None
    prescribedMedications: Optional[str] = None

class VisitCreate(BaseModel):
    # Patient info (for creation or lookup)
    patientName: str
    patientAge: int
    patientGender: str
    patientPhone: str
    patientAddress: Optional[str] = None
    
    # Vitals
    bloodPressure: str
    oxygen: str
    weight: str
    didRecover: bool = False
    
    # Clinical data
    clinicalTests: Optional[str] = None
    doctorNoticed: Optional[str] = None
    prescribedMedications: Optional[str] = None

class Visit(VisitBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    patientId: PyObjectId
    doctorId: PyObjectId
    vitals: VitalsBase
    embedding: Optional[List[float]] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# Chat Models
class ChatQuery(BaseModel):
    message: str
    context: Optional[str] = None  # Current patient context if any

class ChatResponse(BaseModel):
    response: str
    similar_cases: List[dict]
    confidence_scores: List[float]

# Search Models
class SimilarCase(BaseModel):
    visit_id: str
    patient_info: dict
    clinical_data: dict
    similarity_score: float 