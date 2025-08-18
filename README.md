# Survey Summarization Prompt Generator

*This project is a fork of the original Survey Scoring Prompt Generator, adapted to focus on generating summarization instructions rather than classification scoring. The core architecture and workflow structure have been preserved while repurposing the functionality for summarization use cases.*

A comprehensive Flask web application for generating and iterating on AI prompts used to create summaries of survey responses. This tool enables users to create intelligent summarization systems through an intuitive multi-step workflow, with built-in prompt optimization based on user feedback.

## Overview

The Survey Summarization Prompt Generator streamlines the process of creating AI-powered survey summarization systems. It guides users through data selection, summarization criteria definition, summary type generation, and prompt refinement, ultimately producing optimized prompts for consistent and comprehensive survey response summarization.

## Key Features

### Core Functionality
- **Multi-step Guided Workflow**: 7-step process from data selection to final results
- **Intelligent Prompt Generation**: LLM-powered prompt creation based on summarization criteria
- **Batch Processing**: Efficient summarization of multiple survey responses simultaneously
- **Custom Data Upload**: Support for JSON and CSV file formats with intelligent column detection
- **Interactive Feedback Collection**: Streamlined interface for reviewing and refining AI-generated summaries

### Advanced Features
- **Prompt Iteration Engine**: Automatically refines prompts based on user corrections
- **Feedback Pattern Analysis**: Identifies common summarization issues for targeted improvements
- **Intelligent Diff Display**: Word-level comparison showing exact prompt changes with semantic summaries
- **Session Management**: File-based storage system preventing data loss from session limitations
- **Responsive Design**: Optimized for desktop and mobile devices

## System Requirements

### Dependencies
- Python 3.7+
- Flask 2.3.3
- boto3 1.34.144 (for AWS Bedrock integration)
- Additional dependencies listed in `requirements.txt`

### External Services
- AWS Bedrock with Claude model access
- Valid AWS credentials configured

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd summary_prompt_gen_ux
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure AWS credentials:
```bash
aws configure
# or set environment variables:
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

5. Run the application:
```bash
./run.sh
# or manually:
python app_frontend.py
```

6. Access the application at `http://localhost:5000`

## Quick Start

### Command Options
```bash
# Production mode (clean UI)
./run.sh

# Development mode (with debug elements)  
./run.sh --dev_mode
./run.sh --dev

# Show help
./run.sh --help
```

## Usage Guide

### Step-by-Step Workflow

**Step 1: Data Selection**
- Choose from pre-built survey examples or upload custom data
- Supported formats: JSON arrays or CSV files with column selection
- Automatic data cleaning and random sampling (15 responses with fixed seed)

**Step 1.5: Data Preview**
- Review sample responses from selected dataset
- Verify data quality before proceeding

**Step 2: Summarization Criteria**
- Define what aspects you want to summarize in 1-3 sentences
- System uses this to generate relevant summary types and focus areas

**Step 3: Summary Type Generation**
- Review AI-generated summary type categories
- Edit summary type names and descriptions as needed
- Typically generates summary types: Key Themes, Sentiment Overview, Specific Issues, General Feedback

**Step 4: Prompt Review**
- Examine the generated expert-level summarization prompt
- Make manual adjustments if necessary
- Prompt optimized for batch processing consistency

**Step 5: Inference Processing**
- Automatic batch summarization of all survey responses
- Real-time progress tracking with completion status

**Step 6: Feedback Collection**
- Review AI-generated summaries in compact interface
- Mark satisfactory summaries or provide corrections
- Optional feedback text for detailed explanations

**Step 7: Results and Iteration**
- View comprehensive results with summary breakdowns
- Option to iterate on prompt based on feedback patterns
- Start new session or refine current prompt

**Step 7.5: Prompt Analysis (Optional)**
- Intelligent analysis of feedback patterns
- Side-by-side comparison of original and improved prompts
- Semantic summary of conceptual improvements
- Word-level diff highlighting exact changes

### Data Format Requirements

