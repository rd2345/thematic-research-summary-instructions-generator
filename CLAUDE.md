# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

*This project is a fork of the original Survey Scoring Prompt Generator, repurposed to focus on summarization instructions rather than classification scoring.*

This project is an interface for generating and iterating prompts that provide instructions for creating comprehensive summaries of survey responses. The goal is to create a user-friendly system that helps users craft and refine prompts used by LLMs to summarize survey data effectively.

## Project Structure

```
summary_prompt_gen_ux/
├── reference_materials/
│   ├── llm_call_example.py      # Empty placeholder file  
│   └── llm_claude_example.py    # AWS Bedrock + Claude integration reference
```

## Core Functionality

The main purpose is to build an interface that allows users to:
- Generate prompts for survey response summarization
- **AI-powered summary type generation** - Automatically create relevant summary categories based on summarization criteria
- Iterate and refine those prompts based on results
- Test prompts against sample survey data
- Optimize prompt effectiveness for consistent, comprehensive summarization

## LLM Integration Reference

The `reference_materials/llm_claude_example.py` shows how to integrate with Claude via AWS Bedrock:
- AWS Bedrock runtime client setup for `us-east-1` region
- Claude 3.5 Sonnet inference profile usage
- Proper API request structure with anthropic_version and message format
- Response handling and text extraction

## Dependencies

Current reference dependencies:
- `boto3` for AWS Bedrock integration
- `pandas` for data handling
- Standard Python libraries (`math`, `json`, `random`, `textwrap`)

## Development Commands

### Setup
```bash
# Create virtual environment (first time only)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Option 1: Use startup script
./run.sh

# Option 2: Manual startup
source venv/bin/activate
python app.py
```

The application will be available at http://localhost:5000

### Development Status

- Flask web application with 7-step workflow implemented
- **Smart summary type generation** - Uses LLM to generate contextually relevant summary categories
- Virtual environment setup with all dependencies
- Three sample survey datasets included
- End-to-end functionality complete with user feedback integration

## 7-Step Workflow Overview

The application guides users through a systematic 7-step process to create, test, and refine prompts for summarizing survey responses.

**Linear Workflow:**
1. **Step 1:** Select Survey Example → Choose from available datasets
2. **Step 2:** Summarization Description → Define summarization criteria  
3. **Step 3:** Generate Summary Types → AI-powered summary categories
4. **Step 4:** Review Prompt → AI-generated expert summarization prompt
5. **Step 5:** Run Inference → Batch process all responses
6. **Step 6:** Provide Feedback → Review and refine AI summaries
7. **Step 7:** Final Results → View completed summarization results

**Key Innovation:** The system uses AI at multiple stages to create contextually relevant summary types and expert-level prompts, then processes all responses in a single efficient batch call rather than individual API requests.

## Detailed Step Explanations

### Step 1: Select Survey Example
**Purpose:** Choose from pre-loaded survey datasets to work with

**User Experience:** 
- View available survey datasets with titles and response counts
- Select one dataset via radio button selection
- Three built-in examples: Customer Satisfaction, Employee Feedback, Product Reviews

**Technical Implementation:**
- Loads JSON files from `examples/` directory using `load_survey_examples()`
- Each dataset contains `title`, `description`, and `responses` array
- Selected data stored in `session['survey_data']` for subsequent steps
- Supports up to 50 responses per dataset (limit applied in Step 5)

**Input Format:** JSON files with structure:
```json
{
  "title": "Survey Name",
  "description": "Survey description", 
  "responses": [
    {"id": 1, "text": "Survey response text"},
    {"id": 2, "text": "Another response"}
  ]
}
```

---

### Step 2: Summarization Description  
**Purpose:** Define what aspects you want to summarize in the survey responses

**User Experience:**
- Enter free-text description of summarization criteria 
- Suggestion: 2-3 sentences work well (not enforced)
- Example: "I want to create summaries focusing on customer satisfaction themes and product quality feedback"

**Technical Implementation:**
- User input stored in `session['summarization_description']`
- Triggers AI-powered summary type generation via `generate_smart_summary_types()`
- Handles empty/invalid input with flash messages
- No character limits or strict formatting requirements

**AI Integration:** This description becomes the foundation for contextual summary type generation in Step 3

---

### Step 3: Generate Summary Types (AI-Enhanced)
**Purpose:** Create summary type categories tailored to your specific summarization criteria

