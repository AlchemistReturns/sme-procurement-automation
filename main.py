from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as procurement_router

app = FastAPI(
    title="SME Procurement Automation Platform API",
    description="Agentic pipeline for automating procurement, quoting, and supplier negotiation.",
    version="0.1.0"
)

# Configure CORS for the future frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(procurement_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "healthy"}
