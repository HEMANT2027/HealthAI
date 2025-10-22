from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jwtsign import signup, login
from jwtvalidate import Bearer

app = FastAPI(title="JWT Auth with MongoDB", version="1.0")

origins = [
    "http://localhost:5173",  # React dev server
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # URLs allowed to make requests
    allow_credentials=True,
    allow_methods=["*"],            # Allow all HTTP methods
    allow_headers=["*"],            # Allow all headers
)

# -------------------------------
# Request Schemas
# -------------------------------
class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

# -------------------------------
# Routes
# -------------------------------
@app.post("/signup")
async def sign_up(request: SignupRequest):
    """Register a new user"""
    return await signup(request.username, request.email, request.password)


@app.post("/signin")
async def sign_in(request: LoginRequest):
    """User login"""
    return await login(request.email, request.password)


@app.get("/protected")
async def protected_route(payload=Depends(Bearer())):
    """Protected route that requires valid JWT"""
    return {"message": "Access granted!", "user": payload}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from intake import router as intake_router
import uvicorn

app = FastAPI(title="MedicoTourism API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(intake_router)

@app.get("/")
def read_root():
    return {"message": "MedicoTourism API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
