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

    // Check for form element
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

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        const formData = new FormData(form);

        // Ensure all UI elements exist before trying to manipulate them
        if (loading) loading.classList.remove('d-none');
        if (error) error.classList.add('d-none');
        if (results) results.classList.add('d-none');
        if (timeline) timeline.innerHTML = '';
        if (clipList) clipList.innerHTML = '';
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

            // Hide loading spinner and show results
            if (loading) loading.classList.add('d-none');

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
                        const row = createClipRow(item);
                        clipList.appendChild(row);
                    });
                }

                // Populate summary
                if (summaryText) summaryText.textContent = data.summary || 'No summary available.';
                if (keyPointsList && data.key_points) {
                    data.key_points.forEach(point => {
                        const listItem = document.createElement('li');
                        listItem.textContent = point;
                        keyPointsList.appendChild(listItem);
                    });
                }
                if (visualDescription) {
                    visualDescription.textContent = data.visual_description || 'No visual description available.';
                }
            } else {
                throw new Error(data.error);
            }
        } catch (error) {
            if (loading) loading.classList.add('d-none');
            if (error) {
                error.classList.remove('d-none');
                error.textContent = `Error: ${error.message}`;
            }
        }
    });

    function createTimelineFrame(frame, index) {
        const frameElement = document.createElement('div');
        frameElement.className = 'timeline-frame';
        frameElement.innerHTML = `
            <img src="/download_frame/${frame.clip}/${frame.path}" alt="Frame ${index}">
        `;
        frameElement.addEventListener('click', () => scrollToClip(frame.clip));
        return frameElement;
    }

    function createClipRow(item) {
        const row = document.createElement('div');
        row.className = 'row mb-4';
        const col = document.createElement('div');
        col.className = 'col-md-4 mb-3';
        col.innerHTML = `
            <div class="card h-100">
                <img src="/download_frame/${item.clip}/${item.frame}" class="card-img-top" alt="${item.frame}">
                <div class="card-body">
                    <p class="card-text clip-name-small">${item.clip}</p>
                    <a href="/download/${item.clip}" class="btn btn-primary btn-sm me-2">Download Clip</a>
                    <a href="/download_frame/${item.clip}/${item.frame}" class="btn btn-secondary btn-sm">Download Frame</a>
                </div>
            </div>
        `;
        row.appendChild(col);
        return row;
    }

    function scrollToClip(clipName) {
        const clipElement = document.getElementById(`clip-${clipName}`);
        if (clipElement) {
            clipElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
});