**JSON Format:**
```json
[
  {"text": "Response text here"},
  {"response": "Alternative field name"},
  {"comment": "Another supported field"}
]
```

**CSV Format:**
- Any CSV file with text columns
- Interactive column selection interface
- Automatic detection of likely response columns

## Configuration

### Environment Variables
- `AWS_ACCESS_KEY_ID`: AWS access key for Bedrock
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_DEFAULT_REGION`: AWS region (default: us-east-1)
- `FLASK_ENV`: Set to 'development' for debug mode

### File Locations
- `examples/`: Pre-built survey data files (JSON format)
- `uploads/`: Temporary storage for uploaded files
- `temp_results/`: Session data and inference results
- `static/`: CSS, JavaScript, and other static assets
- `templates/`: HTML templates

## Architecture

### Backend Components
- **Flask Application**: Main web framework and routing
- **Session Management**: File-based storage to prevent cookie size limits
- **LLM Integration**: AWS Bedrock Claude model for prompt generation and refinement
- **Data Processing**: Built-in CSV/JSON parsing with intelligent field detection
- **Batch Summarization**: Optimized single-call processing for multiple responses

### Frontend Components
- **Responsive UI**: Mobile-friendly interface with Bootstrap-inspired styling
- **Interactive Elements**: Dynamic form handling and progress tracking
- **Drag-and-Drop Upload**: File upload with progress indicators
- **Real-time Feedback**: AJAX-powered interactions without page reloads

### Key Files
- `app_frontend.py`: Flask application with web routes and UI logic
- `app_backend.py`: Core business logic and LLM integration (framework-agnostic)
- `app_terminal.py`: Terminal interface using the same backend
- `run.sh`: Startup script with development mode support
- `templates/index.html`: Single-page application template
- `static/app.js`: Client-side JavaScript functionality  
- `static/style.css`: Comprehensive styling and responsive design

## API Endpoints

### Main Routes
- `GET /`: Landing page and Step 1
- `GET /step/<float:step_num>`: Navigate to specific workflow step
- `POST /process_step`: Handle form submissions between steps
- `POST /run_inference`: Execute batch summarization
- `POST /submit_feedback`: Process user corrections

### Upload Routes
- `POST /upload_data`: Handle file uploads with validation
- `POST /process_csv`: Process CSV column selection

### Iteration Routes
- `POST /iterate_prompt`: Analyze feedback and generate improved prompt
- `POST /approve_iteration`: Apply prompt changes and continue workflow
- `POST /reject_iteration`: Discard changes and return to results

## Security Considerations

- **File Upload Security**: Secure filename handling and type validation
- **Data Sanitization**: HTML escaping and input validation
- **Session Security**: File-based storage with unique session identifiers
- **AWS Security**: Proper credential management and least-privilege access

## Development

### Project Structure
```
summary_prompt_gen_ux/
├── app_frontend.py        # Flask web interface
├── app_backend.py         # Core business logic (framework-agnostic)
├── app_terminal.py        # Terminal interface
├── run.sh                 # Startup script with dev_mode support
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── static/               # Static assets
│   ├── app.js           # JavaScript functionality
│   └── style.css        # Styling and responsive design
├── templates/           # HTML templates
│   └── index.html       # Main application template
├── examples/            # Sample survey data
├── uploads/             # Temporary file storage
└── temp_results/        # Session and results storage
```

### Adding New Features
1. **Backend logic**: Core functionality in `app_backend.py` (framework-agnostic)
2. **Web interface**: Routes and web logic in `app_frontend.py` 
3. **Templates**: UI structure in `templates/index.html`
4. **Styling**: Visual design in `static/style.css`
5. **Client behavior**: Interactive features in `static/app.js`
6. **Development elements**: Use `{% if dev_mode %}` for debug/dev-only features

### Testing
- Manual testing through web interface
- Verify all workflow steps complete successfully
- Test with various data formats and sizes
- Validate prompt iteration functionality

## Troubleshooting

### Common Issues

**AWS Credential Errors**
- Verify AWS credentials are properly configured
- Ensure Bedrock access permissions are granted
- Check regional availability of Claude models

**File Upload Issues**
- Confirm file size is under 10MB limit
- Verify file format is JSON or CSV
- Check upload directory permissions

**Session Data Loss**
- Clear browser cache if experiencing persistent issues
- Ensure `temp_results/` directory is writable
- Check disk space availability

**Performance Issues**
- Large datasets may require increased timeout settings
- Consider reducing sample size for testing
- Monitor AWS API rate limits

### Development vs Production Mode

The application supports two operational modes controlled via command-line arguments:

#### Development Mode (`dev_mode`)
Enable development mode to show additional debug elements, developer tools, and diagnostic information in the UI:

```bash
# Enable development mode
./run.sh --dev_mode
# or short form:
./run.sh --dev

