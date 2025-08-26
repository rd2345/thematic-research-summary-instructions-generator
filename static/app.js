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
                previewHtml += `<td>${row[col] || ''}</td>`;
            });
            previewHtml += '</tr>';
        });
        previewHtml += '</tbody></table>';
        
        $('#csv-preview').html(previewHtml);
        
        // Populate column select
        const columnSelect = $('#column-select');
        columnSelect.empty().append('<option value="">-- Select Column --</option>');
        
        response.columns.forEach(col => {
            const isRecommended = /comment|response|text|feedback|review|answer/i.test(col);
            const option = `<option value="${col}"${isRecommended ? ' selected' : ''}>${col}${isRecommended ? ' (recommended)' : ''}</option>`;
            columnSelect.append(option);
        });
        
        // Store filename for processing
        $('#process-csv').data('filename', response.filename);
        
        // Show column selection interface
        $('#column-selection').show();
        
        // Auto-enable process button if recommended column selected
        if (columnSelect.val()) {
            $('#process-csv').prop('disabled', false);
        }
    }
    
    function processCsvColumn(filename, column) {
        $('#process-csv').prop('disabled', true).text('Processing...');
        
        $.ajax({
            url: '/process_csv',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                filename: filename,
                column: column
            }),
            success: function(response) {
                if (response.success) {
                    showUploadSuccess(response);
                } else {
                    alert(response.message);
                    $('#process-csv').prop('disabled', false).text('Process Selected Column');
                }
            },
            error: function(xhr) {
                const response = xhr.responseJSON || {};
                alert(response.message || 'Processing failed. Please try again.');
                $('#process-csv').prop('disabled', false).text('Process Selected Column');
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
                const newClassification = item.find('.classification-select').val();
                const feedbackText = item.find('.feedback-text').val().trim();
                
                changesCount++;
                feedbackData.push({
                    index: index,
                    original_classification: originalClassification,
                    new_classification: newClassification,
                    feedback: feedbackText
                });
            }
        });
        
        // Calculate total reviewed for the request
        const totalReviewed = $('.review-item').length;
        
        button.prop('disabled', true).text('Processing Feedback...');
        
        // Submit feedback
        $.ajax({
            url: '/submit_feedback',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                feedback: feedbackData,
                total_reviewed: totalReviewed,
                changes_count: changesCount
            }),
            success: function(response) {
                console.log('Feedback submission successful:', response);
                // Always redirect to final results
                window.location.href = response.redirect;
            },
            error: function(xhr, status, error) {
                console.error('Feedback submission error:', error, xhr.responseText);
                button.prop('disabled', false).text('Submit Feedback & View Final Results');
            },
            timeout: 10000, // 10 second timeout
            complete: function() {
                console.log('AJAX request completed');
            }
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
    
    // Add loading state for class generation (Step 2 to Step 3)
    $('form').on('submit', function(e) {
        const form = $(this);
        const currentStep = $('.step.active .step-number').text();
        
        if (currentStep === '2') {
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
    
    // Step 7: Iteration functionality
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
    
});