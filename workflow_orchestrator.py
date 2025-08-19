"""
Workflow Orchestrator for Dental Insurance Eligibility System
Manages the complete workflow from data ingestion to API persistence
"""

from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio
import logging
from datetime import datetime
import json
import uuid
from dataclasses import dataclass, asdict
from celery import Celery
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from dental_eligibility_agent import DentalEligibilityAgent, EligibilityUpdate
import httpx
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"

class DataSource(str, Enum):
    EMAIL = "email"
    EXCEL = "excel"
    MANUAL = "manual"
    API = "api"

@dataclass
class WorkflowJob:
    job_id: str
    source: DataSource
    input_data: Any
    status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
    results: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None

@dataclass
class ProcessingMetrics:
    total_records: int
    processed_successfully: int
    validation_failures: int
    api_failures: int
    processing_time_seconds: float
    started_at: datetime
    completed_at: Optional[datetime] = None

class NotificationService:
    """Service for sending notifications to EDI analysts"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
    
    async def send_completion_notification(self, job: WorkflowJob, metrics: ProcessingMetrics):
        """Send email notification when processing completes"""
        try:
            subject = f"Eligibility Processing Complete - Job {job.job_id[:8]}"
            
            html_body = f"""
            <html>
            <body>
                <h2>Dental Eligibility Processing Complete</h2>
                
                <h3>Job Summary</h3>
                <ul>
                    <li><strong>Job ID:</strong> {job.job_id}</li>
                    <li><strong>Source:</strong> {job.source}</li>
                    <li><strong>Status:</strong> {job.status}</li>
                    <li><strong>Started:</strong> {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}</li>
                    <li><strong>Duration:</strong> {metrics.processing_time_seconds:.2f} seconds</li>
                </ul>
                
                <h3>Processing Results</h3>
                <ul>
                    <li><strong>Total Records:</strong> {metrics.total_records}</li>
                    <li><strong>Successfully Processed:</strong> {metrics.processed_successfully}</li>
                    <li><strong>Validation Failures:</strong> {metrics.validation_failures}</li>
                    <li><strong>API Failures:</strong> {metrics.api_failures}</li>
                    <li><strong>Success Rate:</strong> {(metrics.processed_successfully/metrics.total_records*100):.1f}%</li>
                </ul>
                
                {self._format_errors_html(job.errors) if job.errors else ""}
                
                <p><em>This is an automated notification from the Dental Eligibility Management System.</em></p>
            </body>
            </html>
            """
            
            await self._send_email(subject, html_body)
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
    
    def _format_errors_html(self, errors: List[str]) -> str:
        """Format errors for HTML email"""
        if not errors:
            return ""
        
        error_list = "\n".join([f"<li>{error}</li>" for error in errors[:10]])  # Limit to first 10 errors
        
        return f"""
        <h3>Processing Errors</h3>
        <ul style="color: #dc3545;">
            {error_list}
        </ul>
        {f"<p><em>... and {len(errors) - 10} more errors</em></p>" if len(errors) > 10 else ""}
        """
    
    async def _send_email(self, subject: str, html_body: str):
        """Send email using SMTP"""
        try:
            msg = MimeMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_user
            msg['To'] = os.getenv("NOTIFICATION_EMAIL", "edi-team@company.com")
            
            html_part = MimeText(html_body, 'html')
            msg.attach(html_part)
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Notification email sent: {subject}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

class WorkflowOrchestrator:
    """Main orchestrator for the eligibility processing workflow"""
    
    def __init__(self, openai_api_key: str):
        self.agent = DentalEligibilityAgent(openai_api_key)
        self.notification_service = NotificationService()
        self.jobs: Dict[str, WorkflowJob] = {}
        self.api_client = self._create_api_client()
    
    def _create_api_client(self) -> httpx.AsyncClient:
        """Create HTTP client for API calls"""
        return httpx.AsyncClient(
            base_url=os.getenv("API_BASE_URL", "http://localhost:8000"),
            timeout=30.0,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "EligibilityOrchestrator/1.0"
            }
        )
    
    async def submit_job(self, source: DataSource, input_data: Any, metadata: Dict[str, Any] = None) -> str:
        """Submit a new processing job"""
        job_id = str(uuid.uuid4())
        
        job = WorkflowJob(
            job_id=job_id,
            source=source,
            input_data=input_data,
            status=WorkflowStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {}
        )
        
        self.jobs[job_id] = job
        
        # Start processing asynchronously
        asyncio.create_task(self._process_job(job))
        
        logger.info(f"Job {job_id} submitted for processing")
        return job_id
    
    async def _process_job(self, job: WorkflowJob):
        """Process a single job through the complete workflow"""
        start_time = datetime.now()
        
        try:
            # Update job status
            job.status = WorkflowStatus.PROCESSING
            job.updated_at = datetime.now()
            
            logger.info(f"Starting processing for job {job.job_id}")
            
            # Step 1: Parse input data
            parsed_updates = await self._parse_input_data(job)
            
            if not parsed_updates:
                raise ValueError("No valid data could be parsed from input")
            
            # Step 2: Validate and enrich data
            enriched_data = self.agent.validate_and_enrich_data(parsed_updates)
            
            # Step 3: Create API requests
            api_requests = self.agent.create_api_requests(enriched_data)
            
            # Step 4: Execute API requests
            results = await self._execute_api_requests(api_requests)
            
            # Step 5: Calculate metrics and update job
            metrics = self._calculate_metrics(enriched_data, results, start_time)
            job.results = {
                "metrics": asdict(metrics),
                "api_results": results,
                "enriched_data_count": len(enriched_data)
            }
            
            # Determine final status
            if metrics.api_failures == 0:
                job.status = WorkflowStatus.COMPLETED
            elif metrics.processed_successfully > 0:
                job.status = WorkflowStatus.PARTIAL
            else:
                job.status = WorkflowStatus.FAILED
            
            job.updated_at = datetime.now()
            
            # Send notification
            await self.notification_service.send_completion_notification(job, metrics)
            
            logger.info(f"Job {job.job_id} completed with status {job.status}")
            
        except Exception as e:
            job.status = WorkflowStatus.FAILED
            job.errors = job.errors or []
            job.errors.append(f"Processing failed: {str(e)}")
            job.updated_at = datetime.now()
            
            logger.error(f"Job {job.job_id} failed: {e}")
            
            # Still send notification for failures
            metrics = ProcessingMetrics(
                total_records=0,
                processed_successfully=0,
                validation_failures=0,
                api_failures=1,
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                started_at=start_time,
                completed_at=datetime.now()
            )
            
            await self.notification_service.send_completion_notification(job, metrics)
    
    async def _parse_input_data(self, job: WorkflowJob) -> List[EligibilityUpdate]:
        """Parse input data based on source type"""
        try:
            if job.source == DataSource.EMAIL:
                return self.agent.parse_email_content(job.input_data)
            
            elif job.source == DataSource.EXCEL:
                # For Excel, input_data should be the file path
                return self.agent.parse_excel_file(job.input_data)
            
            elif job.source == DataSource.MANUAL:
                # For manual input, data is already structured
                return [EligibilityUpdate(**job.input_data)]
            
            elif job.source == DataSource.API:
                # For API input, convert list of dicts to EligibilityUpdate objects
                return [EligibilityUpdate(**item) for item in job.input_data]
            
            else:
                raise ValueError(f"Unsupported data source: {job.source}")
                
        except Exception as e:
            logger.error(f"Failed to parse input data for job {job.job_id}: {e}")
            job.errors = job.errors or []
            job.errors.append(f"Data parsing failed: {str(e)}")
            return []
    
    async def _execute_api_requests(self, api_requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute API requests with proper error handling and retries"""
        results = []
        
        for i, request in enumerate(api_requests):
            try:
                # Extract request details
                endpoint = request["endpoint"]
                method = request["method"]
                payload = request["payload"]
                
                # Make API call
                if method == "POST":
                    response = await self.api_client.post(endpoint, json=payload)
                elif method == "PUT":
                    response = await self.api_client.put(endpoint, json=payload)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                response.raise_for_status()
                
                results.append({
                    "request_index": i,
                    "status": "success",
                    "response_data": response.json(),
                    "http_status": response.status_code
                })
                
            except httpx.HTTPError as e:
                logger.error(f"API request {i} failed: {e}")
                results.append({
                    "request_index": i,
                    "status": "failed",
                    "error": str(e),
                    "http_status": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                })
            
            except Exception as e:
                logger.error(f"Unexpected error in API request {i}: {e}")
                results.append({
                    "request_index": i,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _calculate_metrics(self, enriched_data: List[Dict[str, Any]], 
                          api_results: List[Dict[str, Any]], start_time: datetime) -> ProcessingMetrics:
        """Calculate processing metrics"""
        total_records = len(enriched_data)
        validation_failures = sum(1 for item in enriched_data if item["validation_status"] != "valid")
        
        successful_api_calls = sum(1 for result in api_results if result["status"] == "success")
        api_failures = len(api_results) - successful_api_calls
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return ProcessingMetrics(
            total_records=total_records,
            processed_successfully=successful_api_calls,
            validation_failures=validation_failures,
            api_failures=api_failures,
            processing_time_seconds=processing_time,
            started_at=start_time,
            completed_at=datetime.now()
        )
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a job"""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        return {
            "job_id": job.job_id,
            "source": job.source,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "metadata": job.metadata,
            "results": job.results,
            "errors": job.errors
        }
    
    def get_all_jobs(self, status_filter: Optional[WorkflowStatus] = None) -> List[Dict[str, Any]]:
        """Get all jobs, optionally filtered by status"""
        jobs = self.jobs.values()
        
        if status_filter:
            jobs = [job for job in jobs if job.status == status_filter]
        
        return [self.get_job_status(job.job_id) for job in jobs]
    
    async def retry_failed_job(self, job_id: str) -> bool:
        """Retry a failed job"""
        job = self.jobs.get(job_id)
        if not job or job.status != WorkflowStatus.FAILED:
            return False
        
        # Reset job status and clear errors
        job.status = WorkflowStatus.PENDING
        job.errors = []
        job.results = None
        job.updated_at = datetime.now()
        
        # Start processing again
        asyncio.create_task(self._process_job(job))
        
        logger.info(f"Retrying failed job {job_id}")
        return True

# Example usage and testing
async def main():
    """Example usage of the workflow orchestrator"""
    
    # Initialize orchestrator
    orchestrator = WorkflowOrchestrator(openai_api_key="your-openai-api-key")
    
    # Example: Submit email processing job
    sample_email = """
    Subject: Dental Benefit Updates
    
    Member ID: 12345678
    Policy: DEN-2024-001
    Benefit Type: Preventive Care
    Coverage: 100% in-network
    Annual Max: $1,500
    Effective: January 1, 2025
    """
    
    job_id = await orchestrator.submit_job(
        source=DataSource.EMAIL,
        input_data=sample_email,
        metadata={"email_subject": "Dental Benefit Updates", "analyst": "john.doe@company.com"}
    )
    
    print(f"Submitted job: {job_id}")
    
    # Wait for processing to complete
    await asyncio.sleep(5)
    
    # Check job status
    status = orchestrator.get_job_status(job_id)
    print(f"Job status: {json.dumps(status, indent=2, default=str)}")

if __name__ == "__main__":
    asyncio.run(main())