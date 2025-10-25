// API endpoint (your Flask server)
const API_URL = 'http://localhost:5000/add-company';

// Wait for DOM to load
document.addEventListener('DOMContentLoaded', async () => {
    // Get current tab info
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Auto-fill URL field with current page URL
    document.getElementById('careersUrl').value = tab.url;

    // Try to extract company name from page title
    // (e.g., "Careers - Boston Dynamics" → "Boston Dynamics")
    const pageTitle = tab.title;
    const companyName = extractCompanyName(pageTitle);
    if (companyName) {
        document.getElementById('companyName').value = companyName;
    }

    // Handle form submission
    document.getElementById('addCompanyForm').addEventListener('submit', handleSubmit);
});

// Extract company name from page title
function extractCompanyName(title) {
    // Remove common suffixes
    let name = title
        .replace(/\s*[-|]\s*careers?.*$/i, '')
        .replace(/\s*[-|]\s*jobs?.*$/i, '')
        .replace(/\s*[-|]\s*join\s+us.*$/i, '')
        .trim();

    return name || '';
}

// Handle form submission
async function handleSubmit(event) {
    event.preventDefault(); // Prevent page reload

    const submitBtn = document.getElementById('submitBtn');
    const messageDiv = document.getElementById('message');

    // Get form values
    const companyName = document.getElementById('companyName').value.trim();
    const careersUrl = document.getElementById('careersUrl').value.trim();
    const notes = document.getElementById('notes').value.trim();

    // Disable button while submitting
    submitBtn.disabled = true;
    submitBtn.textContent = 'Adding...';

    try {
        // Send POST request to Flask API
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: companyName,
                careers_url: careersUrl,
                notes: notes
            })
        });

        const data = await response.json();

        if (data.success) {
            // Success!
            showMessage(`✓ ${companyName} added successfully!`, 'success');

            // Clear form
            document.getElementById('addCompanyForm').reset();

            // Re-populate URL (in case user wants to add another from same page)
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
            document.getElementById('careersUrl').value = tab.url;
        } else {
            // API returned error (e.g., duplicate)
            showMessage(`Error: ${data.error}`, 'error');
        }

    } catch (error) {
        // Network error or Flask server not running
        showMessage(`Failed to connect to server. Is Flask running?`, 'error');
        console.error('Error:', error);
    } finally {
        // Re-enable button
        submitBtn.disabled = false;
        submitBtn.textContent = 'Add Company';
    }
}

// Show success/error message
function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = `message ${type}`;
    messageDiv.style.display = 'block';

    // Hide message after 5 seconds
    setTimeout(() => {
        messageDiv.style.display = 'none';
    }, 5000);
}