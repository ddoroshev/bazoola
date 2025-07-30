"""
Database schema definitions for the Task Manager demo
"""

from bazoola import CHAR, FK, INT, PK, Field, Schema, Table


class TableUsers(Table):
    name = "users"
    schema = Schema(
        [
            Field("id", PK()),
            Field("username", CHAR(20)),
            Field("email", CHAR(50)),
            Field("role", CHAR(10)),  # "admin", "manager", "user"
        ]
    )


class TableProjects(Table):
    name = "projects"
    schema = Schema(
        [
            Field("id", PK()),
            Field("name", CHAR(30)),
            Field("description", CHAR(100)),
            Field("owner_id", FK("users")),
            Field("status", CHAR(10)),  # "active", "completed", "paused"
            Field("created_date", CHAR(10)),  # "2024-12-23"
            Field("due_date", CHAR(10, null=True)),
        ]
    )


class TableTasks(Table):
    name = "tasks"
    schema = Schema(
        [
            Field("id", PK()),
            Field("title", CHAR(50)),
            Field("description", CHAR(150)),
            Field("project_id", FK("projects")),
            Field("assignee_id", FK("users", null=True)),
            Field("status", CHAR(15)),  # "todo", "in_progress", "done", "blocked"
            Field("priority", CHAR(6)),  # "low", "medium", "high"
            Field("created_date", CHAR(10)),  # "2024-12-23"
            Field("due_date", CHAR(10, null=True)),
            Field("estimated_hours", INT(null=True)),
        ]
    )


class TableComments(Table):
    name = "comments"
    schema = Schema(
        [
            Field("id", PK()),
            Field("task_id", FK("tasks")),
            Field("user_id", FK("users")),
            Field("content", CHAR(200)),
            Field("created_date", CHAR(10)),  # "2024-12-23"
        ]
    )
