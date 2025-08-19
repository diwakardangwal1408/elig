"""
Streamlit UI for Dental Insurance Eligibility Management System
User-friendly interface for EDI analysts
"""

import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any
import io
from dental_eligibility_agent import DentalEligibilityAgent
import time

# Page Configuration
st.set_page_config(
    page_title="Dental Eligibility Manager",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []

if 'current_batch' not in st.session_state:
    st.session_state.current_batch = []

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"

class UIManager:
    def __init__(self):
        self.agent = None
    
    def initialize_agent(self, api_key: str):
        """Initialize the LLM agent"""
        try:
            self.agent = DentalEligibilityAgent(api_key)
            return True
        except Exception as e:
            st.error(f"Failed to initialize agent: {e}")
            return False
    
    def make_api_request(self, endpoint: str, method: str = "GET", data: Dict = None):
        """Make API request to backend"""
        try:
            url = f"{API_BASE_URL}{endpoint}"
            
            if method == "GET":
                response = requests.get(url)
            elif method == "POST":
                response = requests.post(url, json=data)
            elif method == "PUT":
                response = requests.put(url, json=data)
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {e}")
            return None

ui_manager = UIManager()

def main():
    # Header
    st.markdown('<h1 class="main-header">🦷 Dental Insurance Eligibility Manager</h1>', unsafe_allow_html=True)
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Key Input
        api_key = st.text_input("OpenAI API Key", type="password", help="Required for LLM parsing")
        
        if api_key:
            if ui_manager.initialize_agent(api_key):
                st.success("✅ Agent initialized")
            else:
                st.error("❌ Agent initialization failed")
        
        st.divider()
        
        # Navigation
        st.header("📋 Navigation")
        selected_page = st.selectbox(
            "Select Function",
            ["Dashboard", "Data Upload", "Batch Processing", "Member Search", "Analytics", "Settings"]
        )
    
    # Main Content Area
    if selected_page == "Dashboard":
        show_dashboard()
    elif selected_page == "Data Upload":
        show_data_upload()
    elif selected_page == "Batch Processing":
        show_batch_processing()
    elif selected_page == "Member Search":
        show_member_search()
    elif selected_page == "Analytics":
        show_analytics()
    elif selected_page == "Settings":
        show_settings()

def show_dashboard():
    """Dashboard with key metrics and recent activity"""
    st.header("📊 Dashboard")
    
    # Metrics Row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Members", "12,458", "+234")
    
    with col2:
        st.metric("Processed Today", "89", "+12")
    
    with col3:
        st.metric("Success Rate", "96.2%", "+1.1%")
    
    with col4:
        st.metric("Avg Processing Time", "2.3s", "-0.4s")
    
    st.divider()
    
    # Recent Activity
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Recent Processing Activity")
        
        # Sample data for demonstration
        recent_activity = pd.DataFrame({
            'Timestamp': [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                (datetime.now().replace(hour=datetime.now().hour-1)).strftime("%Y-%m-%d %H:%M:%S"),
                (datetime.now().replace(hour=datetime.now().hour-2)).strftime("%Y-%m-%d %H:%M:%S")
            ],
            'Source': ['Email', 'Excel Upload', 'Manual Entry'],
            'Records': [15, 47, 3],
            'Status': ['✅ Completed', '⏳ Processing', '✅ Completed']
        })
        
        st.dataframe(recent_activity, use_container_width=True)
    
    with col2:
        st.subheader("📈 Processing Stats")
        
        # Processing status chart
        status_data = pd.DataFrame({
            'Status': ['Completed', 'Processing', 'Failed'],
            'Count': [156, 12, 8]
        })
        
        fig = px.pie(status_data, values='Count', names='Status', 
                    color_discrete_map={'Completed': '#28a745', 'Processing': '#ffc107', 'Failed': '#dc3545'})
        st.plotly_chart(fig, use_container_width=True)

def show_data_upload():
    """Data upload and parsing interface"""
    st.header("📤 Data Upload & Parsing")
    
    if not ui_manager.agent:
        st.warning("⚠️ Please configure OpenAI API key in the sidebar first.")
        return
    
    tab1, tab2, tab3 = st.tabs(["📧 Email Content", "📊 Excel Upload", "✍️ Manual Entry"])
    
    with tab1:
        st.subheader("Email Content Parsing")
        
        email_content = st.text_area(
            "Paste email content here:",
            height=200,
            placeholder="Paste the email content containing eligibility updates..."
        )
        
        if st.button("🔍 Parse Email", type="primary"):
            if email_content:
                with st.spinner("Parsing email content..."):
                    try:
                        updates = ui_manager.agent.parse_email_content(email_content)
                        enriched_data = ui_manager.agent.validate_and_enrich_data(updates)
                        
                        st.success(f"✅ Successfully parsed {len(updates)} eligibility updates")
                        
                        # Display parsed results
                        for i, update in enumerate(updates):
                            with st.expander(f"Update {i+1}: {update.member_id or 'Unknown Member'}"):
                                st.json(update.dict())
                        
                        # Store in session state for batch processing
                        st.session_state.current_batch.extend(enriched_data)
                        
                    except Exception as e:
                        st.error(f"❌ Parsing failed: {e}")
    
    with tab2:
        st.subheader("Excel File Upload")
        
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="Upload Excel file containing eligibility updates"
        )
        
        if uploaded_file:
            st.info(f"📁 File uploaded: {uploaded_file.name}")
            
            if st.button("🔍 Parse Excel", type="primary"):
                with st.spinner("Parsing Excel file..."):
                    try:
                        # Save uploaded file temporarily
                        temp_path = f"temp_{uploaded_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        
                        updates = ui_manager.agent.parse_excel_file(temp_path)
                        enriched_data = ui_manager.agent.validate_and_enrich_data(updates)
                        
                        st.success(f"✅ Successfully parsed {len(updates)} eligibility updates")
                        
                        # Preview data
                        if updates:
                            df = pd.DataFrame([update.dict() for update in updates])
                            st.dataframe(df, use_container_width=True)
                        
                        # Store in session state
                        st.session_state.current_batch.extend(enriched_data)
                        
                        # Clean up temp file
                        import os
                        os.remove(temp_path)
                        
                    except Exception as e:
                        st.error(f"❌ Parsing failed: {e}")
    
    with tab3:
        st.subheader("Manual Entry")
        
        with st.form("manual_entry"):
            col1, col2 = st.columns(2)
            
            with col1:
                member_id = st.text_input("Member ID")
                policy_number = st.text_input("Policy Number")
                benefit_type = st.selectbox("Benefit Type", 
                    ["preventive", "basic", "major", "orthodontic", "emergency"])
                coverage_percentage = st.number_input("Coverage %", 0.0, 100.0, step=0.1)
            
            with col2:
                annual_maximum = st.number_input("Annual Maximum $", 0.0, step=100.0)
                deductible = st.number_input("Deductible $", 0.0, step=50.0)
                waiting_period = st.number_input("Waiting Period (days)", 0, step=30)
                effective_date = st.date_input("Effective Date")
            
            provider_network = st.selectbox("Provider Network", ["in-network", "out-of-network", "both"])
            procedure_codes = st.text_input("Procedure Codes (comma-separated)", 
                placeholder="D0120, D1110, D2140")
            
            if st.form_submit_button("➕ Add Entry", type="primary"):
                entry = {
                    "member_id": member_id,
                    "policy_number": policy_number,
                    "benefit_type": benefit_type,
                    "coverage_percentage": coverage_percentage,
                    "annual_maximum": annual_maximum,
                    "deductible": deductible,
                    "waiting_period": waiting_period,
                    "effective_date": effective_date.isoformat(),
                    "provider_network": provider_network,
                    "procedure_codes": [code.strip() for code in procedure_codes.split(",") if code.strip()]
                }
                
                st.session_state.current_batch.append({
                    "raw_data": entry,
                    "validation_status": "valid",
                    "validation_errors": [],
                    "enriched_fields": {},
                    "processing_timestamp": datetime.now().isoformat()
                })
                
                st.success("✅ Entry added to current batch")

