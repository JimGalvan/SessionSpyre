(function (config) {
    // Utility function to get a cookie value
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    // Utility function to set a cookie with a custom expiration time in hours
    function setCookie(name, value, hours) {
        const expires = new Date(Date.now() + hours * 60 * 60 * 1000).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/`;
    }

    // Utility function to delete a cookie
    function deleteCookie(name) {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
    }

    // Check if a session cookie exists, if not, create one
    let sessionId = getCookie('recording_session_id');
    if (!sessionId) {
        sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
        setCookie('recording_session_id', sessionId, 8); // Cookie valid for 8 hours
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
    const userId = config.userId;
    const siteId = config.siteId || 'unknown';
    const siteKey = config.siteKey || 'unknown';

    if (!userId) {
        console.error("User ID is not provided. Event recording will not start.");
        return; // Exit if user_id is not provided
    }

    console.log('User ID:', userId);

    let events = [];
    let host = window.location.host; // dynamically gets the current server host
    let socket = new WebSocket(`ws://${host}/ws/record-session/${sessionId}/?site_key=${siteKey}`);

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
                    site_id: siteId,
                    events: events,
                }));
                events = [];
            }
            resetInactivityTimeout(); // Reset inactivity timeout on every event
        },
        sampling: {
            input: 'last',
            mouseInteraction: {
                MouseUp: false,
                MouseDown: false,
                Click: false,
                ContextMenu: false,
                DblClick: false,
                Focus: false,
                Blur: false,
                TouchStart: false,
                TouchEnd: false,
            },
        }
    });

    // Inactivity detection logic
    let inactivityTimeout;
    let extendedInactivityTimeout;
    const extendedInactivityLimit = 1800000; // 30 minutes for terminating the session

    function resetInactivityTimeout() {
        clearTimeout(inactivityTimeout);
        clearTimeout(extendedInactivityTimeout);

        extendedInactivityTimeout = setTimeout(() => {
            console.log("User inactive for 30 minutes. Terminating session.");
            terminateSession();
        }, extendedInactivityLimit);
    }

    function resumeRecordingOnActivity() {
        resetInactivityTimeout(); // Reset inactivity timer on activity
    }

    function terminateSession() {
        stopRecording();
        deleteCookie('recording_session_id'); // Clear the session cookie
        if (socket.readyState === WebSocket.OPEN) {
            socket.close(); // Close the WebSocket connection
        }
    }

    // Start listening for user activity to reset inactivity timer
    document.addEventListener('mousemove', resumeRecordingOnActivity);
    document.addEventListener('keydown', resumeRecordingOnActivity);
    document.addEventListener('scroll', resumeRecordingOnActivity);

    // Initialize inactivity timeout
    resetInactivityTimeout();

    window.addEventListener('beforeunload', () => {
        if (events.length > 0) {
            socket.send(JSON.stringify({
                user_id: userId,
                events: events,
                site_id: siteId,
            }));
        }
        stopRecording();
        socket.close();
    });

})({
    userId: 1,
    siteId: 37,
    siteKey: '3773363413483d51613948a5bdb145c26eaf57da6391d5b7f57edffc2800ab20',
});
