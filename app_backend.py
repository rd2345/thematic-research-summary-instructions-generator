"""
Backend logic for Score Prompt Generation UX
Extracted from app.py to be framework-agnostic
"""

import json
import os
import datetime
import uuid
import csv
import difflib
import html
import boto3
import random
import re


class SessionManager:
    """Manages session state without Flask dependency"""
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.data = {}
        self.temp_dir = os.path.join(os.getcwd(), 'temp_results')
        os.makedirs(self.temp_dir, exist_ok=True)
        print(f"DEBUG: SessionManager initialized with session_id: {self.session_id}")
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def set(self, key, value):
        self.data[key] = value
    
    def clear(self):
        self.data.clear()
        self.cleanup_session_files()
    
    def cleanup_session_files(self):
        """Clean up session files"""
        if os.path.exists(self.temp_dir):
            for filename in [f"session_{self.session_id}_object.json", f"session_{self.session_id}_responses.json"]:
                filepath = os.path.join(self.temp_dir, filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        print(f"DEBUG: Cleaned up file: {filename}")
                    except Exception as e:
                        print(f"DEBUG: Failed to clean up {filename}: {e}")


class ScorePromptBackend:
    """Core business logic for score prompt generation"""
    
    def __init__(self, session_manager=None):
        self.session = session_manager or SessionManager()
        
        # AWS Bedrock setup
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.inference_profile_arn = 'arn:aws:bedrock:us-east-1:457209544455:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0'
    
    def generate_response(self, prompt):
        """Generate response from LLM"""
        request_payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        response = self.bedrock_runtime.invoke_model(
            modelId=self.inference_profile_arn,
            body=json.dumps(request_payload)
        )
        response_body = response['body'].read()
        text = json.loads(response_body)
        answer = text['content'][0]['text']
        return answer

    def load_survey_examples(self):
        """Load pre-built survey examples"""
        examples = {}
        examples_dir = 'examples'
        if os.path.exists(examples_dir):
            for filename in os.listdir(examples_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(examples_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        name = filename.replace('.json', '').replace('_', ' ').title()
                        examples[filename] = {
                            'name': name,
                            'data': data,
                            'count': len(data.get('responses', []))
                        }
        return examples

    def generate_default_classes(self):
        """Generate default classification classes"""
        return {
            'high_score': {
                'name': 'High Score',
                'description': 'Responses that clearly deserve a high score based on the criteria',
                'score': '100'
            },
            'low_score': {
                'name': 'Low Score', 
                'description': 'Responses that clearly deserve a low score based on the criteria',
                'score': '0'
            },
            'not_relevant': {
                'name': 'Not Relevant',
                'description': 'Responses that are not relevant to the scoring criteria',
                'score': ''
            },
            'unclear': {
                'name': 'Unclear',
                'description': 'Responses where it is unclear whether they should receive a high or low score',
                'score': ''
            }
        }

    def generate_smart_classes(self, score_description):
        """Generate contextually relevant classes using LLM based on score description"""
        
        class_generation_prompt = f"""Based on the following scoring criteria, generate 4 classification categories that would be most relevant for scoring survey responses.

SCORING CRITERIA:
{score_description}

Please generate exactly 4 categories following this pattern:
1. A "high score" category - responses that clearly deserve high scores
2. A "low score" category - responses that clearly deserve low scores  
3. A "not relevant" category - responses not related to the scoring criteria
4. An "unclear/ambiguous" category - responses where scoring is difficult to determine

For each category, provide:
- A clear, concise, specific name (1-3 words)
- A detailed description explaining what types of responses belong in this category
- A numeric score (use 100 for high score category, 0 for low score category, leave empty string for not relevant and unclear)

Format your response as JSON like this:
{{
    "high_score": {{
        "name": "Great Battery Performance",
        "description": "Responses that mention the battery lasting a full day or longer, fast charging, or exceptional power management",
        "score": "100"
    }},
    "low_score": {{
        "name": "Poor Battery Performance", 
        "description": "Responses that mention battery draining quickly, not lasting through the day, slow charging, or battery-related problems",
        "score": "0"
    }},
    "not_relevant": {{
        "name": "Non-Battery Related",
        "description": "Responses that discuss other product features, general satisfaction, or topics unrelated to battery performance",
        "score": ""
    }},
    "unclear": {{
        "name": "Battery Mentions Unclear",
        "description": "Responses that mention battery but without clear positive or negative sentiment, or with mixed/contradictory battery feedback",
        "score": ""
    }}
}}

Generate categories that are specifically tailored to the scoring criteria provided above."""

        try:
            llm_response = self.generate_response(class_generation_prompt)
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                classes = json.loads(json_str)
                
                # Validate that we have the expected structure
                required_keys = ['high_score', 'low_score', 'not_relevant', 'unclear']
                if all(key in classes for key in required_keys):
                    for key in required_keys:
                        if 'name' in classes[key] and 'description' in classes[key] and 'score' in classes[key]:
                            continue
                        else:
                            raise ValueError("Missing name, description, or score")
                    return classes
            
            # If parsing fails, fall back to default
            print("Failed to parse LLM response for class generation, using defaults")
            return self.generate_default_classes()
            
        except Exception as e:
            print(f"Error generating smart classes: {e}")
            return self.generate_default_classes()

    def generate_initial_prompt(self, score_description, classes):
        """Generate an intelligent scoring prompt using LLM based on description and classes"""
        
        # Prepare class information for the prompt generation
        class_details = []
        class_names = []
        for key, class_info in classes.items():
            class_details.append(f"- {class_info['name']}: {class_info['description']}")
            class_names.append(class_info['name'])
        
        prompt_generation_request = f"""Create an expert-level prompt for batch scoring of survey responses. The prompt will be used to classify multiple survey responses simultaneously in a single API call.

SCORING CRITERIA:
{score_description}

CLASSIFICATION CATEGORIES:
{chr(10).join(class_details)}

Please generate a professional prompt that:
1. Clearly explains the scoring task and criteria
2. Provides detailed guidance on how to classify responses consistently across a batch
3. Includes specific instructions for edge cases or ambiguous responses
4. Emphasizes consistency when processing multiple responses together
5. Instructs the AI to process multiple responses provided in JSON format
6. Uses the exact category names: {', '.join(class_names)}
7. Should NOT include output format instructions (this will be added separately)
8. Is concise and to the point.

IMPORTANT: This prompt will be used for BATCH processing where multiple survey responses will be provided in a JSON object with numeric keys (0, 1, 2, etc.) and the AI must return classifications for all responses in a JSON format.

The prompt should be written for an AI assistant that will be classifying multiple survey responses at once. Make it clear to understand and concise.

Generate the complete prompt now:"""

        try:
            llm_response = self.generate_response(prompt_generation_request)
            
            # Clean up the response - this will be used for batch processing
            generated_prompt = llm_response.strip()
            
            # For batch processing, we don't add the individual CLASSIFICATION format
            # The batch format will be added by make_batch_inference_prompt()
            return generated_prompt
            
        except Exception as e:
            print(f"Error generating intelligent prompt: {e}")
            # Fallback to template-based approach
            return self.generate_template_prompt(score_description, classes)

    def generate_template_prompt(self, score_description, classes):
        """Fallback template-based prompt generation"""
        class_descriptions = []
        for key, class_info in classes.items():
            class_descriptions.append(f"- {class_info['name']}: {class_info['description']}")
        
        prompt = f"""You are tasked with scoring survey responses based on the following criteria:

SCORING CRITERIA:
{score_description}

CLASSIFICATION CATEGORIES:
{chr(10).join(class_descriptions)}

For each survey response, you must:
1. Read the response carefully
2. Classify it into one of the categories above
3. Provide your classification in this exact format: CLASSIFICATION: [category_name]

Please be consistent in your classifications and consider the nuances of each response."""
        
        return prompt

    def make_batch_inference_prompt(self, instructions, responses):
        """Create a batch inference prompt for processing multiple survey responses at once"""
        responses_json = {str(i): response for i, response in enumerate(responses)}
        prompt = f"""{instructions}

Responses = {json.dumps(responses_json, indent=4)}

Do not return any explanation or pre-amble.
Only return the scores in the format specified.

Return scores in this format:
{{
    "0": <score category>,
    "1": <score category>,
    ...
    "n": <score category>
}}
"""
        return prompt

    def get_score_json(self, response):
        """Parse the batch classification response and extract JSON scores"""
        print(f"Raw batch response length: {len(response)}")  # Debug logging
        print(f"Raw batch response preview: {response[:500]}...")  # Debug logging
        
        # Remove any markdown formatting
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            print(f"Found JSON match: {json_str[:200]}...")  # Debug logging
            try:
                score_json = json.loads(json_str)
                print(f"Successfully parsed JSON with {len(score_json)} entries")  # Debug logging
                return score_json
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")  # Debug logging
        
        # If direct parsing fails, try to parse the entire response
        try:
            score_json = json.loads(cleaned_response)
            print(f"Parsed entire response as JSON with {len(score_json)} entries")  # Debug logging
            return score_json
        except json.JSONDecodeError as e:
            print(f"Final JSON decode error: {e}")  # Debug logging
            raise ValueError(f"Could not parse JSON from response: {response[:200]}...")

    def process_json_file(self, file_path):
        """Process uploaded JSON file and extract responses"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle different JSON structures
            if isinstance(data, list):
                # If it's a list of objects, extract text from each
                responses = []
                for item in data:
                    if isinstance(item, dict):
                        # Try common text field names
                        text = item.get('text') or item.get('response') or item.get('comment') or item.get('feedback') or item.get('answer')
                        if text and str(text).strip():
                            responses.append({'text': str(text).strip()})
                    elif isinstance(item, str) and item.strip():
                        responses.append({'text': item.strip()})
            elif isinstance(data, dict):
                # Check if it has a responses array
                if 'responses' in data and isinstance(data['responses'], list):
                    responses = []
                    for item in data['responses']:
                        if isinstance(item, dict):
                            text = item.get('text') or item.get('response') or item.get('comment')
                            if text and str(text).strip():
                                responses.append({'text': str(text).strip()})
                        elif isinstance(item, str) and item.strip():
                            responses.append({'text': item.strip()})
                else:
                    # Try to extract values that look like text responses
                    responses = []
                    for key, value in data.items():
                        if isinstance(value, str) and value.strip() and len(value) > 10:
                            responses.append({'text': value.strip()})
            else:
                raise ValueError("JSON must be an array of objects or an object with responses")
            
            # Filter out empty responses and collect all valid responses
            valid_responses = []
            for resp in responses:
                text = resp.get('text', '').strip()
                if text and text.lower() not in ['na', 'n/a', 'null', 'none', '']:
                    valid_responses.append(resp)
            
            # If more than 15 responses, randomly select 15 with fixed seed
            if len(valid_responses) > 15:
                random.seed(42)  # Fixed seed for reproducible results
                valid_responses = random.sample(valid_responses, 15)
            
            return valid_responses
            
        except Exception as e:
            raise ValueError(f"Error processing JSON file: {str(e)}")

    def process_csv_file(self, file_path):
        """Process uploaded CSV file and return column information"""
        try:
            # Try to read with utf-8 encoding first
            with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                # Read CSV
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                columns = reader.fieldnames
                
                # Get preview data (first 5 rows)
                preview_data = []
                total_rows = 0
                for i, row in enumerate(reader):
                    if i < 5:
                        preview_data.append(dict(row))
                    total_rows += 1
            
            return {
                'columns': columns,
                'preview': preview_data,
                'total_rows': total_rows
            }
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1', newline='') as csvfile:
                    sample = csvfile.read(1024)
                    csvfile.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.DictReader(csvfile, delimiter=delimiter)
                    columns = reader.fieldnames
                    
                    preview_data = []
                    total_rows = 0
                    for i, row in enumerate(reader):
                        if i < 5:
                            preview_data.append(dict(row))
                        total_rows += 1
                
                return {
                    'columns': columns,
                    'preview': preview_data,
                    'total_rows': total_rows
                }
            except Exception as e:
                raise ValueError(f"Error reading CSV file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error processing CSV file: {str(e)}")

    def extract_csv_column_data(self, file_path, column_name):
        """Extract data from specific CSV column"""
        try:
            # Try to read with utf-8 encoding first
            with open(file_path, 'r', encoding='utf-8', newline='') as csvfile:
                # Detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                # Read CSV
                reader = csv.DictReader(csvfile, delimiter=delimiter)
                
                if column_name not in reader.fieldnames:
                    raise ValueError(f"Column '{column_name}' not found in CSV")
                
                # Extract column data and filter out missing values
                valid_responses = []
                for row in reader:
                    value = row.get(column_name, '').strip()
                    if value and value.lower() not in ['na', 'n/a', 'null', 'none', '', 'nan']:
                        valid_responses.append({'text': value})
            
            # If more than 15 responses, randomly select 15 with fixed seed
            if len(valid_responses) > 15:
                random.seed(42)  # Fixed seed for reproducible results
                valid_responses = random.sample(valid_responses, 15)
            
            return valid_responses
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1', newline='') as csvfile:
                    sample = csvfile.read(1024)
                    csvfile.seek(0)
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                    
                    reader = csv.DictReader(csvfile, delimiter=delimiter)
                    
                    if column_name not in reader.fieldnames:
                        raise ValueError(f"Column '{column_name}' not found in CSV")
                    
                    valid_responses = []
                    for row in reader:
                        value = row.get(column_name, '').strip()
                        if value and value.lower() not in ['na', 'n/a', 'null', 'none', '', 'nan']:
                            valid_responses.append({'text': value})
                
                # If more than 15 responses, randomly select 15 with fixed seed
                if len(valid_responses) > 15:
                    random.seed(42)  # Fixed seed for reproducible results
                    valid_responses = random.sample(valid_responses, 15)
                
                return valid_responses
            except Exception as e:
                raise ValueError(f"Error reading CSV file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error extracting CSV column data: {str(e)}")

    def run_batch_inference(self, responses, prompt):
        """Run batch inference on survey responses"""
        try:
            # Extract response texts for batch processing
            response_texts = []
            for response in responses:
                response_text = response.get('text', response.get('response', ''))
                response_texts.append(response_text)
            
            # Create batch inference prompt
            batch_prompt = self.make_batch_inference_prompt(prompt, response_texts)
            print(f"DEBUG: Created batch prompt with {len(batch_prompt)} characters")
            
            # Make single LLM call for all responses
            print("DEBUG: Calling generate_response...")
            batch_response = self.generate_response(batch_prompt)
            print(f"DEBUG: Got response with {len(batch_response)} characters")
            
            # Parse batch results
            try:
                score_json = self.get_score_json(batch_response)
                print(f"Parsed score_json: {score_json}")  # Debug logging
                
                # Convert batch results to individual results format
                results = []
                for i, response_text in enumerate(response_texts):
                    str_index = str(i)
                    if str_index in score_json:
                        classification = score_json[str_index].strip()  # Clean up whitespace
                        print(f"Response {i}: '{classification}'")  # Debug logging
                    else:
                        classification = 'error'
                        print(f"Response {i}: Missing from batch response")  # Debug logging
                    
                    results.append({
                        'response_text': response_text,
                        'ai_classification': classification,
                        'index': i
                    })
                
                print(f"Created {len(results)} results")  # Debug logging
                return results
                
            except Exception as parse_error:
                # If batch parsing fails, create error results for all responses
                print(f"Batch parsing error: {parse_error}")
                results = []
                for i, response_text in enumerate(response_texts):
                    results.append({
                        'response_text': response_text,
                        'ai_classification': 'error',
                        'index': i
                    })
                return results
        
        except Exception as e:
            # If batch processing completely fails, create error results
            print(f"=== DEBUG: Batch inference error: {e} ===")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            results = []
            for i, response in enumerate(responses):
                response_text = response.get('text', response.get('response', ''))
                results.append({
                    'response_text': response_text,
                    'ai_classification': 'error',
                    'index': i
                })
            return results

    def analyze_feedback_patterns(self, feedback_data, results, classes):
        """Analyze Step 6 feedback to identify patterns in misclassifications"""
        try:
            if not feedback_data or not feedback_data.get('feedback'):
                return None
            
            corrections = feedback_data.get('feedback', [])
            if not corrections:
                return None
            
            # Build pattern analysis
            patterns = {
                'total_corrections': len(corrections),
                'misclassification_patterns': {},
                'category_confusion_matrix': {},
                'common_errors': [],
                'specific_examples': []
            }
            
            # Analyze each correction
            for correction in corrections:
                original = correction.get('original_classification', '')
                corrected = correction.get('new_classification', '')
                feedback_text = correction.get('feedback', '')
                index = correction.get('index', 0)
                
                # Find the actual response text
                response_text = ''
                if index < len(results):
                    response_text = results[index].get('response_text', '')[:100] + '...'
                
                # Track misclassification patterns
                pattern_key = f"{original} → {corrected}"
                if pattern_key not in patterns['misclassification_patterns']:
                    patterns['misclassification_patterns'][pattern_key] = {
                        'count': 0,
                        'examples': []
                    }
                
                patterns['misclassification_patterns'][pattern_key]['count'] += 1
                patterns['misclassification_patterns'][pattern_key]['examples'].append({
                    'response': response_text,
                    'feedback': feedback_text,
                    'index': index
                })
                
                # Build confusion matrix
                if original not in patterns['category_confusion_matrix']:
                    patterns['category_confusion_matrix'][original] = {}
                if corrected not in patterns['category_confusion_matrix'][original]:
                    patterns['category_confusion_matrix'][original][corrected] = 0
                patterns['category_confusion_matrix'][original][corrected] += 1
                
                # Store specific examples for context
                patterns['specific_examples'].append({
                    'original_classification': original,
                    'corrected_classification': corrected,
                    'response_text': response_text,
                    'user_feedback': feedback_text,
                    'index': index
                })
            
            # Identify most common errors (patterns that occur more than once)
            for pattern, data in patterns['misclassification_patterns'].items():
                if data['count'] > 1:
                    patterns['common_errors'].append({
                        'pattern': pattern,
                        'count': data['count'],
                        'examples': data['examples'][:2]  # Limit examples for brevity
                    })
            
            # Sort common errors by frequency
            patterns['common_errors'].sort(key=lambda x: x['count'], reverse=True)
            
            return patterns
            
        except Exception as e:
            print(f"Error analyzing feedback: {e}")
            return None

    def generate_refined_prompt(self, original_prompt, feedback_analysis, classes, score_description):
        """Generate an improved prompt based on feedback analysis"""
        try:
            if not feedback_analysis or not feedback_analysis.get('misclassification_patterns'):
                return original_prompt, "No significant patterns found for improvement."
            
            # Prepare class information
            class_details = []
            class_names = []
            for key, class_info in classes.items():
                class_details.append(f"- {class_info['name']}: {class_info['description']}")
                class_names.append(class_info['name'])
            
            # Build improvement analysis for the LLM
            improvement_context = []
            
            # Add common error patterns
            if feedback_analysis.get('common_errors'):
                improvement_context.append("COMMON MISCLASSIFICATION PATTERNS:")
                for error in feedback_analysis['common_errors'][:3]:  # Top 3 errors
                    improvement_context.append(f"- {error['pattern']} (occurred {error['count']} times)")
                    if error['examples']:
                        improvement_context.append(f"  Example: \"{error['examples'][0]['response']}\"")
                        if error['examples'][0]['feedback']:
                            improvement_context.append(f"  User noted: \"{error['examples'][0]['feedback']}\"")
            
            # Add specific examples for context
            if feedback_analysis.get('specific_examples'):
                improvement_context.append("\nSPECIFIC CORRECTION EXAMPLES:")
                for example in feedback_analysis['specific_examples'][:3]:  # Top 3 examples
                    improvement_context.append(f"- Response: \"{example['response_text']}\"")
                    improvement_context.append(f"  AI classified as: {example['original_classification']}")
                    improvement_context.append(f"  Should be: {example['corrected_classification']}")
                    if example['user_feedback']:
                        improvement_context.append(f"  User explanation: \"{example['user_feedback']}\"")
            
            # Generate the prompt refinement request
            refinement_request = f"""You are tasked with improving a scoring prompt based on user feedback. The current prompt has some classification errors that need to be addressed.

CURRENT PROMPT:
{original_prompt}

ORIGINAL SCORING CRITERIA:
{score_description}

CLASSIFICATION CATEGORIES:
{chr(10).join(class_details)}

FEEDBACK ANALYSIS:
{chr(10).join(improvement_context)}

Please improve the prompt by:
1. Adding specific guidance to address the misclassification patterns identified above
2. Clarifying distinctions between categories that were frequently confused
4. Maintaining the overall structure and batch processing format
5. Using the exact category names: {', '.join(class_names)}
6. Minimizing the amount of extra text that is added to the prompt.

Focus on preventing the specific errors identified in the feedback. Be precise and specific in your improvements.

Generate the improved prompt:"""

            # Get the improved prompt from LLM
            improved_prompt = self.generate_response(refinement_request)
            
            # Generate rationale for the changes
            rationale_request = f"""Based on the feedback analysis provided, explain in 2-3 simple bullet points why the following changes were made to improve the prompt:

ORIGINAL ISSUES IDENTIFIED:
{chr(10).join(improvement_context[:10])}  # Limit context for rationale

Provide a concise explanation of the key improvements made to address these classification errors. Format your response as plain text using simple em dashes for bullet points, like this:

— Added specific guidance to prevent confusion between X and Y categories
— Clarified edge case handling for ambiguous responses  
— Enhanced examples to improve consistency

Use simple, readable formatting with em dashes (—) for bullets. Focus on the technical reasoning behind the specific changes made."""

            rationale = self.generate_response(rationale_request)
            
            return improved_prompt.strip(), rationale.strip()
            
        except Exception as e:
            print(f"Error generating refined prompt: {e}")
            return original_prompt, f"Error generating improvements: {str(e)}"

    def create_intelligent_diff(self, old_prompt, new_prompt):
        """Create an intelligent word-level diff"""
        try:
            # Create word-level diff using difflib
            old_words = old_prompt.split()
            new_words = new_prompt.split()
            
            # Use SequenceMatcher for intelligent comparison
            matcher = difflib.SequenceMatcher(None, old_words, new_words)
            
            # Build inline diff HTML
            inline_diff_html = []
            
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == 'equal':
                    # Unchanged text
                    inline_diff_html.append(' '.join(old_words[i1:i2]))
                elif tag == 'delete':
                    # Deleted text (red)
                    deleted_text = ' '.join(old_words[i1:i2])
                    inline_diff_html.append(f'<span class="diff-deleted">{html.escape(deleted_text)}</span>')
                elif tag == 'insert':
                    # Added text (green)
                    added_text = ' '.join(new_words[j1:j2])
                    inline_diff_html.append(f'<span class="diff-added">{html.escape(added_text)}</span>')
                elif tag == 'replace':
                    # Changed text (show both old and new)
                    deleted_text = ' '.join(old_words[i1:i2])
                    added_text = ' '.join(new_words[j1:j2])
                    inline_diff_html.append(f'<span class="diff-deleted">{html.escape(deleted_text)}</span>')
                    inline_diff_html.append(f'<span class="diff-added">{html.escape(added_text)}</span>')
            
            # Join with spaces and fix line breaks
            inline_diff = ' '.join(inline_diff_html)
            
            # Restore paragraph structure by replacing multiple spaces with line breaks
            # This is a simple heuristic - we could make it more sophisticated
            inline_diff = re.sub(r'(\. )', r'\1\n\n', inline_diff)  # Add breaks after sentences
            inline_diff = re.sub(r'\n\n+', r'\n\n', inline_diff)  # Clean up multiple breaks
            
            # Count changes for statistics
            changes_count = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag != 'equal')
            
            # Calculate similarity ratio
            similarity_ratio = matcher.ratio()
            
            # Extract key changes for summary
            key_changes = []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag != 'equal':
                    if tag == 'delete':
                        key_changes.append({
                            'type': 'deletion',
                            'text': ' '.join(old_words[i1:i2])[:50] + ('...' if i2-i1 > 10 else ''),
                            'context': 'Removed content'
                        })
                    elif tag == 'insert':
                        key_changes.append({
                            'type': 'addition',
                            'text': ' '.join(new_words[j1:j2])[:50] + ('...' if j2-j1 > 10 else ''),
                            'context': 'Added content'
                        })
                    elif tag == 'replace':
                        key_changes.append({
                            'type': 'modification',
                            'old_text': ' '.join(old_words[i1:i2])[:30] + ('...' if i2-i1 > 5 else ''),
                            'new_text': ' '.join(new_words[j1:j2])[:30] + ('...' if j2-j1 > 5 else ''),
                            'context': 'Modified content'
                        })
            
            return {
                'inline_diff_html': inline_diff,
                'changes_count': changes_count,
                'similarity_ratio': round(similarity_ratio * 100, 1),
                'key_changes': key_changes[:5],  # Limit to top 5 changes
                'original_prompt': old_prompt,
                'improved_prompt': new_prompt
            }
            
        except Exception as e:
            print(f"Error creating intelligent diff: {e}")
            return {
                'inline_diff_html': 'Error generating diff visualization',
                'changes_count': 0,
                'similarity_ratio': 0,
                'key_changes': [],
                'original_prompt': old_prompt,
                'improved_prompt': new_prompt
            }

    # === SESSION MANAGEMENT METHODS ===
    
    def save_consolidated_session(self, session_data):
        """Save consolidated session object to single file"""
        filename = f"session_{self.session.session_id}_object.json"
        filepath = os.path.join(self.session.temp_dir, filename)
        
        # Add metadata
        session_data['session_id'] = self.session.session_id
        session_data['timestamps'] = {
            'last_updated': datetime.datetime.now().isoformat()
        }
        
        # Add created timestamp if not exists
        if 'timestamps' not in session_data or 'created' not in session_data['timestamps']:
            if 'timestamps' not in session_data:
                session_data['timestamps'] = {}
            session_data['timestamps']['created'] = datetime.datetime.now().isoformat()
        
        with open(filepath, 'w') as f:
            json.dump(session_data, f, indent=4)
        
        print(f"DEBUG: Saved consolidated session to {filename}")
        return filepath

    def load_consolidated_session(self):
        """Load consolidated session object"""
        filename = f"session_{self.session.session_id}_object.json"
        filepath = os.path.join(self.session.temp_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f"DEBUG: Loaded consolidated session from {filename}")
                return data
        else:
            print(f"DEBUG: Consolidated session file not found: {filename}")
            return None

    def save_response_data(self, responses):
        """Save response texts to separate file"""
        filename = f"session_{self.session.session_id}_responses.json"
        filepath = os.path.join(self.session.temp_dir, filename)
        
        response_data = {
            'session_id': self.session.session_id,
            'responses': []
        }
        
        # Convert responses to ID-based format
        for i, response in enumerate(responses):
            response_data['responses'].append({
                'id': response.get('id', i + 1),
                'text': response.get('text', response.get('response', ''))
            })
        
        with open(filepath, 'w') as f:
            json.dump(response_data, f, indent=4)
        
        print(f"DEBUG: Saved response data to {filename}")
        return filepath

    def load_response_data(self):
        """Load response texts from separate file"""
        filename = f"session_{self.session.session_id}_responses.json"
        filepath = os.path.join(self.session.temp_dir, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                print(f"DEBUG: Loaded response data from {filename}")
                return data.get('responses', [])
        else:
            print(f"DEBUG: Response data file not found: {filename}")
            return []

    def get_consolidated_session_data(self, key=None):
        """Get data from consolidated session"""
        session_obj = self.load_consolidated_session()
        
        if session_obj:
            # Map legacy keys to consolidated structure
            if key == 'survey_data':
                responses = self.load_response_data()
                return {
                    'title': session_obj.get('survey_metadata', {}).get('title', ''),
                    'description': session_obj.get('survey_metadata', {}).get('description', ''),
                    'responses': responses
                }
            elif key == 'classes':
                return session_obj.get('scoring_criteria', {}).get('classes', {})
            elif key == 'initial_prompt':
                return session_obj.get('prompt_data', {}).get('initial_prompt', '')
            elif key == 'user_feedback':
                return session_obj.get('user_feedback', {})
            elif key == 'iteration_history':
                return session_obj.get('prompt_data', {}).get('iteration_history', [])
            elif key == 'current_iteration_data':
                return session_obj.get('current_iteration_data', {})
            elif key is None:
                return session_obj
            else:
                return session_obj.get(key, None)
        else:
            print(f"DEBUG: No consolidated session found for key: {key}")
            return None

    def save_consolidated_session_data(self, key, data):
        """Save data to consolidated session format"""
        # Load existing session or create new one
        session_obj = self.load_consolidated_session() or {
            'workflow_state': {},
            'survey_metadata': {},
            'scoring_criteria': {},
            'prompt_data': {},
            'inference_results': [],
            'user_feedback': {},
            'current_iteration_data': {}
        }
        
        # Update specific section based on key
        if key == 'survey_data':
            # Extract and save responses separately
            responses = data.get('responses', [])
            if responses:
                self.save_response_data(responses)
            
            # Update metadata
            session_obj['survey_metadata'] = {
                'title': data.get('title', ''),
                'description': data.get('description', ''),
                'response_count': len(responses),
                'response_ids': [r.get('id', i+1) for i, r in enumerate(responses)]
            }
            
        elif key == 'classes':
            session_obj['scoring_criteria']['classes'] = data
            
        elif key == 'initial_prompt':
            session_obj['prompt_data']['initial_prompt'] = data
            
        elif key == 'user_feedback':
            session_obj['user_feedback'] = data
            
        elif key == 'iteration_history':
            session_obj['prompt_data']['iteration_history'] = data
            
        elif key == 'current_iteration_data':
            session_obj['current_iteration_data'] = data
            
        else:
            # Direct key assignment
            session_obj[key] = data
        
        # Update workflow state
        session_obj['workflow_state'].update({
            'step': self.session.get('step', 1),
            'selected_example': self.session.get('selected_example', ''),
            'iteration_count': self.get_iteration_count()
        })
        
        # Update score description from session
        if 'score_description' in self.session.data:
            session_obj['scoring_criteria']['score_description'] = self.session.data['score_description']
        
        self.save_consolidated_session(session_obj)

    def save_results_to_file(self, results):
        """Save results to consolidated session only (no legacy files)"""
        # Update consolidated session with results
        try:
            session_obj = self.load_consolidated_session() or {
                'workflow_state': {},
                'survey_metadata': {},
                'scoring_criteria': {},
                'prompt_data': {},
                'inference_results': [],
                'user_feedback': {}
            }
            
            # Convert results to ID-based format for consolidated session
            responses = self.load_response_data()
            consolidated_results = []
            
            for i, result in enumerate(results):
                response_id = i + 1  # Default
                if i < len(responses):
                    response_id = responses[i].get('id', i + 1)
                
                consolidated_results.append({
                    'response_id': response_id,
                    'ai_classification': result.get('ai_classification', result.get('classification', '')),
                    'index': result.get('index', i)
                })
            
            session_obj['inference_results'] = consolidated_results
            self.save_consolidated_session(session_obj)
            print(f"DEBUG: Saved {len(consolidated_results)} results to consolidated session only")
            
        except Exception as e:
            print(f"DEBUG: Failed to update consolidated session with results: {e}")
        
        return None  # No legacy file path to return

    def load_results_from_file(self):
        """Load results from consolidated session"""
        # Try consolidated session first
        session_obj = self.load_consolidated_session()
        if session_obj and session_obj.get('inference_results'):
            # Convert consolidated format back to legacy format
            consolidated_results = session_obj['inference_results']
            responses = self.load_response_data()
            response_map = {r.get('id'): r.get('text', '') for r in responses}
            
            legacy_results = []
            for result in consolidated_results:
                response_id = result.get('response_id')
                response_text = response_map.get(response_id, '')
                
                legacy_results.append({
                    'response_text': response_text,
                    'response': response_text,  # Backward compatibility
                    'ai_classification': result.get('ai_classification', ''),
                    'classification': result.get('ai_classification', ''),  # Backward compatibility
                    'index': result.get('index', 0)
                })
            
            print(f"DEBUG: Loaded {len(legacy_results)} results from consolidated session")
            return legacy_results
        
        print("DEBUG: No results found in consolidated session")
        return []

    def get_iteration_count(self):
        """Get current iteration count from session"""
        return self.session.get('iteration_count', 0)

    def increment_iteration_count(self):
        """Increment and return iteration count"""
        current = self.get_iteration_count()
        self.session.set('iteration_count', current + 1)
        return self.session.get('iteration_count')

    def reset_iteration_count(self):
        """Reset iteration count for new session"""
        self.session.set('iteration_count', 0)