def show_batch_processing():
    """Batch processing and review interface"""
    st.header("⚡ Batch Processing")
    
    if not st.session_state.current_batch:
        st.info("📝 No items in current batch. Upload data first.")
        return
    
    st.subheader(f"📋 Current Batch ({len(st.session_state.current_batch)} items)")
    
    # Validation Summary
    valid_count = sum(1 for item in st.session_state.current_batch if item["validation_status"] == "valid")
    invalid_count = len(st.session_state.current_batch) - valid_count
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Items", len(st.session_state.current_batch))
    with col2:
        st.metric("Valid", valid_count, delta=None, delta_color="normal")
    with col3:
        st.metric("Invalid", invalid_count, delta=None, delta_color="inverse")
    
    # Batch Review
    if st.checkbox("🔍 Review Batch Items"):
        for i, item in enumerate(st.session_state.current_batch):
            with st.expander(f"Item {i+1}: {item['raw_data'].get('member_id', 'Unknown')} - {item['validation_status']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Raw Data")
                    st.json(item["raw_data"])
                
                with col2:
                    st.subheader("Validation")
                    if item["validation_status"] == "valid":
                        st.success("✅ Valid")
                    else:
                        st.error("❌ Invalid")
                        for error in item["validation_errors"]:
                            st.error(f"• {error}")
    
    st.divider()
    
    # Processing Actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Process Valid Items", type="primary", disabled=valid_count == 0):
            process_batch(valid_only=True)
    
    with col2:
        if st.button("🔧 Process All Items", disabled=len(st.session_state.current_batch) == 0):
            process_batch(valid_only=False)
    
    with col3:
        if st.button("🗑️ Clear Batch", type="secondary"):
            st.session_state.current_batch = []
            st.rerun()

