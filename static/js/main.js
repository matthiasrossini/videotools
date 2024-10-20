document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('videoForm');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const timeline = document.getElementById('timeline');
    const clipList = document.getElementById('clipList');
    const summaryText = document.getElementById('summaryText');
    const keyPointsList = document.getElementById('keyPointsList');
    const visualDescription = document.getElementById('visualDescription');
    const retrySummaryBtn = document.getElementById('retrySummaryBtn');

    if (!form) {
        console.error("Form element not found!");
        return;
    }

    // Ensure that all elements are found before continuing
    if (!loading) console.error("Loading element not found");
    if (!error) console.error("Error element not found");
    if (!results) console.error("Results element not found");
    if (!timeline) console.error("Timeline element not found");
    if (!clipList) console.error("Clip list element not found");
    if (!summaryText) console.error("Summary text element not found");
    if (!keyPointsList) console.error("Key points list element not found");
    if (!visualDescription) console.error("Visual description element not found");
    if (!retrySummaryBtn) console.error("Retry summary button not found");

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        await processVideo();
    });

    retrySummaryBtn.addEventListener('click', async function() {
        await retrySummaryGeneration();
    });

    async function processVideo() {
        const formData = new FormData(form);

        if (loading) loading.classList.remove('d-none');
        if (error) error.classList.add('d-none');
        if (results) results.classList.add('d-none');
        if (timeline) timeline.innerHTML = '';
        if (clipList) clipList.innerHTML = '';
        if (summaryText) summaryText.textContent = '';
        if (keyPointsList) keyPointsList.innerHTML = '';
        if (visualDescription) visualDescription.textContent = '';
        if (retrySummaryBtn) retrySummaryBtn.classList.add('d-none');

        try {
            console.log('Submitting form data...');
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Received data:', data);

            if (loading) loading.classList.add('d-none');

            if (data.success) {
                if (results) results.classList.remove('d-none');

                if (data.timeline_frames && timeline) {
                    console.log('Creating timeline frames...');
                    data.timeline_frames.forEach((frame, index) => {
                        const frameElement = createTimelineFrame(frame, index);
                        timeline.appendChild(frameElement);
                    });
                }

                if (data.clips_and_frames && clipList) {
                    console.log('Creating clip rows...');
                    data.clips_and_frames.forEach(item => {
                        const row = createClipRow(item);
                        clipList.appendChild(row);
                    });
                }

                updateSummarySection(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error processing video:', error);
            if (loading) loading.classList.add('d-none');
            if (error) {
                error.classList.remove('d-none');
                error.textContent = `Error: ${error.message}`;
            }
        }
    }

    async function retrySummaryGeneration() {
        if (loading) loading.classList.remove('d-none');
        if (retrySummaryBtn) retrySummaryBtn.classList.add('d-none');

        try {
            const response = await fetch('/retry_summary', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({}),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            console.log('Received retry data:', data);

            if (loading) loading.classList.add('d-none');

            if (data.success) {
                updateSummarySection(data);
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            console.error('Error retrying summary generation:', error);
            if (loading) loading.classList.add('d-none');
            if (error) {
                error.classList.remove('d-none');
                error.textContent = `Error: ${error.message}`;
            }
            if (retrySummaryBtn) retrySummaryBtn.classList.remove('d-none');
        }
    }

    function updateSummarySection(data) {
        if (summaryText) {
            summaryText.textContent = data.summary || 'No summary available.';
        }
        if (keyPointsList) {
            keyPointsList.innerHTML = '';
            if (data.key_points && data.key_points.length > 0) {
                data.key_points.forEach(point => {
                    const listItem = document.createElement('li');
                    listItem.textContent = point;
                    keyPointsList.appendChild(listItem);
                });
            } else {
                const listItem = document.createElement('li');
                listItem.textContent = 'No key points available.';
                keyPointsList.appendChild(listItem);
            }
        }
        if (visualDescription) {
            visualDescription.textContent = data.visual_description || 'No visual description available.';
        }
        if (retrySummaryBtn) {
            if (data.summary === 'Unable to generate summary due to an error.') {
                retrySummaryBtn.classList.remove('d-none');
            } else {
                retrySummaryBtn.classList.add('d-none');
            }
        }
    }

    function createTimelineFrame(frame, index) {
        const frameElement = document.createElement('div');
        frameElement.className = 'timeline-frame';
        const img = document.createElement('img');
        if (frame && frame.clip && frame.path) {
            img.src = `/download_frame/${encodeURIComponent(frame.clip)}/${encodeURIComponent(frame.path)}`;
            img.alt = `Frame ${index}`;
            img.onerror = function() {
                console.error(`Failed to load image: ${img.src}`);
                img.src = '/static/images/placeholder.jpg';
                img.alt = 'Image not found';
            };
        } else {
            console.error(`Invalid frame data for index ${index}:`, frame);
            img.src = '/static/images/placeholder.jpg';
            img.alt = 'Placeholder';
        }
        frameElement.appendChild(img);
        frameElement.addEventListener('click', () => scrollToClip(frame.clip));
        return frameElement;
    }

    function createClipRow(item) {
        console.log('Creating clip row for:', item);
        const row = document.createElement('div');
        row.className = 'row mb-4';
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        col.innerHTML = `
            <div class="card h-100">
                <div id="clip-${encodeURIComponent(item.clip)}" class="carousel slide" data-bs-ride="carousel">
                    <div class="carousel-inner">
                        ${item.frames.map((frame, index) => `
                            <div class="carousel-item ${index === 0 ? 'active' : ''}">
                                <img src="/download_frame/${encodeURIComponent(item.clip)}/${encodeURIComponent(frame)}" 
                                     class="d-block w-100" 
                                     alt="${frame}" 
                                     onerror="this.onerror=null; this.src='/static/images/placeholder.jpg'; console.error('Failed to load frame:', '${item.clip}/${frame}');">
                            </div>
                        `).join('')}
                    </div>
                    <button class="carousel-control-prev" type="button" data-bs-target="#clip-${encodeURIComponent(item.clip)}" data-bs-slide="prev">
                        <span class="carousel-control-prev-icon" aria-hidden="true"></span>
                        <span class="visually-hidden">Previous</span>
                    </button>
                    <button class="carousel-control-next" type="button" data-bs-target="#clip-${encodeURIComponent(item.clip)}" data-bs-slide="next">
                        <span class="carousel-control-next-icon" aria-hidden="true"></span>
                        <span class="visually-hidden">Next</span>
                    </button>
                </div>
                <div class="card-body">
                    <p class="card-text clip-name-small">${item.clip}</p>
                    <a href="/download/${encodeURIComponent(item.clip)}" class="btn btn-primary btn-sm me-2">Download Clip</a>
                </div>
            </div>
        `;
        row.appendChild(col);
        return row;
    }

    function scrollToClip(clipName) {
        const clipElement = document.getElementById(`clip-${encodeURIComponent(clipName)}`);
        if (clipElement) {
            clipElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            console.error(`Clip element not found for: ${clipName}`);
        }
    }
});
