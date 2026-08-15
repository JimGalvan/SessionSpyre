import os
import sys
import uuid
from pathlib import Path

from playwright.sync_api import expect

BASE_URL = os.environ.get("SESSIONSPYRE_BASE_URL", "http://localhost:8000")

TEST_APP_DIR = Path(__file__).parent / "test_app"
TODO_APP_PATH = TEST_APP_DIR / "todo-app.html"
SCRIPT_PLACEHOLDER = "{#  Add Recording script in here  #}"

sys.path.insert(0, str(TEST_APP_DIR))
from test_app.test_todo_session_playback import test_add_and_edit_todo_priority as run_todo_interactions  # noqa: E402


def test_register_login_create_site_and_inject_snippet(page, context):
    unique = uuid.uuid4().hex[:10]
    username = f"pwtest_{unique}"
    email = f"{username}@example.com"
    password = "Playwright-Test-2026!"

    print(f"username: {username}")
    print(f"email: {email}")
    print(f"password: {password}")

    page.goto(f"{BASE_URL}/register")
    page.fill('input[name="username"]', username)
    page.fill('input[name="email"]', email)
    page.fill('input[name="password1"]', password)
    page.fill('input[name="password2"]', password)
    page.get_by_role("button", name="Register").click()
    page.wait_for_url("**/login")

    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.get_by_role("button", name="Login").click()
    page.wait_for_url("**/accounts/profile/")

    page.goto(f"{BASE_URL}/sites")
    page.get_by_role("button", name="Add New Site").click()
    page.wait_for_selector("#name")
    page.fill("#name", "Todo app")
    page.get_by_role("button", name="Create Site").click()
    page.wait_for_url("**/sites")

    # scoped to the outer x-data wrapper — the x-if snippet modal is a
    # sibling of the inner "cursor-pointer" card div, not its descendant
    site_card = page.locator("h2", has_text="Todo app").locator(
        "xpath=ancestor::div[@x-data][1]"
    )
    site_card.get_by_role("button", name="Install Code").click()

    snippet_content = site_card.locator("#snippet-content")
    expect(snippet_content).to_contain_text("recordConfig", timeout=10000)

    context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.once("dialog", lambda dialog: dialog.accept())
    site_card.get_by_role("button", name="Copy Snippet").click()
    page.wait_for_function("() => navigator.clipboard.readText().then(t => t.length > 0)")
    snippet_text = page.evaluate("navigator.clipboard.readText()")
    assert "recordConfig" in snippet_text, f"unexpected clipboard content: {snippet_text!r}"

    html = TODO_APP_PATH.read_text(encoding="utf-8")
    if SCRIPT_PLACEHOLDER not in html:
        raise RuntimeError(f"Placeholder {SCRIPT_PLACEHOLDER!r} not found in {TODO_APP_PATH}")
    TODO_APP_PATH.write_text(html.replace(SCRIPT_PLACEHOLDER, snippet_text, 1), encoding="utf-8")

    run_todo_interactions(page)
