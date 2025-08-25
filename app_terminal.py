#!/usr/bin/env python3
"""
Terminal interface for Summary Prompt Generation UX
Uses app_backend.py for all business logic
"""

import os
import sys
import json
import time
from typing import Dict, List, Any, Optional
from app_backend import SummaryPromptBackend, SessionManager


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title: str, step: int = None):
    """Print a formatted header"""
    print("=" * 80)
    if step:
        print(f"Step {step}: {title}")
    else:
        print(title)
    print("=" * 80)


def print_separator():
    """Print a separator line"""
    print("-" * 80)


def format_table(data: List[Dict], headers: List[str], max_width: int = 50) -> str:
    """Simple table formatting function"""
    if not data:
        return "No data to display"
    
    # Calculate column widths
    col_widths = []
    for header in headers:
        max_len = len(header)
        for row in data:
            if header in row:
                cell_value = str(row[header])
                if len(cell_value) > max_width:
                    cell_value = cell_value[:max_width-3] + "..."
                max_len = max(max_len, len(cell_value))
        col_widths.append(min(max_len, max_width))
    
    # Build table
    lines = []
    
    # Header
    header_line = " | ".join([headers[i].ljust(col_widths[i]) for i in range(len(headers))])
    lines.append(header_line)
    lines.append("-" * len(header_line))
    
    # Data rows
    for row in data:
        row_parts = []
        for i, header in enumerate(headers):
            cell_value = str(row.get(header, ""))
            if len(cell_value) > max_width:
                cell_value = cell_value[:max_width-3] + "..."
            row_parts.append(cell_value.ljust(col_widths[i]))
        lines.append(" | ".join(row_parts))
    
    return "\n".join(lines)


def progress_bar(current: int, total: int, width: int = 50):
    """Display a simple progress bar"""
    if total == 0:
        return ""
    
    progress = current / total
    filled = int(width * progress)
    bar = "█" * filled + "░" * (width - filled)
    percentage = int(progress * 100)
    return f"[{bar}] {percentage}% ({current}/{total})"


