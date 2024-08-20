document.addEventListener('DOMContentLoaded', (event) => {
    const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    // Check if the timezone is already set in the session
    if (!sessionStorage.getItem('timezoneSet')) {
        fetch('/set-timezone/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')  // Ensure CSRF token is included
            },
            body: JSON.stringify({'timezone': userTimezone})
        }).then(response => response.json())
            .then(data => {
                console.log('Timezone set:', data);
                sessionStorage.setItem('timezoneSet', 'true');
            });
    }
});

function getCookie(name) {
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
    return cookieValue;
}
