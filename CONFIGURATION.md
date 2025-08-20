# Configuration Guide

## API Key Configuration

The OpenAI API key configuration has been moved from the UI to environment variables for better security and configuration management.

### Setup Instructions

1. **Copy the template file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file:**
   ```bash
   # Required: Add your OpenAI API key
   OPENAI_API_KEY=sk-your-actual-openai-api-key-here
   
   # Optional: Customize other settings
   API_BASE_URL=http://localhost:8000/api/v1
   API_TIMEOUT=30
   RETRY_ATTEMPTS=3
   ```

3. **Restart the application:**
   ```bash
   # Stop the current Streamlit session (Ctrl+C)
   # Then restart:
   python -m streamlit run streamlit_ui.py --server.port 8502
   ```

### Configuration Validation

The application will automatically validate your configuration:

- ✅ **Green status**: API key configured and agent initialized successfully
- ⚠️ **Yellow warning**: API key found but agent initialization failed
- ❌ **Red error**: API key not found in environment variables

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | OpenAI API key for LLM processing | - | ✅ Yes |
| `API_BASE_URL` | Backend API endpoint | http://localhost:8000/api/v1 | No |
| `API_TIMEOUT` | Request timeout in seconds | 30 | No |
| `RETRY_ATTEMPTS` | Number of retry attempts for failed requests | 3 | No |
| `MAX_BATCH_SIZE` | Maximum items per batch | 100 | No |
| `AUTO_PROCESS_VALID` | Auto-process valid items | true | No |
| `REQUIRE_MANUAL_REVIEW` | Require manual review | false | No |

### Security Benefits

Moving API key configuration to environment variables provides:

- 🔒 **Security**: API keys are not exposed in the UI or stored in session state
- 🔄 **Consistency**: Same configuration across all application restarts
- 🛡️ **Best Practices**: Following standard environment-based configuration
- 📝 **Audit Trail**: Configuration changes are tracked via environment management

### Troubleshooting

**API Key Not Found:**
- Check that `.env` file exists in the project root
- Verify `OPENAI_API_KEY` is set in the `.env` file
- Ensure no extra spaces around the `=` sign
- Restart the Streamlit application after making changes

**Agent Initialization Failed:**
- Verify the API key is valid and has sufficient credits
- Check internet connectivity
- Review any error messages in the sidebar

**Configuration Not Loading:**
- Ensure `python-dotenv` is installed: `pip install python-dotenv`
- Check file permissions on the `.env` file
- Verify the `.env` file is in the same directory as `streamlit_ui.py`

### Getting Your OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and add it to your `.env` file

**Note**: Keep your API key secure and never commit it to version control. The `.env` file should be added to your `.gitignore` file.