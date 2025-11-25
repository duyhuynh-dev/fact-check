// Use same origin since frontend is served by FastAPI
const API_BASE = window.location.origin;

// DOM Elements
const fileInput = document.getElementById('fileInput');
const uploadBox = document.getElementById('uploadBox');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultsSection = document.getElementById('results');
const claimsList = document.getElementById('claimsList');
const newDocumentBtn = document.getElementById('newDocumentBtn');

let currentDocumentId = null;
let checkInterval = null;

// Initialize
uploadBox.addEventListener('click', () => fileInput.click());
uploadBox.addEventListener('dragover', handleDragOver);
uploadBox.addEventListener('drop', handleDrop);
fileInput.addEventListener('change', handleFileSelect);
newDocumentBtn.addEventListener('click', resetUpload);

function handleDragOver(e) {
    e.preventDefault();
    uploadBox.style.borderColor = '#000';
    uploadBox.style.background = '#fff';
}

function handleDrop(e) {
    e.preventDefault();
    uploadBox.style.borderColor = '#e9ecef';
    uploadBox.style.background = '#f8f9fa';
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
}

async function handleFile(file) {
    // Support PDF, DOCX, TXT, and image formats (PNG, JPG, JPEG, GIF, WEBP, BMP)
    if (!file.name.match(/\.(pdf|docx|txt|png|jpg|jpeg|gif|webp|bmp)$/i)) {
        alert('Please upload a PDF, DOCX, TXT, or image file (PNG, JPG, GIF, WEBP, BMP)');
        return;
    }

    uploadBox.style.display = 'none';
    uploadProgress.style.display = 'block';
    updateProgress(10, 'Uploading document...');

    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name);
        formData.append('source_type', 'upload');

        updateProgress(30, 'Sending to server...');
        const response = await fetch(`${API_BASE}/v1/documents`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            // Try to get error details from response (read body only once)
            let errorMessage = `Upload failed: ${response.status} ${response.statusText}`;
            try {
                const contentType = response.headers.get('content-type') || '';
                let errorText = '';
                
                // Read the response body only once
                if (contentType.includes('application/json')) {
                    const errorData = await response.json();
                    if (errorData.detail) {
                        errorText = errorData.detail;
                    } else if (errorData.message) {
                        errorText = errorData.message;
                    } else if (typeof errorData === 'string') {
                        errorText = errorData;
                    } else {
                        errorText = JSON.stringify(errorData);
                    }
                } else {
                    errorText = await response.text();
                }
                
                if (errorText) {
                    errorMessage += ` - ${errorText.substring(0, 200)}`;
                }
            } catch (e) {
                // If we can't parse the error, just use the status
                console.error('Error parsing error response:', e);
            }
            throw new Error(errorMessage);
        }

        const document = await response.json();
        currentDocumentId = document.id;
        
        updateProgress(50, 'Processing document...');
        await waitForIngestion(document.id);
        
    } catch (error) {
        console.error('Upload error:', error);
        alert(`Error: ${error.message}`);
        resetUpload();
    }
}

async function waitForIngestion(documentId) {
    updateProgress(60, 'Extracting claims...');
    
    return new Promise((resolve, reject) => {
        let attempts = 0;
        const maxAttempts = 180; // allow up to 3 minutes for large docs
        
        checkInterval = setInterval(async () => {
            attempts++;
            
            try {
                const response = await fetch(`${API_BASE}/v1/documents/${documentId}`);
                if (!response.ok) throw new Error('Failed to check status');
                
                const doc = await response.json();
                
                if (doc.ingest_status === 'succeeded') {
                    clearInterval(checkInterval);
                    updateProgress(80, 'Loading evidence...');
                    await loadEvidence();
                    updateProgress(90, 'Verifying claims...');
                    await verifyClaims(documentId);
                    updateProgress(100, 'Complete!');
                    setTimeout(() => {
                        showResults(documentId);
                        resolve();
                    }, 500);
                } else if (doc.ingest_status === 'failed') {
                    clearInterval(checkInterval);
                    throw new Error(doc.ingest_failure_reason || 'Ingestion failed');
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    throw new Error('Processing timeout');
                } else {
                    // Use actual progress from backend if available
                    const progress = doc.ingest_progress !== null ? 
                        (60 + doc.ingest_progress * 30) : 
                        (60 + (attempts * 0.3));
                    const message = doc.ingest_progress_message || 'Processing...';
                    updateProgress(progress, message);
                }
            } catch (error) {
                clearInterval(checkInterval);
                reject(error);
            }
        }, 1000);
    });
}

async function loadEvidence() {
    // Load sample evidence (you can customize this)
    const evidenceContent = `The Holocaust, also known as the Shoah, was the genocide of European Jews during World War II.
Between 1941 and 1945, Nazi Germany and its collaborators systematically murdered approximately six million Jews,
around two-thirds of Europe's Jewish population. The murders were carried out through mass shootings,
concentration camps, and extermination camps. The Holocaust is one of the most extensively documented
genocides in history, with millions of pages of documentation, thousands of photographs, and extensive
survivor testimonies. Holocaust denial is illegal in many countries and is widely condemned as antisemitic.`;

    const blob = new Blob([evidenceContent], { type: 'text/plain' });
    const formData = new FormData();
    formData.append('file', blob, 'evidence.txt');
    formData.append('source_name', 'Holocaust Encyclopedia');

    try {
        await fetch(`${API_BASE}/v1/evidence/load`, {
            method: 'POST',
            body: formData
        });
    } catch (error) {
        console.warn('Evidence loading failed:', error);
        // Continue anyway
    }
}

