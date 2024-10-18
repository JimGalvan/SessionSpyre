document.addEventListener('DOMContentLoaded', function () {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    fetch('/set-timezone/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': '{{ csrf_token }}'
        },
        body: JSON.stringify({timezone: timezone})
    });
});
