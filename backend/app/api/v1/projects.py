from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
import uuid
import os
import shutil
import zipfile
import re
from pydantic import BaseModel
from backend.app.core.auth import require_user
from backend.app.core.database import get_db
from backend.app.db.models import Project, AuditLog
from backend.app.schemas.projects import ProjectCreate, ProjectUpdate, ProjectResponse
from backend.app.engines.terraform_engine import TerraformEngine
from backend.app.engines.application_remediator import ApplicationRemediator

router = APIRouter(prefix="/projects", tags=["Projects"])

class RemediateRequest(BaseModel):
    action_ids: List[str]

@router.get("", response_model=List[ProjectResponse])
def list_projects(current_user=Depends(require_user), db: Session = Depends(get_db)):
    if current_user.role == "ADMIN":
        return db.query(Project).all()
    else:
        return db.query(Project).filter(Project.owner == current_user.username).all()

@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, current_user=Depends(require_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if current_user.role != "ADMIN" and project.owner != current_user.username:
        raise HTTPException(status_code=403, detail="Forbidden")
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
        owner=req.owner,
        regulatory_scope=req.regulatory_scope or [],
        hcl_content=req.hcl_content
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: str, req: ProjectUpdate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    update_data = req.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(project, field, val)
        
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

UPLOAD_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads", "projects"))

def secure_filename(filename: str) -> str:
    # Basic secure filename implementation
    filename = os.path.basename(filename)
    filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    return filename.strip('_.-')

def extract_safe_zip(zip_path: str, extract_to: str):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for member in zip_ref.namelist():
            # Basic path traversal protection
            if member.startswith("/") or ".." in member:
                continue
            zip_ref.extract(member, extract_to)

@router.post("/{project_id}/upload/infrastructure")
async def upload_infrastructure(
    project_id: str,
    file: UploadFile = File(None),
    hcl_code: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "ADMIN" and project.owner != current_user.username:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to access this project's artifacts.")

    project_dir = os.path.join(UPLOAD_BASE_DIR, project_id, "infrastructure")
    os.makedirs(project_dir, exist_ok=True)

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(project_dir, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if filename.endswith(".zip"):
            extract_safe_zip(file_path, project_dir)
            
            # Read all .tf files for hcl_content if available
            tf_files = []
            for root, _, files in os.walk(project_dir):
                for f in files:
                    if f.endswith(".tf"):
                        tf_files.append(os.path.join(root, f))
            
            if tf_files:
                tf_files.sort()
                hcl_contents = []
                for tf_file in tf_files:
                    with open(tf_file, "r") as tff:
                        hcl_contents.append(tff.read())
                project.hcl_content = "\n\n".join(hcl_contents)
        elif filename.endswith(".tf"):
            with open(file_path, "r") as tff:
                project.hcl_content = tff.read()
        
        project.infrastructure_path = project_dir

    if hcl_code:
        project.hcl_content = hcl_code

    db.commit()
    return {"success": True, "message": "Infrastructure artifacts updated."}

@router.post("/{project_id}/upload/application")
async def upload_application(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "ADMIN" and project.owner != current_user.username:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to access this project's artifacts.")

    filename = secure_filename(file.filename)
    if not filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are supported for application source.")

    project_dir = os.path.join(UPLOAD_BASE_DIR, project_id, "application")
    os.makedirs(project_dir, exist_ok=True)
    
    file_path = os.path.join(project_dir, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    extract_safe_zip(file_path, project_dir)
    
    project.application_source_path = project_dir
    db.commit()
    return {"success": True, "message": "Application source updated."}

@router.get("/{project_id}/hcl")
def get_project_hcl(project_id: str, db: Session = Depends(get_db), current_user=Depends(require_user)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "ADMIN" and project.owner != current_user.username:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to access this project's artifacts.")
    
    return {"hcl_code": project.hcl_content or ""}

@router.post("/{project_id}/remediate")
def remediate_project(
    project_id: str,
    req: RemediateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_user)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "ADMIN" and project.owner != current_user.username:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have permission to access this project's artifacts.")

    if not project.hcl_content:
        raise HTTPException(status_code=400, detail="Project has no HCL content to remediate.")

    new_hcl, tf_applied, tf_skipped = TerraformEngine.apply_rl_actions(project.hcl_content, req.action_ids)
    
    app_action_ids = [a for a in req.action_ids if a not in tf_applied]
    
    if project.application_source_path and app_action_ids:
        app_applied, app_skipped_temp, changed_files = ApplicationRemediator.apply_source_actions(
            project.application_source_path, app_action_ids
        )
        app_skipped = app_skipped_temp
    else:
        app_applied = []
        app_skipped = [f"{a}: No application source path available to patch." for a in app_action_ids if a in ["ACT_UPGRADE_WEAK_CRYPTO", "ACT_PARAMETERIZE_SQL_QUERIES", "ACT_PATCH_SONAR_INJECTION"]]
        changed_files = []

    applied = tf_applied + app_applied
    
    # Merge skipped actions correctly, omitting ones that were eventually applied
    skipped = [s for s in tf_skipped if not any(s.startswith(a) for a in app_applied)]
    for app_s in app_skipped:
        action_id = app_s.split(":")[0]
        if not any(s.startswith(action_id) for s in skipped):
            skipped.append(app_s)
    
    project.hcl_content = new_hcl
    
    AuditLog.create_entry(
        session=db,
        actor=f"user.{current_user.username}",
        action="REMEDIATION_APPLIED",
        resource_type="PROJECT",
        resource_id=project.id,
        severity="Medium",
        details={
            "applied_action_ids": applied,
            "skipped_action_ids": skipped,
            "changed_files": changed_files,
            "remediated_hcl_hash": __import__('hashlib').sha256(new_hcl.encode()).hexdigest() if new_hcl else None
        }
    )
    
    db.commit()
    
    return {
        "project_id": project.id,
        "hcl_code": new_hcl,
        "applied_actions": applied,
        "skipped_actions": skipped,
        "message": "Remediation applied successfully." if applied else "No remediations could be applied."
    }

