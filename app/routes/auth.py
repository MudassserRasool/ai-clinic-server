from fastapi import APIRouter, Depends, HTTPException, status
from ..models import UserLogin, Token
from ..auth import authenticate_user, create_access_token

router = APIRouter()

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """Login endpoint for both doctors and admin"""
    user = await authenticate_user(user_data.username, user_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["phone"], "role": user["role"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "phone": user["phone"],
            "name": user["name"],
            "role": user["role"],
            "id": user.get("id")
        }
    }

@router.post("/token", response_model=Token)
async def login_for_access_token(user_data: UserLogin):
    """OAuth2 compatible token endpoint"""
    return await login(user_data) 