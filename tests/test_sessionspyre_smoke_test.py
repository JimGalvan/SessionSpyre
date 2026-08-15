import json
import os
import sys
import tempfile
import time
import uuid
from pathlib import Path

from playwright.sync_api import expect

BASE_URL = os.environ.get("SESSIONSPYRE_BASE_URL", "http://localhost:8000")

TEST_APP_DIR = Path(__file__).parent / "test_app"
TODO_APP_TEMPLATE_PATH = TEST_APP_DIR / "todo-app.html"
SCRIPT_PLACEHOLDER = "{#  Add Recording script in here  #}"

sys.path.insert(0, str(TEST_APP_DIR))
from test_app.test_todo_session_playback import add_and_edit_todo_priority  # noqa: E402


def test_register_login_create_site_and_inject_snippet(page, context):
    result = {
        "test": "session_recording_end_to_end",
        "status": "running",
        "completed_steps": [],
        "failed_step": None,
        "error": None,
        "current_url": None,
    }

    current_step = "setup"
    started_at = time.monotonic()

    def checkpoint(name, **details):
        result["completed_steps"].append(name)
        if details:
            result.setdefault("details", {})[name] = details

    try:
        unique = uuid.uuid4().hex[:10]
        username = f"pwtest_{unique}"
        email = f"{username}@example.com"
        password = "Playwright-Test-2026!"

        result["test_user"] = {
            "username": username,
            "email": email,
        }

        # 1. Registration
        current_step = "user_registration"

        page.goto(f"{BASE_URL}/register")
        page.fill('input[name="username"]', username)
        page.fill('input[name="email"]', email)
        page.fill('input[name="password1"]', password)
        page.fill('input[name="password2"]', password)
        page.get_by_role("button", name="Register").click()
        page.wait_for_url("**/login")

        checkpoint("user_registered")

        # 2. Login
        current_step = "user_login"

        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.get_by_role("button", name="Login").click()
        page.wait_for_url("**/accounts/profile/")

        checkpoint("user_logged_in")

        # 3. Site creation
        current_step = "site_creation"

        page.goto(f"{BASE_URL}/sites")
        page.get_by_role("button", name="Add New Site").click()
        page.wait_for_selector("#name")
        page.fill("#name", "Todo app")
        page.get_by_role("button", name="Create Site").click()
        page.wait_for_url("**/sites")

        checkpoint("site_created", site_name="Todo app")

        # 4. Snippet generation
        current_step = "snippet_generation"

        site_card = page.locator("h2", has_text="Todo app").locator(
            "xpath=ancestor::div[@x-data][1]"
        )
        site_card.get_by_role("button", name="Install Code").click()

        snippet_content = site_card.locator("#snippet-content")
        expect(snippet_content).to_contain_text(
            "recordConfig",
            timeout=10000,
        )

        checkpoint("recording_snippet_generated")

        # 5. Clipboard
        current_step = "snippet_copy"

        context.grant_permissions(["clipboard-read", "clipboard-write"])
        page.once("dialog", lambda dialog: dialog.accept())

        site_card.get_by_role("button", name="Copy Snippet").click()

        page.wait_for_function(
            "() => navigator.clipboard.readText().then(t => t.length > 0)"
        )

        snippet_text = page.evaluate("navigator.clipboard.readText()")

        assert "recordConfig" in snippet_text, (
            "Copied installation snippet did not contain recordConfig"
        )

        checkpoint(
            "recording_snippet_copied",
            snippet_length=len(snippet_text),
        )

        # 6. Inject snippet
        current_step = "snippet_injection"

        html = TODO_APP_TEMPLATE_PATH.read_text(encoding="utf-8")

        if SCRIPT_PLACEHOLDER not in html:
            raise RuntimeError(
                f"Recording script placeholder was not found in "
                f"{TODO_APP_TEMPLATE_PATH}"
            )

        injected_html = html.replace(
            SCRIPT_PLACEHOLDER,
            snippet_text,
            1,
        )

        temp_dir = Path(
            tempfile.mkdtemp(prefix="sessionspyre_todo_app_")
        )
        temp_todo_path = temp_dir / "todo-app.html"
        temp_todo_path.write_text(injected_html, encoding="utf-8")

        checkpoint("recording_snippet_injected")

        # 7. Generate recording
        current_step = "record_todo_session"

        add_and_edit_todo_priority(
            page,
            temp_todo_path.as_uri(),
        )

        checkpoint("todo_app_exercised")

        # 8. Sessions page
        current_step = "open_sessions"

        page.goto(f"{BASE_URL}/sites")
        site_card.get_by_role("link", name="View Sessions").click()
        page.wait_for_url("**/sessions_view/**")

        checkpoint("sessions_page_opened")

        # 9. Recorded session appears
        current_step = "recorded_session_appears"

        session_item = page.locator(
            "#sessions_list .cursor-pointer"
        ).first

        expect(
            session_item,
            "Expected the generated Todo app recording to appear "
            "in the sessions list",
        ).to_be_visible(timeout=10000)

        checkpoint("recorded_session_found")

        session_item.click()

        # 10. Playback
        current_step = "session_playback"

        expect(
            page.locator("#rrweb-player iframe"),
            "Expected the rrweb playback iframe to load for "
            "the newly recorded session",
        ).to_be_visible(timeout=10000)

        checkpoint("session_playback_loaded")

        result["status"] = "passed"

    except Exception as exc:
        result["status"] = "failed"
        result["failed_step"] = current_step
        result["error"] = f"{type(exc).__name__}: {exc}"

        # Evidence useful to an agent/debugger.
        result["current_url"] = page.url

        screenshot_path = (
            Path(tempfile.gettempdir())
            / f"sessionspyre-smoke-{uuid.uuid4().hex[:8]}.png"
        )

        try:
            page.screenshot(
                path=str(screenshot_path),
                full_page=True,
            )
            result["screenshot"] = str(screenshot_path)
        except Exception as screenshot_error:
            result["screenshot_error"] = str(screenshot_error)

        raise

    finally:
        result["duration_seconds"] = round(
            time.monotonic() - started_at,
            2,
        )
        result["current_url"] = page.url

        # One predictable line for the agent/harness to find.
        print(
            "SMOKE_RESULT_JSON="
            + json.dumps(result, default=str)
        )