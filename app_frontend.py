"""
Flask frontend for Summary Prompt Generation UX
Uses app_backend.py for all business logic - clean separation of concerns
"""

import os
import datetime
import uuid
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app_backend import SummaryPromptBackend, SessionManager

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Read dev_mode from environment variable
DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() == 'true'

# Configuration for inference processing
INFERENCE_LIMIT = 3  # Number of conversations to process during inference

def get_template_context(**kwargs):
    """Helper function to add common template variables"""
    kwargs['dev_mode'] = DEV_MODE
    return kwargs

# Global backend instance - each request will get session-specific backend
def get_backend():
    """Get or create backend instance for current Flask session"""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        print(f"DEBUG: Created NEW Flask session_id: {session['session_id']}")
    
    # Create session manager with Flask session ID
    session_manager = SessionManager(session_id=session['session_id'])
    
    # Sync Flask session data with backend session
    for key, value in session.items():
        if key != 'session_id':  # Don't sync the session_id itself
            session_manager.set(key, value)
    
    return SummaryPromptBackend(session_manager)

def sync_session_data(backend):
    """Sync backend session data back to Flask session"""
    for key, value in backend.session.data.items():
        session[key] = value

@app.route('/')
def index():
    print("DEBUG: ======================================")
    print("DEBUG: === INDEX ROUTE - NEW SESSION ===")
    print("DEBUG: ======================================")
    
    backend = get_backend()
    
    # Clear session data for fresh start
    session.clear()
    session['step'] = 1
    session['session_id'] = str(uuid.uuid4())  # Force new session ID
    
    # Get fresh backend with new session
    backend = get_backend()
    backend.session.clear()
    backend.session.set('step', 1)
    backend.reset_iteration_count()
    
    print("DEBUG: Session cleared completely - fresh start guaranteed")
    
    # Load survey examples using backend
    examples = backend.load_survey_examples()
    return render_template('index.html', **get_template_context(step=1, examples=examples))

@app.route('/step/final')
def show_step_final():
    """Step Final: Export Instructions"""
    backend = get_backend()
    prompt = backend.get_consolidated_session_data('initial_prompt') or ''
    if not prompt:
        # If no prompt available, redirect to start
        return redirect(url_for('index'))
    
    return render_template('index.html', **get_template_context(step=8, prompt=prompt))

