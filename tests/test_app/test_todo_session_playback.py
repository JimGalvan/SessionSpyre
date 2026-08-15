"""
Drives the standalone todo app (tests/todo-app.html) with a real browser so
SessionSpyre's tracking snippet embedded in that page has real interactions
to record. No assertions on purpose — this isn't testing the todo app, it's
generating session data to inspect in the SessionSpyre dashboard.
"""
from pathlib import Path

TODO_APP_URL = (Path(__file__).parent / "todo-app.html").as_uri()


def test_add_and_edit_todo_priority(page):
    page.goto(TODO_APP_URL)
    page.wait_for_timeout(2000)

    page.fill("#new-todo-text", "Playwright generated todo")
    page.select_option("#new-todo-priority", "Medium")
    page.click("#add-btn")

    todo_item = page.locator("li.todo-item", has_text="Playwright generated todo")
    todo_item.get_by_role("button", name="Edit").click()

    editing_item = page.locator("li.todo-item:has(.edit-input)")
    editing_item.locator("select").select_option("High")
    editing_item.get_by_role("button", name="Save").click()

    page.wait_for_timeout(2000)
