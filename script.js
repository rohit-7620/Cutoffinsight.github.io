document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('predictor-form');
    const resultsArea = document.getElementById('results-area');
    const resultsBody = document.getElementById('results-body');
    const errorMessageDiv = document.getElementById('error-message');
    const loadingIndicator = document.getElementById('loading-indicator');
    const noResultsMessage = document.getElementById('no-results-message');
    const resultsTableContainer = document.getElementById('results-table-container');
    const submitButton = document.getElementById('submit-button');

    // --- Collapsible Section Logic ---
    const collapsibleHeaders = document.querySelectorAll('.collapsible > .collapsible-header');
    collapsibleHeaders.forEach(header => {
        const content = header.nextElementSibling;
        // Set initial state if needed (e.g., start collapsed)
        content.style.maxHeight = null;
        content.style.paddingTop = null;
        header.classList.remove('active'); // Ensure starts collapsed

        header.addEventListener('click', () => {
            header.classList.toggle('active');
            if (content.style.maxHeight) {
                // Collapse
                content.style.maxHeight = null;
                content.style.paddingTop = null;
            } else {
                // Expand
                content.style.paddingTop = '20px'; 
                content.style.maxHeight = content.scrollHeight + "px";
            }
        });
    });
    // --- End Collapsible Section Logic ---

    // --- Form Submission Logic ---
    if (!form) {
        console.error("Predictor form element not found.");
        return; 
    }

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        handleFormSubmit();
    });

    async function handleFormSubmit() {
        // --- UI Reset and Loading State --- 
        resultsArea.classList.remove('results-hidden');
        loadingIndicator.style.display = 'flex';
        errorMessageDiv.style.display = 'none';
        resultsTableContainer.style.display = 'none';
        noResultsMessage.style.display = 'none';
        resultsBody.innerHTML = '';
        submitButton.disabled = true;
        submitButton.textContent = 'Predicting...';

        // --- Get Form Data --- 
        const formData = new FormData(form);
        const data = {};
        let hasRequiredFields = true;
        const requiredFields = ['rank', 'category', 'pool'];

        formData.forEach((value, key) => {
            if (value) { 
                data[key] = value.trim(); // Trim whitespace
            }
        });

        // --- Input Validation --- 
        for (const field of requiredFields) {
            if (!data[field]) {
                hasRequiredFields = false;
                break;
            }
        }

        if (!hasRequiredFields) {
            showError("Please fill in all required fields: Rank, Category, and Gender Pool.");
            resetButtonState();
            loadingIndicator.style.display = 'none';
            return;
        }
        
        // Validate rank is a positive number
        const rankValue = parseInt(data.rank, 10);
        if (isNaN(rankValue) || rankValue <= 0) {
             showError("Rank must be a positive whole number.");
             resetButtonState();
             loadingIndicator.style.display = 'none';
             return;
        }
        data.rank = rankValue; // Ensure rank is sent as a number

        // --- Call API --- 
        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json' // Explicitly accept JSON
                },
                body: JSON.stringify(data),
            });

            // Attempt to parse JSON regardless of status code for better error info
            let result;
            try {
                result = await response.json();
            } catch (jsonError) {
                // Handle cases where response is not JSON (e.g., HTML error page)
                console.error("JSON Parse Error:", jsonError);
                showError(`Server returned a non-JSON response (Status: ${response.status}). Check network tab or server logs.`);
                loadingIndicator.style.display = 'none';
                resetButtonState();
                return;
            }

            loadingIndicator.style.display = 'none';

            if (!response.ok) {
                // Use error message from JSON if available, otherwise use status
                showError(result?.error || `Server error: ${response.status}.`);
            } else if (result.error) {
                // Handle application-specific errors returned in JSON
                showError(result.error);
            } else if (result.colleges && result.colleges.length > 0) {
                // Success: Display results
                displayResults(result.colleges);
                resultsTableContainer.style.display = 'block';
            } else {
                // Success but no colleges found
                noResultsMessage.style.display = 'block';
            }

        } catch (error) {
            // Handle network errors or issues with fetch itself
            console.error("Fetch/Network Error:", error);
            loadingIndicator.style.display = 'none';
            showError("A network error occurred. Please check your connection and try again.");
        } finally {
            resetButtonState();
        }
    }

    // --- Helper Functions --- 
    function displayResults(colleges) {
        const colInst = 'institute_short';
        const colProg = 'program_name';
        const colDegree = 'degree_short';
        const colYear = 'year';
        const colRound = 'round_no';
        const colRank = 'closing_rank';

        // Clear previous results
        resultsBody.innerHTML = ''; 

        colleges.forEach(college => {
            const row = resultsBody.insertRow();
            row.insertCell().textContent = college[colInst] ?? 'N/A'; // Use nullish coalescing
            row.insertCell().textContent = college[colProg] ?? 'N/A';
            row.insertCell().textContent = college[colDegree] ?? 'N/A';
            row.insertCell().textContent = college[colYear] ?? 'N/A';
            row.insertCell().textContent = college[colRound] ?? 'N/A';
            row.insertCell().textContent = college[colRank] ?? 'N/A';
        });
    }

    function showError(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
        resultsTableContainer.style.display = 'none'; // Hide table on error
        noResultsMessage.style.display = 'none'; // Hide no-results message on error
    }

    function resetButtonState() {
         submitButton.disabled = false;
         submitButton.textContent = 'Predict Colleges';
    }
}); 