from pathlib import Path

TODO_APP_URL = (Path(__file__).parent / "todo-app.html").as_uri()


def add_and_edit_todo_priority(page, url=TODO_APP_URL):
    page.goto(url)
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


def test_add_and_edit_todo_priority(page):
    add_and_edit_todo_priority(page)
