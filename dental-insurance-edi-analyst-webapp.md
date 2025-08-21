name: "DentaCorrect - Dental Insurance EDI Analyst Web Application"
description: |

# DentaCorrect - Dental Insurance EDI Analyst Web Application

## Goal
Create a comprehensive Flask-based web application for EDI (Electronic Data Interchange) analysts working with US healthcare dental insurance data. The application must provide file upload capabilities, member search functionality, and an interactive chat interface with history and predefined shortcuts for common analytical tasks.

## Why
- **Business Value**: Streamline EDI analyst workflows for processing adhoc member data requests, reducing manual processing time by 60%
- **User Impact**: Enable analysts to quickly upload member data files, search existing records, and interact with data through conversational interface
- **Integration Needs**: Support existing EDI transaction standards (270/271, 834) and healthcare data formats
- **Problem Solving**: Replace manual Excel analysis with automated web-based tools for faster turnaround on member eligibility updates

## What
A Flask web application with three core modules:
1. **File Upload Module**: Accept and process email attachments or Excel files containing member data
2. **Search Module**: Query member records by member ID or product ID with flexible search patterns  
3. **Interactive Chat Module**: Real-time chat interface with conversation history and analytical shortcuts

### Success Criteria
- [ ] Successfully upload and parse Excel files with member data (target: 10,000+ records in <30 seconds)
- [ ] Search members by ID with sub-second response times
- [ ] Real-time chat with persistent history and 5+ predefined analytical shortcuts
- [ ] Secure handling of PHI (Protected Health Information) with basic HIPAA considerations
- [ ] Responsive web interface accessible on desktop and tablet devices

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://flask.palletsprojects.com/en/stable/
  why: Official Flask documentation for web framework patterns
  
- url: https://flask-sqlalchemy.readthedocs.io/en/stable/quickstart/
  why: Modern SQLAlchemy patterns and database integration
  
- url: https://flask-socketio.readthedocs.io/en/latest/
  why: Real-time WebSocket implementation for chat functionality
  
- url: https://pandas.pydata.org/docs/user_guide/io.html#excel-files
  why: Excel file processing patterns and error handling
  
- url: https://www.geeksforgeeks.org/upload-and-read-excel-file-in-flask/
  why: Flask Excel upload implementation tutorial
  
- url: https://medium.com/@adrianhuber17/how-to-build-a-simple-real-time-application-using-flask-react-and-socket-io-7ec2ce2da977
  why: Real-time Flask chat application patterns
  
- url: https://www.invene.com/blog/demystifying-healthcare-edi-the-9-critical-transactions-explained
  why: EDI transaction types (270/271, 834) for healthcare context

- file: use-cases/pydantic-ai/examples/basic_chat_agent/agent.py
  why: Pattern for environment configuration and settings management
  
- file: PRPs/templates/prp_base.md
  why: Standard validation patterns and error handling approaches

- doc: https://docs.python.org/3/library/sqlite3.html
  section: Database connection and query patterns
  critical: Use parameterized queries to prevent SQL injection with healthcare data
```

### Current Codebase Tree
```bash
C:\Claude_Projects\DentaCorrect\
├── CLAUDE.md                 # Global project rules
├── INITIAL.md                # Feature requirements
├── PRPs/                     # This PRP location
├── README.md                 # Project documentation
└── use-cases/               # Reference patterns
    ├── pydantic-ai/examples/basic_chat_agent/agent.py  # Settings pattern
    └── template patterns for project structure