@app.route('/step/<float:step_num>')
def show_step(step_num):
    if step_num < 1 or (step_num > 6 and step_num not in [7.5, 8]):
        return redirect(url_for('index'))
    
    # Redirect non-dev users away from Step 4 (prompt review)
    if step_num == 4 and not DEV_MODE:
        return redirect(url_for('show_step', step_num=5))

    backend = get_backend()

    # Clean up session files when going back to step 1
    if step_num == 1:
        print("DEBUG: ======================================")
        print("DEBUG: === STEP 1 ROUTE - RESET SESSION ===")
        print("DEBUG: ======================================")

        # Clear sessions for fresh start
        session.clear()
        session['step'] = 1
        session['session_id'] = str(uuid.uuid4())  # Force new session ID
        
        # Get fresh backend with new session
        backend = get_backend()
        backend.session.clear()
        backend.session.set('step', 1)
        
        print("DEBUG: Session cleared completely - fresh start from step 1")
    else:
        session['step'] = step_num
        backend.session.set('step', step_num)

    if step_num == 1:
        examples = backend.load_survey_examples()
        return render_template('index.html', **get_template_context(step=1, examples=examples))
    elif step_num == 2:
        # Load dataset and get sample responses for Step 2
        current_session_id = session.get('session_id', 'NO_SESSION_ID')
        print(f"DEBUG Step 2: Using session_id: {current_session_id}")
        
        survey_data = backend.get_consolidated_session_data('survey_data') or {}
        
        # Get dataset name from the survey data itself (more reliable than session)
        dataset_title = survey_data.get('title', 'Unknown Dataset')
        # Clean up the title for display
        selected_dataset_name = dataset_title.replace('_', ' ').title()
        
        # Get first 10 responses as samples for Step 2 (showing 3 initially, expandable to 10)
        responses = survey_data.get('responses', [])
        sample_responses = responses[:10]
        
        print(f"DEBUG Step 2: Dataset title from survey_data: {dataset_title}")
        print(f"DEBUG Step 2: Selected dataset name: {selected_dataset_name}")
        print(f"DEBUG Step 2: Number of responses: {len(responses)}")
        if len(responses) > 0:
            print(f"DEBUG Step 2: First response preview: {responses[0].get('text', '')[:100]}...")
        print(f"DEBUG Step 2: Selected example in session: {session.get('selected_example', 'NOT_SET')}")
        
        return render_template('index.html', **get_template_context(step=2, 
                             sample_responses=sample_responses, 
                             selected_dataset_name=selected_dataset_name))
    elif step_num == 3:
        summary_instructions = backend.get_consolidated_session_data('summary_instructions') or ''
        data_source_analysis = backend.get_consolidated_session_data('data_source_analysis') or {}
        return render_template('index.html', **get_template_context(step=3, 
                             summary_instructions=summary_instructions,
                             data_source_analysis=data_source_analysis))
    elif step_num == 4:
        prompt = backend.get_consolidated_session_data('initial_prompt') or ''
        return render_template('index.html', **get_template_context(step=4, prompt=prompt))
    elif step_num == 5:
        survey_data = backend.get_consolidated_session_data('survey_data') or {}
        # Calculate actual number of conversations that will be processed
        responses = survey_data.get('responses', [])
        actual_inference_count = min(len(responses), INFERENCE_LIMIT)
        return render_template('index.html', **get_template_context(
            step=5, 
            survey_data=survey_data,
            actual_inference_count=actual_inference_count
        ))
    elif step_num == 6:
        results = backend.load_results_from_file()
        classes = backend.get_consolidated_session_data('classes') or {}
        return render_template('index.html', **get_template_context(step=6, results=results, classes=classes))
    elif step_num == 7.5:
        iteration_data = backend.get_consolidated_session_data('current_iteration_data') or {}
        if not iteration_data:
            return redirect(url_for('show_step', step_num=6))
        return render_template('index.html', **get_template_context(step=7.5, iteration_data=iteration_data))