class TerminalInterface:
    """Terminal-based interface for the summary prompt generation workflow"""
    
    def __init__(self):
        self.backend = SummaryPromptBackend(SessionManager())
        self.current_step = 1
        self.workflow_data = {}
    
    def run(self):
        """Main entry point for the terminal interface"""
        clear_screen()
        print_header("Summary Prompt Generation - Terminal Interface")
        print("\nWelcome to the 7-step workflow for generating and refining survey summary prompts!")
        print("This tool helps you create AI prompts for summarizing survey responses consistently.")
        print("\nPress Enter to continue...")
        input()
        
        try:
            while True:
                if self.current_step == 1:
                    if self.step_1_select_survey():
                        self.current_step = 2
                elif self.current_step == 2:
                    if self.step_2_summary_description():
                        self.current_step = 3
                elif self.current_step == 3:
                    if self.step_3_generate_classes():
                        self.current_step = 4
                elif self.current_step == 4:
                    if self.step_4_review_prompt():
                        self.current_step = 5
                elif self.current_step == 5:
                    if self.step_5_run_inference():
                        self.current_step = 6
                elif self.current_step == 6:
                    if self.step_6_provide_feedback():
                        self.current_step = 7
                elif self.current_step == 7:
                    self.step_7_final_results()
                    break
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n\nWorkflow interrupted by user.")
            return
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            return
    
    def step_1_select_survey(self) -> bool:
        """Step 1: Select Survey Example"""
        while True:
            clear_screen()
            print_header("Select Survey Example", 1)
            
            print("Choose your data source:")
            print("1. Use pre-built example datasets")
            print("2. Upload custom JSON file")
            print("3. Upload custom CSV file")
            print("4. Exit")
            
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                return self._select_example_dataset()
            elif choice == "2":
                return self._upload_json_file()
            elif choice == "3":
                return self._upload_csv_file()
            elif choice == "4":
                print("Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
                input("Press Enter to continue...")
    
    def _select_example_dataset(self) -> bool:
        """Select from pre-built example datasets"""
        try:
            examples = self.backend.load_survey_examples()
            
            if not examples:
                print("No example datasets found in the examples/ directory.")
                input("Press Enter to go back...")
                return False
            
            clear_screen()
            print_header("Available Survey Examples", 1)
            
            example_list = list(examples.items())
            for i, (filename, info) in enumerate(example_list, 1):
                print(f"{i}. {info['name']} ({info['count']} responses)")
                if 'data' in info and 'description' in info['data']:
                    desc = info['data']['description']
                    if len(desc) > 100:
                        desc = desc[:100] + "..."
                    print(f"   Description: {desc}")
                print()
            
            while True:
                try:
                    choice = input(f"Select dataset (1-{len(example_list)}) or 'b' to go back: ").strip()
                    
                    if choice.lower() == 'b':
                        return False
                    
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(example_list):
                        selected_filename, selected_info = example_list[choice_idx]
                        selected_data = selected_info['data']
                        
                        # Save to workflow data
                        self.workflow_data['survey_data'] = selected_data
                        self.workflow_data['selected_example'] = selected_filename
                        
                        # Save to backend session
                        self.backend.save_consolidated_session_data('survey_data', selected_data)
                        self.backend.session.set('selected_example', selected_filename)
                        
                        print(f"\n✅ Selected: {selected_info['name']}")
                        print(f"   Responses: {len(selected_data.get('responses', []))}")
                        input("Press Enter to continue to Step 2...")
                        return True
                    else:
                        print("Invalid selection. Please try again.")
                
                except ValueError:
                    print("Please enter a valid number or 'b' to go back.")
                    
        except Exception as e:
            print(f"Error loading examples: {e}")
            input("Press Enter to go back...")
            return False
    
    def _upload_json_file(self) -> bool:
        """Handle JSON file upload"""
        clear_screen()
        print_header("Upload JSON File", 1)
        
        while True:
            filepath = input("Enter the full path to your JSON file (or 'b' to go back): ").strip()
            
            if filepath.lower() == 'b':
                return False
            
            if not filepath:
                print("Please enter a file path.")
                continue
            
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                continue
            
            if not filepath.lower().endswith('.json'):
                print("File must have a .json extension.")
                continue
            
            try:
                print("Processing JSON file...")
                responses = self.backend.process_json_file(filepath)
                
                if not responses:
                    print("No valid responses found in the JSON file.")
                    continue
                
                # Create survey data structure
                survey_data = {
                    'title': f'Uploaded: {os.path.basename(filepath)}',
                    'description': f'Custom data from {filepath}',
                    'responses': responses
                }
                
                # Save to workflow data
                self.workflow_data['survey_data'] = survey_data
                self.workflow_data['selected_example'] = f'uploaded_{os.path.basename(filepath)}'
                
                # Save to backend session
                self.backend.save_consolidated_session_data('survey_data', survey_data)
                self.backend.session.set('selected_example', f'uploaded_{os.path.basename(filepath)}')
                
                print(f"\n✅ Successfully processed JSON file!")
                print(f"   File: {os.path.basename(filepath)}")
                print(f"   Valid responses: {len(responses)}")
                input("Press Enter to continue to Step 2...")
                return True
                
            except Exception as e:
                print(f"Error processing JSON file: {e}")
                print("Please check your file format and try again.")
                continue
    
    def _upload_csv_file(self) -> bool:
        """Handle CSV file upload"""
        clear_screen()
        print_header("Upload CSV File", 1)
        
        while True:
            filepath = input("Enter the full path to your CSV file (or 'b' to go back): ").strip()
            
            if filepath.lower() == 'b':
                return False
            
            if not filepath:
                print("Please enter a file path.")
                continue
            
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                continue
            
            if not filepath.lower().endswith('.csv'):
                print("File must have a .csv extension.")
                continue
            
            try:
                print("Analyzing CSV file...")
                csv_info = self.backend.process_csv_file(filepath)
                
                # Show column selection
                print(f"\nFound {csv_info['total_rows']} rows with the following columns:")
                for i, col in enumerate(csv_info['columns'], 1):
                    print(f"{i}. {col}")
                
                print(f"\nPreview of first few rows:")
                preview_data = []
                for row in csv_info['preview'][:3]:
                    preview_data.append(row)
                
                if preview_data:
                    print(format_table(preview_data, csv_info['columns']))
                
                while True:
                    try:
                        col_choice = input(f"\nSelect column containing survey responses (1-{len(csv_info['columns'])}) or 'b' to go back: ").strip()
                        
                        if col_choice.lower() == 'b':
                            break
                        
                        col_idx = int(col_choice) - 1
                        if 0 <= col_idx < len(csv_info['columns']):
                            selected_column = csv_info['columns'][col_idx]
                            
                            print(f"Extracting data from column '{selected_column}'...")
                            responses = self.backend.extract_csv_column_data(filepath, selected_column)
                            
                            if not responses:
                                print("No valid responses found in the selected column.")
                                continue
                            
                            # Create survey data structure
                            survey_data = {
                                'title': f'Uploaded: {os.path.basename(filepath)} (Column: {selected_column})',
                                'description': f'Custom data from {filepath}, column: {selected_column}',
                                'responses': responses
                            }
                            
                            # Save to workflow data
                            self.workflow_data['survey_data'] = survey_data
                            self.workflow_data['selected_example'] = f'uploaded_{os.path.basename(filepath)}'
                            
                            # Save to backend session
                            self.backend.save_consolidated_session_data('survey_data', survey_data)
                            self.backend.session.set('selected_example', f'uploaded_{os.path.basename(filepath)}')
                            
                            print(f"\n✅ Successfully processed CSV file!")
                            print(f"   File: {os.path.basename(filepath)}")
                            print(f"   Column: {selected_column}")
                            print(f"   Valid responses: {len(responses)}")
                            input("Press Enter to continue to Step 2...")
                            return True
                        else:
                            print("Invalid selection. Please try again.")
                    
                    except ValueError:
                        print("Please enter a valid number or 'b' to go back.")
                
                # If we reach here, user chose to go back from column selection
                continue
                
            except Exception as e:
                print(f"Error processing CSV file: {e}")
                print("Please check your file format and try again.")
                continue
    
    def step_2_summary_description(self) -> bool:
        """Step 2: Summary Description"""
        clear_screen()
        print_header("Describe Summarization Criteria", 2)
        
        # Show dataset info
        survey_data = self.workflow_data.get('survey_data', {})
        print(f"Dataset: {survey_data.get('title', 'Unknown')}")
        print(f"Responses: {len(survey_data.get('responses', []))}")
        
        # Show sample responses
        responses = survey_data.get('responses', [])
        if responses:
            print("\nSample responses from your dataset:")
            print_separator()
            for i, response in enumerate(responses[:3], 1):
                text = response.get('text', '')
                if len(text) > 150:
                    text = text[:150] + "..."
                print(f"{i}. {text}")
            print_separator()
        
        print("\nNow describe what you want to summarize in these survey responses.")
        print("For example:")
        print("- 'I want to summarize customer satisfaction themes and sentiment patterns'")
        print("- 'Summarize responses focusing on product feedback and recommendation likelihood'")
        print("- 'Rate the responses based on technical knowledge and helpfulness'")
        
        while True:
            print("\nEnter your summarization description (2-3 sentences work best):")
            summary_description = input("> ").strip()
            
            if not summary_description:
                print("Please provide a summarization description.")
                continue
            
            if len(summary_description) < 10:
                print("Please provide a more detailed description (at least 10 characters).")
                continue
            
            # Confirm the description
            print(f"\nYour summarization criteria:")
            print(f"'{summary_description}'")
            confirm = input("\nIs this correct? (y/n/edit): ").strip().lower()
            
            if confirm == 'y':
                # Save to workflow data and backend
                self.workflow_data['summary_description'] = summary_description
                self.backend.session.set('summary_description', summary_description)
                
                print("\n⏳ Generating contextually relevant classification categories...")
                
                # Generate smart summary types based on the summary description
                try:
                    classes = self.backend.generate_smart_summary_types(summary_description)
                    self.workflow_data['classes'] = classes
                    self.backend.save_consolidated_session_data('classes', classes)
                    
                    print("✅ Classification categories generated successfully!")
                    input("Press Enter to continue to Step 3...")
                    return True
                    
                except Exception as e:
                    print(f"Error generating classes: {e}")
                    print("Using default classes instead.")
                    classes = self.backend.generate_default_classes()
                    self.workflow_data['classes'] = classes
                    self.backend.save_consolidated_session_data('classes', classes)
                    input("Press Enter to continue to Step 3...")
                    return True
            
            elif confirm == 'n':
                continue  # Ask for description again
            elif confirm == 'edit':
                continue  # Ask for description again
            else:
                print("Please enter 'y', 'n', or 'edit'.")
    
    def step_3_generate_classes(self) -> bool:
        """Step 3: Generate Classes"""
        clear_screen()
        print_header("Review Classification Categories", 3)
        
        classes = self.workflow_data.get('classes', {})
        if not classes:
            print("Error: No classes found. Returning to previous step.")
            self.current_step = 2
            return False
        
        print("AI has generated the following classification categories based on your scoring criteria:")
        print_separator()
        
        class_order = ['key_themes', 'sentiment_overview', 'not_relevant', 'unclear']
        for key in class_order:
            if key in classes:
                class_info = classes[key]
                print(f"Category: {class_info['name']}")
                print(f"Description: {class_info['description']}")
                print(f"Score: {class_info.get('score', 'N/A')}")
                print()
        
        print_separator()
        
        while True:
            choice = input("Would you like to (c)ontinue with these categories, (e)dit them, or go (b)ack? ").strip().lower()
            
            if choice == 'c':
                # Generate initial prompt
                summary_description = self.workflow_data.get('summary_description', '')
                print("\n⏳ Generating expert summarization prompt...")
                
                try:
                    initial_prompt = self.backend.generate_initial_summary_prompt(summary_description, self.workflow_data['classes'])
                    self.workflow_data['initial_prompt'] = initial_prompt
                    self.backend.save_consolidated_session_data('initial_prompt', initial_prompt)
                    
                    return True
                except Exception as e:
                    print(f"Error generating prompt: {e}")
                    initial_prompt = self.backend.generate_template_summary_prompt(summary_description, self.workflow_data['classes'])
                    self.workflow_data['initial_prompt'] = initial_prompt
                    self.backend.save_consolidated_session_data('initial_prompt', initial_prompt)
                    
                    return True
                    
            elif choice == 'e':
                if self._edit_classes():
                    # Regenerate prompt with edited classes
                    summary_description = self.workflow_data.get('summary_description', '')
                    print("\n⏳ Regenerating prompt with updated categories...")
                    
                    try:
                        initial_prompt = self.backend.generate_initial_summary_prompt(summary_description, self.workflow_data['classes'])
                        self.workflow_data['initial_prompt'] = initial_prompt
                        self.backend.save_consolidated_session_data('initial_prompt', initial_prompt)
                        
                        print("✅ Prompt regenerated successfully!")
                        input("Press Enter to continue to Step 4...")
                        return True
                        
                    except Exception as e:
                        print(f"Error regenerating prompt: {e}")
                        initial_prompt = self.backend.generate_template_summary_prompt(summary_description, self.workflow_data['classes'])
                        self.workflow_data['initial_prompt'] = initial_prompt
                        self.backend.save_consolidated_session_data('initial_prompt', initial_prompt)
                        input("Press Enter to continue to Step 4...")
                        return True
                        
            elif choice == 'b':
                self.current_step = 2
                return False
            else:
                print("Please enter 'c', 'e', or 'b'.")
    
    def _edit_classes(self) -> bool:
        """Edit classification classes"""
        classes = self.workflow_data.get('classes', {}).copy()
        class_order = ['key_themes', 'sentiment_overview', 'not_relevant', 'unclear']
        
        print("\n" + "="*60)
        print("EDITING CLASSIFICATION CATEGORIES")
        print("="*60)
        print("Press Enter to keep current value, or type new value to change it.")
        
        for key in class_order:
            if key in classes:
                class_info = classes[key]
                print(f"\n--- {key.replace('_', ' ').title()} Category ---")
                
                # Edit name
                current_name = class_info['name']
                print(f"Current name: {current_name}")
                new_name = input("New name (or Enter to keep): ").strip()
                if new_name:
                    class_info['name'] = new_name
                
                # Edit description
                current_desc = class_info['description']
                print(f"Current description: {current_desc}")
                new_desc = input("New description (or Enter to keep): ").strip()
                if new_desc:
                    class_info['description'] = new_desc
                
                # Edit score
                current_score = class_info.get('score', '')
                print(f"Current score: {current_score}")
                new_score = input("New score (or Enter to keep): ").strip()
                if new_score is not None and new_score != current_score:
                    class_info['score'] = new_score
        
        # Save the updated classes
        self.workflow_data['classes'] = classes
        self.backend.save_consolidated_session_data('classes', classes)
        
        print("\n✅ Categories updated successfully!")
        return True
    
    def step_4_review_prompt(self) -> bool:
        """Step 4: Review Prompt"""
        clear_screen()
        print_header("Review Generated Prompt", 4)
        
        initial_prompt = self.workflow_data.get('initial_prompt', '')
        if not initial_prompt:
            print("Error: No prompt found. Returning to previous step.")
            self.current_step = 3
            return False
        
        print("AI has generated the following expert scoring prompt:")
        print_separator()
        print(initial_prompt)
        print_separator()
        
        while True:
            choice = input("Would you like to (c)ontinue with this prompt, (e)dit it, or go (b)ack? ").strip().lower()
            
            if choice == 'c':
                input("Press Enter to continue to Step 5...")
                return True
            elif choice == 'e':
                if self._edit_prompt():
                    input("Press Enter to continue to Step 5...")
                    return True
            elif choice == 'b':
                self.current_step = 3
                return False
            else:
                print("Please enter 'c', 'e', or 'b'.")
    
    def _edit_prompt(self) -> bool:
        """Edit the prompt"""
        initial_prompt = self.workflow_data.get('initial_prompt', '')
        
        print("\n" + "="*60)
        print("EDITING PROMPT")
        print("="*60)
        print("Current prompt:")
        print(initial_prompt)
        print("="*60)
        
        print("\nEnter your edited prompt below.")
        print("Type 'DONE' on a new line when finished, or 'CANCEL' to cancel editing.")
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == 'DONE':
                    break
                elif line.strip() == 'CANCEL':
                    print("Edit cancelled.")
                    return False
                else:
                    lines.append(line)
            except EOFError:
                break
        
        new_prompt = '\n'.join(lines).strip()
        
        if not new_prompt:
            print("Empty prompt. Edit cancelled.")
            return False
        
        # Save the updated prompt
        self.workflow_data['initial_prompt'] = new_prompt
        self.backend.save_consolidated_session_data('initial_prompt', new_prompt)
        
        print("\n✅ Prompt updated successfully!")
        return True
    
    def step_5_run_inference(self) -> bool:
        """Step 5: Run Inference"""
        clear_screen()
        print_header("Run Batch Inference", 5)
        
        survey_data = self.workflow_data.get('survey_data', {})
        responses = survey_data.get('responses', [])
        prompt = self.workflow_data.get('initial_prompt', '')
        
        if not responses:
            print("Error: No survey responses found. Returning to Step 1.")
            self.current_step = 1
            return False
        
        if not prompt:
            print("Error: No prompt found. Returning to Step 4.")
            self.current_step = 4
            return False
        
        # Limit to 50 responses
        responses_to_process = responses[:50]
        
        print(f"Dataset: {survey_data.get('title', 'Unknown')}")
        print(f"Responses to process: {len(responses_to_process)}")
        print(f"Prompt length: {len(prompt)} characters")
        
        print(f"\n⏳ Starting batch inference processing...")
        print("This will process all responses in a single API call for efficiency.")
        
        # Show progress simulation
        total_steps = 10
        for i in range(total_steps + 1):
            print(f"\r{progress_bar(i, total_steps)} Processing responses...", end='', flush=True)
            time.sleep(0.3)  # Simulate processing time
        
        print()  # New line after progress bar
        
        try:
            # Run the actual batch inference
            results = self.backend.run_batch_inference(responses_to_process, prompt)
            
            if not results:
                print("❌ No results were generated. Please check your prompt and try again.")
                input("Press Enter to go back to Step 4...")
                self.current_step = 4
                return False
            
            # Save results
            self.workflow_data['results'] = results
            self.backend.save_results_to_file(results)
            
            print(f"\n✅ Batch processing completed successfully!")
            print(f"   Processed: {len(results)} responses")
            
            # Show summary statistics
            classification_counts = {}
            error_count = 0
            for result in results:
                classification = result.get('ai_classification', 'error')
                if classification == 'error':
                    error_count += 1
                else:
                    classification_counts[classification] = classification_counts.get(classification, 0) + 1
            
            if classification_counts:
                print(f"\nClassification Summary:")
                for category, count in sorted(classification_counts.items()):
                    print(f"   {category}: {count}")
            
            if error_count > 0:
                print(f"   Errors: {error_count}")
            
            input("Press Enter to continue to Step 6...")
            return True
            
        except Exception as e:
            print(f"\n❌ Error during batch processing: {e}")
            print("Please check your configuration and try again.")
            input("Press Enter to go back to Step 4...")
            self.current_step = 4
            return False
    
    def step_6_provide_feedback(self) -> bool:
        """Step 6: Provide Feedback"""
        clear_screen()
        print_header("Review Results and Provide Feedback", 6)
        
        results = self.workflow_data.get('results', [])
        classes = self.workflow_data.get('classes', {})
        
        if not results:
            print("Error: No results found. Returning to Step 5.")
            self.current_step = 5
            return False
        
        # Display results in organized format
        print(f"Results for {len(results)} responses:")
        print("Review the AI classifications below and provide corrections if needed.")
        print_separator()
        
        # Group results by classification for better organization
        classification_groups = {}
        for result in results:
            classification = result.get('ai_classification', 'error')
            if classification not in classification_groups:
                classification_groups[classification] = []
            classification_groups[classification].append(result)
        
        # Show grouped results with limited examples per category
        max_examples_per_category = 10
        total_displayed = 0
        
        for classification, group_results in classification_groups.items():
            print(f"\n=== {classification} ({len(group_results)} responses) ===")
            
            display_count = min(len(group_results), max_examples_per_category)
            for i in range(display_count):
                result = group_results[i]
                response_text = result.get('response_text', '')
                if len(response_text) > 100:
                    response_text = response_text[:100] + "..."
                
                print(f"{result.get('index', 0) + 1}. {response_text}")
            
            if len(group_results) > max_examples_per_category:
                print(f"   ... and {len(group_results) - max_examples_per_category} more")
            
            total_displayed += display_count
        
        print_separator()
        
        # Collect feedback
        feedback_data = {'feedback': []}
        corrections_made = 0
        
        print(f"\nTo provide feedback, enter response numbers and corrections.")
        print("Available categories:")
        for key, class_info in classes.items():
            print(f"  - {class_info['name']}")
        
        print(f"\nExample: '3 High Score' (changes response 3 to 'High Score')")
        print("Enter 'done' when finished, or 'skip' to continue without feedback.\n")
        
        while True:
            feedback_input = input("Enter feedback (response_number new_category) or 'done'/'skip': ").strip()
            
            if feedback_input.lower() in ['done', 'skip']:
                break
            
            if not feedback_input:
                continue
            
            # Parse feedback input
            parts = feedback_input.split(' ', 1)
            if len(parts) != 2:
                print("Please use format: 'response_number new_category' (e.g., '3 High Score')")
                continue
            
            try:
                response_num = int(parts[0])
                new_category = parts[1].strip()
                
                # Validate response number
                if response_num < 1 or response_num > len(results):
                    print(f"Response number must be between 1 and {len(results)}")
                    continue
                
                # Validate category name
                valid_categories = [class_info['name'] for class_info in classes.values()]
                if new_category not in valid_categories:
                    print(f"Category must be one of: {', '.join(valid_categories)}")
                    continue
                
                # Find the result to update
                result_index = response_num - 1
                original_classification = results[result_index].get('ai_classification', '')
                
                # Add to feedback data
                feedback_item = {
                    'index': result_index,
                    'original_classification': original_classification,
                    'new_classification': new_category,
                    'feedback': '',
                    'response_text': results[result_index].get('response_text', '')
                }
                
                feedback_data['feedback'].append(feedback_item)
                corrections_made += 1
                
                print(f"✅ Feedback recorded: Response {response_num} changed from '{original_classification}' to '{new_category}'")
                
            except ValueError:
                print("Please enter a valid response number.")
                continue
        
        # Save feedback data
        if corrections_made > 0:
            print(f"\n📝 {corrections_made} corrections recorded.")
            self.workflow_data['user_feedback'] = feedback_data
            self.backend.save_consolidated_session_data('user_feedback', feedback_data)
            
            # Apply corrections to results for final display
            feedback_lookup = {item['index']: item['new_classification'] for item in feedback_data['feedback']}
            for i, result in enumerate(results):
                if i in feedback_lookup:
                    result['final_classification'] = feedback_lookup[i]
                else:
                    result['final_classification'] = result.get('ai_classification', '')
        else:
            print("\nNo corrections provided.")
            # Set final classification same as AI classification
            for result in results:
                result['final_classification'] = result.get('ai_classification', '')
        
        # Update results with final classifications
        self.workflow_data['results'] = results
        
        input("Press Enter to continue to Step 7...")
        return True
    
    def step_7_final_results(self):
        """Step 7: Final Results"""
        clear_screen()
        print_header("Final Results", 7)
        
        results = self.workflow_data.get('results', [])
        user_feedback = self.workflow_data.get('user_feedback', {})
        classes = self.workflow_data.get('classes', {})
        
        if not results:
            print("Error: No results found.")
            return
        
        # Calculate final statistics
        final_classification_counts = {}
        for result in results:
            final_class = result.get('final_classification', 'error')
            final_classification_counts[final_class] = final_classification_counts.get(final_class, 0) + 1
        
        print(f"Processing complete for {len(results)} survey responses.")
        print(f"Dataset: {self.workflow_data.get('survey_data', {}).get('title', 'Unknown')}")
        
        print_separator()
        print("FINAL CLASSIFICATION SUMMARY:")
        print_separator()
        
        for category, count in sorted(final_classification_counts.items()):
            percentage = (count / len(results)) * 100 if results else 0
            print(f"{category:20s}: {count:3d} responses ({percentage:.1f}%)")
        
        print_separator()
        
        # Show feedback summary if provided
        feedback_corrections = user_feedback.get('feedback', [])
        if feedback_corrections:
            print(f"USER FEEDBACK SUMMARY:")
            print(f"Total corrections made: {len(feedback_corrections)}")
            print("Most common corrections:")
            
            # Count correction patterns
            correction_patterns = {}
            for correction in feedback_corrections:
                pattern = f"{correction['original_classification']} → {correction['new_classification']}"
                correction_patterns[pattern] = correction_patterns.get(pattern, 0) + 1
            
            for pattern, count in sorted(correction_patterns.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"  {pattern}: {count} times")
            
            print_separator()
        
        # Offer iteration option
        iteration_count = self.backend.get_iteration_count()
        max_iterations = 3
        
        if iteration_count < max_iterations and feedback_corrections:
            print(f"PROMPT IMPROVEMENT AVAILABLE:")
            print(f"Based on your feedback, I can improve the prompt to reduce similar errors.")
            print(f"Current iteration: {iteration_count}/{max_iterations}")
            
            improve = input("\nWould you like to improve the prompt and run another iteration? (y/n): ").strip().lower()
            
            if improve == 'y':
                if self._run_iteration():
                    return  # Will restart from Step 5 with improved prompt
        
        print(f"\n🎉 Workflow completed successfully!")
        print(f"All {len(results)} responses have been classified.")
        
        # Show option to start over
        print(f"\nOptions:")
        print(f"1. Start new workflow")
        print(f"2. Exit")
        
        while True:
            choice = input("Enter your choice (1-2): ").strip()
            if choice == "1":
                self.__init__()  # Reset the interface
                self.run()
                return
            elif choice == "2":
                print("Thank you for using Score Prompt Generation!")
                return
            else:
                print("Please enter 1 or 2.")
    
    def _run_iteration(self) -> bool:
        """Run prompt iteration based on user feedback"""
        try:
            print("\n⏳ Analyzing feedback patterns...")
            
            # Get required data
            user_feedback = self.workflow_data.get('user_feedback', {})
            results = self.workflow_data.get('results', [])
            classes = self.workflow_data.get('classes', {})
            original_prompt = self.workflow_data.get('initial_prompt', '')
            summary_description = self.workflow_data.get('summary_description', '')
            
            # Analyze feedback patterns
            feedback_analysis = self.backend.analyze_feedback_patterns(user_feedback, results, classes)
            
            if not feedback_analysis:
                print("❌ Unable to analyze feedback patterns.")
                return False
            
            print("✅ Feedback patterns analyzed.")
            print(f"   Total corrections: {feedback_analysis.get('total_corrections', 0)}")
            print(f"   Common error patterns: {len(feedback_analysis.get('common_errors', []))}")
            
            # Generate refined prompt
            print("\n⏳ Generating improved prompt...")
            
            improved_prompt, rationale = self.backend.generate_refined_prompt(
                original_prompt, feedback_analysis, classes, summary_description
            )
            
            print("✅ Improved prompt generated!")
            
            # Show improvement rationale
            print("\nIMPROVEMENT RATIONALE:")
            print_separator()
            print(rationale)
            print_separator()
            
            # Ask for approval
            approve = input("\nApprove this improved prompt and continue to re-run inference? (y/n): ").strip().lower()
            
            if approve == 'y':
                # Increment iteration count and update prompt
                self.backend.increment_iteration_count()
                self.workflow_data['initial_prompt'] = improved_prompt
                self.backend.save_consolidated_session_data('initial_prompt', improved_prompt)
                
                # Store iteration history
                iteration_history = self.backend.get_consolidated_session_data('iteration_history') or []
                iteration_history.append({
                    'iteration': self.backend.get_iteration_count(),
                    'original_prompt': original_prompt,
                    'improved_prompt': improved_prompt,
                    'rationale': rationale,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                })
                self.backend.save_consolidated_session_data('iteration_history', iteration_history)
                
                print(f"\n✅ Starting iteration {self.backend.get_iteration_count()} with improved prompt!")
                input("Press Enter to continue...")
                
                # Go back to Step 5 to re-run inference
                self.current_step = 5
                self.run()
                return True
            else:
                print("Iteration cancelled.")
                return False
                
        except Exception as e:
            print(f"❌ Error during iteration: {e}")
            return False


def main():
    """Main entry point"""
    try:
        interface = TerminalInterface()
        interface.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Please check your configuration and try again.")


if __name__ == "__main__":
    main()