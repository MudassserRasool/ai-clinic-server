from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings
from .database import get_database
from .models import Doctor
from bson import ObjectId

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt

async def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        phone: str = payload.get("sub")
        if phone is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    payload = await verify_token(token)
    phone = payload.get("sub")
    role = payload.get("role")
    
    if not phone or not role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    db = get_database()
    
    if role == "admin":
        # For admin, we'll check a simple admin collection or hardcoded admin
        admin_data = {"phone": phone, "role": "admin", "name": "Admin User"}
        return admin_data
    elif role == "doctor":
        doctor = await db.doctors.find_one({"phone": phone})
        if not doctor:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Doctor not found")
        if doctor.get("isBlocked", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")
        
        doctor["id"] = str(doctor["_id"])
        doctor["role"] = "doctor"
        return doctor
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role")

async def get_current_doctor(current_user: dict = Depends(get_current_user)):
    """Get current doctor (role check)"""
    if current_user.get("role") != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access required")
    return current_user

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    """Get current admin (role check)"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

async def authenticate_user(phone: str, password: str):
    """Authenticate user by phone and password"""
    db = get_database()
    
    # Check admins collection first
    admin = await db.admins.find_one({"phone": phone})
    if admin and verify_password(password, admin["password"]):
        admin["id"] = str(admin["_id"])
        admin["role"] = "admin"
        return admin
    
    # Fallback to hardcoded admin (for backward compatibility during migration)
    if phone == "admin123" and password == "admin123":
        return {"phone": phone, "role": "admin", "name": "Admin User", "isSuperAdmin": True}
    
    # Check doctors
    doctor = await db.doctors.find_one({"phone": phone})
    if doctor and verify_password(password, doctor["password"]):
        if doctor.get("isBlocked", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")
        
        doctor["id"] = str(doctor["_id"])
        doctor["role"] = "doctor"
        return doctor
    
    return None 