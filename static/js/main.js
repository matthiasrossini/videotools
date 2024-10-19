document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('videoForm');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const timeline = document.getElementById('timeline');
    const clipList = document.getElementById('clipList');
    const useCustomSettings = document.getElementById('use_custom_settings');
    const customSettings = document.getElementById('custom_settings');

    useCustomSettings.addEventListener('change', function() {
        customSettings.style.display = this.checked ? 'block' : 'none';
    });

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);
        
        // Only include custom settings if the checkbox is checked
        if (!useCustomSettings.checked) {
            formData.delete('number_of_clips');
        }
        
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
            console.log('Received data:', data);
            loading.classList.add('d-none');
            if (data.success) {
                results.classList.remove('d-none');
                
                console.log('Creating timeline with frames:', data.timeline_frames);
                data.timeline_frames.forEach((frame, index) => {
                    const frameElement = document.createElement('div');
                    frameElement.className = 'timeline-frame';
                    const frameSrc = `/download_frame/${encodeURIComponent(frame.clip)}/${encodeURIComponent(frame.path)}`;
                    console.log(`Timeline frame URL: ${frameSrc}`);
                    frameElement.innerHTML = `
                        <img src="${frameSrc}" alt="Frame ${index}">
                        <div class="text-center small">${frame.timestamp}s</div>
                    `;
                    frameElement.addEventListener('click', () => scrollToClip(frame.clip));
                    timeline.appendChild(frameElement);
                });
                
                console.log('Creating clip list with data:', data.clips_and_frames);
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
                                <a href="/download/${encodeURIComponent(item.clip)}" class="btn btn-primary btn-sm mb-2">Download Clip</a>
                                <div class="row row-cols-3 g-2" id="frames${j}"></div>
                            </div>
                        `;
                        
                        col.appendChild(card);
                        row.appendChild(col);
                        
                        setTimeout(() => {
                            const framesContainer = document.getElementById(`frames${j}`);
                            item.frames.forEach(frame => {
                                const frameCol = document.createElement('div');
                                frameCol.className = 'col';
                                const frameSrc = `/download_frame/${encodeURIComponent(item.clip)}/${encodeURIComponent(frame)}`;
                                console.log(`Clip frame URL: ${frameSrc}`);
                                frameCol.innerHTML = `
                                    <div class="card">
                                        <img src="${frameSrc}" class="card-img-top" alt="${frame}">
                                        <div class="card-body p-1">
                                            <a href="${frameSrc}" class="btn btn-sm btn-secondary w-100">Download</a>
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
            console.error('Error:', err);
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

    window.addEventListener('beforeunload', function() {
        fetch('/cleanup', { method: 'POST' });
    });
});
