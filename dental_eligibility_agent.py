"""
Dental Insurance Eligibility Parsing Agent
Handles semi-structured data parsing using LLM for healthcare eligibility updates
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from langchain.schema import HumanMessage, SystemMessage
from langchain.chat_models import ChatOpenAI
import pandas as pd
import json
import re
from datetime import datetime
from enum import Enum

class BenefitType(str, Enum):
    PREVENTIVE = "preventive"
    BASIC = "basic"
    MAJOR = "major"
    ORTHODONTIC = "orthodontic"
    EMERGENCY = "emergency"

class EligibilityUpdate(BaseModel):
    member_id: Optional[str] = Field(description="Member identification number")
    policy_number: Optional[str] = Field(description="Insurance policy number")
    benefit_type: BenefitType = Field(description="Type of dental benefit")
    coverage_percentage: Optional[float] = Field(description="Percentage of coverage (0-100)")
    annual_maximum: Optional[float] = Field(description="Annual maximum benefit amount")
    deductible: Optional[float] = Field(description="Annual deductible amount")
    waiting_period: Optional[int] = Field(description="Waiting period in days")
    effective_date: Optional[str] = Field(description="Effective date in YYYY-MM-DD format")
    expiration_date: Optional[str] = Field(description="Expiration date in YYYY-MM-DD format")
    provider_network: Optional[str] = Field(description="In-network or out-of-network")
    procedure_codes: Optional[List[str]] = Field(description="List of applicable CDT procedure codes")

class DentalEligibilityAgent:
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.1,
            openai_api_key=openai_api_key
        )
        
        self.system_prompt = """
        You are an expert EDI analyst specializing in dental insurance eligibility parsing.
        Your task is to extract structured eligibility information from semi-structured data.
        
        Key Information to Extract:
        - Member/Policy identification
        - Benefit types (preventive, basic, major, orthodontic, emergency)
        - Coverage percentages and limits
        - Deductibles and maximums
        - Effective/expiration dates
        - Waiting periods
        - Provider network restrictions
        - Applicable procedure codes (CDT codes)
        
        Return data in valid JSON format matching the EligibilityUpdate schema.
        If information is unclear or missing, use null values.
        """

    def parse_email_content(self, email_content: str) -> List[EligibilityUpdate]:
        """Parse eligibility updates from email content"""
        try:
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"""
                Parse the following email content for dental insurance eligibility updates:
                
                {email_content}
                
                Extract all eligibility updates and return as a JSON array of objects.
                """)
            ]
            
            response = self.llm(messages)
            parsed_data = json.loads(response.content)
            
            updates = []
            for item in parsed_data:
                updates.append(EligibilityUpdate(**item))
            
            return updates
            
        except Exception as e:
            print(f"Error parsing email content: {e}")
            return []

    def parse_excel_file(self, excel_path: str) -> List[EligibilityUpdate]:
        """Parse eligibility updates from Excel file"""
        try:
            df = pd.read_excel(excel_path)
            excel_content = df.to_string()
            
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"""
                Parse the following Excel data for dental insurance eligibility updates:
                
                {excel_content}
                
                Extract all eligibility updates and return as a JSON array of objects.
                """)
            ]
            
            response = self.llm(messages)
            parsed_data = json.loads(response.content)
            
            updates = []
            for item in parsed_data:
                updates.append(EligibilityUpdate(**item))
            
            return updates
            
        except Exception as e:
            print(f"Error parsing Excel file: {e}")
            return []

    def validate_and_enrich_data(self, updates: List[EligibilityUpdate]) -> List[Dict[str, Any]]:
        """Validate and enrich parsed eligibility data"""
        enriched_updates = []
        
        for update in updates:
            enriched_data = {
                "raw_data": update.dict(),
                "validation_status": "valid",
                "validation_errors": [],
                "enriched_fields": {},
                "processing_timestamp": datetime.now().isoformat()
            }
            
            # Validation rules
            if update.coverage_percentage and (update.coverage_percentage < 0 or update.coverage_percentage > 100):
                enriched_data["validation_errors"].append("Invalid coverage percentage")
                enriched_data["validation_status"] = "invalid"
            
            if update.effective_date:
                try:
                    datetime.strptime(update.effective_date, "%Y-%m-%d")
                except ValueError:
                    enriched_data["validation_errors"].append("Invalid effective date format")
                    enriched_data["validation_status"] = "invalid"
            
            # Enrichment - normalize procedure codes
            if update.procedure_codes:
                normalized_codes = []
                for code in update.procedure_codes:
                    # Remove any non-alphanumeric characters and convert to uppercase
                    clean_code = re.sub(r'[^A-Za-z0-9]', '', code).upper()
                    if len(clean_code) >= 4:  # CDT codes are typically 4-5 characters
                        normalized_codes.append(clean_code)
                
                enriched_data["enriched_fields"]["normalized_procedure_codes"] = normalized_codes
            
            enriched_updates.append(enriched_data)
        
        return enriched_updates

    def create_api_requests(self, enriched_updates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert enriched data to API request format"""
        api_requests = []
        
        for update_data in enriched_updates:
            if update_data["validation_status"] != "valid":
                continue
            
            raw_data = update_data["raw_data"]
            
            # Create API request payload
            api_request = {
                "endpoint": "/api/v1/eligibility/update",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer {token}",  # To be replaced with actual token
                    "X-Request-Source": "automated-agent"
                },
                "payload": {
                    "member_id": raw_data.get("member_id"),
                    "policy_number": raw_data.get("policy_number"),
                    "benefit_updates": [
                        {
                            "benefit_type": raw_data.get("benefit_type"),
                            "coverage_percentage": raw_data.get("coverage_percentage"),
                            "annual_maximum": raw_data.get("annual_maximum"),
                            "deductible": raw_data.get("deductible"),
                            "waiting_period": raw_data.get("waiting_period"),
                            "effective_date": raw_data.get("effective_date"),
                            "expiration_date": raw_data.get("expiration_date"),
                            "provider_network": raw_data.get("provider_network"),
                            "procedure_codes": update_data["enriched_fields"].get(
                                "normalized_procedure_codes", 
                                raw_data.get("procedure_codes", [])
                            )
                        }
                    ]
                },
                "metadata": {
                    "processing_timestamp": update_data["processing_timestamp"],
                    "agent_version": "1.0.0",
                    "data_source": "email_or_excel"
                }
            }
            
            api_requests.append(api_request)
        
        return api_requests

# Example usage and testing
if __name__ == "__main__":
    # Initialize agent
    agent = DentalEligibilityAgent(openai_api_key="your-openai-api-key")
    
    # Sample email content for testing
    sample_email = """
    Subject: Dental Benefit Updates - Q4 2024
    
    Dear EDI Team,
    
    Please process the following dental insurance eligibility updates:
    
    Member ID: 12345678
    Policy: DEN-2024-001
    Benefit Type: Preventive Care
    Coverage: 100% in-network
    Annual Max: $1,500
    Effective: January 1, 2025
    
    Member ID: 87654321
    Policy: DEN-2024-002
    Benefit Type: Basic Services
    Coverage: 80% in-network, 60% out-of-network
    Deductible: $50
    Annual Max: $2,000
    Waiting Period: 6 months
    Effective: February 1, 2025
    
    Best regards,
    Insurance Provider
    """
    
    # Parse and process
    updates = agent.parse_email_content(sample_email)
    enriched_data = agent.validate_and_enrich_data(updates)
    api_requests = agent.create_api_requests(enriched_data)
    
    print("Generated API Requests:")
    for req in api_requests:
        print(json.dumps(req, indent=2))