def process_batch(valid_only: bool = True):
    """Process the current batch"""
    items_to_process = st.session_state.current_batch
    
    if valid_only:
        items_to_process = [item for item in items_to_process if item["validation_status"] == "valid"]
    
    if not items_to_process:
        st.warning("No items to process")
        return
    
    # Convert to API format
    updates = []
    for item in items_to_process:
        raw_data = item["raw_data"]
        updates.append({
            "member_id": raw_data.get("member_id"),
            "policy_number": raw_data.get("policy_number"),
            "benefit_type": raw_data.get("benefit_type"),
            "coverage_percentage": raw_data.get("coverage_percentage"),
            "annual_maximum": raw_data.get("annual_maximum"),
            "deductible": raw_data.get("deductible"),
            "waiting_period": raw_data.get("waiting_period"),
            "effective_date": raw_data.get("effective_date"),
            "expiration_date": raw_data.get("expiration_date"),
            "provider_network": raw_data.get("provider_network"),
            "procedure_codes": raw_data.get("procedure_codes", []),
            "source": "ui_batch"
        })
    
    # Make API request
    with st.spinner(f"Processing {len(updates)} items..."):
        result = ui_manager.make_api_request(
            "/eligibility/bulk-update",
            method="POST",
            data={"updates": updates}
        )
        
        if result:
            st.success(f"✅ Batch submitted successfully! Request ID: {result['request_id']}")
            
            # Add to processing history
            st.session_state.processing_history.append({
                "timestamp": datetime.now(),
                "request_id": result["request_id"],
                "item_count": len(updates),
                "status": "submitted"
            })
            
            # Clear current batch
            st.session_state.current_batch = []
            st.rerun()
        else:
            st.error("❌ Failed to submit batch")

