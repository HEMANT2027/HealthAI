import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
import os

# ----------------------------------------
# JWT Configuration
# ----------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "your_secret_key_here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----------------------------------------
# MongoDB (Async)
# ----------------------------------------
MONGO_URI = "mongodb+srv://user2:Gbh2yk98RaWptxph@cluster0.xoyb9qw.mongodb.net/?retryWrites=true&w=majority"
client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
db = client["medicotourism"]
users_collection = db["users"]

# ----------------------------------------
# Helper Functions
# ----------------------------------------
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Generate JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password):
    return pwd_context.hash(password)


def decode_token(token: str):
    """Decode and validate JWT."""
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ----------------------------------------
# User Functions
# ----------------------------------------
async def signup(username: str, email: str, password: str):
    """Register new user."""
    existing_user = await users_collection.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = hash_password(password)
    new_user = {
        "username": username,
        "email": email,
        "password": hashed_pw,
        "created_at": datetime.utcnow(),
    }
    result = await users_collection.insert_one(new_user)

    token_data = {"sub": str(result.inserted_id), "email": email}
    token = create_access_token(data=token_data)
    return {"access_token": token, "token_type": "bearer"}


async def login(email: str, password: str):
    """Authenticate user."""
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token_data = {"sub": str(user["_id"]), "email": email}
    token = create_access_token(data=token_data)
    return {"access_token": token, "token_type": "bearer"}