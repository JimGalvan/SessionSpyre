document.addEventListener('DOMContentLoaded', (event) => {
    console.log('DOM fully loaded and parsed.');

    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    console.log('Detected user timezone:', userTimezone);

    fetch('/check-timezone/')
        .then(response => response.json())
        .then(data => {
            if (!data.timezoneSet) {
                console.log('Timezone not set on the server, sending to server...');

                fetch('/set-timezone/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')  // Ensure CSRF token is included
                    },
                    body: JSON.stringify({'timezone': userTimezone})
                }).then(response => {
                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }
                    return response.json();
                })
                .then(data => {
                    console.log('Timezone successfully set on server:', data);
                    sessionStorage.setItem('timezoneSet', 'true');
                })
                .catch(error => {
                    console.error('Error setting timezone:', error);
                });
            } else {
                console.log('Timezone already set on the server.');
            }
        });
});

function getCookie(name) {
    console.log('Retrieving CSRF token from cookies...');
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    console.log('CSRF token retrieved:', cookieValue);
    return cookieValue;
}
