"""
Flask frontend for Score Prompt Generation UX
Uses app_backend.py for all business logic - clean separation of concerns
"""

import os
import datetime
import uuid
from flask import Flask, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app_backend import ScorePromptBackend, SessionManager

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Read dev_mode from environment variable
DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() == 'true'

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
    
    return ScorePromptBackend(session_manager)

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

@app.route('/step/<float:step_num>')
def show_step(step_num):
    if step_num < 1 or step_num > 7.5:
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
        classes = backend.get_consolidated_session_data('classes') or backend.generate_default_classes()
        return render_template('index.html', **get_template_context(step=3, classes=classes))
    elif step_num == 4:
        prompt = backend.get_consolidated_session_data('initial_prompt') or ''
        return render_template('index.html', **get_template_context(step=4, prompt=prompt))
    elif step_num == 5:
        return render_template('index.html', **get_template_context(step=5))
    elif step_num == 6:
        results = backend.load_results_from_file()
        classes = backend.get_consolidated_session_data('classes') or {}
        return render_template('index.html', **get_template_context(step=6, results=results, classes=classes))
    elif step_num == 7:
        final_results = backend.load_results_from_file()  # Use same results for final display
        user_feedback = backend.get_consolidated_session_data('user_feedback') or {}
        classes = backend.get_consolidated_session_data('classes') or {}
        prompt = backend.get_consolidated_session_data('initial_prompt') or ''
        iteration_count = backend.get_iteration_count()
        iteration_history = backend.get_consolidated_session_data('iteration_history') or []
        return render_template('index.html', **get_template_context(step=7, final_results=final_results, 
                             user_feedback=user_feedback, classes=classes, prompt=prompt,
                             iteration_count=iteration_count, iteration_history=iteration_history))
    elif step_num == 7.5:
        iteration_data = backend.get_consolidated_session_data('current_iteration_data') or {}
        if not iteration_data:
            return redirect(url_for('show_step', step_num=7))
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
        
        if not filename or not column:
            return jsonify({'success': False, 'message': 'Missing filename or column'}), 400
        
        backend = get_backend()
        
        # Construct file path
        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        file_path = os.path.join(uploads_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'File not found'}), 404
        
        # Extract data from selected column using backend
        responses = backend.extract_csv_column_data(file_path, column)
        
        if not responses:
            return jsonify({'success': False, 'message': 'No valid responses found in selected column'}), 400
        
        # Save processed data using backend
        original_filename = filename.split('_', 2)[-1] if '_' in filename else filename
        upload_data = {
            'title': f'Uploaded: {original_filename} (Column: {column})',
            'responses': responses
        }
        backend.save_consolidated_session_data('survey_data', upload_data)
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
        score_description = request.form.get('score_description', '').strip()
        if score_description:
            session['score_description'] = score_description
            backend.session.set('score_description', score_description)
            
            # Generate smart classes based on the score description using backend
            classes = backend.generate_smart_classes(score_description)
            backend.save_consolidated_session_data('classes', classes)
            sync_session_data(backend)
            return redirect(url_for('show_step', step_num=3))
        else:
            flash('Please provide a description of the scoring criteria')
            return redirect(url_for('show_step', step_num=2))
    
    elif current_step == 3:
        classes = {}
        for key in ['high_score', 'low_score', 'not_relevant', 'unclear']:
            name = request.form.get(f'{key}_name', '').strip()
            description = request.form.get(f'{key}_description', '').strip()
            score = request.form.get(f'{key}_score', '').strip()
            if name and description:
                classes[key] = {'name': name, 'description': description, 'score': score}
        
        if len(classes) == 4:
            backend.save_consolidated_session_data('classes', classes)
            
            # Generate initial prompt using backend
            score_description = session.get('score_description', '')
            initial_prompt = backend.generate_initial_prompt(score_description, classes)
            backend.save_consolidated_session_data('initial_prompt', initial_prompt)
            sync_session_data(backend)
            
            # Skip Step 4 (prompt review) in production mode, go directly to Step 5
            if DEV_MODE:
                return redirect(url_for('show_step', step_num=4))
            else:
                return redirect(url_for('show_step', step_num=5))
        else:
            flash('Please fill in all class names and descriptions')
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
    responses = survey_data.get('responses', [])[:50]  # Max 50 responses
    print(f"DEBUG: Found {len(responses)} responses")
    if len(responses) > 0:
        print(f"DEBUG: First response preview: {responses[0].get('text', '')[:100]}...")
    prompt = backend.get_consolidated_session_data('initial_prompt') or ''
    
    print(f"DEBUG: Found {len(responses)} responses")
    print(f"DEBUG: Prompt length: {len(prompt)}")
    
    try:
        # Use backend's batch inference method
        print("DEBUG: Calling backend.run_batch_inference...")
        results = backend.run_batch_inference(responses, prompt)
        
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
        
        # Results are already stored in file, no need to move them
        # The final results will be loaded from the same file in Step 7
        response = jsonify({'status': 'complete', 'redirect': url_for('show_step', step_num=7)})
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
        score_description = session.get('score_description', '')
        
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
            original_prompt, feedback_analysis, classes, score_description
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
            'message': 'Iteration rejected, returning to final results',
            'redirect': url_for('show_step', step_num=7)
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)