def show_member_search():
    """Member eligibility search interface"""
    st.header("🔍 Member Search")
    
    # Search Form
    with st.form("search_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            member_id = st.text_input("Member ID")
        with col2:
            policy_number = st.text_input("Policy Number")
        with col3:
            benefit_type = st.selectbox("Benefit Type", 
                ["", "preventive", "basic", "major", "orthodontic", "emergency"])
        
        search_clicked = st.form_submit_button("🔍 Search", type="primary")
    
    if search_clicked:
        # Build search parameters
        params = {}
        if member_id:
            params["member_id"] = member_id
        if policy_number:
            params["policy_number"] = policy_number
        if benefit_type:
            params["benefit_type"] = benefit_type
        
        # Make search request
        with st.spinner("Searching..."):
            result = ui_manager.make_api_request("/eligibility/search", method="GET")
            
            if result and result.get("records"):
                st.success(f"Found {result['total']} records")
                
                # Display results
                records_df = pd.DataFrame([
                    {
                        "Member ID": record.get("member_id"),
                        "Policy": record.get("policy_number"),
                        "Benefit Type": record.get("benefit_type"),
                        "Coverage %": record.get("coverage_percentage"),
                        "Annual Max": record.get("annual_maximum"),
                        "Effective Date": record.get("effective_date"),
                        "Status": record.get("processing_status")
                    }
                    for record in result["records"]
                ])
                
                st.dataframe(records_df, use_container_width=True)
            else:
                st.info("No records found")

def show_analytics():
    """Analytics and reporting interface"""
    st.header("📈 Analytics & Reports")
    
    # Sample analytics data
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Processing Volume")
        
        # Sample time series data
        dates = pd.date_range(start="2024-01-01", end="2024-01-31", freq="D")
        volume_data = pd.DataFrame({
            "Date": dates,
            "Processed": [abs(int(x)) for x in (50 + 20 * pd.Series(range(len(dates))).apply(lambda x: (x % 7) - 3.5))]
        })
        
        fig = px.line(volume_data, x="Date", y="Processed", title="Daily Processing Volume")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Benefit Type Distribution")
        
        benefit_data = pd.DataFrame({
            "Benefit Type": ["Preventive", "Basic", "Major", "Orthodontic", "Emergency"],
            "Count": [450, 320, 180, 90, 45]
        })
        
        fig = px.bar(benefit_data, x="Benefit Type", y="Count", title="Eligibility Updates by Benefit Type")
        st.plotly_chart(fig, use_container_width=True)
    
    # Processing History
    st.subheader("📋 Processing History")
    
    if st.session_state.processing_history:
        history_df = pd.DataFrame(st.session_state.processing_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No processing history available")

def show_settings():
    """Settings and configuration interface"""
    st.header("⚙️ Settings")
    
    tab1, tab2, tab3 = st.tabs(["🔧 API Configuration", "🎯 Processing Rules", "📊 Export Settings"])
    
    with tab1:
        st.subheader("API Configuration")
        
        api_url = st.text_input("Backend API URL", value="http://localhost:8000")
        timeout = st.number_input("Request Timeout (seconds)", 5, 300, value=30)
        retry_attempts = st.number_input("Retry Attempts", 1, 10, value=3)
        
        if st.button("💾 Save API Settings"):
            st.success("Settings saved!")
    
    with tab2:
        st.subheader("Processing Rules")
        
        auto_process_valid = st.checkbox("Auto-process valid items", value=True)
        require_manual_review = st.checkbox("Require manual review for high-value claims")
        max_batch_size = st.number_input("Maximum batch size", 1, 1000, value=100)
        
        if st.button("💾 Save Processing Rules"):
            st.success("Rules saved!")
    
    with tab3:
        st.subheader("Export Settings")
        
        export_format = st.selectbox("Default export format", ["CSV", "Excel", "JSON"])
        include_metadata = st.checkbox("Include processing metadata", value=True)
        
        if st.button("💾 Save Export Settings"):
            st.success("Export settings saved!")

if __name__ == "__main__":
    main()