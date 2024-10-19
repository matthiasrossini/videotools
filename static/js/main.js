document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('videoForm');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const timeline = document.getElementById('timeline');
    const clipList = document.getElementById('clipList');

    // Handle form submission
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);

        // Show loading, hide results and error
        loading.classList.remove('d-none');
        error.classList.add('d-none');
        results.classList.add('d-none');
        timeline.innerHTML = '';
        clipList.innerHTML = '';

        // Fetch to backend to process the video
        fetch('/process', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.classList.add('d-none');
            if (data.success) {
                results.classList.remove('d-none');

                // Create timeline from frames
                data.timeline_frames.forEach((frame, index) => {
                    const frameElement = createTimelineFrame(frame, index);
                    timeline.appendChild(frameElement);
                });

                // Create rows with 3 clips each (or fewer if < 3 remain)
                for (let i = 0; i < data.clips_and_frames.length; i += 3) {
                    const row = document.createElement('div');
                    row.className = 'row mb-4';

                    for (let j = i; j < i + 3 && j < data.clips_and_frames.length; j++) {
                        const item = data.clips_and_frames[j];
                        const col = document.createElement('div');
                        col.className = 'col-md-4 mb-3';
                        col.id = `clip-${item.clip}`;

                        // Create a card for each clip
                        const card = createClipCard(item);
                        col.appendChild(card);
                        row.appendChild(col);
                    }

                    clipList.appendChild(row);
                }
            } else {
                throw new Error(data.error);
            }
        })
        .catch(err => {
            loading.classList.add('d-none');
            error.classList.remove('d-none');
            error.textContent = `Error: ${err.message}`;
        });
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
        return card;
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
});
