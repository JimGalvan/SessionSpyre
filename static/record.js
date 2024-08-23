(function (config) {
    // Utility function to get a cookie value
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Utility function to set a cookie
    function setCookie(name, value, days) {
        const expires = new Date(Date.now() + days * 864e5).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
    }

    // Check if a session cookie exists, if not, create one
    let sessionId = getCookie('recording_session_id');
    if (!sessionId) {
        sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        setCookie('recording_session_id', sessionId, 1); // Cookie valid for 1 day
        console.log('New Session ID:', sessionId);
    } else {
        console.log('Existing Session ID:', sessionId);
    }

    // Function to check if the user is logged in by looking for common session-related cookies or tokens
    function checkSession() {
        const commonSessionCookies = ['sessionid', 'authToken', 'JSESSIONID', 'csrftoken'];

        for (const cookieName of commonSessionCookies) {
            if (document.cookie.includes(cookieName + '=')) {
                return true;
            }
        }

        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
            const [name, value] = cookie.split('=');
            if (value && value.length > 20 && /^[a-zA-Z0-9_-]+$/.test(value.trim())) {
                return true; // Found a likely session cookie
            }
        }

        const possibleTokens = ['authToken', 'sessionToken', 'jwtToken', 'accessToken'];
        for (const tokenName of possibleTokens) {
            if (localStorage.getItem(tokenName) || sessionStorage.getItem(tokenName)) {
                return true;
            }
        }

        return false; // No session detected
    }

    // Use developer-defined session check if provided, otherwise use default checkSession
    const sessionIsActive = (typeof config.checkSession === 'function' ? config.checkSession : checkSession)();

    // Configuration for the fallback behavior
    const enableFallback = config.enableFallback !== undefined ? config.enableFallback : true;

    if (!sessionIsActive && !enableFallback) {
        console.log("No active session detected and fallback is disabled. Event recording will not start.");
        return; // Exit if no session detected and fallback is disabled
    }

    if (!sessionIsActive && enableFallback) {
        console.log("No active session detected, but fallback is enabled. Recording will start.");
    }

    // Ensure user_id is provided by the developer
    const userId = config.user_id;

    if (!userId) {
        console.error("User ID is not provided. Event recording will not start.");
        return; // Exit if user_id is not provided
    }

    console.log('User ID:', userId);

    let events = [];
    const socket = new WebSocket(`ws://localhost:8000/ws/record-session/${sessionId}/`);

    socket.onopen = function () {
        console.log("WebSocket connection opened");
    };

    socket.onmessage = function (event) {
        console.log("Message from server:", event.data);
    };

    socket.onclose = function () {
        console.log("WebSocket connection closed");
    };

    const stopRecording = rrweb.record({
        emit(event) {
            events.push(event);
            if (events.length >= 10) { // Adjust the batch size as needed
                socket.send(JSON.stringify({
                    user_id: userId,
                    events: events,
                }));
                events = [];
            }
        },
    });

    window.addEventListener('beforeunload', () => {
        if (events.length > 0) {
            socket.send(JSON.stringify({
                user_id: userId,
                events: events,
            }));
        }
        stopRecording();
        socket.close();
    });

})({
    user_id: '1' // The ID defined by the developer, representing the logged-in user
});
