# lithoxyl Changelog

## 26.0.0

_(Unreleased)_

- Migrate build system from setup.py to pyproject.toml with flit
- Add GitHub Actions CI (Python 3.10-3.13, Linux/Windows/Mac)
- Add automated PyPI publishing via trusted OIDC on tag push
- Add Codecov coverage reporting
- Drop Python 2.x and 3.5-3.9 support
- Remove Python 2 artifacts (future imports, coding cookies)
- Add CHANGELOG.md

## 21.0.0

_(October 24, 2021)_

- Remove vendored statsutils
- Add FileEmitter test coverage
- Remove six dependency and imports
- Modernize StreamEmitter and SensibleFormatter for Python 3 unicode handling
- Fix Python 3.7-3.9 compatibility issues
- Run python-modernize for broader Python 3 support

## 20.0.0

_(January 9, 2020)_

- Add Python 3 support (all tests passing under Python 3.6+)
- Fix removed/changed builtins for Python 3 (print, hashing, exceptions)
- Add Travis CI configuration
- Add tox packaging environment
- Make lithoxyl.tests a proper package
- Drop Python 3.4 support
- Add coverage reporting via Codecov

## 0.4.3

_(October 6, 2018)_

- Add preliminary file stream reopening to handle ESTALE IOErrors (NFS stale file handles)
- Pass posargs through to pytest in tox.ini
