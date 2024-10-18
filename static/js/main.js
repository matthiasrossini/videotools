document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('videoForm');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const timeline = document.getElementById('timeline');
    const clipList = document.getElementById('clipList');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);

        loading.classList.remove('d-none');
        error.classList.add('d-none');
        results.classList.add('d-none');
        timeline.innerHTML = '';
        clipList.innerHTML = '';

        fetch('/process', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            loading.classList.add('d-none');
            if (data.success) {
                results.classList.remove('d-none');
                
                // Create timeline
                data.timeline_frames.forEach((frame, index) => {
                    const frameElement = document.createElement('div');
                    frameElement.className = 'timeline-frame';
                    frameElement.innerHTML = `
                        <img src="/download_frame/${frame.clip}/${frame.path}" alt="Frame ${index}">
                        <div class="text-center small">${frame.timestamp}s</div>
                    `;
                    frameElement.addEventListener('click', () => scrollToClip(frame.clip));
                    timeline.appendChild(frameElement);
                });
                
                // Create rows with 3 scenes each
                for (let i = 0; i < data.clips_and_frames.length; i += 3) {
                    const row = document.createElement('div');
                    row.className = 'row mb-4';
                    
                    for (let j = i; j < i + 3 && j < data.clips_and_frames.length; j++) {
                        const item = data.clips_and_frames[j];
                        const col = document.createElement('div');
                        col.className = 'col-md-4 mb-3';
                        col.id = `clip-${item.clip}`;
                        
                        const card = document.createElement('div');
                        card.className = 'card h-100';
                        card.innerHTML = `
                            <div class="card-header">
                                <h6 class="card-title mb-0">${item.clip}</h6>
                            </div>
                            <div class="card-body">
                                <a href="/download/${item.clip}" class="btn btn-primary btn-sm mb-2">Download Clip</a>
                                <div class="row row-cols-3 g-2" id="frames${j}"></div>
                            </div>
                        `;
                        
                        col.appendChild(card);
                        row.appendChild(col);
                        
                        // Add frames after the row is appended to ensure the container exists
                        setTimeout(() => {
                            const framesContainer = document.getElementById(`frames${j}`);
                            item.frames.forEach(frame => {
                                const frameCol = document.createElement('div');
                                frameCol.className = 'col';
                                frameCol.innerHTML = `
                                    <div class="card">
                                        <img src="/download_frame/${item.clip}/${frame}" class="card-img-top" alt="${frame}">
                                        <div class="card-body p-1">
                                            <a href="/download_frame/${item.clip}/${frame}" class="btn btn-sm btn-secondary w-100">Download</a>
                                        </div>
                                    </div>
                                `;
                                framesContainer.appendChild(frameCol);
                            });
                        }, 0);
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

    function scrollToClip(clipName) {
        const clipElement = document.getElementById(`clip-${clipName}`);
        if (clipElement) {
            clipElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // Cleanup temporary files when leaving the page
    window.addEventListener('beforeunload', function() {
        fetch('/cleanup', { method: 'POST' });
    });
});
