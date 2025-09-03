// JavaScript for Custom Summary Creation Tool

$(document).ready(function() {
    
    // Step 1: Tab switching for data source selection
    $('.tab-button').click(function() {
        const tabName = $(this).data('tab');
        
        // Update active tab button
        $('.tab-button').removeClass('active');
        $(this).addClass('active');
        
        // Update active tab content
        $('.tab-content').removeClass('active');
        $(`#${tabName}-tab`).addClass('active');
    });
    
    // Step 1: File upload handling
    const uploadZone = $('#upload-zone');
    const fileInput = $('#file-input');
    
    // Click to upload
    uploadZone.click(function() {
        fileInput.click();
    });
    
    // Drag and drop
    uploadZone.on('dragover', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).addClass('dragover');
    });
    
    uploadZone.on('dragleave', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
    });
    
    uploadZone.on('drop', function(e) {
        e.preventDefault();
        e.stopPropagation();
        $(this).removeClass('dragover');
        
        const files = e.originalEvent.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
    
    // File input change
    fileInput.change(function() {
        const files = this.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });
    
    // Column selection change
    $('#column-select').change(function() {
        const selectedColumn = $(this).val();
        $('#process-csv').prop('disabled', !selectedColumn);
    });
    
    // Process CSV button
    $('#process-csv').click(function() {
        const selectedColumn = $('#column-select').val();
        const filename = $(this).data('filename');
        
        if (selectedColumn && filename) {
            processCsvColumn(filename, selectedColumn);
        }
    });
    
    // File upload handler
    function handleFileUpload(file) {
        // Validate file
        if (!file) return;
        
        if (file.size > 10 * 1024 * 1024) {
            alert('File too large. Please upload files smaller than 10MB.');
            return;
        }
        
        const allowedTypes = ['application/json', 'text/csv', 'application/csv'];
        const isValidType = allowedTypes.includes(file.type) || 
                           file.name.toLowerCase().endsWith('.json') || 
                           file.name.toLowerCase().endsWith('.csv');
                           
        if (!isValidType) {
            alert('Please upload a JSON or CSV file.');
            return;
        }
        
        // Show upload progress
        $('#upload-zone').hide();
        $('#upload-progress').show();
        $('#upload-status').text('Uploading file...');
        
        // Create form data
        const formData = new FormData();
        formData.append('file', file);
        
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 30;
            if (progress > 90) progress = 90;
            $('#upload-progress-bar').css('width', progress + '%');
        }, 200);
        
        // Upload file
        $.ajax({
            url: '/upload_data',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                clearInterval(progressInterval);
                $('#upload-progress-bar').css('width', '100%');
                
                if (response.success) {
                    if (response.file_type === 'csv') {
                        // Show CSV column selection
                        showCsvColumnSelection(response);
                    } else {
                        // Show JSON success
                        showUploadSuccess(response);
                    }
                } else {
                    showUploadError(response.message);
                }
            },
            error: function(xhr) {
                clearInterval(progressInterval);
                const response = xhr.responseJSON || {};
                showUploadError(response.message || 'Upload failed. Please try again.');
            }
        });
    }
    
    function showCsvColumnSelection(response) {
        $('#upload-progress').hide();
        
        // Build CSV preview table
        let previewHtml = '<table class="csv-table"><thead><tr>';
        response.columns.forEach(col => {
            previewHtml += `<th>${col}</th>`;
        });
        previewHtml += '</tr></thead><tbody>';
        
        response.preview.forEach(row => {
            previewHtml += '<tr>';
            response.columns.forEach(col => {
                const value = row[col] || '';
                const truncated = value.length > 50 ? value.substring(0, 50) + '...' : value;
                previewHtml += `<td title="${value.replace(/"/g, '&quot;')}">${truncated}</td>`;
            });
            previewHtml += '</tr>';
        });
        previewHtml += '</tbody></table>';
        
        $('#csv-preview').html(previewHtml);
        
        // Populate all column selects
        const columnSelect = $('#column-select');
        const conversationIdSelect = $('#conversation-id-select');
        const authorSelect = $('#author-select');
        
        // Clear and populate response column (required)
        columnSelect.empty().append('<option value="">-- Select Column --</option>');
        
        // Clear and populate required columns
        conversationIdSelect.empty().append('<option value="">-- Select Column --</option>');
        authorSelect.empty().append('<option value="">-- Select Column --</option>');
        
        response.columns.forEach(col => {
            // Response column with recommendations
            const isResponseRecommended = /comment|response|text|feedback|review|answer|content|message/i.test(col);
            columnSelect.append(`<option value="${col}"${isResponseRecommended ? ' selected' : ''}>${col}${isResponseRecommended ? ' (recommended)' : ''}</option>`);
            
            // Conversation ID column with recommendations
            const isIdRecommended = /conversation.*id|conv.*id|^id$/i.test(col);
            conversationIdSelect.append(`<option value="${col}"${isIdRecommended && conversationIdSelect.val() === '' ? ' selected' : ''}>${col}${isIdRecommended ? ' (recommended)' : ''}</option>`);
            
            // Author column with recommendations
            const isAuthorRecommended = /author|user|name|speaker|agent|customer|participant|sender/i.test(col);
            authorSelect.append(`<option value="${col}"${isAuthorRecommended && authorSelect.val() === '' ? ' selected' : ''}>${col}${isAuthorRecommended ? ' (recommended)' : ''}</option>`);
        });
        
        // Store filename for processing
        $('#process-csv').data('filename', response.filename);
        
        // Show column selection interface
        $('#column-selection').show();
        
        // Enable process button only if ALL THREE columns are selected
        updateProcessButtonState();
        
        // Add event handlers for all column selects to update button state
        $('#column-select, #conversation-id-select, #author-select').on('change', updateProcessButtonState);
    }
    
    function updateProcessButtonState() {
        const responseCol = $('#column-select').val();
        const convIdCol = $('#conversation-id-select').val();
        const authorCol = $('#author-select').val();
        
        // Enable button only if all three columns are selected
        const allSelected = responseCol && convIdCol && authorCol;
        $('#process-csv').prop('disabled', !allSelected);
        
        if (allSelected) {
            $('#process-csv').text('Process Selected Columns');
        } else {
            $('#process-csv').text('Select All Required Columns');
        }
    }
    
    function processCsvColumn(filename, column) {
        $('#process-csv').prop('disabled', true)
                         .text('🔄 Processing Selected Columns...')
                         .addClass('btn-processing');
        
        // Get optional column selections
        const conversationId = $('#conversation-id-select').val();
        const author = $('#author-select').val();
        
        $.ajax({
            url: '/process_csv',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                filename: filename,
                column: column,
                conversation_id_column: conversationId,
                author_column: author
            }),
            success: function(response) {
                if (response.success) {
                    showUploadSuccess(response);
                } else {
                    alert(response.message);
                    $('#process-csv').prop('disabled', false)
                                     .text('Process Selected Columns')
                                     .removeClass('btn-processing');
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                alert(response.message || 'Processing failed. Please try again.');
                $('#process-csv').prop('disabled', false)
                                 .text('Process Selected Columns')
                                 .removeClass('btn-processing');
            }
        });
    }
    
    function showUploadSuccess(response) {
        $('#upload-progress').hide();
        $('#column-selection').hide();
        
        $('#upload-filename').text(response.original_filename || 'File uploaded successfully');
        $('#upload-summary').text(`Found ${response.response_count} valid responses`);
        $('#uploaded-file-input').val(response.filename);
        
        $('#upload-success').show();
    }
    
    function showUploadError(message) {
        $('#upload-progress').hide();
        $('#upload-zone').show();
        alert(message);
    }
    
    // Step 5: Auto-start inference (handled in template inline script)
    
    // Step 6: Compact Review Interface
    $('.is-correct').on('change', function() {
        const checkbox = $(this);
        const reviewItem = checkbox.closest('.review-item');
        const correctionSection = reviewItem.find('.correction-section');
        
        if (checkbox.is(':checked')) {
            // Hide correction section when marked as correct
            correctionSection.hide();
            reviewItem.removeClass('needs-correction');
        } else {
            // Show correction section when marked as incorrect
            correctionSection.show();
            reviewItem.addClass('needs-correction');
        }
    });
    
    $('#submit-feedback').click(function() {
        const button = $(this);
        
        // Collect feedback data and count changes
        const feedbackData = [];
        let changesCount = 0;
        
        $('.review-item').each(function() {
            const item = $(this);
            const index = item.data('index');
            const isCorrect = item.find('.is-correct').is(':checked');
            const originalClassification = item.find('.is-correct').data('original');
            
            if (!isCorrect) {
                // Item is marked as incorrect, collect correction data
                // Try to find summary correction first, fall back to classification select
                let newValue = item.find('.summary-correction').val();
                if (!newValue) {
                    // Fallback for classification mode
                    newValue = item.find('.classification-select').val();
                }
                const feedbackText = item.find('.feedback-text').val().trim();
                
                changesCount++;
                feedbackData.push({
                    index: index,
                    original_classification: originalClassification,
                    new_classification: newValue,
                    original_summary: originalClassification, // For compatibility
                    new_summary: newValue,
                    feedback: feedbackText
                });
            }
        });
        
        // Calculate total reviewed for the request
        const totalReviewed = $('.review-item').length;
        
        button.prop('disabled', true)
              .text('🔄 Analyzing Feedback & Improving Instructions...')
              .addClass('btn-processing');
        
        // Add processing indicator
        const processingIndicator = $('<div class="processing-indicator">')
            .html(`
                <div class="processing-spinner"></div>
                <div class="processing-steps">
                    <div class="step-item active">📊 Analyzing your feedback...</div>
                    <div class="step-item">🔧 Generating improved instructions...</div>
                    <div class="step-item">✅ Applying improvements...</div>
                </div>
            `)
            .insertAfter(button.closest('.action-buttons-row'));
        
        // Progressive step updates
        setTimeout(() => {
            if (processingIndicator.length) {
                processingIndicator.find('.step-item').removeClass('active');
                processingIndicator.find('.step-item:eq(1)').addClass('active');
            }
        }, 2000);
        
        setTimeout(() => {
            if (processingIndicator.length) {
                processingIndicator.find('.step-item').removeClass('active');
                processingIndicator.find('.step-item:eq(2)').addClass('active');
            }
        }, 4000);
        
        // Submit feedback
        $.ajax({
            url: '/submit_feedback',
            method: 'POST',
            contentType: 'application/json',
            dataType: 'json',  // Explicitly tell jQuery to expect JSON
            data: JSON.stringify({
                feedback: feedbackData,
                total_reviewed: totalReviewed,
                changes_count: changesCount
            }),
            success: function(response) {
                console.log('Feedback submission successful:', response);
                console.log('Response status:', response.status);
                console.log('Response redirect:', response.redirect);
                
                // Clean up processing indicator
                processingIndicator.remove();
                
                if (response.status === 'no_changes') {
                    console.log('Handling no_changes case');
                    alert(response.message);
                    button.prop('disabled', false)
                          .text('Submit Feedback & Improve Instructions')
                          .removeClass('btn-processing');
                } else if (response.status === 'iterate') {
                    console.log('Handling iterate case - redirecting to:', response.redirect);
                    // Update final step before redirect
                    processingIndicator.find('.step-item').removeClass('active');
                    processingIndicator.find('.step-item:eq(2)').addClass('active');
                    
                    try {
                        console.log('Attempting window.location.href redirect...');
                        window.location.href = response.redirect;
                        console.log('Redirect command executed');
                    } catch (redirect_error) {
                        console.error('Redirect failed:', redirect_error);
                        console.log('Trying fallback redirect method...');
                        window.location.replace(response.redirect);
                    }
                } else {
                    console.log('Handling fallback case, status was:', response.status);
                    if (response.redirect) {
                        console.log('Fallback redirecting to:', response.redirect);
                        window.location.href = response.redirect;
                    } else {
                        console.log('No redirect URL in response');
                        button.prop('disabled', false)
                              .text('Submit Feedback & Improve Instructions')
                              .removeClass('btn-processing');
                    }
                }
            },
            error: function(xhr, status, error) {
                console.error('=== AJAX ERROR DEBUG ===');
                console.error('Error:', error);
                console.error('Status:', status);
                console.error('XHR Status:', xhr.status);
                console.error('XHR Response Text:', xhr.responseText);
                console.error('XHR Ready State:', xhr.readyState);
                console.error('XHR Status Text:', xhr.statusText);
                console.error('XHR Response Headers:', xhr.getAllResponseHeaders());
                console.error('========================');
                
                // Clean up processing indicator and reset button
                processingIndicator.remove();
                button.prop('disabled', false)
                      .text('Submit Feedback & Improve Instructions')
                      .removeClass('btn-processing');
                alert('Error submitting feedback. Check console for details.');
            },
            timeout: 30000, // Increase to 30 second timeout
            complete: function(xhr, status) {
                console.log('=== AJAX COMPLETE DEBUG ===');
                console.log('Final status:', status);
                console.log('XHR status:', xhr.status);
                console.log('Response headers:', xhr.getAllResponseHeaders());
                console.log('==========================');
            }
        });
    });
    
    // Rerun inference on unseen examples
    $('#rerun-unseen').click(function() {
        const button = $(this);
        const originalText = button.text();
        
        // Disable button and show processing state
        button.prop('disabled', true)
              .text('🔄 Selecting Unseen Examples...')
              .addClass('btn-processing');
        
        // Submit request to preselect unseen examples and redirect to Step 5
        $.ajax({
            url: '/preselect_unseen',
            method: 'POST',
            success: function(response) {
                if (response.status === 'success') {
                    console.log('Successfully preselected unseen examples, redirecting to Step 5');
                    // Redirect to Step 5 which will immediately process the preselected examples
                    window.location.href = response.redirect;
                } else {
                    alert('Error: ' + (response.message || 'Unknown error occurred'));
                    button.prop('disabled', false)
                          .text(originalText)
                          .removeClass('btn-processing');
                }
            },
            error: function(xhr, status, error) {
                console.error('Preselect unseen error:', xhr.responseText);
                let errorMsg = 'Error selecting unseen examples';
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMsg += ': ' + xhr.responseJSON.message;
                }
                alert(errorMsg);
                button.prop('disabled', false)
                      .text(originalText)
                      .removeClass('btn-processing');
            },
            timeout: 30000 // 30 second timeout for selection
        });
    });
    
    // Initialize checkbox handlers for dynamically loaded content
    $(document).on('change', '.is-correct', function() {
        const checkbox = $(this);
        const reviewItem = checkbox.closest('.review-item');
        const correctionSection = reviewItem.find('.correction-section');
        
        if (checkbox.is(':checked')) {
            correctionSection.hide();
            reviewItem.removeClass('needs-correction');
        } else {
            correctionSection.show();
            reviewItem.addClass('needs-correction');
        }
    });
    
    // Auto-save form data to session storage (for back button support)
    $('input, textarea, select').on('change input', function() {
        const field = $(this);
        const fieldName = field.attr('name') || field.attr('id');
        if (fieldName) {
            sessionStorage.setItem('form_' + fieldName, field.val());
        }
    });
    
    // Restore form data from session storage
    $('input, textarea, select').each(function() {
        const field = $(this);
        const fieldName = field.attr('name') || field.attr('id');
        if (fieldName) {
            const savedValue = sessionStorage.getItem('form_' + fieldName);
            if (savedValue) {
                field.val(savedValue);
            }
        }
    });
    
    // Clear session storage when starting new session
    if (window.location.pathname === '/' || window.location.pathname.includes('step/1')) {
        sessionStorage.clear();
    }
    
    // Character counter for text areas
    $('textarea').each(function() {
        const textarea = $(this);
        const maxLength = textarea.attr('maxlength');
        
        if (maxLength) {
            const counter = $('<div class="char-counter"></div>');
            textarea.after(counter);
            
            const updateCounter = () => {
                const remaining = maxLength - textarea.val().length;
                counter.text(`${remaining} characters remaining`);
                counter.css('color', remaining < 50 ? '#e74c3c' : '#666');
            };
            
            textarea.on('input', updateCounter);
            updateCounter();
        }
    });
    
    // Add smooth scrolling for long forms
    $('html').css('scroll-behavior', 'smooth');
    
    // Focus first input field on page load
    setTimeout(() => {
        $('input:visible, textarea:visible, select:visible').first().focus();
    }, 100);
    
    // Step 2: Handle "see more examples" functionality
    $('#see-more-examples').click(function(e) {
        e.preventDefault();
        $('#additional-examples').slideDown(300);
        $(this).hide();
        $('#see-less-examples').show();
    });
    
    $('#see-less-examples').click(function(e) {
        e.preventDefault();
        $('#additional-examples').slideUp(300);
        $(this).hide();
        $('#see-more-examples').show();
    });
    
    // Add loading state for form submissions
    $('form').on('submit', function(e) {
        const form = $(this);
        const currentStep = $('.step.active .step-number').text();
        
        if (currentStep === '1') {
            const submitButton = form.find('button[type="submit"]');
            
            submitButton.prop('disabled', true)
                       .text('Analyzing Input Data...')
                       .addClass('generating');
        } else if (currentStep === '2') {
            const submitButton = form.find('button[type="submit"]');
            
            submitButton.prop('disabled', true)
                       .text('Generating Summary Types...')
                       .addClass('generating');
        } else if (currentStep === '3') {
            const submitButton = form.find('button[type="submit"]');
            
            submitButton.prop('disabled', true)
                       .text('Generating Summary Prompt...')
                       .addClass('generating');
        }
        
        // Add CSS for generating state (if not already added)
        if (!$('#generating-styles').length) {
            $('<style id="generating-styles">')
                .prop('type', 'text/css')
                .html(`
                    .btn.generating {
                        background-color: #9b59b6 !important;
                        animation: pulse 1.5s infinite;
                    }
                    @keyframes pulse {
                        0% { opacity: 1; }
                        50% { opacity: 0.7; }
                        100% { opacity: 1; }
                    }
                `)
                .appendTo('head');
        }
    });
    
    // Step 7: Iteration functionality - No longer needed as iteration happens automatically in submit_feedback
    // Keeping for reference but commented out
    /*
    $('#iterate-prompt').click(function() {
        const button = $(this);
        button.prop('disabled', true)
              .text('🔄 Analyzing Feedback...')
              .addClass('btn-processing');
        
        // Add processing indicator to show something is happening
        const processingIndicator = $('<div class="processing-indicator">')
            .html('<div class="processing-spinner"></div><p>Analyzing your feedback and improving instructions...</p>')
            .insertAfter(button.closest('.iteration-buttons'));
        
        $.ajax({
            url: '/iterate_prompt',
            method: 'POST',
            success: function(response) {
                console.log('Iteration started successfully:', response);
                // Update indicator before redirect
                processingIndicator.html('<div class="processing-success">✅ Analysis complete! Redirecting...</div>');
                setTimeout(() => {
                    window.location.href = response.redirect;
                }, 1000);
            },
            error: function(xhr, status, error) {
                console.error('Iteration error:', error, xhr.responseText);
                const response = xhr.responseJSON || {};
                alert(response.message || 'Failed to start iteration. Please try again.');
                button.prop('disabled', false)
                      .text('🔄 Iterate on Summarization Instructions')
                      .removeClass('btn-processing');
                processingIndicator.remove();
            }
        });
    });
    */
    
    $('#finish-session').click(function() {
        // Just hide the iteration section to show the final results
        $('.iteration-section').slideUp();
    });
    
    // Step 7.5: Iteration approval/rejection
    $('#approve-iteration').click(function() {
        const button = $(this);
        button.prop('disabled', true).text('✅ Applying Changes...');
        
        $.ajax({
            url: '/approve_iteration',
            method: 'POST',
            success: function(response) {
                console.log('Iteration approved:', response);
                // Redirect immediately without popup, like Step 4
                window.location.href = response.redirect;
            },
            error: function(xhr, status, error) {
                console.error('Approval error:', error, xhr.responseText);
                const response = xhr.responseJSON || {};
                alert(response.message || 'Failed to approve iteration. Please try again.');
                button.prop('disabled', false).text('✅ Apply Changes & Continue');
            }
        });
    });
    
    $('#reject-iteration').click(function() {
        const button = $(this);
        button.prop('disabled', true).text('❌ Rejecting Changes...');
        
        $.ajax({
            url: '/reject_iteration',
            method: 'POST',
            success: function(response) {
                console.log('Iteration rejected:', response);
                window.location.href = response.redirect;
            },
            error: function(xhr, status, error) {
                console.error('Rejection error:', error, xhr.responseText);
                const response = xhr.responseJSON || {};
                alert(response.message || 'Failed to reject iteration. Please try again.');
                button.prop('disabled', false).text('❌ Keep Original Prompt');
            }
        });
    });
    
    // Step 3: Dynamic Participant Management for Data Source Analysis
    let participantIndex = $('.participant-row').length || 1;
    
    // Add participant functionality
    $('#add-participant').click(function() {
        const newParticipantRow = `
            <div class="participant-row" data-index="${participantIndex}">
                <div class="participant-fields">
                    <input type="text" 
                           name="participant_role_${participantIndex}" 
                           value=""
                           placeholder="Role (e.g., Agent, Customer)"
                           class="form-control participant-role">
                    <input type="text" 
                           name="participant_desc_${participantIndex}" 
                           value=""
                           placeholder="Role description"
                           class="form-control participant-desc">
                    <button type="button" class="btn btn-sm btn-outline-danger remove-participant">Remove</button>
                </div>
            </div>
        `;
        
        $('#participants-container').append(newParticipantRow);
        participantIndex++;
        
        // Focus on the new role input
        $(`input[name="participant_role_${participantIndex-1}"]`).focus();
    });
    
    // Remove participant functionality (using event delegation for dynamically added elements)
    $(document).on('click', '.remove-participant', function() {
        const participantRow = $(this).closest('.participant-row');
        
        // Don't allow removing the last participant
        if ($('.participant-row').length > 1) {
            participantRow.remove();
        } else {
            // If it's the last one, just clear the values
            participantRow.find('input').val('');
        }
    });
    
    // Auto-resize textareas
    $('textarea.analysis-textarea').on('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Initialize textarea height on page load
    $('textarea.analysis-textarea').each(function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
    
    // Step 6: Export Instructions button
    $('#export-instructions').click(function(e) {
        e.preventDefault();
        window.location.href = '/step/final';
    });
    
    // Step Final: Copy Instructions String functionality
    $('#copy-instructions-json').click(function(e) {
        e.preventDefault();
        
        // Get the instructions text from the pre element
        const instructionsText = $('#instructions-content').text();
        
        // Create JSON string with the instructions
        const jsonString = JSON.stringify({
            "instructions": instructionsText
        });
        
        // Copy to clipboard
        if (navigator.clipboard && window.isSecureContext) {
            // Modern approach
            navigator.clipboard.writeText(jsonString).then(function() {
                showCopySuccess();
            }).catch(function(err) {
                console.error('Failed to copy: ', err);
                fallbackCopy(jsonString);
            });
        } else {
            // Fallback for older browsers or non-HTTPS
            fallbackCopy(jsonString);
        }
    });
    
    function fallbackCopy(text) {
        // Create temporary textarea element
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            showCopySuccess();
        } catch (err) {
            console.error('Fallback copy failed: ', err);
            alert('Failed to copy to clipboard. Please copy the text manually.');
        } finally {
            document.body.removeChild(textArea);
        }
    }
    
    function showCopySuccess() {
        const successMessage = $('#copy-success-message');
        successMessage.show();
        setTimeout(function() {
            successMessage.fadeOut();
        }, 3000);
    }
    
});