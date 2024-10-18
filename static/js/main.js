document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('videoForm');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    const results = document.getElementById('results');
    const clipList = document.getElementById('clipList');

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(form);

        loading.classList.remove('d-none');
        error.classList.add('d-none');
        results.classList.add('d-none');
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
                data.clips_and_frames.forEach((item, index) => {
                    const accordionItem = document.createElement('div');
                    accordionItem.className = 'accordion-item';
                    accordionItem.innerHTML = `
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}">
                                ${item.clip}
                            </button>
                        </h2>
                        <div id="collapse${index}" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <a href="/download/${item.clip}" class="btn btn-primary mb-3">Download Clip</a>
                                <div class="row row-cols-1 row-cols-md-3 g-4" id="frames${index}"></div>
                            </div>
                        </div>
                    `;
                    clipList.appendChild(accordionItem);

                    const framesContainer = document.getElementById(`frames${index}`);
                    item.frames.forEach(frame => {
                        const frameCol = document.createElement('div');
                        frameCol.className = 'col';
                        frameCol.innerHTML = `
                            <div class="card">
                                <img src="/download_frame/${item.clip}/${frame}" class="card-img-top" alt="${frame}">
                                <div class="card-body">
                                    <a href="/download_frame/${item.clip}/${frame}" class="btn btn-sm btn-secondary">Download Frame</a>
                                </div>
                            </div>
                        `;
                        framesContainer.appendChild(frameCol);
                    });
                });
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

    // Cleanup temporary files when leaving the page
    window.addEventListener('beforeunload', function() {
        fetch('/cleanup', { method: 'POST' });
    });
});
