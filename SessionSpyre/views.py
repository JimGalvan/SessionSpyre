from django.shortcuts import render


def sessions_view(request):
    sessions = [
        {
            "session_id": "session_1",
            "user_id": "user_1",
            "events": [
                {"event": "click", "element": "button_1"},
                {"event": "click", "element": "button_2"},
            ]
        },
        {
            "session_id": "session_2",
            "user_id": "user_2",
            "events": [
                {"event": "click", "element": "button_3"},
                {"event": "click", "element": "button_4"},
            ]
        }
    ]

    return render(request, 'sessions.html', {'sessions': sessions})