async function verifyClaims(documentId) {
    try {
        await fetch(`${API_BASE}/v1/documents/${documentId}/claims:verify`, {
            method: 'POST'
        });
    } catch (error) {
        console.warn('Verification failed:', error);
        // Continue anyway
    }
}

async function showResults(documentId) {
    uploadProgress.style.display = 'none';
    resultsSection.style.display = 'block';
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
    
    try {
        // Load document info
        const docResponse = await fetch(`${API_BASE}/v1/documents/${documentId}`);
        if (!docResponse.ok) {
            const errorText = await docResponse.text();
            throw new Error(`Failed to load document (${docResponse.status}): ${errorText}`);
        }
        const docData = await docResponse.json();
        
        document.getElementById('documentTitle').textContent = docData.title || 'Document';
        const statusBadge = document.getElementById('statusBadge');
        statusBadge.textContent = docData.ingest_status;
        statusBadge.className = `status-badge ${docData.ingest_status}`;
        
        // Load results
        const resultsResponse = await fetch(`${API_BASE}/v1/documents/${documentId}/results`);
        if (!resultsResponse.ok) {
            const errorText = await resultsResponse.text();
            throw new Error(`Failed to load results (${resultsResponse.status}): ${errorText}`);
        }
        const results = await resultsResponse.json();
        
        displayResults(results);
        
        // Load claims
        const claimsResponse = await fetch(`${API_BASE}/v1/documents/${documentId}/claims`);
        if (!claimsResponse.ok) {
            const errorText = await claimsResponse.text();
            throw new Error(`Failed to load claims (${claimsResponse.status}): ${errorText}`);
        }
        const claimsData = await claimsResponse.json();
        
        displayClaims(claimsData.items);
    } catch (error) {
        console.error('Error loading results:', error);
        alert(`Error loading results: ${error.message}`);
    }
}

function displayResults(results) {
    // Score
    const score = results.overall_score || 0;
    const scoreValue = document.getElementById('scoreValue');
    const scoreCircle = document.getElementById('scoreCircle');
    const riskLevel = document.getElementById('riskLevel');
    
    scoreValue.textContent = score !== null ? Math.round(score) : '--';
    
    if (score !== null) {
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (score / 100) * circumference;
        scoreCircle.style.strokeDashoffset = offset;
    }
    
    riskLevel.textContent = results.risk_level || 'unknown';
    riskLevel.className = `risk-level ${results.risk_level}`;
    
    // Verdict stats
    const vs = results.verdict_summary;
    document.getElementById('statSupported').textContent = vs.supported;
    document.getElementById('statPartial').textContent = vs.partial;
    document.getElementById('statContradicted').textContent = vs.contradicted;
    document.getElementById('statNoEvidence').textContent = vs.no_evidence;
    document.getElementById('statNotApplicable').textContent = vs.not_applicable || 0;
    document.getElementById('statAntisemiticTrope').textContent = vs.antisemitic_trope || 0;
}

function displayClaims(claims) {
    claimsList.innerHTML = '';
    
    claims.forEach(claim => {
        const card = document.createElement('div');
        card.className = 'claim-card';
        
        const verdict = claim.verdict || 'unverified';
        const verdictClass = verdict.replace(/_/g, '-');  // Replace all underscores
        
        // Format verdict display
        let verdictDisplay = verdict;
        if (verdict === 'not_applicable') {
            verdictDisplay = 'Not Applicable';
        } else if (verdict === 'no_evidence') {
            verdictDisplay = 'No Evidence';
        } else if (verdict === 'antisemitic_trope') {
            verdictDisplay = 'Antisemitic Trope';
        }
        
        card.innerHTML = `
            <div class="claim-header">
                <div class="claim-text">${escapeHtml(claim.text)}</div>
                <div class="claim-verdict ${verdictClass}">${verdictDisplay}</div>
            </div>
            <div class="claim-details">
                <div class="claim-score">Score: ${claim.score !== null ? Math.round(claim.score) : 'N/A'}</div>
            </div>
            ${claim.rationale ? `<div class="claim-rationale">${escapeHtml(claim.rationale)}</div>` : ''}
        `;
        
        claimsList.appendChild(card);
    });
}

function updateProgress(percent, text) {
    progressFill.style.width = `${percent}%`;
    progressText.textContent = text;
}

function resetUpload() {
    if (checkInterval) {
        clearInterval(checkInterval);
    }
    currentDocumentId = null;
    uploadBox.style.display = 'block';
    uploadProgress.style.display = 'none';
    resultsSection.style.display = 'none';
    fileInput.value = '';
    document.getElementById('upload').scrollIntoView({ behavior: 'smooth' });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

