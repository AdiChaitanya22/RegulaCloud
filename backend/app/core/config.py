import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "RegulaCloud Platform"
    PROJECT_TITLE: str = "A Regulation-Aware Cloud Compliance Verification and Deployment Framework"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Database: SQLite fallback by default for local development, or PostgreSQL URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./regulacloud.db")
    
    # SonarQube Settings
    SONARQUBE_URL: str = os.getenv("SONARQUBE_URL", "http://localhost:9000")
    SONARQUBE_TOKEN: str = os.getenv("SONARQUBE_TOKEN", "")
    
    # OPA Settings
    OPA_URL: str = os.getenv("OPA_URL", "http://localhost:8181/v1/data")
    
    # AWS Settings
    AWS_DEFAULT_REGION: str = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
    AWS_MOCK_MODE: bool = os.getenv("AWS_MOCK_MODE", "true").lower() == "true"
    
    # CORS Origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "*"
    ]

settings = Settings()
