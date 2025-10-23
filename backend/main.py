from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from intake import router as intake_router
from Mongo_connect import router as mongo_router
# from ocr_ner import router as ocr_router
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
app.include_router(mongo_router)
# app.include_router(ocr_router)

@app.get("/")
def read_root():
    return {"message": "MedicoTourism API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
