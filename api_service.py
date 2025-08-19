"""
API Service for Dental Insurance Eligibility System
Handles HTTP requests and database persistence
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import asyncio
from datetime import datetime
import json
import logging
from celery import Celery
import os

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dental_eligibility")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Celery Configuration
celery_app = Celery(
    "dental_eligibility",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)

# Database Models
class EligibilityRecord(Base):
    __tablename__ = "eligibility_records"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(String, index=True)
    policy_number = Column(String, index=True)
    benefit_type = Column(String)
    coverage_percentage = Column(Float)
    annual_maximum = Column(Float)
    deductible = Column(Float)
    waiting_period = Column(Integer)
    effective_date = Column(DateTime)
    expiration_date = Column(DateTime)
    provider_network = Column(String)
    procedure_codes = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String)  # email, excel, manual
    processing_status = Column(String, default="pending")  # pending, processed, failed

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String, unique=True, index=True)
    input_data = Column(JSON)
    output_data = Column(JSON)
    processing_status = Column(String)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float)  # seconds

# Pydantic Models
class EligibilityUpdateRequest(BaseModel):
    member_id: Optional[str]
    policy_number: Optional[str]
    benefit_type: str
    coverage_percentage: Optional[float]
    annual_maximum: Optional[float]
    deductible: Optional[float]
    waiting_period: Optional[int]
    effective_date: Optional[str]
    expiration_date: Optional[str]
    provider_network: Optional[str]
    procedure_codes: Optional[List[str]]
    source: str = "api"

class BulkUpdateRequest(BaseModel):
    updates: List[EligibilityUpdateRequest]
    batch_id: Optional[str]

class ProcessingStatus(BaseModel):
    request_id: str
    status: str
    processed_count: int
    failed_count: int
    errors: List[str]

# FastAPI App
app = FastAPI(
    title="Dental Insurance Eligibility API",
    description="API for managing dental insurance eligibility updates",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
Base.metadata.create_all(bind=engine)

class ExternalAPIClient:
    """Client for making requests to external insurance systems"""
    
    def __init__(self):
        self.base_url = os.getenv("INSURANCE_API_URL", "https://api.insurance-provider.com")
        self.api_key = os.getenv("INSURANCE_API_KEY", "")
        self.timeout = 30
    
    async def update_eligibility(self, member_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update eligibility in external system"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "member_id": member_id,
                "updates": updates,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            try:
                response = await client.post(
                    f"{self.base_url}/eligibility/update",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPError as e:
                logging.error(f"API request failed: {e}")
                raise HTTPException(status_code=500, detail=f"External API error: {str(e)}")

# Celery Tasks
@celery_app.task
def process_bulk_updates(updates_data: List[Dict], request_id: str):
    """Background task for processing bulk eligibility updates"""
    db = SessionLocal()
    api_client = ExternalAPIClient()
    
    processed_count = 0
    failed_count = 0
    errors = []
    
    try:
        for update_data in updates_data:
            try:
                # Save to database
                db_record = EligibilityRecord(**update_data)
                db.add(db_record)
                db.commit()
                
                # Call external API
                if update_data.get("member_id"):
                    result = asyncio.run(api_client.update_eligibility(
                        update_data["member_id"], 
                        update_data
                    ))
                    
                    # Update processing status
                    db_record.processing_status = "processed"
                    db.commit()
                    processed_count += 1
                
            except Exception as e:
                failed_count += 1
                errors.append(f"Member {update_data.get('member_id', 'unknown')}: {str(e)}")
                logging.error(f"Failed to process update for member {update_data.get('member_id')}: {e}")
        
        # Log processing results
        log_entry = ProcessingLog(
            request_id=request_id,
            input_data=updates_data,
            processing_status="completed" if failed_count == 0 else "partial",
            error_message="; ".join(errors) if errors else None
        )
        db.add(log_entry)
        db.commit()
        
    except Exception as e:
        logging.error(f"Bulk processing failed: {e}")
        log_entry = ProcessingLog(
            request_id=request_id,
            input_data=updates_data,
            processing_status="failed",
            error_message=str(e)
        )
        db.add(log_entry)
        db.commit()
    
    finally:
        db.close()
    
    return {
        "processed_count": processed_count,
        "failed_count": failed_count,
        "errors": errors
    }

# API Endpoints
@app.post("/api/v1/eligibility/update")
async def update_single_eligibility(
    update: EligibilityUpdateRequest, 
    db: Session = Depends(get_db)
):
    """Update single member eligibility"""
    try:
        # Convert effective_date string to datetime if provided
        update_dict = update.dict()
        if update_dict.get("effective_date"):
            update_dict["effective_date"] = datetime.fromisoformat(update_dict["effective_date"])
        if update_dict.get("expiration_date"):
            update_dict["expiration_date"] = datetime.fromisoformat(update_dict["expiration_date"])
        
        # Save to database
        db_record = EligibilityRecord(**update_dict)
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        # Call external API
        api_client = ExternalAPIClient()
        if update.member_id:
            await api_client.update_eligibility(update.member_id, update_dict)
            db_record.processing_status = "processed"
            db.commit()
        
        return {"status": "success", "record_id": db_record.id}
        
    except Exception as e:
        logging.error(f"Failed to update eligibility: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/eligibility/bulk-update")
async def bulk_update_eligibility(
    request: BulkUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process bulk eligibility updates asynchronously"""
    import uuid
    request_id = str(uuid.uuid4())
    
    # Convert updates to dict format
    updates_data = []
    for update in request.updates:
        update_dict = update.dict()
        if update_dict.get("effective_date"):
            update_dict["effective_date"] = datetime.fromisoformat(update_dict["effective_date"])
        if update_dict.get("expiration_date"):
            update_dict["expiration_date"] = datetime.fromisoformat(update_dict["expiration_date"])
        updates_data.append(update_dict)
    
    # Start background processing
    process_bulk_updates.delay(updates_data, request_id)
    
    return {
        "status": "accepted", 
        "request_id": request_id,
        "message": f"Processing {len(request.updates)} updates in background"
    }

@app.get("/api/v1/eligibility/status/{request_id}")
async def get_processing_status(request_id: str, db: Session = Depends(get_db)):
    """Get processing status for bulk update request"""
    log_entry = db.query(ProcessingLog).filter(ProcessingLog.request_id == request_id).first()
    
    if not log_entry:
        raise HTTPException(status_code=404, detail="Request not found")
    
    return {
        "request_id": request_id,
        "status": log_entry.processing_status,
        "created_at": log_entry.created_at,
        "error_message": log_entry.error_message
    }

@app.get("/api/v1/eligibility/member/{member_id}")
async def get_member_eligibility(member_id: str, db: Session = Depends(get_db)):
    """Get current eligibility for a member"""
    records = db.query(EligibilityRecord).filter(
        EligibilityRecord.member_id == member_id
    ).order_by(EligibilityRecord.created_at.desc()).all()
    
    if not records:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"member_id": member_id, "eligibility_records": records}

@app.get("/api/v1/eligibility/search")
async def search_eligibility(
    member_id: Optional[str] = None,
    policy_number: Optional[str] = None,
    benefit_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Search eligibility records"""
    query = db.query(EligibilityRecord)
    
    if member_id:
        query = query.filter(EligibilityRecord.member_id == member_id)
    if policy_number:
        query = query.filter(EligibilityRecord.policy_number == policy_number)
    if benefit_type:
        query = query.filter(EligibilityRecord.benefit_type == benefit_type)
    
    records = query.offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)