```

### Desired Codebase Tree with New Files
```bash
C:\Claude_Projects\DentaCorrect\
├── app/                      # Main Flask application
│   ├── __init__.py          # Flask app factory
│   ├── models.py            # SQLAlchemy models for Member, Product, ChatHistory
│   ├── routes/              # Blueprint modules
│   │   ├── __init__.py     
│   │   ├── upload.py       # File upload and processing routes
│   │   ├── search.py       # Member search functionality
│   │   └── chat.py         # Chat interface routes
│   ├── static/             # CSS, JS, uploaded files
│   │   ├── css/
│   │   ├── js/
│   │   └── uploads/        # Temporary file storage
│   ├── templates/          # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── upload.html
│   │   ├── search.html
│   │   └── chat.html
│   └── utils/              # Helper functions
│       ├── __init__.py
│       ├── excel_processor.py  # Excel parsing and validation
│       ├── search_engine.py    # Search logic and optimization
│       └── chat_handlers.py    # SocketIO event handlers
├── tests/                   # Pytest test suite
│   ├── __init__.py
│   ├── conftest.py         # Test configuration
│   ├── test_upload.py      # File upload tests
│   ├── test_search.py      # Search functionality tests
│   └── test_chat.py        # Chat interface tests
├── requirements.txt         # Python dependencies
├── .env.example            # Environment variables template
├── config.py               # Application configuration
└── run.py                  # Application entry point
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Flask-SocketIO requires specific async handling
# Example: Flask-SocketIO uses threading model, not asyncio
from flask_socketio import SocketIO, emit, join_room, leave_room

# CRITICAL: Pandas Excel reading requires openpyxl for .xlsx files
# Must install: pip install openpyxl xlrd for Excel support
import pandas as pd
df = pd.read_excel(file, engine='openpyxl')  # Specify engine for .xlsx

# CRITICAL: SQLAlchemy modern patterns (avoid legacy Model.query)
# Use: db.session.execute(db.select(Member).filter_by(member_id=id)).scalar_one()
# Not: Member.query.filter_by(member_id=id).first()

# CRITICAL: Healthcare data requires parameterized queries ALWAYS
# Use: db.session.execute(text("SELECT * FROM members WHERE id = :id"), {"id": user_input})
# Never: f"SELECT * FROM members WHERE id = {user_input}"

# CRITICAL: File upload security - validate file extensions and size
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB limit

# CRITICAL: Flask-SocketIO requires eventlet for production
# Development: socketio.run(app, debug=True)
# Production: Must use eventlet or gevent
```

## Implementation Blueprint

### Data Models and Structure

Create healthcare-compliant data models with proper validation and indexing.

```python
# Core models following EDI healthcare standards
class Member(db.Model):
    """Member record following EDI 834 enrollment standards"""
    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    subscriber_id = db.Column(db.String(50), index=True)  # Primary insurance holder
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date)
    product_id = db.Column(db.String(20), db.ForeignKey('product.product_id'), index=True)
    eligibility_start = db.Column(db.Date)
    eligibility_end = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Product(db.Model):
    """Insurance product following EDI benefit structure"""
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    coverage_type = db.Column(db.String(50))  # Medical, Dental, Vision
    payer_id = db.Column(db.String(50))  # EDI Payer identifier
    members = db.relationship('Member', backref='product', lazy='dynamic')

