from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.db.init_db import init_database
from backend.app.api.v1 import (
    applicability,
    compliance,
    policies,
    projects,
    remediation_rl,
    security_sonar,
    deployments,
    terraform_opa,
    audit,
    reports,
    drift,
    ai_copilot
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A Regulation-Aware Cloud Compliance Verification and Deployment Framework (India DPDP Act 2023 & CERT-In 2022)",
    version=settings.VERSION
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database startup hook
@app.on_event("startup")
def on_startup():
    init_database()

# Root Health Check
@app.get("/")
def root():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "title": settings.PROJECT_TITLE,
        "version": settings.VERSION,
        "regulatory_corpus": "India (DPDPA 2023, DPDP Rules 2025, CERT-In 2022)"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RegulaCloud API Gateway"}

# Register v1 API Routers
app.include_router(compliance.router, prefix=settings.API_V1_STR)
app.include_router(applicability.router, prefix=settings.API_V1_STR)
app.include_router(policies.router, prefix=settings.API_V1_STR)
app.include_router(projects.router, prefix=settings.API_V1_STR)
app.include_router(remediation_rl.router, prefix=settings.API_V1_STR)
app.include_router(security_sonar.router, prefix=settings.API_V1_STR)
app.include_router(deployments.router, prefix=settings.API_V1_STR)
app.include_router(terraform_opa.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(drift.router, prefix=settings.API_V1_STR)
app.include_router(ai_copilot.router, prefix=settings.API_V1_STR)
