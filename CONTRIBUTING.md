# Contributing

Thanks for your interest in contributing to CloudLap.

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/cloudlap.git
cd cloudlap
pip install -r requirements.txt
pip install pytest

copy config.example.json config.json
# Edit config.json with your ngrok domain

python server.py          # Run server
python -m pytest tests/ -v  # Run tests
```

## Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — new features
- `fix:` — bug fixes
- `docs:` — documentation
- `test:` — test changes
- `security:` — security improvements

## Pull Request Process

1. Fork and clone the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Make changes and add tests
4. Run `python -m pytest tests/ -v` — all tests must pass
5. Commit, push, and open a PR

## Areas Where Help Is Needed

- macOS and Linux support
- Docker deployment
- Web dashboard UI
- OAuth authentication
- More test coverage

## Security Vulnerabilities

Do not open a public issue. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your work will be licensed under the MIT License.