# View available options
./run.sh --help
```

**What Development Mode Includes:**
- Debug information panels showing session data, step information, and internal state
- Developer tools and debug buttons for testing and troubleshooting  
- Enhanced error messages with detailed technical information
- Session and workflow state visibility
- Internal diagnostic displays

#### Production Mode (Default)
Run without the development flag for a clean, user-focused interface:

```bash
# Production mode (default)
./run.sh
```

**Production Mode Features:**
- Clean, streamlined user interface
- Professional appearance without debug elements
- Optimized for end-user experience
- No internal technical information displayed

#### Customizing Development Elements

To add your own development-only elements to the UI, use the `dev_mode` variable in templates:

```html
<!-- Only show in development mode -->
{% if dev_mode %}
<div class="debug-panel">
    <h4>🔧 Development Info</h4>
    <p>Current Step: {{ step }}</p>
    <p>Session ID: {{ session.session_id if session else 'N/A' }}</p>
    <button onclick="console.log('Debug data:', {step: {{ step }}, dev_mode: {{ dev_mode }}})">
        Log Debug Info
    </button>
</div>
{% endif %}

<!-- Show different content based on mode -->
{% if dev_mode %}
<div class="dev-controls">
    <button onclick="localStorage.clear()">Clear Storage</button>
    <button onclick="window.location.href='/step/1'">Reset Workflow</button>
</div>
{% else %}
<div class="user-help">
    <p>Having trouble? Contact support for assistance.</p>
</div>
{% endif %}

<!-- Conditional styling -->
{% if dev_mode %}
<style>
.container {
    border: 2px dashed #007bff;
}
.container::before {
    content: "🔧 DEVELOPMENT MODE";
    background: #007bff;
    color: white;
    padding: 2px 8px;
    font-size: 12px;
    position: fixed;
    top: 0;
    right: 0;
    z-index: 1000;
}
</style>
{% endif %}
```

#### Development Workflow

**For Developers:**
1. Use `./run.sh --dev_mode` during development and testing
2. Add debug elements using `{% if dev_mode %}` conditionals in templates
3. Test with both modes to ensure production UI remains clean

**For End Users:**
1. Use `./run.sh` (without flags) for normal operation
2. Clean interface without technical details
3. Optimized user experience

#### Technical Implementation

The `dev_mode` system works by:
1. **Command-line argument**: `./run.sh --dev_mode` sets `DEV_MODE=true` environment variable
2. **Backend reading**: `app_frontend.py` reads the environment variable on startup
3. **Template passing**: All `render_template()` calls include `dev_mode=True/False`
4. **Template usage**: HTML templates use `{% if dev_mode %}` to conditionally show elements

This approach allows for:
- **Single codebase**: Same application code for both modes
- **Easy toggling**: Simple command-line flag to switch modes
- **Template flexibility**: Any UI element can be made development-only
- **Clean separation**: Production users never see debug elements

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with appropriate testing
4. Submit a pull request with detailed description

## License

This project is proprietary software. All rights reserved.

## Support

For technical support or feature requests, please contact the development team or submit an issue through the appropriate channels.