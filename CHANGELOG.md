# Changelog

## 0.0.6 - 2025-08-11

### Added
- Script to update LOC in repository description
- PyPI badge in README

### Changed
- Demo application improvements with extracted sample data
- Refactored `find_by` to use `find_by_cond` for better consistency

### Fixed
- Concurrency issue resolution

## 0.0.5 - 2025-07-30

### Added
- `SUBSTR` and `ISUBSTR` condition classes for substring matching in `find_by_cond`
- Comprehensive Flask demo application (`demo/`) showcasing real-world usage:
  - Task management system with users, projects, tasks, and comments
  - Complex schema with foreign key relationships
  - Web interface with CRUD operations
  - Case-insensitive search functionality using `ISUBSTR`
  - Proper separation of concerns with `schema.py`
- Import sorting configuration with `ruff`

### Changed
- Replaced `find_by_substr` with `SUBSTR` condition for `find_by_cond`
- Updated demo to use explicit imports instead of wildcard imports
- Enhanced README with demo application section

### Removed
- `find_by_substr` method from DB and Table classes
- `delete_by_substr` method from DB and Table classes

## 0.0.4 - 2025-07-21

### Added
- Global lock to handle concurrency

## 0.0.3 - 2025-07-18

### Changed
- CI workflow now allows tests on all branches

## 0.0.2 - 2025-07-16

### Added
- `base_dir` parameter instead of `TEST_BASE_DIR` environment variable

### Fixed
- Import statements in README documentation

## 0.0.1 - 2025-07-14

### Added
- Initial implementation of minimal DB with demo
- Test suite
- README documentation
- Pre-commit hooks configuration
- GitHub Actions CI workflow
- Proper package structure
- Package checker in CI
- Python 3.10+ compatibility
- PyPI publishing workflow
