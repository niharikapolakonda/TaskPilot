from flask import Flask, render_template, request, redirect, url_for
from datetime import date, datetime
from pathlib import Path
import json
import os

app = Flask(__name__)

DATA_FILE = Path(__file__).with_name("tasks.json")

CATEGORIES = [
    "Study", "Work", "Personal", "Health", "Project", "Other"
]

PRIORITIES = ["Low", "Medium", "High"]


def load_tasks():
    if not DATA_FILE.exists():
        return []

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks(tasks):
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(tasks, file, indent=2, ensure_ascii=False)


def get_next_id(tasks):
    return max((task.get("id", 0) for task in tasks), default=0) + 1


@app.route("/")
def index():
    tasks = load_tasks()

    today = date.today().isoformat()
    search = request.args.get("search", "").strip().lower()
    category_filter = request.args.get("category", "All")
    status_filter = request.args.get("status", "All")
    priority_filter = request.args.get("priority", "All")

    total = len(tasks)
    completed = sum(1 for task in tasks if task.get("completed"))
    pending = total - completed

    overdue = sum(
        1 for task in tasks
        if not task.get("completed")
        and task.get("due_date")
        and task["due_date"] < today
    )

    due_today = sum(
        1 for task in tasks
        if not task.get("completed")
        and task.get("due_date") == today
    )

    progress = round((completed / total) * 100) if total else 0

    filtered_tasks = []

    for task in tasks:
        if search and search not in (
            task.get("title", "") + " " + task.get("description", "")
        ).lower():
            continue

        if category_filter != "All" and task.get("category") != category_filter:
            continue

        if priority_filter != "All" and task.get("priority") != priority_filter:
            continue

        if status_filter == "Pending" and task.get("completed"):
            continue

        if status_filter == "Completed" and not task.get("completed"):
            continue

        filtered_tasks.append(task)

    # Incomplete tasks first, then earliest deadline.
    filtered_tasks.sort(
        key=lambda task: (
            task.get("completed", False),
            task.get("due_date") or "9999-12-31",
            {"High": 0, "Medium": 1, "Low": 2}.get(
                task.get("priority"), 3
            )
        )
    )

    category_counts = {
        category: sum(
            1 for task in tasks
            if task.get("category") == category
        )
        for category in CATEGORIES
    }

    return render_template(
        "index.html",
        tasks=filtered_tasks,
        total=total,
        completed=completed,
        pending=pending,
        overdue=overdue,
        due_today=due_today,
        progress=progress,
        categories=CATEGORIES,
        priorities=PRIORITIES,
        category_counts=category_counts,
        today=today,
        search=request.args.get("search", ""),
        category_filter=category_filter,
        status_filter=status_filter,
        priority_filter=priority_filter
    )


@app.route("/add", methods=["POST"])
def add_task():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "Other")
    priority = request.form.get("priority", "Medium")
    due_date = request.form.get("due_date", "")

    if not title or len(title) > 120:
        return "Enter a task title (maximum 120 characters).", 400

    if category not in CATEGORIES or priority not in PRIORITIES:
        return "Invalid category or priority.", 400

    if due_date:
        try:
            datetime.strptime(due_date, "%Y-%m-%d")
        except ValueError:
            return "Invalid due date.", 400

    tasks = load_tasks()

    tasks.append({
        "id": get_next_id(tasks),
        "title": title,
        "description": description[:500],
        "category": category,
        "priority": priority,
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.now().isoformat(timespec="minutes")
    })

    save_tasks(tasks)
    return redirect(url_for("index"))


@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle_task(task_id):
    tasks = load_tasks()

    for task in tasks:
        if task.get("id") == task_id:
            task["completed"] = not task.get("completed", False)
            break

    save_tasks(tasks)
    return redirect(url_for("index"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):
    tasks = load_tasks()
    tasks = [task for task in tasks if task.get("id") != task_id]
    save_tasks(tasks)
    return redirect(url_for("index"))


@app.route("/clear-completed", methods=["POST"])
def clear_completed():
    tasks = load_tasks()
    tasks = [task for task in tasks if not task.get("completed", False)]
    save_tasks(tasks)
    return redirect(url_for("index"))


@app.route("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )