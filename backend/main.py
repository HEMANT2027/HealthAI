from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints.auth import router as auth_router
from endpoints.intake import router as intake_router
from endpoints.Mongo_connect import router as mongo_router
from endpoints.admin import router as admin_router
from models.report_router import router as report_router
from chatbot.chat_router import router as chat_router
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
app.include_router(admin_router)
app.include_router(report_router)
app.include_router(chat_router)

@app.get("/")
def read_root():
    return {"message": "MedicoTourism API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
