from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
from backend.app.core.database import get_db
from backend.app.db.models import Project
from backend.app.schemas.projects import ProjectCreate, ProjectResponse

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("", response_model=ProjectResponse)
def create_project(req: ProjectCreate, db: Session = Depends(get_db)):
    p_id = req.id or f"proj-{uuid.uuid4().hex[:6]}"
    project = Project(
        id=p_id,
        name=req.name,
        organization=req.organization,
        sector=req.sector,
        jurisdiction=req.jurisdiction,
        data_categories=req.data_categories,
        environment=req.environment,
        cloud_provider=req.cloud_provider,
        aws_region=req.aws_region,
        compliance_score=100.0,
        status="Protected",
        owner=req.owner
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(project)
    db.commit()
    return {"success": True}
