(function() {
    const userId = new URLSearchParams(window.location.search).get('user_id') || 'anonymous';

    let sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
    let events = [];

    const stopRecording = rrweb.record({
        emit(event) {
            events.push(event);
            if (events.length >= 50) {
                sendEvents();
            }
        },
    });

    function sendEvents() {
        fetch('http://localhost:8000/api/save-session/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                user_id: userId,
                events: events,
            }),
        }).then(() => {
            events = [];
        });
    }

    window.addEventListener('beforeunload', () => {
        if (events.length > 0) sendEvents();
        stopRecording();
    });
})();
