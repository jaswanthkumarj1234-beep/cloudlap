# Contributing to CloudLap

Thanks for your interest in contributing to CloudLap! 🎉

## Quick Start

1. Fork the repo
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/cloudlap.git`
3. Create a branch: `git checkout -b feature/my-feature`
4. Make your changes
5. Run tests: `python -m pytest tests/ -v`
6. Commit: `git commit -m "feat: add my feature"`
7. Push: `git push origin feature/my-feature`
8. Open a Pull Request

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt
pip install pytest

# Copy config
copy config.example.json config.json
# Edit config.json with your ngrok domain

# Run server locally
python server.py

# Run tests
python -m pytest tests/ -v
```

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | Use For |
|--------|---------|
| `feat:` | New features |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes |
| `test:` | Adding/updating tests |
| `refactor:` | Code restructuring |
| `security:` | Security improvements |

## What We Need Help With

- 🍎 **macOS / Linux support** — test and fix platform-specific code
- 🐳 **Docker** — containerized deployment option
- 🌐 **Web Dashboard** — browser-based control panel
- 🔐 **OAuth** — proper authentication for the MCP endpoint
- 📱 **Mobile** — better experience on phone browsers
- 🧪 **Tests** — more edge cases and integration tests

## Security

If you find a security vulnerability, **do NOT open a public issue**. Email the maintainer or use GitHub's private vulnerability reporting. See [SECURITY.md](SECURITY.md).

## Code Style

- Python 3.10+ with type hints
- Async/await for all tool handlers
- Docstrings on all public functions
- Keep security checks in every file-access tool

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
