import json
import os
from sqlalchemy.orm import Session
from backend.app.core.database import Base, engine, SessionLocal
from backend.app.core.security import hash_password
from backend.app.db.models import (
    User,
    Regulation,
    RegulatoryRequirement,
    TechnicalControl,
    RequirementControlMapping,
    Project,
    AuditLog
)

SEED_DIR = os.path.join(os.path.dirname(__file__), "seeds")

def init_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # Check if users already seeded
        if db.query(User).count() == 0:
            print("[INFO] Seeding default platform users (admin, operator)...")
            admin_user = User(
                id="usr-admin-01",
                username="admin",
                email="admin@regulacloud.gov.in",
                hashed_password=hash_password("AdminPassword123!"),
                role="ADMIN",
                is_active=True
            )
            op_user = User(
                id="usr-operator-02",
                username="operator",
                email="operator@regulacloud.gov.in",
                hashed_password=hash_password("UserPassword123!"),
                role="USER",
                is_active=True
            )
            db.add(admin_user)
            db.add(op_user)
            db.commit()

        # Check if regulations already seeded
        if db.query(Regulation).count() == 0:
            print("[INFO] Seeding Regulatory Knowledge Base...")
            
            # 1. DPDP Act 2023
            with open(os.path.join(SEED_DIR, "india_dpdp_2023.json"), "r") as f:
                dpdp_data = json.load(f)
                reg = Regulation(**dpdp_data["regulation"])
                db.add(reg)
                db.flush()
                for req_data in dpdp_data["requirements"]:
                    db.add(RegulatoryRequirement(regulation_id=reg.id, **req_data))

            # 2. DPDP Rules 2025
            with open(os.path.join(SEED_DIR, "india_dpdp_rules_2025.json"), "r") as f:
                rules_data = json.load(f)
                reg = Regulation(**rules_data["regulation"])
                db.add(reg)
                db.flush()
                for req_data in rules_data["requirements"]:
                    db.add(RegulatoryRequirement(regulation_id=reg.id, **req_data))

            # 3. CERT-In 2022
            with open(os.path.join(SEED_DIR, "cert_in_2022.json"), "r") as f:
                certin_data = json.load(f)
                reg = Regulation(**certin_data["regulation"])
                db.add(reg)
                db.flush()
                for req_data in certin_data["requirements"]:
                    db.add(RegulatoryRequirement(regulation_id=reg.id, **req_data))

            # 4. Controls & Mappings
            with open(os.path.join(SEED_DIR, "control_mappings.json"), "r") as f:
                mapping_data = json.load(f)
                for ctrl in mapping_data["controls"]:
                    db.add(TechnicalControl(**ctrl))
                db.flush()
                for m in mapping_data["mappings"]:
                    db.add(RequirementControlMapping(**m))

            # 5. Default Projects
            demo_project = Project(
                id="proj-healthcare-india",
                name="Ayushman Digital Health Registry",
                organization="Ministry of Health & Family Welfare",
                sector="Healthcare",
                jurisdiction="India",
                data_categories=["personal_data", "health_data"],
                environment="production",
                cloud_provider="AWS",
                aws_region="ap-south-1",
                compliance_score=94.5,
                status="Protected",
                owner="compliance.officer@mohfw.gov.in"
            )
            edu_project = Project(
                id="proj-education-portal",
                name="National Skills & Student Education Portal",
                organization="Department of Higher Education",
                sector="Education",
                jurisdiction="India",
                data_categories=["personal_data", "child_data"],
                environment="production",
                cloud_provider="AWS",
                aws_region="ap-south-1",
                compliance_score=88.0,
                status="Review",
                owner="admin@education.gov.in"
            )
            db.add(demo_project)
            db.add(edu_project)

            # 6. Initial Audit Log
            AuditLog.create_entry(
                session=db,
                actor="system.provisioner",
                action="INITIALIZE_REGULATORY_KNOWLEDGE_BASE",
                resource_type="KNOWLEDGE_BASE",
                resource_id="CORPUS-INDIA-V1",
                severity="Low",
                details={"seeded_regulations": ["DPDP-ACT-2023", "DPDP-RULES-2025", "CERTIN-DIR-2022"]}
            )
            db.commit()
            print("[SUCCESS] Regulatory Knowledge Base & Control Mappings Seeded Successfully.")
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
