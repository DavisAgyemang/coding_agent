# 🤖 CodeMan: Advanced Multi-Provider LLM & Secure Sandboxed Execution Harness

CodeMan is a modular AI developer assistant that integrates with local files and validates code changes in an isolated container.

## Core features

- Multi-provider LLM support
- Saved, switchable chat histories
- Tree-sitter repository mapping
- Self-correcting code validation
- Ephemeral Podman or Docker sandboxing

## Sandbox setup (Podman without Docker)

CodeMan uses the Python Docker API client because Podman exposes a Docker-compatible API. The Docker application and Docker CLI are **not required**. CodeMan automatically discovers the active Podman socket.

### macOS or Windows

Install and initialize Podman once:

```bash
brew install podman                 # macOS example
podman machine init                 # only needed once
```

Each time the machine is not running, start it in another terminal:

```bash
podman machine start
```

Then start CodeMan normally:

```bash
codeman
```

You do not need to export `DOCKER_HOST`; CodeMan discovers the local socket from `podman machine inspect`. An explicitly configured `DOCKER_HOST` is still respected.

### Linux (rootless Podman)

Start the Docker-compatible user API socket:

```bash
systemctl --user enable --now podman.socket
```

Then start CodeMan:

```bash
codeman
```

The standard rootless socket at `/run/user/$UID/podman/podman.sock` is detected automatically.

### Verify Podman

```bash
podman info
podman run --rm hello-world
```

CodeMan pulls `python:3.11-slim` on its first sandbox startup, so the first launch may take longer.

## Docker alternative

If Docker is installed, CodeMan continues to support it. Start Docker Desktop or the Docker daemon, then run CodeMan normally. When `DOCKER_HOST` is set, CodeMan tries that endpoint first.

## Install and run

```bash
pip install -r requirements.txt
python main.py
```

## Run CodeMan from anywhere

For bash:

```bash
echo 'alias codeman="<PATH_TO_PROJECT>/.venv/bin/python <PATH_TO_PROJECT>/main.py"' >> ~/.bashrc
source ~/.bashrc
```

For zsh:

```bash
echo 'alias codeman="<PATH_TO_PROJECT>/.venv/bin/python <PATH_TO_PROJECT>/main.py"' >> ~/.zshrc
source ~/.zshrc
```
