# Task Manager Demo

A Flask web application demonstrating Bazoola's database capabilities through a practical task management system.

## Quick Start

```bash
git clone https://github.com/ddoroshev/bazoola.git
cd bazoola
poetry install
poetry run python demo/app.py
```

Open http://localhost:5000 - sample data is created automatically.

## Database Schema

```
users:     id(PK), username(CHAR20), email(CHAR50), role(CHAR10)
projects:  id(PK), name(CHAR30), description(CHAR100), owner_id(FK→users),
           status(CHAR10), created_date(CHAR10), due_date(CHAR10,null)
tasks:     id(PK), title(CHAR50), description(CHAR150), project_id(FK→projects),
           assignee_id(FK→users,null), status(CHAR15), priority(CHAR6),
           created_date(CHAR10), due_date(CHAR10,null), estimated_hours(INT,null)
comments:  id(PK), task_id(FK→tasks), user_id(FK→users),
           content(CHAR200), created_date(CHAR10)
```

## Key Features

### Database Operations
- **CRUD**: Full create, read, update, delete operations
- **Relationships**: Foreign key constraints with validation
- **Joins**: Related data fetching with `Join()` and `InverseJoin()`
- **Search**: Case-insensitive substring search using `ISUBSTR` condition
- **Thread Safety**: File locking for concurrent access

### Application Routes
- `/` - Dashboard with projects and recent tasks
- `/projects` - Project management with owner relationships
- `/tasks` - Task tracking with multi-table joins
- `/users` - User management
- `/search` - Cross-table search using `ISUBSTR`
- `/tasks/{id}` - Task details with comments

## Notable Constraints

- **Fixed-width CHAR fields** - No variable-length text storage
- **6-byte integers** - Limited number range
- **No indexes** except primary keys - Full table scans for searches
- **No transactions** - Operations can't be rolled back

## Educational Value

This demo illustrates:
- Schema design with relationships and constraints
- SQL concepts implemented in Python
- Performance trade-offs of file-based storage
- Working within database limitations

---

**Note**: This is an educational toy database. Use proper database systems for production applications.
