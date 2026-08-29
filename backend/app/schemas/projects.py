from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProjectBase(BaseModel):
    name: str
    organization: str
    sector: str = "Healthcare"
    jurisdiction: str = "India"
    data_categories: List[str] = Field(default_factory=lambda: ["personal_data"])
    environment: str = "production"
    cloud_provider: str = "AWS"
    aws_region: str = "ap-south-1"
    owner: str = "admin@regulacloud.gov.in"

class ProjectCreate(ProjectBase):
    id: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    compliance_score: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
