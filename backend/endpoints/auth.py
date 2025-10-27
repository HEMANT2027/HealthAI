from fastapi import FastAPI, APIRouter, Depends, HTTPException, status, Request, Response, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from passlib.context import CryptContext
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from datetime import datetime, timedelta
from typing import Annotated, Optional
import os
import dotenv
import secrets

dotenv.load_dotenv()

app = FastAPI()
router = APIRouter(prefix="/auth", tags=["Authentication"])

# ---------- Configuration ----------
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 240

# MongoDB Connection with error handling
try:
    MONGODB_URI = os.getenv("MONGODB_KEY")
    if not MONGODB_URI:
        raise ValueError("MONGODB_KEY environment variable is not set")
    
    # Use standard connection string format instead of SRV if having DNS issues
    # Replace mongodb+srv:// with mongodb:// in your .env if needed
    client = MongoClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000
    )
    
    # Test the connection
    client.server_info()
    print("✅ MongoDB connected successfully")
    
    db = client.get_database("medicotourism")
    user_collection = db.get_collection("users")
except ServerSelectionTimeoutError as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("Please check your MONGODB_KEY in .env file")
    print("Tip: If using MongoDB Atlas, try replacing 'mongodb+srv://' with 'mongodb://' and use direct connection string")
    raise
except Exception as e:
    print(f"❌ Error connecting to MongoDB: {e}")
    raise

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# ---------- User Schema ----------
class User(BaseModel):
    username: str
    email: EmailStr
    hashed_password: str
    role: str  # "patient", "doctor", or "admin"
    pseudonym_id: str | None = None
    # Doctor-specific fields
    license_id: str | None = None
    specialization: str | None = None
    hospital: str | None = None
    verified: bool = False  # For doctor verification
    license_document_url: str | None = None

# ---------- Request Models ----------
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str  # "patient" or "doctor" (admin cannot register)
    # Optional doctor fields
    license_id: Optional[str] = None
    specialization: Optional[str] = None
    hospital: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ---------- Utility Functions ----------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def generate_pseudonym_id(role: str) -> str:
    """Generate a unique pseudonym ID based on role matching P-XXXX-XXXX format"""
    prefix = "P" if role == "patient" else "D" if role == "doctor" else "A"
    # Generate 4-character segments to match the schema pattern P-XXXX-XXXX
    part1 = secrets.token_hex(2).upper()  # 4 hex characters
    part2 = secrets.token_hex(2).upper()  # 4 hex characters
    return f"{prefix}-{part1}-{part2}"

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ---------- Auth Middleware ----------
async def authMiddleware(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = user_collection.find_one({"email": email})
    if user is None:
        raise credentials_exception
    
    user["id"] = str(user["_id"])
    del user["_id"]
    if "hashed_password" in user:
        del user["hashed_password"]
    return user

# ---------- REGISTER ----------
@router.post("/register")
async def registerUser(data: RegisterRequest):
    """Register a new user (patient or doctor)"""
    
    # Validate role
    if data.role not in ["patient", "doctor"]:
        raise HTTPException(status_code=400, detail="Role must be 'patient' or 'doctor'")
    
    # Check if email already exists
    if user_collection.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="User already exists with this email")
    
    # Check if username already exists
    if user_collection.find_one({"username": data.username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    
    # Validate doctor-specific fields
    if data.role == "doctor":
        if not data.license_id:
            raise HTTPException(status_code=400, detail="License ID is required for doctors")
        if not data.specialization:
            raise HTTPException(status_code=400, detail="Specialization is required for doctors")
        if not data.hospital:
            raise HTTPException(status_code=400, detail="Hospital/Clinic name is required for doctors")
            
    hashed_pw = hash_password(data.password)
    pseudonym_id = generate_pseudonym_id(data.role)
    
    new_user = {
        "username": data.username,
        "email": data.email,
        "hashed_password": hashed_pw,
        "role": data.role,
        "pseudonym_id": pseudonym_id,
        "verified": True if data.role == "patient" else False,  # Doctors need manual verification
        "created_at": datetime.utcnow()
    }
    
    # Add doctor-specific fields
    if data.role == "doctor":
        new_user.update({
            "license_id": data.license_id,
            "specialization": data.specialization,
            "hospital": data.hospital,
            "license_document_url": None
        })
    
    result = user_collection.insert_one(new_user)
    new_user["id"] = str(result.inserted_id)
    
    # Generate token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": data.email, "role": data.role},
        expires_delta=access_token_expires
    )
    
    message = "Registration successful!"
    if data.role == "doctor":
        message = "Registration successful! Your account is pending verification. You'll be notified once approved."
    
    return {
        "success": True,
        "message": message,
        "token": access_token,
        "user": {
            "id": new_user["id"],
            "email": new_user["email"],
            "username": new_user["username"],
            "role": new_user["role"],
            "verified": new_user["verified"],
            "pseudonym_id": new_user["pseudonym_id"]
        }
    }

# ---------- LOGIN ----------
@router.post("/login")
async def loginUser(data: LoginRequest):
    """Login user (patient, doctor, or admin)"""
    
    user = user_collection.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if doctor is verified (but allow admin to login even if not verified)
    if user.get("role") == "doctor" and not user.get("verified", False):
        raise HTTPException(
            status_code=403, 
            detail="Your doctor account is pending verification. Please wait for admin approval."
        )
    
    token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "role": user.get("role", "patient")},
        expires_delta=token_expires
    )
    
    return {
        "success": True,
        "message": "Login successful",
        "token": access_token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "username": user["username"],
            "role": user.get("role", "patient"),
            "verified": user.get("verified", True),
            "pseudonym_id": user.get("pseudonym_id"),
            "specialization": user.get("specialization"),
            "hospital": user.get("hospital")
        }
    }

# ---------- LOGOUT ----------
@router.post("/logout")
async def logoutUser():
    return {"success": True, "message": "Logout successful"}

# ---------- GET CURRENT USER ----------
@router.get("/me")
async def getCurrentUser(current_user: dict = Depends(authMiddleware)):
    return {
        "success": True,
        "user": current_user
    }

# Mount router
app.include_router(router)