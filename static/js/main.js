document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('videoForm');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const timeline = document.getElementById('timeline');
    const clipList = document.getElementById('clipList');
    const summaryContainer = document.getElementById('summaryContainer');
    const summaryText = document.getElementById('summaryText');
    const keyPointsList = document.getElementById('keyPointsList');
    const visualDescription = document.getElementById('visualDescription');
    const framesTimeline = document.getElementById('framesTimeline');
    const combinedImage = document.getElementById('combinedImage');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const videoFileContainer = document.getElementById('videoFileContainer');

    // Check existence of elements before interacting
    if (loadingSpinner) {
        loadingSpinner.style.display = 'none'; // Hide spinner initially
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(form);

        // Reset UI elements
        if (loading) loading.classList.remove('d-none');
        if (loadingSpinner) loadingSpinner.style.display = 'block';
        if (error) error.classList.add('d-none');
        if (results) results.classList.add('d-none');
        if (timeline) timeline.innerHTML = '';
        if (clipList) clipList.innerHTML = '';
        if (framesTimeline) framesTimeline.innerHTML = '';
        if (combinedImage) combinedImage.src = '';
        if (summaryText) summaryText.textContent = '';
        if (keyPointsList) keyPointsList.innerHTML = '';
        if (visualDescription) visualDescription.textContent = '';

        try {
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            if (loading) loading.classList.add('d-none');
            if (loadingSpinner) loadingSpinner.style.display = 'none';

            if (data.success) {
                if (results) results.classList.remove('d-none');

                // Populate timeline frames
                if (data.timeline_frames && timeline) {
                    data.timeline_frames.forEach((frame, index) => {
                        const frameElement = createTimelineFrame(frame, index);
                        timeline.appendChild(frameElement);
                    });
                }

                // Populate clips and frames
                if (data.clips_and_frames && clipList) {
                    data.clips_and_frames.forEach(item => {
                        const col = createClipCard(item);
                        clipList.appendChild(col);
                    });
                }

                // Display frames in the timeline (if present)
                if (data.frames && framesTimeline) {
                    data.frames.forEach((frame, index) => {
                        const frameImg = document.createElement('img');
                        frameImg.src = `data:image/jpeg;base64,${frame}`;
                        frameImg.alt = `Frame ${index + 1}`;
                        frameImg.className = 'img-thumbnail';
                        frameImg.style.width = `${100 / data.frames.length}%`;
                        framesTimeline.appendChild(frameImg);
                    });
                }

                // Display combined image
                if (combinedImage && data.combined_image) {
                    combinedImage.src = `data:image/jpeg;base64,${data.combined_image}`;
                }

                // Populate summary information
                if (summaryText && data.summary) {
                    summaryText.textContent = data.summary;
                }
                if (keyPointsList && data.key_points) {
                    data.key_points.forEach(point => {
                        const listItem = document.createElement('li');
                        listItem.textContent = point;
                        keyPointsList.appendChild(listItem);
                    });
                }
                if (visualDescription && data.visual_description) {
                    visualDescription.textContent = data.visual_description;
                }

            } else {
                throw new Error(data.error);
            }
        } catch (err) {
            if (loading) loading.classList.add('d-none');
            if (loadingSpinner) loadingSpinner.style.display = 'none';
            if (error) {
                error.classList.remove('d-none');
                error.textContent = `Error: ${err.message}`;
            }
            if (summaryContainer) {
                summaryContainer.innerHTML = `<div class="alert alert-danger">${err.message}</div>`;
            }
            console.error('Error:', err);
        }
    });

    // Helper function to create a timeline frame
    function createTimelineFrame(frame, index) {
        const frameElement = document.createElement('div');
        frameElement.className = 'timeline-frame';
        frameElement.innerHTML = `
            <img src="/download_frame/${frame.clip}/${frame.path}" alt="Frame ${index}">
        `;
        frameElement.addEventListener('click', () => scrollToClip(frame.clip));
        return frameElement;
    }

    // Helper function to create a clip card
    function createClipCard(item) {
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        col.id = `clip-${item.clip}`;

        const card = document.createElement('div');
        card.className = 'card h-100';
        card.innerHTML = `
            <img src="/download_frame/${item.clip}/${item.frame}" class="card-img-top" alt="${item.frame}">
            <div class="card-body">
                <p class="card-text clip-name-small">${item.clip}</p>
                <a href="/download/${item.clip}" class="btn btn-primary btn-sm me-2">Download Clip</a>
                <a href="/download_frame/${item.clip}/${item.frame}" class="btn btn-secondary btn-sm">Download Frame</a>
            </div>
        `;
        col.appendChild(card);
        return col;
    }

    // Scroll to the selected clip when clicked on the timeline frame
    function scrollToClip(clipName) {
        const clipElement = document.getElementById(`clip-${clipName}`);
        if (clipElement) {
            clipElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // Clean up temporary files when the user leaves the page
    window.addEventListener('beforeunload', function() {
        fetch('/cleanup', { method: 'POST' });
    });

    // Show/hide file upload based on YouTube URL input
    const youtubeUrlInput = document.getElementById('youtube_url');
    if (youtubeUrlInput) {
        youtubeUrlInput.addEventListener('input', function() {
            if (this.value.trim() !== '') {
                if (videoFileContainer) videoFileContainer.style.display = 'none';
            } else {
                if (videoFileContainer) videoFileContainer.style.display = 'block';
            }
        });
    }
});
