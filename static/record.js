(function () {
    const REQUIRED_CONFIG_KEYS = ['userId', 'siteId', 'siteKey'];
    const COOKIE_NAMES = ['sessionid', 'authToken', 'JSESSIONID', 'csrftoken'];
    const TOKEN_NAMES = ['authToken', 'sessionToken', 'jwtToken', 'accessToken'];

    function initializeRecording() {
        const config = window.recordConfig;

        if (!isValidConfig(config)) {
            console.error("Invalid or missing configuration. Event recording will not start.");
            return;
        }

        const {userId, siteId, siteKey, enableFallback = true} = config;

        const sessionId = getOrCreateSessionId();
        const sessionIsActive = isSessionActive(config.checkSession);

        if (!sessionIsActive && !enableFallback) {
            console.log("No active session detected and fallback is disabled. Event recording will not start.");
            return;
        }

        if (!sessionIsActive && enableFallback) {
            console.log("No active session detected, but fallback is enabled. Recording will start.");
        }

        console.log('User ID:', userId);

        const socket = setupWebSocketConnection(userId, siteId, siteKey, sessionId);
        startRecording(socket, userId, siteId, siteKey);
    }

    function isValidConfig(config) {
        if (!config || typeof config !== 'object') return false;

        return REQUIRED_CONFIG_KEYS.every(key => {
            const value = config[key];
            switch (key) {
                case 'userId':
                case 'siteId':
                    return typeof value === 'number' && /^\d+$/.test(value.toString());
                case 'siteKey':
                    return typeof value === 'string' && value.length === 64 && /^[a-f0-9]+$/.test(value);
                default:
                    return false;
            }
        });
    }

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    function setCookie(name, value, hours) {
        const expires = new Date(Date.now() + hours * 60 * 60 * 1000).toUTCString();
        document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=None; Secure`;
    }

    function getOrCreateSessionId() {
        let sessionId = getCookie('recording_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
            setCookie('recording_session_id', sessionId, 8);
            console.log('New Session ID:', sessionId);
        } else {
            console.log('Existing Session ID:', sessionId);
        }
        return sessionId;
    }

    function isSessionActive(customCheck) {
        if (typeof customCheck === 'function') return customCheck();

        return COOKIE_NAMES.some(cookieName => document.cookie.includes(`${cookieName}=`)) ||
            document.cookie.split(';').some(cookie => {
                const [, value] = cookie.split('=');
                return value && value.trim().length > 20 && /^[a-zA-Z0-9_-]+$/.test(value.trim());
            }) ||
            TOKEN_NAMES.some(tokenName => localStorage.getItem(tokenName) || sessionStorage.getItem(tokenName));
    }

    function setupWebSocketConnection(userId, siteId, siteKey, sessionId) {
        const socket = new WebSocket(`ws://localhost:8000/ws/record-session/${sessionId}/?site_key=${siteKey}`);

        socket.onopen = () => console.log("WebSocket connection opened");
        socket.onmessage = event => console.log("Message from server:", event.data);
        socket.onclose = () => console.log("WebSocket connection closed");

        return socket;
    }

    function startRecording(socket, userId, siteId, siteKey) {
        let events = [];

        const stopRecording = rrweb.record({
            emit(event) {
                events.push(event);
                if (events.length >= 10) {
                    socket.send(JSON.stringify({user_id: userId, site_id: siteId, events}));
                    events = [];
                }
            },
            sampling: {
                input: 'last',
                mouseInteraction: {
                    MouseUp: false, MouseDown: false, Click: false, ContextMenu: false,
                    DblClick: false, Focus: false, Blur: false, TouchStart: false, TouchEnd: false,
                },
            }
        });

        window.addEventListener('beforeunload', () => {
            if (events.length > 0) {
                socket.send(JSON.stringify({user_id: userId, events, site_id: siteId}));
            }
            stopRecording();
            socket.close();
        });
    }

    function checkConfigAndInitialize() {
        if (window.recordConfig) {
            clearInterval(configCheckInterval);
            clearTimeout(timeoutHandle);
            initializeRecording();
        }
    }

    const configCheckInterval = setInterval(checkConfigAndInitialize, 1000);
    const timeoutHandle = setTimeout(() => {
        clearInterval(configCheckInterval);
        console.error("Configuration object not found within the timeout period. Event recording will not start.");
    }, 20000);

})();