@app.route('/upload_data', methods=['POST'])
def upload_data():
    """Handle file upload for custom data"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Validate file type
        if not file.filename.lower().endswith(('.json', '.csv')):
            return jsonify({'success': False, 'message': 'Only JSON and CSV files are supported'}), 400
        
        backend = get_backend()
        
        # Create uploads directory
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = session.get('session_id', 'unknown')
        safe_filename = f"{session_id}_{timestamp}_{filename}"
        file_path = os.path.join(uploads_dir, safe_filename)
        
        file.save(file_path)
        
        # Determine file type and process accordingly
        if filename.lower().endswith('.json'):
            # Process JSON file using backend
            try:
                responses = backend.process_json_file(file_path)
                
                # Save processed data using backend
                upload_data = {
                    'title': f'Uploaded: {filename}',
                    'responses': responses
                }
                backend.save_consolidated_session_data('survey_data', upload_data)
                
                # Analyze the uploaded data source
                try:
                    data_analysis = backend.analyze_data_source(upload_data)
                    backend.save_consolidated_session_data('data_source_analysis', data_analysis)
                except Exception as e:
                    print(f"Upload data analysis failed: {e}, using default")
                    default_analysis = backend.get_default_data_source_analysis()
                    backend.save_consolidated_session_data('data_source_analysis', default_analysis)
                
                session['selected_example'] = f'uploaded_{filename}'
                sync_session_data(backend)
                
                # Clean up file
                os.remove(file_path)
                
                return jsonify({
                    'success': True,
                    'file_type': 'json',
                    'filename': safe_filename,
                    'original_filename': filename,
                    'response_count': len(responses)
                })
                
            except Exception as e:
                # Clean up file on error
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'success': False, 'message': str(e)}), 400
                
        elif filename.lower().endswith('.csv'):
            # Process CSV file for column selection using backend
            try:
                csv_info = backend.process_csv_file(file_path)
                
                return jsonify({
                    'success': True,
                    'file_type': 'csv',
                    'filename': safe_filename,
                    'original_filename': filename,
                    'columns': csv_info['columns'],
                    'preview': csv_info['preview'],
                    'total_rows': csv_info['total_rows']
                })
                
            except Exception as e:
                # Clean up file on error
                if os.path.exists(file_path):
                    os.remove(file_path)
                return jsonify({'success': False, 'message': str(e)}), 400
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {str(e)}'}), 500

@app.route('/process_csv', methods=['POST'])
def process_csv():
    """Process CSV file with selected column"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        column = data.get('column')
        conversation_id_column = data.get('conversation_id_column')  # New optional column
        author_column = data.get('author_column')  # New optional column
        
        # STRICT VALIDATION - All three columns required
        if not filename or not column:
            return jsonify({'success': False, 'message': 'Missing filename or response column'}), 400
        
        if not conversation_id_column:
            return jsonify({'success': False, 'message': 'Conversation ID column is required for CSV processing'}), 400
            
        if not author_column:
            return jsonify({'success': False, 'message': 'Author column is required for CSV processing'}), 400
        
        backend = get_backend()
        
        # Construct file path
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        file_path = os.path.join(uploads_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        # Extract data using new conversation method (all columns required)
        responses = backend.extract_csv_conversation_data(
            file_path, 
            column, 
            conversation_id_column, 
            author_column
        )
        
        if not responses:
            return jsonify({'success': False, 'message': 'No valid responses found in selected column'}), 400
        
        # Save processed data using backend
        original_filename = filename.split('_', 2)[-1] if '_' in filename else filename
        
        # Build title with selected columns info
        title_parts = [f'Uploaded: {original_filename}']
        title_parts.append(f'Response: {column}')
        if conversation_id_column:
            title_parts.append(f'Conv ID: {conversation_id_column}')
        if author_column:
            title_parts.append(f'Author: {author_column}')
        
        upload_data = {
            'title': ' | '.join(title_parts),
            'responses': responses,
            'conversation_id_column': conversation_id_column,
            'author_column': author_column
        }
        backend.save_consolidated_session_data('survey_data', upload_data)
        
        # Analyze the uploaded data source
        try:
            data_analysis = backend.analyze_data_source(upload_data)
            backend.save_consolidated_session_data('data_source_analysis', data_analysis)
        except Exception as e:
            print(f"CSV data analysis failed: {e}, using default")
            default_analysis = backend.get_default_data_source_analysis()
            backend.save_consolidated_session_data('data_source_analysis', default_analysis)
        
        session['selected_example'] = f'uploaded_{original_filename}'
        sync_session_data(backend)
        
        # Clean up file
        os.remove(file_path)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'original_filename': original_filename,
            'response_count': len(responses),
            'column_used': column
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Processing failed: {str(e)}'}), 500

@app.route('/process_step', methods=['POST'])
def process_step():
    current_step = session.get('step', 1)
    backend = get_backend()

    if current_step == 1:
        data_source = request.form.get('data_source')

        if data_source == 'examples':
            # Handle pre-built examples
            selected_example = request.form.get('selected_example')
            if selected_example:
                # CRITICAL: Force new session ID to prevent data contamination
                print(f"DEBUG: === STARTING NEW WORKFLOW ===")
                print(f"DEBUG: FORCING NEW SESSION ID for dataset selection")
                
                # Clear any existing session ID to force a fresh start
                if 'session_id' in session:
                    old_session_id = session['session_id']
                    print(f"DEBUG: Clearing old session_id: {old_session_id}")
                    del session['session_id']
                
                # Get completely fresh session ID and backend
                session['session_id'] = str(uuid.uuid4())
                backend = get_backend()
                new_session_id = backend.session.session_id
                print(f"DEBUG: NEW session_id: {new_session_id}")
                
                examples = backend.load_survey_examples()
                session['selected_example'] = selected_example
                backend.session.set('selected_example', selected_example)
                print(f"DEBUG: Selected example: {selected_example}")
                print(f"DEBUG: Available examples: {list(examples.keys())}")
                if selected_example in examples:
                    selected_data = examples[selected_example]['data']
                    print(f"DEBUG: ✅ SAVING DATASET: {selected_example}")
                    print(f"DEBUG: Selected dataset title: {selected_data.get('title', 'No title')}")
                    print(f"DEBUG: Selected dataset responses count: {len(selected_data.get('responses', []))}")
                    if len(selected_data.get('responses', [])) > 0:
                        print(f"DEBUG: First response preview: {selected_data['responses'][0].get('text', '')[:100]}...")
                    
                    backend.save_consolidated_session_data('survey_data', selected_data)
                    
                    # Analyze the data source to infer context information
                    print("DEBUG: Analyzing data source...")
                    try:
                        data_analysis = backend.analyze_data_source(selected_data)
                        backend.save_consolidated_session_data('data_source_analysis', data_analysis)
                        print(f"DEBUG: ✅ Data analysis complete - Source: {data_analysis.get('data_source_type', 'Unknown')}")
                        print(f"DEBUG: Business context: {data_analysis.get('business_context', 'Unknown')}")
                        print(f"DEBUG: Found {len(data_analysis.get('author_types', []))} author types")
                    except Exception as e:
                        print(f"DEBUG: ⚠️ Data analysis failed: {e}, continuing with default")
                        default_analysis = backend.get_default_data_source_analysis()
                        backend.save_consolidated_session_data('data_source_analysis', default_analysis)
                    
                    sync_session_data(backend)
                    print(f"DEBUG: ✅ SUCCESSFULLY SAVED dataset to session files with session_id: {new_session_id}")
                else:
                    print(f"DEBUG: ❌ ERROR - Selected example {selected_example} not found in examples!")
                return redirect(url_for('show_step', step_num=2))
            else:
                flash('Please select a survey example')
                return redirect(url_for('show_step', step_num=1))
        
        elif data_source == 'upload':
            # Handle custom upload
            uploaded_file = request.form.get('uploaded_file')
            if uploaded_file:
                # Custom upload data should already be saved by the upload routes
                # Just proceed to step 2
                print(f"DEBUG: Processing uploaded file: {uploaded_file}")
                return redirect(url_for('show_step', step_num=2))
            else:
                flash('Please upload and process a file first')
                return redirect(url_for('show_step', step_num=1))
        
        else:
            flash('Please select a data source')
            return redirect(url_for('show_step', step_num=1))
    
    elif current_step == 2:
        summary_description = request.form.get('summary_description', '').strip()
        if summary_description:
            session['summary_description'] = summary_description
            backend.session.set('summary_description', summary_description)
            
            # Generate detailed summary instructions based on the description
            summary_instructions = backend.generate_summary_instructions(summary_description)
            backend.save_consolidated_session_data('summary_instructions', summary_instructions)
            sync_session_data(backend)
            return redirect(url_for('show_step', step_num=3))
        else:
            flash('Please provide a description of the summarization criteria')
            return redirect(url_for('show_step', step_num=2))
    
    elif current_step == 3:
        edited_instructions = request.form.get('summary_instructions', '').strip()
        if edited_instructions:
            # Save the edited summary instructions
            backend.save_consolidated_session_data('summary_instructions', edited_instructions)
            
            # Process edited data source analysis if present
            data_source_type = request.form.get('data_source_type', '').strip()
            business_context = request.form.get('business_context', '').strip()
            
            if data_source_type or business_context:
                # Collect participant data
                participants = []
                participant_index = 0
                while True:
                    role = request.form.get(f'participant_role_{participant_index}', '').strip()
                    description = request.form.get(f'participant_desc_{participant_index}', '').strip()
                    
                    if role or description:
                        if role and description:  # Only include if both are provided
                            participants.append({
                                'role': role,
                                'description': description
                            })
                        participant_index += 1
                    else:
                        break
                
                # Update the data source analysis with user edits
                updated_analysis = {
                    'data_source_type': data_source_type,
                    'author_types': participants,
                    'business_context': business_context
                }
                
                # Save the updated analysis
                backend.save_consolidated_session_data('data_source_analysis', updated_analysis)
                print(f"DEBUG: Updated data source analysis with user edits: {updated_analysis}")
            
            # Generate initial prompt using summary instructions AND data source analysis
            summary_description = session.get('summary_description', '')
            data_source_analysis = backend.get_consolidated_session_data('data_source_analysis') or {}
            initial_prompt = backend.generate_initial_prompt_for_summarization(summary_description, edited_instructions, data_source_analysis)
            backend.save_consolidated_session_data('initial_prompt', initial_prompt)
            sync_session_data(backend)
            
            # Skip Step 4 (prompt review) in production mode, go directly to Step 5
            if DEV_MODE:
                return redirect(url_for('show_step', step_num=4))
            else:
                return redirect(url_for('show_step', step_num=5))
        else:
            flash('Please review and confirm the summary instructions')
            return redirect(url_for('show_step', step_num=3))
    
    elif current_step == 4:
        edited_prompt = request.form.get('prompt', '').strip()
        if edited_prompt:
            backend.save_consolidated_session_data('initial_prompt', edited_prompt)
            sync_session_data(backend)
            return redirect(url_for('show_step', step_num=5))
        else:
            flash('Please review and confirm the prompt')
            return redirect(url_for('show_step', step_num=4))

    return redirect(url_for('index'))

@app.route('/run_inference', methods=['POST'])
def run_inference():
    print("=== DEBUG: Starting run_inference ===")
    backend = get_backend()
    
    print(f"DEBUG: Selected example from session: {session.get('selected_example', 'Not found')}")
    survey_data = backend.get_consolidated_session_data('survey_data') or {}
    print(f"DEBUG: Loaded survey data title: {survey_data.get('title', 'No title')}")
    responses = survey_data.get('responses', [])[:INFERENCE_LIMIT]   # Limit to configured number of conversations
    print(f"DEBUG: Found {len(responses)} responses")
    if len(responses) > 0:
        print(f"DEBUG: First response preview: {responses[0].get('text', '')[:100]}...")
    prompt = backend.get_consolidated_session_data('initial_prompt') or ''
    
    print(f"DEBUG: Found {len(responses)} responses")
    print(f"DEBUG: Prompt length: {len(prompt)}")
    
    try:
        # Use backend's individual inference method for better summary quality
        print("DEBUG: Calling backend.run_individual_inference...")
        results = backend.run_individual_inference(responses, prompt)
        
        if not results:
            print("DEBUG: No results generated")
            return jsonify({'status': 'error', 'message': 'No results generated'})
        
        print(f"Created {len(results)} results")  # Debug logging
        
        # Save results using backend
        backend.save_results_to_file(results)
        print(f"Stored {len(results)} results in file")  # Debug logging
        
        sync_session_data(backend)
        return jsonify({'status': 'success', 'redirect': url_for('show_step', step_num=6)})
    
    except Exception as e:
        print(f"=== DEBUG: Batch inference error: {e} ===")
        import traceback
        print(f"DEBUG: Full traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    print("DEBUG: === SUBMIT_FEEDBACK ROUTE CALLED ===")
    try:
        feedback_data = request.get_json()
        print(f"DEBUG: Received feedback data: {feedback_data}")
        
        backend = get_backend()
        
        # Load responses to include text for changes
        responses = backend.load_response_data()
        results = backend.load_results_from_file()
        
        # Enhance feedback data with response text for changes
        if feedback_data.get('feedback'):
            for feedback_item in feedback_data['feedback']:
                index = feedback_item.get('index', 0)
                
                # Add response text for this change
                if index < len(results):
                    feedback_item['response_text'] = results[index].get('response_text', '')
                elif index < len(responses):
                    feedback_item['response_text'] = responses[index].get('text', '')
                else:
                    feedback_item['response_text'] = 'Response not found'
                
                # Add response_id if not present
                if 'response_id' not in feedback_item and index < len(responses):
                    feedback_item['response_id'] = responses[index].get('id', index + 1)
                
                print(f"DEBUG: Enhanced feedback for index {index}: {feedback_item}")
        
        # Save using backend consolidated session format
        backend.save_consolidated_session_data('user_feedback', feedback_data)
        print("DEBUG: Successfully saved enhanced user feedback to consolidated session")
        
        sync_session_data(backend)
        
        # Check if there are changes to iterate on
        changes_count = feedback_data.get('changes_count', 0)
        current_iteration = backend.get_iteration_count()
        
        if changes_count > 0 and current_iteration < 3:
            # There are changes and we can iterate - trigger iteration automatically
            print(f"DEBUG: Changes detected ({changes_count}), starting iteration {current_iteration + 1}")
            
            # Load required data for iteration
            classes = backend.get_consolidated_session_data('classes') or {}
            original_prompt = backend.get_consolidated_session_data('initial_prompt') or ''
            summary_description = session.get('summary_description', '')
            
            # Analyze feedback patterns
            print("DEBUG: Analyzing feedback patterns...")
            feedback_analysis = backend.analyze_feedback_patterns(feedback_data, results, classes)
            
            if not feedback_analysis:
                return jsonify({'status': 'error', 'message': 'Unable to analyze feedback patterns'}), 400
            
            # Generate refined prompt
            print("DEBUG: Generating refined prompt...")
            improved_prompt, rationale = backend.generate_refined_prompt(
                original_prompt, feedback_analysis, classes, summary_description
            )
            
            # Create intelligent diff
            diff_data = backend.create_intelligent_diff(original_prompt, improved_prompt)
            
            if DEV_MODE:
                # Dev mode: Save iteration data and go to Step 7.5 for manual review
                print(f"DEBUG: Dev mode - saving iteration data for manual review")
                iteration_data = {
                    'iteration_number': current_iteration + 1,
                    'original_prompt': original_prompt,
                    'improved_prompt': improved_prompt,
                    'rationale': rationale,
                    'feedback_analysis': feedback_analysis,
                    'diff_data': diff_data
                }
                backend.save_consolidated_session_data('current_iteration_data', iteration_data)
                
                # Store iteration history for tracking
                iteration_history = backend.get_consolidated_session_data('iteration_history') or []
                iteration_history.append({
                    'iteration': current_iteration + 1,
                    'feedback_analysis': feedback_analysis,
                    'rationale': rationale,
                    'changes_count': changes_count,
                    'pending_review': True  # Flag for dev mode pending review
                })
                backend.save_consolidated_session_data('iteration_history', iteration_history)
                
                sync_session_data(backend)
                
                # Redirect to Step 7.5 for manual approval
                redirect_url = url_for('show_step', step_num=7.5)
                print(f"DEBUG: Dev mode - redirecting to Step 7.5: {redirect_url}")
                
            else:
                # Production mode: Auto-apply the improved prompt (skip manual approval)
                print(f"DEBUG: Production mode - auto-applying improved prompt for iteration {current_iteration + 1}")
                backend.save_consolidated_session_data('initial_prompt', improved_prompt)
                
                # Update iteration count
                new_iteration_count = backend.increment_iteration_count()
                
                # Store iteration history with auto-applied flag
                iteration_history = backend.get_consolidated_session_data('iteration_history') or []
                iteration_history.append({
                    'iteration': new_iteration_count,
                    'original_prompt': original_prompt,
                    'improved_prompt': improved_prompt,
                    'rationale': rationale,
                    'feedback_analysis': feedback_analysis,
                    'changes_count': changes_count,
                    'auto_applied': True  # Flag to indicate this was automatically applied
                })
                backend.save_consolidated_session_data('iteration_history', iteration_history)
                
                # Clear current iteration data since we've applied it
                backend.save_consolidated_session_data('current_iteration_data', {})
                
                sync_session_data(backend)
                
                # Redirect directly to Step 5 for re-inference
                redirect_url = url_for('show_step', step_num=5)
                print(f"DEBUG: Production mode - redirecting to Step 5: {redirect_url}")
            
            try:
                print(f"DEBUG: Creating JSON response...")
                response = jsonify({'status': 'iterate', 'redirect': redirect_url})
                response.headers['Content-Type'] = 'application/json'
                print(f"DEBUG: JSON response created successfully")
                print(f"DEBUG: Response headers: {dict(response.headers)}")
                print(f"DEBUG: Response data: {response.get_data(as_text=True)}")
            except Exception as resp_error:
                print(f"DEBUG: ERROR creating response: {resp_error}")
                return jsonify({'status': 'error', 'message': f'Response creation failed: {str(resp_error)}'}), 500
        elif changes_count == 0:
            # No changes made - return flag to show popup
            response = jsonify({
                'status': 'no_changes',
                'message': 'No changes or feedback given. If you\'d like to iterate, please make changes or add comments to examples'
            })
            response.headers['Content-Type'] = 'application/json'
        else:
            # Max iterations reached
            response = jsonify({
                'status': 'max_iterations',
                'message': 'Maximum iterations (3) reached. The instructions have been refined based on your feedback.'
            })
            response.headers['Content-Type'] = 'application/json'
        
        print(f"DEBUG: Sending response: {response.get_json()}")
        return response
    except Exception as e:
        print(f"DEBUG: ERROR in submit_feedback: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/iterate_prompt', methods=['POST'])
def iterate_prompt():
    """Initiate prompt iteration based on Step 6 feedback"""
    try:
        backend = get_backend()
        
        # Check iteration limit
        current_iteration = backend.get_iteration_count()
        if current_iteration >= 3:
            return jsonify({'status': 'error', 'message': 'Maximum iteration limit (3) reached'}), 400
        
        # Load required data using backend
        user_feedback = backend.get_consolidated_session_data('user_feedback') or {}
        results = backend.load_results_from_file()
        classes = backend.get_consolidated_session_data('classes') or {}
        original_prompt = backend.get_consolidated_session_data('initial_prompt') or ''
        summary_description = session.get('summary_description', '')
        
        if not user_feedback.get('feedback'):
            return jsonify({'status': 'error', 'message': 'No feedback data available for iteration'}), 400
        
        # Analyze feedback patterns using backend
        print("DEBUG: Analyzing feedback patterns...")
        feedback_analysis = backend.analyze_feedback_patterns(user_feedback, results, classes)
        
        if not feedback_analysis:
            return jsonify({'status': 'error', 'message': 'Unable to analyze feedback patterns'}), 400
        
        # Generate refined prompt using backend
        print("DEBUG: Generating refined prompt...")
        improved_prompt, rationale = backend.generate_refined_prompt(
            original_prompt, feedback_analysis, classes, summary_description
        )
        
        # Create intelligent diff with semantic summary using backend
        diff_data = backend.create_intelligent_diff(original_prompt, improved_prompt)
        
        # Save iteration data using backend
        iteration_data = {
            'iteration_number': current_iteration + 1,
            'original_prompt': original_prompt,
            'improved_prompt': improved_prompt,
            'rationale': rationale,
            'feedback_analysis': feedback_analysis,
            'diff_data': diff_data
        }
        backend.save_consolidated_session_data('current_iteration_data', iteration_data)
        sync_session_data(backend)
        
        return jsonify({
            'status': 'success',
            'redirect': url_for('show_step', step_num=7.5)
        })
        
    except Exception as e:
        print(f"DEBUG: ERROR in iterate_prompt: {e}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/approve_iteration', methods=['POST'])
def approve_iteration():
    """Approve prompt changes and continue to Step 5 with new prompt"""
    try:
        backend = get_backend()
        
        iteration_data = backend.get_consolidated_session_data('current_iteration_data')
        if not iteration_data:
            return jsonify({'status': 'error', 'message': 'No iteration data available'}), 400
        
        # Increment iteration count using backend
        iteration_count = backend.increment_iteration_count()
        
        # Save the improved prompt as the new initial prompt using backend
        backend.save_consolidated_session_data('initial_prompt', iteration_data['improved_prompt'])
        
        # Store iteration history using backend
        iteration_history = backend.get_consolidated_session_data('iteration_history') or []
        iteration_history.append({
            'iteration': iteration_count,
            'original_prompt': iteration_data['original_prompt'],
            'improved_prompt': iteration_data['improved_prompt'],
            'rationale': iteration_data['rationale'],
            'timestamp': datetime.datetime.now().isoformat()
        })
        backend.save_consolidated_session_data('iteration_history', iteration_history)
        
        # Clear current iteration data
        backend.save_consolidated_session_data('current_iteration_data', {})
        
        sync_session_data(backend)
        
        return jsonify({
            'status': 'success',
            'message': f'Starting iteration {iteration_count} with improved prompt',
            'redirect': url_for('show_step', step_num=5)
        })
        
    except Exception as e:
        print(f"DEBUG: ERROR in approve_iteration: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/reject_iteration', methods=['POST'])
def reject_iteration():
    """Reject prompt changes and return to Step 7"""
    try:
        backend = get_backend()
        
        # Clear current iteration data using backend
        backend.save_consolidated_session_data('current_iteration_data', {})
        sync_session_data(backend)
        
        return jsonify({
            'status': 'success',
            'message': 'Iteration rejected, returning to feedback step',
            'redirect': url_for('show_step', step_num=6)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)