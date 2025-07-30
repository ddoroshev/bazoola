# Bazoola

[![CI](https://github.com/ddoroshev/bazoola/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/ddoroshev/bazoola/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight, file-based database implementation in Python designed for educational purposes and simple applications.

## Overview

Bazoola is a minimal database system that stores data in text files with fixed-width fields. It supports basic database operations like CRUD (Create, Read, Update, Delete), schema validation, foreign key relationships, and simple querying capabilities.

## Features

- **File-based storage**: Data is stored in human-readable text files with fixed-width fields
- **Schema definition**: Define table schemas with typed fields
- **Primary keys**: Automatic ID generation (manual ID assignment validates uniqueness but doesn't support custom sequences)
- **Foreign keys**: Support for relationships between tables
- **Indexing**: ID-based indexing for fast lookups
- **Joins**: Support for joining related tables
- **Querying**: Find records by field values, substrings, or custom conditions
- **Free space management**: Reuses deleted record space

## Installation

### Install as a package

```bash
# Install directly from GitHub
pip install git+https://github.com/ddoroshev/bazoola.git
```

### Development setup

```bash
# Clone the repository
git clone https://github.com/ddoroshev/bazoola.git
cd bazoola

# Install dependencies using Poetry
poetry install
```

## Quick Start

```python
from bazoola import DB, Table, Schema, Field, PK, FK, CHAR, INT, Join

# Define table schemas
class TableAuthors(Table):
    name = "authors"
    schema = Schema([
        Field("id", PK()),
        Field("name", CHAR(20)),
    ])

class TableBooks(Table):
    name = "books"
    schema = Schema([
        Field("id", PK()),
        Field("title", CHAR(20)),
        Field("author_id", FK("authors")),
        Field("year", INT(null=True)),
    ])

# Create database instance
db = DB([TableAuthors, TableBooks])

# Insert data
author = db.insert("authors", {"name": "John Doe"})
book = db.insert("books", {
    "title": "My Book",
    "author_id": author["id"],
    "year": 2024
})

# Query with joins
book_with_author = db.find_by_id(
    "books",
    book["id"],
    joins=[Join("author_id", "author", "authors")]
)
print(book_with_author)
# Output: {'id': 1, 'title': 'My Book', 'author_id': 1, 'year': 2024, 'author': {'id': 1, 'name': 'John Doe'}}

# Close the database
db.close()
```

## Field Types

- **PK()**: Primary key field (auto-incrementing integer)
- **INT(null=False)**: Integer field
- **CHAR(size, null=False)**: Fixed-size character field
- **FK(table_name, null=False)**: Foreign key field

## Demo Application

A full-featured task management web application is included to demonstrate Bazoola's capabilities in a real-world scenario.

```bash
# Run the demo
poetry install
poetry run python demo/app.py
```

Visit http://localhost:5000 to explore the demo. It showcases:
- Complex schema with 4 interconnected tables (users, projects, tasks, comments)
- Foreign key relationships and joins
- CRUD operations with web forms
- Case-insensitive search across multiple tables
- Working within Bazoola's constraints (fixed-width fields, no transactions)

See [demo/](demo/) for more details.

## API Reference

### Database Operations

```python
# Insert a record
row = db.insert("table_name", {"field": "value"})

# Find by ID
row = db.find_by_id("table_name", id)

# Find all records
rows = db.find_all("table_name")

# Find by field value
rows = db.find_by("table_name", "field_name", value)

# Update a record
row = db.update_by_id("table_name", id, {"field": "new_value"})

# Delete a record
db.delete_by_id("table_name", id)

# Truncate table
db.truncate("table_name", cascade=False)
```

### Advanced Queries

```python
from bazoola import GT, LT

# Find with conditions
rows = db.find_by_cond("books", GT(year=2020))
rows = db.find_by_cond("books", LT(year=2000))
rows = db.find_by_cond("table_name", SUBSTR(field_name="substr"))
rows = db.find_by_cond("table_name", ISUBSTR(field_name="SuBsTr"))

# Query with joins
rows = db.find_all("books", joins=[
    Join("author_id", "author", "authors")
])

# Inverse joins (one-to-many)
from bazoola import InverseJoin
author = db.find_by_id("authors", 1, joins=[
    InverseJoin("author_id", "books", "books")
])
```

## File Structure

Bazoola creates the following files for each table:
- `{table_name}.dat` - Main data file
- `{table_name}__seqnum.dat` - Sequence number for auto-increment
- `{table_name}__id.idx.dat` - Primary key index
- `{table_name}__free.dat` - Free rownum stack for space reuse

## Configuration

By default, database files are stored in a `data` directory. You can specify a different directory when creating the database:

```python
# Use default 'data' directory
db = DB([TableAuthors, TableBooks])

# Use custom directory
db = DB([TableAuthors, TableBooks], base_dir="/path/to/data/directory")
```

## Testing

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov

# Type checking
poetry run mypy .

# Linting
poetry run ruff check .
```

## Limitations

- No multi-threading support
- No transactions or rollback support
- Limited query optimization
- Fixed-size fields only
- No SQL interface (by design)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
