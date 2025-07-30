"""
Task Manager Demo - Flask Application for Bazoola Toy Database
"""

from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for
from sample_data import init_sample_data
from schema import TableComments, TableProjects, TableTasks, TableUsers

from bazoola import DB, ISUBSTR, Join

app = Flask(__name__)
app.secret_key = "demo-secret-key"

db = DB([TableUsers, TableProjects, TableTasks, TableComments], base_dir="demo/data")


@app.route("/")
def index():
    """
    Dashboard showing overview of projects and tasks
    """
    projects = db.find_all("projects", joins=[Join("owner_id", "owner", "users")])
    recent_tasks = db.find_all(
        "tasks",
        joins=[Join("project_id", "project", "projects"), Join("assignee_id", "assignee", "users")],
    )[:5]  # Limit to 5 most recent

    return render_template("index.html", projects=projects, recent_tasks=recent_tasks)


@app.route("/users")
def users():
    """
    List all users
    """
    all_users = db.find_all("users")
    return render_template("users.html", users=all_users)


@app.route("/users/new", methods=["GET", "POST"])
def new_user():
    """
    Create new user
    """
    if request.method == "POST":
        try:
            user_data = {
                "username": request.form["username"].strip(),
                "email": request.form["email"].strip(),
                "role": request.form["role"],
            }
            db.insert("users", user_data)
            flash(f"User '{user_data['username']}' created successfully!", "success")
            return redirect(url_for("users"))
        except Exception as e:
            flash(f"Error creating user: {e}", "error")

    return render_template("user_form.html", user=None)


@app.route("/projects")
def projects():
    """
    List all projects with owner information
    """
    all_projects = db.find_all("projects", joins=[Join("owner_id", "owner", "users")])
    return render_template("projects.html", projects=all_projects)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    """
    Show project details with associated tasks
    """
    project = db.find_by_id("projects", project_id, joins=[Join("owner_id", "owner", "users")])
    if not project:
        flash("Project not found", "error")
        return redirect(url_for("projects"))

    tasks = db.find_by(
        "tasks", "project_id", project_id, joins=[Join("assignee_id", "assignee", "users")]
    )
    return render_template("project_detail.html", project=project, tasks=tasks)


@app.route("/projects/new", methods=["GET", "POST"])
def new_project():
    """
    Create new project
    """
    if request.method == "POST":
        try:
            project_data = {
                "name": request.form["name"].strip(),
                "description": request.form["description"].strip(),
                "owner_id": int(request.form["owner_id"]),
                "status": request.form["status"],
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "due_date": request.form["due_date"] if request.form["due_date"] else None,
            }
            db.insert("projects", project_data)
            flash(f"Project '{project_data['name']}' created successfully!", "success")
            return redirect(url_for("projects"))
        except Exception as e:
            flash(f"Error creating project: {e}", "error")

    users = db.find_all("users")
    return render_template("project_form.html", project=None, users=users)


@app.route("/tasks")
def tasks():
    """
    List all tasks with project and assignee information
    """
    all_tasks = db.find_all(
        "tasks",
        joins=[Join("project_id", "project", "projects"), Join("assignee_id", "assignee", "users")],
    )
    return render_template("tasks.html", tasks=all_tasks)


@app.route("/tasks/<int:task_id>")
def task_detail(task_id):
    """
    Show task details with comments
    """
    task = db.find_by_id(
        "tasks",
        task_id,
        joins=[Join("project_id", "project", "projects"), Join("assignee_id", "assignee", "users")],
    )
    if not task:
        flash("Task not found", "error")
        return redirect(url_for("tasks"))

    comments = db.find_by(
        "comments", "task_id", task_id, joins=[Join("user_id", "author", "users")]
    )
    return render_template("task_detail.html", task=task, comments=comments)


@app.route("/tasks/new", methods=["GET", "POST"])
def new_task():
    """
    Create new task
    """
    if request.method == "POST":
        try:
            task_data = {
                "title": request.form["title"].strip(),
                "description": request.form["description"].strip(),
                "project_id": int(request.form["project_id"]),
                "assignee_id": int(request.form["assignee_id"])
                if request.form["assignee_id"]
                else None,
                "status": request.form["status"],
                "priority": request.form["priority"],
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "due_date": request.form["due_date"] if request.form["due_date"] else None,
                "estimated_hours": int(request.form["estimated_hours"])
                if request.form["estimated_hours"]
                else None,
            }
            db.insert("tasks", task_data)
            flash(f"Task '{task_data['title']}' created successfully!", "success")
            return redirect(url_for("tasks"))
        except Exception as e:
            flash(f"Error creating task: {e}", "error")

    projects = db.find_all("projects")
    users = db.find_all("users")
    return render_template("task_form.html", task=None, projects=projects, users=users)


@app.route("/tasks/<int:task_id>/edit", methods=["GET", "POST"])
def edit_task(task_id):
    """
    Edit existing task
    """
    task = db.find_by_id("tasks", task_id)
    if not task:
        flash("Task not found", "error")
        return redirect(url_for("tasks"))

    if request.method == "POST":
        try:
            task_data = {
                "title": request.form["title"].strip(),
                "description": request.form["description"].strip(),
                "project_id": int(request.form["project_id"]),
                "assignee_id": int(request.form["assignee_id"])
                if request.form["assignee_id"]
                else None,
                "status": request.form["status"],
                "priority": request.form["priority"],
                "due_date": request.form["due_date"] if request.form["due_date"] else None,
                "estimated_hours": int(request.form["estimated_hours"])
                if request.form["estimated_hours"]
                else None,
            }
            db.update_by_id("tasks", task_id, task_data)
            flash(f"Task '{task_data['title']}' updated successfully!", "success")
            return redirect(url_for("task_detail", task_id=task_id))
        except Exception as e:
            flash(f"Error updating task: {e}", "error")

    projects = db.find_all("projects")
    users = db.find_all("users")
    return render_template("task_form.html", task=task, projects=projects, users=users)


@app.route("/tasks/<int:task_id>/comment", methods=["POST"])
def add_comment(task_id):
    """
    Add comment to task
    """
    try:
        comment_data = {
            "task_id": task_id,
            "user_id": int(request.form["user_id"]),
            "content": request.form["content"].strip(),
            "created_date": datetime.now().strftime("%Y-%m-%d"),
        }
        db.insert("comments", comment_data)
        flash("Comment added successfully!", "success")
    except Exception as e:
        flash(f"Error adding comment: {e}", "error")

    return redirect(url_for("task_detail", task_id=task_id))


@app.route("/search")
def search():
    """
    Search functionality
    """
    query = request.args.get("q", "").strip()
    if not query:
        return render_template("search.html", results=None, query="")

    results = {
        "projects": db.find_by_cond(
            "projects", ISUBSTR(name=query), joins=[Join("owner_id", "owner", "users")]
        ),
        "tasks": db.find_by_cond(
            "tasks",
            ISUBSTR(title=query),
            joins=[
                Join("project_id", "project", "projects"),
                Join("assignee_id", "assignee", "users"),
            ],
        ),
        "users": db.find_by_cond("users", ISUBSTR(username=query)),
    }

    return render_template("search.html", results=results, query=query)


if __name__ == "__main__":
    init_sample_data(db)
    app.run(debug=True)
