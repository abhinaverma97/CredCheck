document.addEventListener('DOMContentLoaded', function () {
    // Elements
    const textBtn = document.getElementById('text-btn');
    const imageBtn = document.getElementById('image-btn');
    const audioBtn = document.getElementById('audio-btn');
    const videoBtn = document.getElementById('video-btn');
    const fileUploadContainer = document.getElementById('file-upload-container');
    const fileUpload = document.getElementById('file-upload');
    const headlineInput = document.getElementById('headline-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const analysisResultsContainer = document.getElementById('analysis-results');
    const fetchHeadlinesBtn = document.getElementById('fetch-headlines-btn');
    const headlinesContainer = document.getElementById('headlines-container');
    const headlinesAnalysis = document.getElementById('headlines-analysis');

    // Add new elements for real-time news
    const realTimeNewsContainer = document.getElementById('real-time-news-container');
    const fetchRealTimeNewsBtn = document.getElementById('fetch-real-time-news-btn');

    // Add elements for video feed
    const videoFeedContainer = document.getElementById('video-feed-container');
    const fetchVideoFeedBtn = document.getElementById('fetch-video-feed-btn');

    // Add elements for live broadcast
    const youtubePlayer = document.getElementById('youtube-player');
    const liveAnalysisResults = document.getElementById('live-analysis-results');
    const refreshLiveBroadcastBtn = document.getElementById('refresh-live-broadcast-btn');

    // YouTube player reference
    let player = null;

    // Auto-refresh timer for live broadcast
    let liveBroadcastRefreshTimer = null;

    // Initialize variables
    let inputType = 'Text';
    let analysisResults = [];

    // Add new elements for recent analyses and charts
    const recentAnalysesContainer = document.getElementById('recent-analyses');
    const statisticsContainer = document.getElementById('statistics');
    const newsDistributionChart = document.getElementById('news-distribution-chart');
    const analysisTrendChart = document.getElementById('analysis-trend-chart');

    // Chart objects
    let pieChart = null;
    let lineChart = null;

    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });

    // Custom file input label
    if (fileUpload) {
        fileUpload.addEventListener('change', function () {
            const fileName = this.files[0] ? this.files[0].name : 'Choose a file or drag it here';
            const fileLabel = document.querySelector('.file-label span');
            if (fileLabel) {
                fileLabel.textContent = fileName;
            }
        });
    }

    // Input method selection
    textBtn.addEventListener('click', function () {
        setActiveInputMethod(this, 'Text');
        fileUploadContainer.style.display = 'none';
        headlineInput.style.display = 'block';
    });

    imageBtn.addEventListener('click', function () {
        setActiveInputMethod(this, 'Image');
        fileUploadContainer.style.display = 'block';
        fileUpload.accept = "image/*";
        headlineInput.style.display = 'none';
    });

    audioBtn.addEventListener('click', function () {
        setActiveInputMethod(this, 'Audio');
        fileUploadContainer.style.display = 'block';
        fileUpload.accept = "audio/*";
        headlineInput.style.display = 'none';
    });

    videoBtn.addEventListener('click', function () {
        setActiveInputMethod(this, 'Video');
        fileUploadContainer.style.display = 'block';
        fileUpload.accept = "video/*";
        headlineInput.style.display = 'none';
    });

    function setActiveInputMethod(button, type) {
        // Remove active class from all buttons
        [textBtn, imageBtn, audioBtn, videoBtn].forEach(btn => {
            btn.classList.remove('active');
        });

        // Add active class to the clicked button
        button.classList.add('active');

        // Set the input type
        inputType = type;
    }

    // Analyze button click handler
    analyzeBtn.addEventListener('click', function () {
        // Clear previous results
        analysisResultsContainer.innerHTML = '';

        // Show loading indicator
        analysisResultsContainer.innerHTML = '<div class="loading"></div>';

        switch (inputType) {
            case 'Text':
                analyzeText();
                break;
            case 'Image':
                analyzeImage();
                break;
            case 'Audio':
                analyzeAudio();
                break;
            case 'Video':
                analyzeVideo();
                break;
        }
    });

    // Fetch headlines button click handler
    fetchHeadlinesBtn.addEventListener('click', function () {
        // Clear previous results
        headlinesContainer.innerHTML = '';
        headlinesAnalysis.innerHTML = '';

        // Show loading indicator
        headlinesContainer.innerHTML = '<div class="loading"></div>';

        fetchHeadlines();
    });

    // Real-time news button click handler
    if (fetchRealTimeNewsBtn) {
        fetchRealTimeNewsBtn.addEventListener('click', function () {
            // Clear previous results
            if (realTimeNewsContainer) {
                realTimeNewsContainer.innerHTML = '';
                realTimeNewsContainer.innerHTML = '<div class="loading"></div>';
            }

            fetchRealTimeNews();
        });
    }

    // Video feed button click handler
    if (fetchVideoFeedBtn) {
        fetchVideoFeedBtn.addEventListener('click', function () {
            // Clear previous results
            if (videoFeedContainer) {
                videoFeedContainer.innerHTML = '';
                videoFeedContainer.innerHTML = '<div class="loading">Loading video feed...</div>';
            }

            fetchVideoFeed();
        });
    }

    // Live broadcast refresh button click handler
    if (refreshLiveBroadcastBtn) {
        refreshLiveBroadcastBtn.addEventListener('click', function () {
            // Update live analysis results
            fetchLiveBroadcastAnalysis();
        });
    }

    // Make fetchRealTimeNews globally accessible
    window.fetchRealTimeNews = fetchRealTimeNews;

    // Make fetchVideoFeed globally accessible
    window.fetchVideoFeed = fetchVideoFeed;

    // Make fetchLiveBroadcastAnalysis globally accessible
    window.fetchLiveBroadcastAnalysis = fetchLiveBroadcastAnalysis;

    // Text analysis function with retry capability
    function analyzeText() {
        const headline = headlineInput.value.trim();

        if (!headline) {
            analysisResultsContainer.innerHTML = '<p class="error">Please enter a headline.</p>';
            return;
        }

        // Clear previous results and show loading
        analysisResultsContainer.innerHTML = '<div class="loading-container"><div class="loading-spinner"></div><p>Analyzing...</p></div>';

        // Small delay to ensure backend services are ready
        setTimeout(() => {
            fetchWithRetry('/analyze_text', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ headline: headline })
            }, 2) // Try up to 2 retries
                .then(data => {
                    displayAnalysisResults(data);
                })
                .catch(error => {
                    analysisResultsContainer.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                });
        }, 300);
    }

    // Fetch with retry capability
    function fetchWithRetry(url, options, retries = 1, delay = 1000) {
        return new Promise((resolve, reject) => {
            // Try the request
            fetch(url, options)
                .then(response => {
                    // Check if the response is ok
                    if (!response.ok) {
                        throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
                    }
                    return response.json();
                })
                .then(resolve)
                .catch(error => {
                    // If we have retries left, try again after delay
                    if (retries > 0) {
                        console.log(`Retrying fetch to ${url}, ${retries} retries left`);
                        setTimeout(() => {
                            fetchWithRetry(url, options, retries - 1, delay)
                                .then(resolve)
                                .catch(reject);
                        }, delay);
                    } else {
                        // No more retries, reject with the error
                        reject(error);
                    }
                });
        });
    }

    // Image analysis function with retry capability
    function analyzeImage() {
        const file = fileUpload.files[0];

        if (!file) {
            analysisResultsContainer.innerHTML = '<p class="error">Please upload an image file.</p>';
            return;
        }

        // Clear previous results and show loading
        analysisResultsContainer.innerHTML = '<div class="loading-container"><div class="loading-spinner"></div><p>Analyzing image...</p></div>';

        const formData = new FormData();
        formData.append('image_file', file);

        // Small delay to ensure backend services are ready
        setTimeout(() => {
            fetchWithRetry('/analyze_image', {
                method: 'POST',
                body: formData
            }, 2)
                .then(data => {
                    displayAnalysisResults(data);
                })
                .catch(error => {
                    analysisResultsContainer.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                });
        }, 300);
    }

    // Audio analysis function with retry capability
    function analyzeAudio() {
        const file = fileUpload.files[0];

        if (!file) {
            analysisResultsContainer.innerHTML = '<p class="error">Please upload an audio file.</p>';
            return;
        }

        // Clear previous results and show loading
        analysisResultsContainer.innerHTML = '<div class="loading-container"><div class="loading-spinner"></div><p>Analyzing audio...</p></div>';

        const formData = new FormData();
        formData.append('audio_file', file);

        // Small delay to ensure backend services are ready
        setTimeout(() => {
            fetchWithRetry('/analyze_audio', {
                method: 'POST',
                body: formData
            }, 2)
                .then(data => {
                    displayAnalysisResults(data);
                })
                .catch(error => {
                    analysisResultsContainer.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                });
        }, 300);
    }

    // Video analysis function with retry capability
    function analyzeVideo() {
        const file = fileUpload.files[0];

        if (!file) {
            analysisResultsContainer.innerHTML = '<p class="error">Please upload a video file.</p>';
            return;
        }

        // Clear previous results and show loading
        analysisResultsContainer.innerHTML = '<div class="loading-container"><div class="loading-spinner"></div><p>Analyzing video...</p></div>';

        const formData = new FormData();
        formData.append('video_file', file);

        // Small delay to ensure backend services are ready
        setTimeout(() => {
            fetchWithRetry('/analyze_video', {
                method: 'POST',
                body: formData
            }, 2)
                .then(data => {
                    displayAnalysisResults(data);
                })
                .catch(error => {
                    analysisResultsContainer.innerHTML = `<p class="error">Error: ${error.message}</p>`;
                });
        }, 300);
    }

    // Fetch headlines function
    function fetchHeadlines() {
        // Clear previous results with a smooth fade out
        if (headlinesContainer.innerHTML !== '') {
            headlinesContainer.style.opacity = '0';
            headlinesAnalysis.style.opacity = '0';

            setTimeout(() => {
                headlinesContainer.innerHTML = '';
                headlinesAnalysis.innerHTML = '';
                headlinesContainer.style.opacity = '1';
                headlinesAnalysis.style.opacity = '1';

                // Show elegant loading spinner
                headlinesContainer.innerHTML = `
                    <div class="loading-container">
                        <div class="loading-spinner"></div>
                        <p>Fetching latest headlines...</p>
                    </div>
                `;

                // Proceed with fetching headlines
                performHeadlinesFetch();
            }, 300);
        } else {
            headlinesContainer.innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <p>Fetching latest headlines...</p>
                </div>
            `;
            performHeadlinesFetch();
        }
    }

    function performHeadlinesFetch() {
        // Use fetchWithRetry for more reliable headline fetching
        fetchWithRetry('/fetch_headlines', {}, 2)
            .then(data => {
                if (data.error) {
                    headlinesContainer.innerHTML = `
                        <div class="error-container">
                            <i class="fas fa-exclamation-circle"></i>
                            <p>Error: ${data.error}</p>
                        </div>
                    `;
                    return;
                }

                // Create containers with nice styling
                headlinesContainer.innerHTML = `
                    <div class="headlines-header">
                        <h3>Today's Top Headlines</h3>
                    </div>
                `;

                const headlinesList = document.createElement('ol');
                headlinesList.className = 'headlines-list';
                headlinesContainer.appendChild(headlinesList);

                // Create analysis container
                headlinesAnalysis.innerHTML = `
                    <div class="analysis-header">
                        <h3>Analysis Results</h3>
                    </div>
                    <div id="analysis-results-list" class="analysis-results-list"></div>
                `;

                const analysisResultsList = document.getElementById('analysis-results-list');

                // Process all headlines
                if (data.headlines.length > 0) {
                    // Add all headlines to the list first
                    data.headlines.forEach((headline, index) => {
                        const listItem = document.createElement('li');
                        listItem.textContent = headline;
                        listItem.className = 'headline-item';
                        listItem.style.opacity = '0';
                        headlinesList.appendChild(listItem);

                        // Fade in the headline
                        setTimeout(() => {
                            listItem.style.opacity = '1';
                        }, 100 * index);
                    });

                    // Show analyzing indicator
                    const analyzeIndicator = document.createElement('div');
                    analyzeIndicator.className = 'analyzing-indicator';
                    analyzeIndicator.innerHTML = `
                        <div class="pulse-dot"></div>
                        <span>Analyzing headlines...</span>
                    `;
                    analysisResultsList.appendChild(analyzeIndicator);

                    // Analyze headlines one by one
                    let currentIndex = 0;
                    const analyzeNextHeadline = () => {
                        if (currentIndex >= data.headlines.length) {
                            // Remove analyzing indicator when done
                            analysisResultsList.removeChild(analyzeIndicator);
                            return;
                        }

                        const headline = data.headlines[currentIndex];

                        // Update analyzing indicator
                        analyzeIndicator.querySelector('span').textContent =
                            `Analyzing headline ${currentIndex + 1} of ${data.headlines.length}...`;

                        // Analyze the headline
                        let headlineToAnalyze = headline;

                        // Check if the headline is too long, truncate if needed
                        if (headline.length > 500) {
                            console.warn('Headline too long, truncating for analysis');
                            headlineToAnalyze = headline.substring(0, 500);
                        }

                        const encodedHeadline = encodeURIComponent(headlineToAnalyze);

                        fetchWithRetry(`/analyze_headline?headline=${encodedHeadline}`, {}, 2)
                            .then(result => {
                                // Create result panel
                                const resultPanel = document.createElement('div');
                                resultPanel.className = `result-panel ${result.is_fake ? 'fake' : 'real'}`;
                                resultPanel.style.opacity = '0';

                                // Build the result content
                                resultPanel.innerHTML = `
                                    <div class="result-header">
                                        <h4 class="headline">${headline}</h4>
                                        <span class="result-badge ${result.is_fake ? 'fake-badge' : 'real-badge'}">
                                            ${result.credcheck_classification}
                                        </span>
                                    </div>
                                    <div class="verification-layers-summary">
                                        <h5>Verification Layers:</h5>
                                        <div class="layers-badges">
                                            ${result.layers && result.layers.credibility ?
                                        (result.layers.credibility.error ?
                                            `<span class="layer-badge">${result.layers.credibility.error.includes('quota exceeded') ?
                                                '⚠️ API Limit' : '⚠️ Unavailable'}</span>` :
                                            `<span class="layer-badge ${result.layer_classifications.credibility.includes('🔴') ? 'fake' : 'real'}">
                                                ${result.layer_classifications.credibility}
                                            </span>`) : ''}
                                            ${result.layer_classifications.deepseek ?
                                        `<span class="layer-badge ${result.layer_classifications.deepseek.includes('🔴') ? 'fake' : 'real'}">
                                                ${result.layer_classifications.deepseek}
                                            </span>` : ''}
                                            ${result.layer_classifications.claimbuster ?
                                        `<span class="layer-badge ${result.layer_classifications.claimbuster.includes('🔴') ? 'fake' : 'real'}">
                                                ${result.layer_classifications.claimbuster}
                                            </span>` : ''}
                                        </div>
                                    </div>
                                    <div class="result-expand">
                                        <button class="expand-btn">
                                            <i class="fas fa-chevron-down"></i> Show Details
                                        </button>
                                    </div>
                                    <div class="result-details" style="display: none;">
                                `;

                                // Add layer details if available
                                if (result.layers && result.layers.credibility) {
                                    const credibility = result.layers.credibility;

                                    // Check if there's an error in credibility layer
                                    if (credibility.error) {
                                        // Handle error case
                                        let errorMessage = '';
                                        let badgeText = '⚠️ Unavailable';

                                        // Special handling for quota exceeded errors
                                        if (credibility.error.includes('quota exceeded')) {
                                            errorMessage = 'API daily limit reached. Continuing with other verification methods.';
                                            badgeText = '⚠️ API Limit Reached';
                                        }

                                        resultPanel.querySelector('.result-details').innerHTML += `
                                            <div class="layer-detail">
                                                <h6>Layer 1: Credibility Check</h6>
                                                <p>${errorMessage || 'Verification using trusted sources is temporarily unavailable.'}</p>
                                                <p>Trusted sources checked:</p>
                                                <div class="source-list">
                                                    <span class="source-item">reuters.com</span>
                                                    <span class="source-item">bbc.com</span>
                                                    <span class="source-item">apnews.com</span>
                                                    <span class="source-item">nytimes.com</span>
                                                    <span class="source-item">washingtonpost.com</span>
                                                </div>
                                            </div>
                                        `;
                                    } else {
                                        // Normal credibility display (no error)
                                        const credibilityClass = credibility.is_fake ? 'fake' : 'real';
                                        resultPanel.querySelector('.result-details').innerHTML += `
                                            <div class="layer-detail">
                                                <h6>Layer 1: Credibility Check</h6>
                                                <p><strong>Sources Found in Search:</strong></p>
                                                <div class="source-list">
                                                    ${credibility.search_results && credibility.search_results.length > 0 ?
                                                credibility.search_results.map(result =>
                                                    `<span class="source-item">${result.link.replace(/^https?:\/\//, '').split('/')[0]}</span>`
                                                ).join('') :
                                                '<span class="no-sources">No specific sources found - This is often a sign of suspicious content</span>'
                                            }
                                                </div>
                                            </div>
                                        `;
                                    }
                                }

                                if (result.layers && result.layers.deepseek) {
                                    const deepseek = result.layers.deepseek;
                                    const deepseekClass = deepseek.is_fake ? 'fake' : 'real';

                                    // Clean the verdict text by removing LaTeX-style formatting
                                    let fullVerdict = deepseek.verdict || 'N/A';

                                    // Extract just the classification (Real/Fake) and explanation
                                    let cleanVerdict = 'No verdict available';
                                    let explanation = '';

                                    // Remove LaTeX formatting
                                    fullVerdict = fullVerdict.replace(/\\boxed{/g, '')
                                        .replace(/}|\\|#/g, '')
                                        .replace(/\*\*/g, '')
                                        .replace(/`/g, '');

                                    // Try to extract simple verdict and explanation
                                    if (fullVerdict.toLowerCase().includes('fake')) {
                                        cleanVerdict = 'FAKE';

                                        // Try to extract explanation
                                        const parts = fullVerdict.split(/(?:because|as|since|explanation:|:)/i);
                                        if (parts.length > 1) {
                                            explanation = parts.slice(1).join(' ').trim();
                                        }
                                    } else if (fullVerdict.toLowerCase().includes('real')) {
                                        cleanVerdict = 'REAL';

                                        // Try to extract explanation
                                        const parts = fullVerdict.split(/(?:because|as|since|explanation:|:)/i);
                                        if (parts.length > 1) {
                                            explanation = parts.slice(1).join(' ').trim();
                                        }
                                    } else {
                                        cleanVerdict = fullVerdict.slice(0, 50); // Just take the first 50 chars if we can't parse it
                                    }

                                    resultPanel.querySelector('.result-details').innerHTML += `
                                        <div class="layer-detail">
                                            <h6>Layer 2: AI Analysis</h6>
                                            <div class="ai-verdict ${deepseekClass}">
                                                ${cleanVerdict}
                                                </div>
                                            ${explanation ? `<div class="ai-explanation"><p>${explanation}</p></div>` : ''}
                                        </div>
                                    `;
                                }

                                if (result.layers && result.layers.claimbuster && result.layers.claimbuster.length > 0) {
                                    resultPanel.querySelector('.result-details').innerHTML += `
                                        <div class="layer-detail">
                                            <h6>Layer 3: ClaimBuster Fact-Checking</h6>
                                            <div class="claims-list">
                                    `;

                                    result.layers.claimbuster.forEach(claim => {
                                        resultPanel.querySelector('.claims-list').innerHTML += `
                                            <div class="claim-item ${claim.classification.includes('🔴') ? 'fake' : 'real'}">
                                                <p><strong>Claim:</strong> ${claim.text}</p>
                                                <p><strong>Score:</strong> ${claim.score.toFixed(2)}</p>
                                                <p><strong>Classification:</strong> ${claim.classification}</p>
                                            </div>
                                        `;
                                    });

                                    resultPanel.querySelector('.result-details').innerHTML += `
                                            </div>
                                        </div>
                                    `;
                                }

                                resultPanel.querySelector('.result-details').innerHTML += `</div>`;

                                // Add expand/collapse functionality
                                resultPanel.querySelector('.expand-btn').addEventListener('click', function () {
                                    const detailsEl = resultPanel.querySelector('.result-details');
                                    const expandBtn = resultPanel.querySelector('.expand-btn');

                                    if (detailsEl.style.display === 'none') {
                                        detailsEl.style.display = 'block';
                                        expandBtn.innerHTML = '<i class="fas fa-chevron-up"></i> Hide Details';
                                    } else {
                                        detailsEl.style.display = 'none';
                                        expandBtn.innerHTML = '<i class="fas fa-chevron-down"></i> Show Details';
                                    }
                                });

                                // Add to analysisList
                                analysisResultsList.appendChild(resultPanel);

                                // Fade in with animation
                                setTimeout(() => {
                                    resultPanel.style.opacity = '1';
                                }, 100);

                                // Update analysis data and refresh statistics
                                analysisResults.push(result);

                                // Refresh recent analyses and statistics
                                loadRecentAnalyses();
                                loadStatistics();

                                // Move to next headline
                                currentIndex++;
                                analyzeNextHeadline();
                            })
                            .catch(error => {
                                console.error('Error analyzing headline:', error);

                                // Skip showing an error message for every headline
                                // Just log the error and continue with the next headline

                                // Move to next headline even if there was an error
                                currentIndex++;
                                analyzeNextHeadline();
                            });
                    };

                    // Start analyzing headlines
                    analyzeNextHeadline();
                } else {
                    const noHeadlines = document.createElement('p');
                    noHeadlines.textContent = 'No headlines available to analyze.';
                    headlinesContainer.appendChild(noHeadlines);
                }
            })
            .catch(error => {
                console.error('Error fetching headlines:', error);
                headlinesContainer.innerHTML = `
                    <div class="error-container">
                        <i class="fas fa-exclamation-circle"></i>
                        <p>Error: ${error.message}</p>
                    </div>
                `;
            });
    }

    // Display analysis results function
    function displayAnalysisResults(data) {
        analysisResultsContainer.innerHTML = '';

        if (data.error) {
            analysisResultsContainer.innerHTML = `<p class="error">Error: ${data.error}</p>`;
            return;
        }

        const resultItem = document.createElement('div');
        resultItem.className = `result-item ${data.is_fake ? 'fake' : 'real'}`;

        // Add extracted or transcribed text if available
        if (data.extracted_text) {
            resultItem.innerHTML += `<p><strong>Extracted Text:</strong> ${data.extracted_text}</p>`;
        } else if (data.transcribed_text) {
            resultItem.innerHTML += `<p><strong>Transcribed Text:</strong> ${data.transcribed_text}</p>`;
        } else if (data.headline) {
            resultItem.innerHTML += `<p><strong>Headline:</strong> ${data.headline}</p>`;
        }

        // Add translated text if available
        if (data.translated_text) {
            resultItem.innerHTML += `<p><strong>Translated Text:</strong> ${data.translated_text}</p>`;
        }

        // Main classification result
        resultItem.innerHTML += `
            <div class="verification-summary">
                <h4>Overall Classification:</h4>
                <p class="classification ${data.is_fake ? 'fake' : 'real'}">${data.credcheck_classification}</p>
            </div>
        `;

        // Add layered verification results if available
        if (data.layers && data.layer_classifications) {
            resultItem.innerHTML += `
                <div class="verification-layers">
                    <h4>Verification Layers:</h4>
                    <div class="layers-container">
            `;

            // Layer 1: Credibility Check
            if (data.layers.credibility) {
                const credibility = data.layers.credibility;

                // Check if there's an error in credibility layer
                if (credibility.error) {
                    // Handle error case
                    let errorMessage = '';
                    let badgeText = '⚠️ Unavailable';

                    // Special handling for quota exceeded errors
                    if (credibility.error.includes('quota exceeded')) {
                        errorMessage = 'API daily limit reached. Continuing with other verification methods.';
                        badgeText = '⚠️ API Limit Reached';
                    }

                    resultItem.innerHTML += `
                        <div class="layer-item">
                            <div class="layer-header">
                                <h5>Layer 1: Credibility Check</h5>
                                <span class="layer-badge">${badgeText}</span>
                            </div>
                            <div class="layer-details">
                                <p>${errorMessage || 'Verification using trusted sources is temporarily unavailable.'}</p>
                                <p>Trusted sources checked:</p>
                                <div class="source-list">
                                    <span class="source-item">reuters.com</span>
                                    <span class="source-item">bbc.com</span>
                                    <span class="source-item">apnews.com</span>
                                    <span class="source-item">nytimes.com</span>
                                    <span class="source-item">washingtonpost.com</span>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    // Normal credibility display (no error)
                    const credibilityClass = credibility.is_fake ? 'fake' : 'real';
                    resultItem.innerHTML += `
                        <div class="layer-item ${credibilityClass}">
                            <div class="layer-header">
                                <h5>Layer 1: Credibility Check</h5>
                                <span class="layer-badge ${credibilityClass}">${data.layer_classifications.credibility}</span>
                            </div>
                            <div class="layer-details">
                                <p><strong>Sources Found in Search:</strong></p>
                                <div class="source-list">
                                    ${credibility.search_results && credibility.search_results.length > 0 ?
                            credibility.search_results.map(result =>
                                `<span class="source-item">${result.link.replace(/^https?:\/\//, '').split('/')[0]}</span>`
                            ).join('') :
                            '<span class="no-sources">No specific sources found - This is often a sign of suspicious content</span>'
                        }
                                </div>
                            </div>
                        </div>
                    `;
                }
            }

            // Layer 2: AI Analysis (renamed from DeepSeek AI Analysis)
            if (data.layers.deepseek) {
                const deepseek = data.layers.deepseek;
                const deepseekClass = deepseek.is_fake ? 'fake' : 'real';

                // Clean the verdict text by removing LaTeX-style formatting
                let fullVerdict = deepseek.verdict || 'N/A';

                // Extract just the classification (Real/Fake) and explanation
                let cleanVerdict = 'No verdict available';
                let explanation = '';

                // Remove LaTeX formatting
                fullVerdict = fullVerdict.replace(/\\boxed{/g, '')
                    .replace(/}|\\|#/g, '')
                    .replace(/\*\*/g, '')
                    .replace(/`/g, '');

                // Try to extract simple verdict and explanation
                if (fullVerdict.toLowerCase().includes('fake')) {
                    cleanVerdict = 'FAKE';

                    // Try to extract explanation
                    const parts = fullVerdict.split(/(?:because|as|since|explanation:|:)/i);
                    if (parts.length > 1) {
                        explanation = parts.slice(1).join(' ').trim();
                    }
                } else if (fullVerdict.toLowerCase().includes('real')) {
                    cleanVerdict = 'REAL';

                    // Try to extract explanation
                    const parts = fullVerdict.split(/(?:because|as|since|explanation:|:)/i);
                    if (parts.length > 1) {
                        explanation = parts.slice(1).join(' ').trim();
                    }
                } else {
                    cleanVerdict = fullVerdict.slice(0, 50); // Just take the first 50 chars if we can't parse it
                }

                resultItem.innerHTML += `
                    <div class="layer-item ${deepseekClass}">
                        <div class="layer-header">
                            <h5>Layer 2: AI Analysis</h5>
                            <span class="layer-badge ${deepseekClass}">${data.layer_classifications.deepseek}</span>
                        </div>
                        <div class="layer-details">
                            <div class="ai-verdict ${deepseekClass}">
                                ${cleanVerdict}
                            </div>
                            ${explanation ? `<div class="ai-explanation"><p>${explanation}</p></div>` : ''}
                        </div>
                    </div>
                `;
            }

            // Layer 3: ClaimBuster
            if (data.layers.claimbuster && data.layers.claimbuster.length > 0) {
                const claimBusterClass = data.layer_classifications.claimbuster.includes('🔴') ? 'fake' : 'real';

                resultItem.innerHTML += `
                    <div class="layer-item ${claimBusterClass}">
                        <div class="layer-header">
                            <h5>Layer 3: ClaimBuster Fact-Checking</h5>
                            <span class="layer-badge ${claimBusterClass}">${data.layer_classifications.claimbuster}</span>
                        </div>
                        <div class="layer-details claims-container">
                `;

                // Add individual claims
                data.layers.claimbuster.forEach(claim => {
                    const claimClass = claim.classification.includes('🔴') ? 'fake' : 'real';
                    resultItem.querySelector('.claims-container').innerHTML += `
                        <div class="claim-result ${claimClass}">
                        <p><strong>Claim:</strong> ${claim.text}</p>
                            <p><strong>Score:</strong> ${claim.score.toFixed(2)}</p>
                        <p><strong>Classification:</strong> ${claim.classification}</p>
                    </div>
                `;
                });

                resultItem.innerHTML += `
                        </div>
                    </div>
                `;
            } else if (data.layer_classifications.claimbuster) {
                // If ClaimBuster was used but no results returned
                resultItem.innerHTML += `
                    <div class="layer-item">
                        <div class="layer-header">
                            <h5>Layer 3: ClaimBuster Fact-Checking</h5>
                            <span class="layer-badge">${data.layer_classifications.claimbuster}</span>
                        </div>
                    </div>
                `;
            }

            resultItem.innerHTML += `
                    </div>
                </div>
            `;
        }

        analysisResultsContainer.appendChild(resultItem);

        // Add to analysis results array 
        analysisResults.push(data);

        // Refresh recent analyses and statistics
        loadRecentAnalyses();
        loadStatistics();
    }

    // Helper function to truncate text
    function truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    // Function to load recent analyses
    function loadRecentAnalyses() {
        fetch('/get_recent_analyses')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error loading recent analyses:', data.error);
                    return;
                }

                recentAnalysesContainer.innerHTML = `
                    <div class="section-header">
                        <h3>Recent Analyses</h3>
                    </div>
                    <div class="recent-analyses-list">
                `;

                data.analyses.forEach(analysis => {
                    const analysisItem = document.createElement('div');
                    analysisItem.className = `analysis-item ${analysis.is_fake ? 'fake' : 'real'}`;

                    const date = new Date(analysis.analyzed_at);
                    const formattedDate = date.toLocaleString();

                    analysisItem.innerHTML = `
                        <div class="analysis-header">
                            <h4>${truncateText(analysis.headline, 80)}</h4>
                            <span class="result-badge ${analysis.is_fake ? 'fake-badge' : 'real-badge'}">
                                ${analysis.credcheck_classification}
                            </span>
                        </div>
                        <div class="analysis-meta">
                            <span class="source-type">${analysis.source_type}</span>
                            <span class="analysis-date">${formattedDate}</span>
                        </div>
                    `;

                    recentAnalysesContainer.querySelector('.recent-analyses-list').appendChild(analysisItem);
                });

                recentAnalysesContainer.innerHTML += '</div>';

                // Update the analysis trend chart with this data
                updateAnalysisTrendChart(data.analyses);
            })
            .catch(error => {
                console.error('Error loading recent analyses:', error);
            });
    }

    // Function to initialize and update the pie chart
    function updateNewsDistributionChart(realCount, fakeCount) {
        if (!newsDistributionChart) {
            console.error('News distribution chart element not found');
            return;
        }

        console.log('Updating pie chart with data:', { real: realCount, fake: fakeCount });

        // Create a canvas element if it doesn't exist
        if (!newsDistributionChart.querySelector('canvas')) {
            const canvas = document.createElement('canvas');
            newsDistributionChart.appendChild(canvas);
        }

        // Destroy previous chart if it exists
        if (pieChart) {
            pieChart.destroy();
        }

        // Create new pie chart
        const ctx = newsDistributionChart.querySelector('canvas').getContext('2d');
        pieChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Real News', 'Fake News'],
                datasets: [{
                    data: [realCount, fakeCount],
                    backgroundColor: [
                        'rgba(75, 192, 120, 0.8)',
                        'rgba(255, 99, 132, 0.8)'
                    ],
                    borderColor: [
                        'rgba(75, 192, 120, 1)',
                        'rgba(255, 99, 132, 1)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#e0e0e0'
                        }
                    },
                    title: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = Math.round((value / total) * 100);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Function to initialize and update the line chart
    function updateAnalysisTrendChart(analyses) {
        if (!analysisTrendChart) {
            console.error('Analysis trend chart element not found');
            return;
        }

        if (!analyses || analyses.length === 0) {
            console.error('No analyses data available for trend chart');
            return;
        }

        console.log('Updating line chart with analyses data:', analyses.length, 'records');

        // Create a canvas element if it doesn't exist
        if (!analysisTrendChart.querySelector('canvas')) {
            const canvas = document.createElement('canvas');
            analysisTrendChart.appendChild(canvas);
        }

        // Organize data by date
        const dateMap = new Map();
        const now = new Date();

        // Initialize the last 7 days with 0 values
        for (let i = 6; i >= 0; i--) {
            const date = new Date(now);
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            dateMap.set(dateStr, { real: 0, fake: 0 });
        }

        // Count analyses by date
        analyses.forEach(analysis => {
            const date = new Date(analysis.analyzed_at);
            const dateStr = date.toISOString().split('T')[0];

            if (dateMap.has(dateStr)) {
                const counts = dateMap.get(dateStr);
                if (analysis.is_fake) {
                    counts.fake++;
                } else {
                    counts.real++;
                }
                dateMap.set(dateStr, counts);
            }
        });

        // Convert to arrays for Chart.js
        const dates = Array.from(dateMap.keys());
        const realCounts = dates.map(date => dateMap.get(date).real);
        const fakeCounts = dates.map(date => dateMap.get(date).fake);

        // Format dates for display
        const formattedDates = dates.map(date => {
            const d = new Date(date);
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        // Destroy previous chart if it exists
        if (lineChart) {
            lineChart.destroy();
        }

        // Create new line chart
        const ctx = analysisTrendChart.querySelector('canvas').getContext('2d');
        lineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: formattedDates,
                datasets: [
                    {
                        label: 'Real News',
                        data: realCounts,
                        borderColor: 'rgba(75, 192, 120, 1)',
                        backgroundColor: 'rgba(75, 192, 120, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Fake News',
                        data: fakeCounts,
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#e0e0e0',
                            precision: 0
                        }
                    },
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#e0e0e0'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#e0e0e0'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                interaction: {
                    mode: 'nearest',
                    intersect: false
                }
            }
        });
    }

    // Function to load statistics
    function loadStatistics() {
        fetch('/get_statistics')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error loading statistics:', data.error);
                    return;
                }

                // Update statistics grid
                statisticsContainer.innerHTML = `
                    <div class="section-header">
                        <h3>Statistics</h3>
                    </div>
                    <div class="statistics-grid">
                        <div class="stat-item">
                            <span class="stat-value">${data.total_count}</span>
                            <span class="stat-label">Total Analyses</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${data.real_count}</span>
                            <span class="stat-label">Real News</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${data.fake_count}</span>
                            <span class="stat-label">Fake News</span>
                        </div>
                        <div class="stat-item">
                            <span class="stat-value">${data.real_percentage.toFixed(1)}%</span>
                            <span class="stat-label">Real News %</span>
                        </div>
                    </div>
                `;

                // Update the news distribution pie chart
                updateNewsDistributionChart(data.real_count, data.fake_count);

                // If the trend chart hasn't been initialized yet, load recent analyses to update it
                if (!lineChart && data.recent_analyses) {
                    updateAnalysisTrendChart(data.recent_analyses);
                }
            })
            .catch(error => {
                console.error('Error loading statistics:', error);
            });
    }

    // Automatically load real-time news when the page loads
    function loadInitialRealTimeNews() {
        if (realTimeNewsContainer) {
            realTimeNewsContainer.innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <p>Loading latest news from trusted sources...</p>
                </div>
            `;
            // Fetch real-time news with a small delay to ensure DOM is ready
            setTimeout(() => {
                fetchRealTimeNews()
                    .then(() => {
                        // Immediately check for analysis updates after loading
                        setTimeout(checkAnalysisUpdates, 1000);
                    });
            }, 100);
        }
    }

    // Automatically refresh the real-time news feed every hour, but check for analysis updates more frequently
    function setupAutoRefresh() {
        // Call fetchRealTimeNews every hour (3600000 ms) for full refresh
        const hourlyRefreshInterval = setInterval(() => {
            if (document.getElementById('real-time-news-tab').classList.contains('active')) {
                console.log('Auto-refreshing real-time news feed (hourly)');
                fetchRealTimeNews();
            }
        }, 3600000);  // 1 hour

        // Check for analysis updates every 10 seconds
        const analysisCheckInterval = setInterval(() => {
            if (document.getElementById('real-time-news-tab').classList.contains('active')) {
                const pendingBadges = document.querySelectorAll('.pending-badge');
                if (pendingBadges.length > 0) {
                    console.log('Checking for analysis updates');
                    checkAnalysisUpdates();
                }
            }
        }, 10000); // 10 seconds

        // Clear intervals when user leaves the page
        window.addEventListener('beforeunload', () => {
            clearInterval(hourlyRefreshInterval);
            clearInterval(analysisCheckInterval);
        });
    }

    // Function to check for analysis updates without refreshing all content
    function checkAnalysisUpdates() {
        fetch('/get_real_time_news?limit=30')
            .then(response => response.json())
            .then(data => {
                if (!data || !data.articles || data.articles.length === 0) return;

                // Create a map of article titles to their analyzed status for quick lookup
                const articleStatusMap = {};
                data.articles.forEach(article => {
                    if (article.title && article.analyzed) {
                        articleStatusMap[article.title] = {
                            is_fake: article.is_fake,
                            analyzed: true
                        };
                    }
                });

                // Look for any pending badges in the DOM
                document.querySelectorAll('.pending-badge').forEach(pendingBadge => {
                    // Find the article title associated with this item
                    const articleItem = pendingBadge.closest('.real-time-article-item');
                    if (!articleItem) return;

                    const titleElement = articleItem.querySelector('.article-title');
                    if (!titleElement) return;

                    const articleTitle = titleElement.textContent;

                    // Check if this article has been analyzed
                    if (articleStatusMap[articleTitle]) {
                        const isFake = articleStatusMap[articleTitle].is_fake;
                        const newBadge = document.createElement('span');
                        newBadge.className = isFake ? 'fake-badge' : 'real-badge';
                        newBadge.textContent = isFake ? '🔴 Fake' : '🟢 Real';
                        pendingBadge.parentNode.replaceChild(newBadge, pendingBadge);
                        console.log(`Updated badge for article: ${articleTitle.substring(0, 30)}...`);
                    }
                });

                // If we still have pending badges, check more frequently
                const remainingPendingBadges = document.querySelectorAll('.pending-badge').length;
                if (remainingPendingBadges > 0) {
                    console.log(`Still have ${remainingPendingBadges} pending badges, checking again soon`);
                    setTimeout(checkAnalysisUpdates, 5000); // Check again in 5 seconds
                }
            })
            .catch(error => {
                console.error('Error checking analysis updates:', error);
            });
    }

    // Function to fetch real-time news articles
    function fetchRealTimeNews() {
        return fetchWithRetry('/get_real_time_news?limit=10', {
            method: 'GET'
        }, 2) // Try up to 2 retries
            .then(data => {
                displayRealTimeNews(data);
                return data; // Return data for chaining
            })
            .catch(error => {
                if (realTimeNewsContainer) {
                    realTimeNewsContainer.innerHTML = `<p class="error">Error fetching real-time news: ${error.message}</p>`;
                }
                return null;
            });
    }

    // Function to display real-time news articles
    function displayRealTimeNews(data) {
        if (!realTimeNewsContainer) return;

        // Clear the container
        realTimeNewsContainer.innerHTML = '';

        if (!data || !data.articles || data.articles.length === 0) {
            realTimeNewsContainer.innerHTML = `
                <div class="empty-state">
                    <p>No real-time news articles available at the moment.</p>
                    <p class="last-updated">News feed updates hourly. Please check back later.</p>
                </div>
            `;
            return;
        }

        // Header with count and last updated time
        const headerDiv = document.createElement('div');
        headerDiv.className = 'real-time-header';

        // Format current time
        const now = new Date();
        const formattedTime = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        headerDiv.innerHTML = `
            <h3>Latest News (${data.articles.length} articles)</h3>
            <p class="last-updated">Last updated: ${formattedTime}</p>
        `;
        realTimeNewsContainer.appendChild(headerDiv);

        // Create a list for the articles
        const articlesList = document.createElement('ul');
        articlesList.className = 'real-time-articles-list';

        // Group articles by source
        const groupedArticles = {};
        data.articles.forEach(article => {
            const source = article.source || 'Unknown';
            if (!groupedArticles[source]) {
                groupedArticles[source] = [];
            }
            groupedArticles[source].push(article);
        });

        // Add each article to the list, grouped by source
        Object.keys(groupedArticles).sort().forEach(source => {
            // Add source header
            const sourceHeader = document.createElement('li');
            sourceHeader.className = 'source-header';
            sourceHeader.textContent = source;
            articlesList.appendChild(sourceHeader);

            // Add articles from this source
            groupedArticles[source].forEach(article => {
                // Skip articles with no title
                if (!article.title) return;

                const articleItem = document.createElement('li');
                articleItem.className = 'real-time-article-item';

                // Create article card
                const articleCard = document.createElement('div');
                articleCard.className = 'article-card';

                // Article header with credibility badge
                const articleHeader = document.createElement('div');
                articleHeader.className = 'article-header';

                // Credibility badge (always show)
                const credibilityBadge = document.createElement('span');

                if (article.analyzed) {
                    const isFake = article.is_fake;
                    credibilityBadge.className = isFake ? 'fake-badge' : 'real-badge';
                    credibilityBadge.textContent = isFake ? '🔴 Fake' : '🟢 Real';
                } else {
                    credibilityBadge.className = 'pending-badge';
                    credibilityBadge.textContent = '⏳ Analyzing';
                }

                // Add badge to header
                articleHeader.appendChild(credibilityBadge);

                // Article title
                const articleTitle = document.createElement('h3');
                articleTitle.className = 'article-title';
                articleTitle.textContent = article.title;

                // Add header and title
                articleCard.appendChild(articleHeader);
                articleCard.appendChild(articleTitle);

                // Add published date if available
                if (article.published) {
                    const publishedDate = document.createElement('p');
                    publishedDate.className = 'published-date';
                    publishedDate.textContent = `Published: ${article.published}`;
                    articleCard.appendChild(publishedDate);
                }

                // Add a snippet of the content if available
                if (article.content) {
                    const contentSnippet = document.createElement('p');
                    contentSnippet.className = 'content-snippet';
                    contentSnippet.textContent = truncateText(article.content, 150);
                    articleCard.appendChild(contentSnippet);
                }

                // Article footer with link
                const articleFooter = document.createElement('div');
                articleFooter.className = 'article-footer';

                // Read more link
                const readMoreLink = document.createElement('a');
                readMoreLink.href = article.link;
                readMoreLink.target = '_blank';
                readMoreLink.className = 'read-more-link';
                readMoreLink.textContent = 'Read full article';
                articleFooter.appendChild(readMoreLink);

                articleCard.appendChild(articleFooter);

                // Add the article card to the item
                articleItem.appendChild(articleCard);

                // Add the item to the list
                articlesList.appendChild(articleItem);
            });
        });

        // Add the list to the container
        realTimeNewsContainer.appendChild(articlesList);

        // Add note about hourly updates
        const updateNote = document.createElement('p');
        updateNote.className = 'update-note';
        updateNote.textContent = 'News feed automatically updates every hour with diverse sources.';
        realTimeNewsContainer.appendChild(updateNote);
    }

    // Function to fetch video feed
    function fetchVideoFeed() {
        const videoFeedContainer = document.getElementById('video-feed-container');
        videoFeedContainer.innerHTML = '<div class="loading">Loading video feed...</div>';

        fetch('/get_video_feed')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.error) {
                    videoFeedContainer.innerHTML = `<div class="error">Error: ${data.error}</div>`;
                    return;
                }

                if (!data.videos || data.videos.length === 0) {
                    videoFeedContainer.innerHTML = '<div class="message">No videos found. Try again later.</div>';
                    return;
                }

                // Create header for video feed
                let html = `
                    <div class="video-feed-header">
                        <h3>Analyzed Video Feed</h3>
                        <p>${data.videos.length} videos analyzed for credibility</p>
                    </div>
                    <div class="video-grid">
                `;

                // Add each video
                data.videos.forEach(video => {
                    const reliabilityBadge = video.is_reliable
                        ? '<span class="badge reliable">🟢 Real</span>'
                        : '<span class="badge unreliable">🔴 Fake</span>';

                    html += `
                        <div class="video-card">
                            <div class="thumbnail-container">
                                <img src="${video.thumbnail_url}" alt="Video thumbnail" />
                                <a href="https://www.youtube.com/watch?v=${video.video_id}" target="_blank" class="play-button">▶</a>
                                ${reliabilityBadge}
                            </div>
                        </div>
                    `;
                });

                html += `</div>
                    <div class="video-feed-note">
                        <p>Note: Video feed is fetched manually. Click "Get Video Feed" to refresh.</p>
                    </div>`;

                videoFeedContainer.innerHTML = html;
            })
            .catch(error => {
                console.error('Error fetching video feed:', error);
                videoFeedContainer.innerHTML = `<div class="error">Failed to fetch video feed: ${error.message}</div>`;
            });
    }

    // Load statistics, recent analyses, and real-time news on page load
    loadStatistics();
    loadRecentAnalyses();
    loadInitialRealTimeNews();
    initializeLiveBroadcast();
    setupAutoRefresh();

    // Initialize the live broadcast functionality
    function initializeLiveBroadcast() {
        // Load YouTube API
        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

        // Fetch initial analysis data
        fetchLiveBroadcastAnalysis();

        // Set up auto-refresh for live broadcast analysis
        if (liveBroadcastRefreshTimer) {
            clearInterval(liveBroadcastRefreshTimer);
        }

        liveBroadcastRefreshTimer = setInterval(fetchLiveBroadcastAnalysis, 30000); // Refresh every 30 seconds
    }

    // Fetch live broadcast analysis data
    function fetchLiveBroadcastAnalysis() {
        if (!liveAnalysisResults) return;

        // Show loading indicator
        liveAnalysisResults.innerHTML = '<div class="loading"></div>';

        fetch('/get_live_broadcast')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    liveAnalysisResults.innerHTML = `<div class="error-container"><i class="fas fa-exclamation-circle"></i><p>${data.error}</p></div>`;
                    return;
                }

                displayLiveBroadcastAnalysis(data);

                // Initialize YouTube player if not already done
                if (!player && data.youtube_url) {
                    initYouTubePlayer(data.youtube_url);
                }
            })
            .catch(error => {
                liveAnalysisResults.innerHTML = `<div class="error-container"><i class="fas fa-exclamation-circle"></i><p>Error fetching live broadcast data: ${error.message}</p></div>`;
            });
    }

    // Display live broadcast analysis results
    function displayLiveBroadcastAnalysis(data) {
        if (!liveAnalysisResults) return;

        const results = data.results;

        if (!results || results.length === 0) {
            liveAnalysisResults.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-info-circle"></i>
                    <p>No news content has been analyzed yet. Analysis results will appear here as they become available.</p>
                </div>
            `;
            return;
        }

        let html = '';

        results.forEach(item => {
            const itemClass = item.is_fake ? 'fake' : 'real';
            const verdict = item.verdict || 'No verdict available';
            const classification = item.is_fake ? '🔴 Fake' : '🟢 Real';

            html += `
                <div class="live-analysis-item ${itemClass}">
                    <div class="analysis-time">${item.timestamp}</div>
                    <div class="news-content">${item.news_item}</div>
                    <div class="verdict-container">
                        <span class="verdict-label">${classification}</span>
                        <span class="verdict-text">${verdict}</span>
                    </div>
                </div>
            `;
        });

        liveAnalysisResults.innerHTML = html;
    }

    // Initialize the YouTube player
    function initYouTubePlayer(videoUrl) {
        if (!youtubePlayer) return;

        // Extract video ID from URL
        const videoId = extractVideoId(videoUrl);

        if (!videoId) {
            youtubePlayer.innerHTML = '<p class="error">Invalid YouTube URL</p>';
            return;
        }

        // Initialize the player
        window.onYouTubeIframeAPIReady = function () {
            player = new YT.Player('youtube-player', {
                height: '360',
                width: '640',
                videoId: videoId,
                playerVars: {
                    'autoplay': 1,
                    'playsinline': 1,
                    'controls': 1,
                    'rel': 0
                },
                events: {
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange
                }
            });
        };

        // If the API is already loaded, manually initialize
        if (typeof YT !== 'undefined' && YT.Player) {
            window.onYouTubeIframeAPIReady();
        }
    }

    // Player ready event handler
    function onPlayerReady(event) {
        event.target.playVideo();
    }

    // Player state change event handler
    function onPlayerStateChange(event) {
        // You can handle player state changes here if needed
    }

    // Extract YouTube video ID from URL
    function extractVideoId(url) {
        const regExp = /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/;
        const match = url.match(regExp);
        return (match && match[7].length === 11) ? match[7] : null;
    }
}); 