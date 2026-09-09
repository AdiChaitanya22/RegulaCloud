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
    regulatory_scope: Optional[List[str]] = None
    hcl_content: Optional[str] = None

class ProjectCreate(ProjectBase):
    id: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    organization: Optional[str] = None
    sector: Optional[str] = None
    jurisdiction: Optional[str] = None
    data_categories: Optional[List[str]] = None
    environment: Optional[str] = None
    cloud_provider: Optional[str] = None
    aws_region: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = None
    regulatory_scope: Optional[List[str]] = None
    hcl_content: Optional[str] = None

class ProjectResponse(ProjectBase):
    id: str
    compliance_score: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
