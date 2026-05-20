
# ovos-adapt-pipeline-plugin — Audit Report

## Documentation Status
- [ ] AGENTS.md Header Format
- [ ] QUICK_FACTS.md (Moved from docs/)
- [ ] FAQ.md (Moved from docs/)
- [ ] MAINTENANCE_REPORT.md
- [x] AUDIT.md
- [ ] SUGGESTIONS.md
- [ ] docs/index.md

## Technical Debt & Issues
- `[MINOR]` **ci**: Action `pypa/gh-action-pypi-publish` pinned to `@master` (should be `@release/v1`)
- `[MINOR]` **ci**: Action `ad-m/github-push-action` pinned to `@master` (should be `@pinned ref`)
- `[MINOR]` **ci**: Deprecated Python version(s) in matrix: 3.7, 3.8, 3.9
- `[INFO]` **ci**: Python matrix missing: 3.12
- `[INFO]` **packaging**: Uses setup.py (consider migrating to pyproject.toml)

## Next Steps
- Pin `pypa/gh-action-pypi-publish` to `@release/v1` instead of `@master`
- Pin `ad-m/github-push-action` to `@pinned ref` instead of `@master`
- Remove EOL Python 3.7, 3.8, 3.9 from test matrix
- Add Python 3.12 to test matrix
- Migrate from setup.py to pyproject.toml
