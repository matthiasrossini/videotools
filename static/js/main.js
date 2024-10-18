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
                data.clips.forEach(clip => {
                    const li = document.createElement('li');
                    li.className = 'list-group-item';
                    const link = document.createElement('a');
                    link.href = `/download/${clip}`;
                    link.textContent = clip;
                    li.appendChild(link);
                    clipList.appendChild(li);
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