class ChatHistory(db.Model):
    """Chat conversation persistence with analyst context"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    analyst_id = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text)
    message_type = db.Column(db.String(20))  # 'user', 'system', 'shortcut'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

### List of Tasks to Complete the PRP Implementation

```yaml
Task 1: Project Setup and Environment
CREATE project structure with virtual environment:
  - SETUP: python -m venv venv_linux && source venv_linux/bin/activate
  - INSTALL: pip install flask flask-sqlalchemy flask-socketio pandas openpyxl python-dotenv pytest
  - CREATE: requirements.txt with all dependencies
  - CREATE: .env.example with database and secret key templates
  - CREATE: config.py with environment-based configuration classes

Task 2: Flask Application Factory and Database Setup
CREATE app/__init__.py:
  - IMPLEMENT: Flask app factory pattern with blueprints registration
  - INTEGRATE: SQLAlchemy with Flask-Migrate for database migrations
  - CONFIGURE: Flask-SocketIO with CORS and session management
  - SETUP: Error handlers for 404, 500, and file upload errors

Task 3: Database Models Implementation
CREATE app/models.py:
  - IMPLEMENT: Member model with healthcare data validation
  - IMPLEMENT: Product model with EDI-compliant fields
  - IMPLEMENT: ChatHistory model with session tracking
  - ADD: Database indexes for search performance optimization
  - CREATE: Database migration scripts for initial schema

Task 4: Excel File Upload and Processing Module
CREATE app/routes/upload.py AND app/utils/excel_processor.py:
  - IMPLEMENT: Secure file upload with extension and size validation
  - IMPLEMENT: Excel parsing using pandas with error handling
  - IMPLEMENT: Data validation against Member model schema
  - IMPLEMENT: Batch database insertion with transaction management
  - HANDLE: Duplicate member detection and update strategies

Task 5: Member Search Engine
CREATE app/routes/search.py AND app/utils/search_engine.py:
  - IMPLEMENT: Multi-field search (member_id, subscriber_id, product_id)
  - IMPLEMENT: Flexible search patterns (exact, partial, wildcard)
  - IMPLEMENT: Search result pagination for large datasets
  - OPTIMIZE: Database queries with proper indexing
  - ADD: Search analytics and performance monitoring

Task 6: Real-time Chat Interface
CREATE app/routes/chat.py AND app/utils/chat_handlers.py:
  - IMPLEMENT: Flask-SocketIO event handlers for messaging
  - IMPLEMENT: Session-based chat rooms for analysts
  - IMPLEMENT: Message persistence to ChatHistory model
  - CREATE: Predefined shortcuts for common analytical queries
  - HANDLE: Connection management and error recovery

Task 7: Frontend Templates and User Interface
CREATE app/templates/ directory with responsive HTML:
  - CREATE: base.html with Bootstrap integration and navigation
  - CREATE: upload.html with drag-drop file interface and progress bars
  - CREATE: search.html with advanced search forms and result tables
  - CREATE: chat.html with real-time messaging and shortcut buttons
  - ADD: JavaScript for SocketIO client and dynamic interactions

Task 8: Static Assets and Client-Side Logic
CREATE app/static/ directory structure:
  - ADD: CSS for custom styling and responsive design
  - CREATE: JavaScript modules for file upload, search, and chat
  - IMPLEMENT: Real-time updates and user feedback mechanisms
  - OPTIMIZE: Asset loading and performance

Task 9: Configuration and Security Hardening
MODIFY config.py AND create security measures:
  - IMPLEMENT: Environment-based configuration (dev, test, prod)
  - ADD: Secret key management and session security
  - IMPLEMENT: File upload security and validation
  - ADD: Basic CSRF protection for forms
  - CONFIGURE: Database connection security

Task 10: Comprehensive Testing Suite
CREATE tests/ directory with pytest coverage:
  - CREATE: conftest.py with test database fixtures
  - IMPLEMENT: Unit tests for models and utility functions
  - IMPLEMENT: Integration tests for file upload workflows
  - IMPLEMENT: SocketIO client tests for chat functionality
  - ADD: Performance tests for large file processing

Task 11: Application Entry Point and Deployment Prep
CREATE run.py and deployment configuration:
  - IMPLEMENT: Application startup with proper error handling
  - ADD: Database initialization and migration commands
  - CONFIGURE: Production-ready SocketIO settings
  - CREATE: Docker configuration files (optional)
  - ADD: Logging configuration for monitoring
```

### Per-Task Pseudocode and Critical Implementation Details

```python
# Task 4: Excel Processing Implementation
def process_excel_file(file_path: str) -> Dict[str, Any]:
    """
    Process uploaded Excel file following healthcare data standards
    
    CRITICAL: Must validate data format before database insertion
    PATTERN: Use pandas chunking for large files (see GeeksforGeeks tutorial)
    """
    try:
        # SECURITY: Validate file extension and size first
        if not validate_file_security(file_path):
            raise ValidationError("Invalid file format or size")
        
        # GOTCHA: Must specify engine for .xlsx files
        df = pd.read_excel(file_path, engine='openpyxl')
        
        # VALIDATION: Check required columns match Member model
        required_columns = ['member_id', 'first_name', 'last_name', 'product_id']
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise ValidationError(f"Missing columns: {missing_cols}")
        
        # PROCESSING: Clean and validate data
        processed_records = []
        for index, row in df.iterrows():
            # PATTERN: Validate each record against Pydantic schema
            member_data = validate_member_record(row.to_dict())
            processed_records.append(member_data)
        
        # DATABASE: Batch insertion with transaction management
        with db.session.begin():
            db.session.bulk_insert_mappings(Member, processed_records)
            
        return {
            'status': 'success',
            'records_processed': len(processed_records),
            'file_name': file_path
        }
        
    except Exception as e:
        # LOGGING: Log errors for analyst troubleshooting
        logger.error(f"Excel processing failed: {str(e)}")
        raise ProcessingError(f"File processing failed: {str(e)}")

# Task 6: Real-time Chat Implementation  
@socketio.on('send_message')
def handle_message(data: Dict[str, str]) -> None:
    """
    Handle chat messages with shortcut processing
    
    PATTERN: Follow Flask-SocketIO event handling (see Medium tutorial)
    CRITICAL: Save all messages to database for audit trail
    """
    try:
        session_id = data.get('session_id')
        message = data.get('message', '').strip()
        analyst_id = data.get('analyst_id')
        
        # SHORTCUT: Process predefined analytical shortcuts
        if message.startswith('/'):
            response = process_analytical_shortcut(message, session_id)
            message_type = 'shortcut'
        else:
            # FUTURE: Integration point for AI analysis
            response = f"Processed: {message}"
            message_type = 'user'
        
        # PERSISTENCE: Save conversation to database
        chat_record = ChatHistory(
            session_id=session_id,
            analyst_id=analyst_id,
            message=message,
            response=response,
            message_type=message_type
        )
        db.session.add(chat_record)
        db.session.commit()
        
        # BROADCAST: Send response to client
        emit('message_response', {
            'message': message,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'type': message_type
        }, room=session_id)
        
    except Exception as e:
        logger.error(f"Chat message handling failed: {str(e)}")
        emit('error', {'message': 'Message processing failed'}, room=session_id)
```

### Integration Points
```yaml
DATABASE:
  - migration: "Create members, products, chat_history tables with proper indexes"
  - indexes: "CREATE INDEX idx_member_search ON members(member_id, subscriber_id, product_id)"
  
CONFIG:
  - add to: config.py
  - pattern: "SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')"
  - database: "SQLALCHEMY_DATABASE_URI for SQLite (dev) and PostgreSQL (prod)"
  
ROUTES:
  - add to: app/__init__.py
  - pattern: "app.register_blueprint(upload_bp, url_prefix='/upload')"
  - websocket: "socketio.init_app(app, cors_allowed_origins='*')"
  
SECURITY:
  - validation: "Implement file type checking and size limits"
  - healthcare: "Basic PHI handling with secure sessions"
  - sql: "Use parameterized queries exclusively"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
source venv_linux/bin/activate  # Use virtual environment
pip install ruff mypy           # Install linting tools

ruff check app/ tests/ --fix    # Auto-fix code style issues
mypy app/                       # Type checking for main application code

# Expected: No errors. If errors exist, read and fix each one.
```

### Level 2: Unit Tests for Each Module
```python
# CREATE comprehensive test suite covering all components
# Following pytest patterns from existing codebase

def test_excel_processing_valid_file():
    """Test successful Excel file processing"""
    # Setup test file with valid member data
    test_data = create_test_excel_file()
    
    result = process_excel_file(test_data.name)
    
    assert result['status'] == 'success'
    assert result['records_processed'] > 0
    assert Member.query.count() > 0

def test_member_search_by_id():
    """Test member search functionality"""
    # Setup test member in database
    test_member = Member(member_id='TEST123', first_name='John', last_name='Doe')
    db.session.add(test_member)
    db.session.commit()
    
    results = search_members('TEST123')
    
    assert len(results) == 1
    assert results[0].member_id == 'TEST123'

def test_chat_message_persistence():
    """Test chat message saving and retrieval"""
    # Setup test chat session
    session_id = 'test-session-123'
    
    handle_message({
        'session_id': session_id,
        'message': 'Analyze trends in data',
        'analyst_id': 'analyst001'
    })
    
    chat_history = ChatHistory.query.filter_by(session_id=session_id).all()
    assert len(chat_history) == 1
    assert chat_history[0].message == 'Analyze trends in data'
```

```bash
# Run and iterate until all tests pass:
source venv_linux/bin/activate
pytest tests/ -v --cov=app --cov-report=html

# Expected: All tests pass with >80% code coverage
# If failing: Read error messages, understand root cause, fix code, re-run
```

### Level 3: Integration Testing
```bash
# Start the development server
source venv_linux/bin/activate
python run.py

# Test file upload workflow
curl -X POST http://localhost:5000/upload \
  -F "file=@test_data/sample_members.xlsx" \
  -H "Content-Type: multipart/form-data"

# Expected: {"status": "success", "records_processed": N}

# Test member search endpoint  
curl "http://localhost:5000/search?member_id=TEST123"

# Expected: JSON array with member details

# Test chat interface (manual browser testing required for SocketIO)
# Navigate to: http://localhost:5000/chat
# Send test message and verify real-time response
```

## Final Validation Checklist
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No linting errors: `ruff check app/ tests/`
- [ ] No type errors: `mypy app/`
- [ ] File upload works with sample Excel file
- [ ] Member search returns accurate results
- [ ] Chat interface sends/receives messages in real-time
- [ ] Database queries use parameterized statements
- [ ] Error handling covers file processing failures
- [ ] Chat history persists across sessions
- [ ] Bootstrap UI is responsive on mobile/desktop

---

## Anti-Patterns to Avoid
- ❌ Don't use f-strings for database queries - always use parameterized queries
- ❌ Don't process large Excel files synchronously - implement progress feedback
- ❌ Don't ignore file upload security - validate extensions, size, and content
- ❌ Don't use Flask development server for SocketIO in production
- ❌ Don't store sensitive healthcare data in logs or error messages
- ❌ Don't skip database transactions for batch operations
- ❌ Don't hardcode analytical shortcuts - make them configurable
- ❌ Don't forget to handle SocketIO connection failures gracefully

---

## PRP Quality Assessment

**Confidence Score: 7/10**

**Strengths:**
- ✅ Comprehensive external research with specific URLs and tutorials
- ✅ Healthcare domain context with EDI standards knowledge  
- ✅ Detailed implementation blueprint with 11 structured tasks
- ✅ Security considerations appropriate for healthcare data
- ✅ Multi-level validation gates with executable commands
- ✅ Real-world patterns from established Flask tutorials
- ✅ Complete technology stack decision with rationale

**Risk Factors:**
- ⚠️ Complex multi-feature application requiring Flask + SocketIO + Pandas integration
- ⚠️ Healthcare compliance requirements may need additional security measures
- ⚠️ Real-time chat features add deployment complexity
- ⚠️ Large Excel file processing may require performance optimization

**Mitigation Strategies Included:**
- Comprehensive testing at unit, integration, and manual levels
- Specific gotchas documented for each major library
- Security patterns for healthcare data handling
- Performance considerations for large dataset processing

This PRP provides sufficient context and validation loops for an experienced developer to implement the complete application in a single focused session, with clear fallback strategies if issues arise during implementation.