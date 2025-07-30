from datetime import datetime


def init_sample_data(db):
    """
    Initialize database with sample data if empty
    """
    try:
        if db.find_all("users"):
            return

        # Sample users
        users = [
            {"username": "admin", "email": "admin@example.com", "role": "admin"},
            {"username": "alice", "email": "alice@example.com", "role": "manager"},
            {"username": "bob", "email": "bob@example.com", "role": "user"},
            {"username": "charlie", "email": "charlie@example.com", "role": "user"},
        ]

        for user in users:
            db.insert("users", user)

        # Sample projects
        today = datetime.now().strftime("%Y-%m-%d")
        projects = [
            {
                "name": "Website Redesign",
                "description": "Complete overhaul of company website",
                "owner_id": 2,
                "status": "active",
                "created_date": today,
                "due_date": "2024-12-31",
            },
            {
                "name": "Mobile App",
                "description": "Develop iOS and Android app",
                "owner_id": 2,
                "status": "active",
                "created_date": today,
                "due_date": "2025-03-15",
            },
        ]

        for project in projects:
            db.insert("projects", project)

        # Sample tasks
        tasks = [
            {
                "title": "Design mockups",
                "description": "Create wireframes and visual designs",
                "project_id": 1,
                "assignee_id": 3,
                "status": "done",
                "priority": "high",
                "created_date": today,
                "estimated_hours": 16,
            },
            {
                "title": "Frontend development",
                "description": "Implement responsive HTML/CSS",
                "project_id": 1,
                "assignee_id": 3,
                "status": "in_progress",
                "priority": "high",
                "created_date": today,
                "due_date": "2024-12-25",
                "estimated_hours": 40,
            },
            {
                "title": "Backend API",
                "description": "Develop REST API endpoints",
                "project_id": 1,
                "assignee_id": 4,
                "status": "todo",
                "priority": "medium",
                "created_date": today,
                "estimated_hours": 32,
            },
            {
                "title": "App architecture",
                "description": "Plan mobile app structure",
                "project_id": 2,
                "assignee_id": 3,
                "status": "todo",
                "priority": "medium",
                "created_date": today,
                "estimated_hours": 8,
            },
        ]

        for task in tasks:
            db.insert("tasks", task)

        # Sample comments
        comments = [
            {
                "task_id": 1,
                "user_id": 2,
                "content": "Great work on the initial designs!",
                "created_date": today,
            },
            {
                "task_id": 2,
                "user_id": 3,
                "content": "Need clarification on mobile responsiveness requirements",
                "created_date": today,
            },
        ]

        for comment in comments:
            db.insert("comments", comment)

    except Exception as e:
        print(f"Error initializing sample data: {e}")
