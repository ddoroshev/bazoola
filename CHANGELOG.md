# Changelog

## 0.0.5 - ...

### Added
- `SUBSTR` and `ISUBSTR` condition classes for substring matching in `find_by_cond`

### Changed
- Replaced `find_by_substr` with `SUBSTR` condition for `find_by_cond`

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