**User Experience:**
- Review AI-generated summary type categories 
- Edit summary type names and descriptions as needed
- Multiple summary types generated: key_themes, sentiment_overview, specific_issues, general_feedback
- Example for "customer experience": "Key Experience Themes", "Overall Sentiment", "Specific Pain Points", "General Comments"

**Technical Implementation:**
- Uses `generate_smart_summary_types(summarization_description)` to create contextual categories
- Makes LLM call with detailed prompt requesting multiple summary type categories
- Parses JSON response for summary type names and descriptions
- Fallback to `generate_default_summary_types()` if AI generation fails
- Final summary types stored in `session['summary_types']` as nested dictionary

**AI Prompt Strategy:**
- Requests summary types specifically tailored to the summarization criteria
- Ensures coverage of different summary perspectives and focus areas
- Returns structured JSON with names and detailed descriptions

---

### Step 4: Review Prompt (AI-Enhanced)
**Purpose:** Generate and refine the expert summarization prompt for consistent summaries

**User Experience:**
- Review comprehensive AI-generated summarization prompt
- Edit prompt text as needed in large textarea
- Prompt includes summarization criteria, summary type definitions, and consistency guidelines

**Technical Implementation:**
- Uses `generate_initial_prompt(summarization_description, summary_types)` for expert prompt creation
- Makes LLM call requesting professional prompt with batch processing instructions
- Designed specifically for batch inference with JSON output format
- Fallback to `generate_template_prompt()` if AI generation fails
- Final prompt stored in `session['initial_prompt']`

**Prompt Engineering:** 
- Creates expert-level instructions for consistent summarization
- Includes edge case handling and ambiguity resolution guidance
- Optimized for batch processing of multiple responses simultaneously
- Does NOT include output format instructions (added separately in Step 5)

---

### Step 5: Run Inference (Batch Processing)
**Purpose:** Process all survey responses using the finalized prompt to generate summaries with maximum efficiency

**User Experience:**
- Click "Start Processing" to begin batch inference
- Watch progress bar with realistic timing simulation
- Automatic redirect to Step 6 when complete
- Processing message: "Batch processing all responses... X%"

**Technical Implementation:**
- Extracts up to 50 response texts from survey data
- Uses `make_batch_inference_prompt()` to create single comprehensive prompt
- Makes ONE API call via `generate_response()` instead of 50 individual calls
- Parses batch JSON response using `get_summary_json()`
- Stores results in `session['inference_results']` with dual field structure
- Exports results to timestamped JSON file in `temp_results/` directory

**Batch Processing Benefits:**
- **50x faster** than individual API calls
- **50x cheaper** in API costs
- **Better consistency** across summaries
- **Robust error handling** with detailed debug logging

**Data Structure:** Results stored with both old and new field names for compatibility:
```python
{
  'response_text': text,        # New format
  'response': text,             # Backward compatibility  
  'ai_summary': summary,        # New format
  'summary': summary,           # Backward compatibility
  'index': i,
  'full_response': batch_response
}
```

---

### Step 6: Provide Feedback (Interactive)
**Purpose:** Review AI-generated summaries and provide corrections to improve prompt effectiveness

**User Experience:**
- View all survey responses with AI-generated summaries
- See up to 10 examples per summary type category (organized view)
- Emergency fallback shows all responses if summary matching fails
- Edit summaries via text areas or dropdown menus
- Optionally add feedback text explaining changes
- Visual indicators show modified responses
- Submit feedback with change summary confirmation

**Technical Implementation:**
- Displays `session['inference_results']` with comprehensive debug information
- Uses fuzzy matching logic to organize responses by summary type
- Tracks changes between original and corrected summaries
- JavaScript handles interactive change indicators and progress tracking
- Collects feedback data via AJAX call to `/submit_feedback`

**Visual Features:**
- **AI Result Section:** Blue background showing AI summary
- **User Correction Section:** Yellow background for user changes  
- **Change Indicators:** Visual markers for modified responses
- **Debug Panel:** Shows summary counts and matching statistics
- **Fallback Display:** Ensures all responses visible even if categorization fails

**Data Collection:** Gathers detailed feedback including:
- Original vs corrected summaries
- Optional explanatory text
- Change counts and summary statistics

---

### Step 7: Final Results
**Purpose:** View completed summarization results with user feedback incorporated

**User Experience:** 
- See summary results with counts per summary type
- Final results incorporating any user corrections from Step 6
- Option to start new session
- Classification statistics display

**Technical Implementation:**
- Displays `session['final_results']` with aggregated statistics
- Calculates summary type counts using dictionary aggregation
- Provides clean interface for starting new workflow
- Maintains session data for reference

**Workflow Completion:** 
- Displays final results immediately after Step 6 feedback submission
- Incorporates any user corrections made during feedback phase
- Provides summary statistics and option to begin new summarization session

## Technical Implementation Details

### Session Management
- Flask sessions store workflow state across steps
- Key session variables: `step`, `selected_example`, `survey_data`, `summarization_description`, `summary_types`, `initial_prompt`, `inference_results`, `user_feedback`, `final_results`
- Session cleared on new workflow start
- Persistent across browser refresh within workflow

### Data Flow Architecture
1. **Step 1:** Load examples → session['survey_data']  
2. **Step 2:** User input → session['summarization_description'] → AI summary type generation
3. **Step 3:** AI summary types → user editing → session['summary_types'] → AI prompt generation  
4. **Step 4:** AI prompt → user editing → session['initial_prompt']
5. **Step 5:** Batch processing → session['inference_results'] + temp file export
6. **Step 6:** User feedback → session['user_feedback'] → session['final_results']
7. **Step 7:** Final display with user corrections incorporated

### Error Handling & Fallbacks
- **AI Generation Failures:** Automatic fallback to template-based approaches
- **API Call Failures:** Error results created for all responses with diagnostic info
- **JSON Parsing Errors:** Detailed logging with response preview for debugging  
- **Session Loss:** Debug panels show session state for troubleshooting
- **Summary Mismatches:** Fuzzy matching + emergency fallback display

### File Structure
```
summary_prompt_gen_ux/
├── app_frontend.py           # Flask web interface
├── app_backend.py            # Core business logic (framework-agnostic)
├── app_terminal.py           # Terminal interface
├── templates/index.html      # Single-page application template
├── static/
│   ├── style.css            # Professional styling
│   └── app.js               # Interactive JavaScript
├── examples/                 # Sample survey datasets
│   ├── customer_satisfaction.json
│   ├── employee_feedback.json  
│   └── product_reviews.json
├── temp_results/            # Exported inference results
├── reference_materials/     # LLM integration examples
└── requirements.txt         # Python dependencies
```

## Key Features Summary

- **AI-Powered Summary Type Generation:** Context-specific summary categories instead of generic templates
- **Expert Prompt Creation:** Professional prompts with consistency guidelines  
- **Efficient Batch Processing:** 50x faster and cheaper than individual API calls
- **Interactive Feedback Interface:** Visual distinction between AI vs human corrections
- **Robust Error Handling:** Comprehensive fallbacks and debug information
- **Results Export:** Timestamped JSON files for analysis and debugging
- **User Feedback Integration:** Single feedback cycle for summary corrections
- **Professional UI/UX:** Progress tracking, change indicators, and intuitive workflow

## Usage Examples

### Complete Workflow Example

**Scenario:** Summarizing customer satisfaction survey responses

1. **Step 1:** Select "Customer Satisfaction Survey" (15 responses)
2. **Step 2:** Enter "I want to create summaries focusing on key satisfaction themes, sentiment patterns, and specific product feedback"  
3. **Step 3:** Review AI-generated summary types:
   - "Key Satisfaction Themes" - Main topics and themes mentioned across responses
   - "Overall Sentiment Patterns" - Emotional tone and satisfaction levels
   - "Specific Product Feedback" - Concrete mentions of product features
   - "General Comments" - Other miscellaneous feedback not fitting other categories
4. **Step 4:** Review and edit comprehensive AI-generated summarization prompt (15+ lines)
5. **Step 5:** Batch process all 15 responses in ~3 seconds
6. **Step 6:** Review results, refine 2-3 summaries, provide feedback
7. **Step 7:** View final results: 4 comprehensive summary categories with key insights extracted

### Expected Performance
- **Processing Time:** 3-5 seconds for 50 responses (vs 2-3 minutes individually)
- **API Cost:** ~$0.02 per batch (vs ~$1.00 for 50 individual calls)
- **Quality:** Enhanced through user feedback and refinement capabilities
- **Consistency:** Higher than individual processing due to batch context

## AWS Configuration

For Bedrock integration reference:
- Region: `us-east-1`
- Inference profile ARN: `arn:aws:bedrock:us-east-1:457209544455:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0`
- Max tokens: 2000 (configurable)