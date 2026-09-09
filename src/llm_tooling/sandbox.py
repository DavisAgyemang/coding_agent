"""Cross-platform container sandbox for Podman and Docker.

The Python ``docker`` package is only an API client.  Podman exposes a
Docker-compatible API, so neither the Docker CLI nor Docker Desktop is required
when a Podman service or machine is running.
"""

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional

import docker


class ContainerSandbox:
    """Run validation commands in an ephemeral Docker-API-compatible container."""

    _DISCOVERY_TIMEOUT = 5

    def __init__(self, image_name: str = "python:3.11-slim"):
        self.image_name = image_name
        self.runtime = "container runtime"
        self.base_url: Optional[str] = None
        errors = []
        attempted = set()

        # Layer 1: let docker-py interpret a user-configured endpoint.  If it is
        # stale, discovery continues instead of making the CLI unusable.
        explicit_host = os.environ.get("DOCKER_HOST")
        if explicit_host:
            try:
                client = docker.from_env()
                client.ping()
                self._activate_client(client, explicit_host)
                return
            except Exception as exc:
                errors.append(f"DOCKER_HOST {explicit_host!r}: {exc}")
                attempted.add(self._normalise_socket(explicit_host) or explicit_host)

        # Layers 2-4 discover Podman and native platform endpoints.  Usually this
        # contains one item, but trying every usable socket avoids one stale socket
        # preventing a healthy engine later in the fallback list from being used.
        for endpoint in self._discover_socket_candidates(include_environment=False):
            if endpoint in attempted:
                continue
            attempted.add(endpoint)
            try:
                client = docker.DockerClient(base_url=endpoint)
                client.ping()
                self._activate_client(client, endpoint)
                return
            except Exception as exc:
                errors.append(f"socket {endpoint}: {exc}")

        # Keep docker.from_env as a backwards-compatible final fallback (for
        # Docker contexts/defaults which are not represented by a local path).
        try:
            client = docker.from_env()
            client.ping()
            self._activate_client(client, None)
            return
        except Exception as exc:
            errors.append(f"default Docker endpoint: {exc}")

        raise RuntimeError(self._connection_error_message(errors))

    def _activate_client(self, client: Any, endpoint: Optional[str]) -> None:
        """Record a verified client and ensure the sandbox image is available."""
        self.client = client
        self.runtime = self._runtime_name(client)
        self.base_url = endpoint
        self.client.images.pull(self.image_name)

    @staticmethod
    def _runtime_name(client: Any) -> str:
        try:
            text = json.dumps(client.version()).lower()
            return "Podman" if "podman" in text else "Docker"
        except Exception:
            return "container runtime"

    @staticmethod
    def _normalise_socket(value: Optional[str]) -> Optional[str]:
        """Convert a discovered path/pipe to a docker-py-compatible endpoint."""
        if not isinstance(value, str):
            return None
        value = value.strip().strip("'\"").strip()
        if not value:
            return None

        lower_value = value.lower()
        # docker-py cannot establish Podman's SSH transport itself.  Machine
        # inspection supplies the corresponding local forwarded socket instead.
        if lower_value.startswith("ssh://"):
            return None
        if lower_value.startswith("npipe://"):
            return "npipe://" + value[len("npipe://") :].replace("\\", "/")
        if value.startswith("\\\\.\\pipe\\") or lower_value.startswith("//./pipe/"):
            pipe = value.replace("\\", "/")
            return f"npipe://{pipe}"
        if lower_value.startswith(("unix://", "tcp://", "http://", "https://")):
            return value
        if value.startswith("/"):
            return f"unix://{value}"
        return None

    @staticmethod
    def _run_podman(args: list[str]) -> Optional[str]:
        """Run a bounded discovery query, suppressing expected CLI failures."""
        if not shutil.which("podman"):
            return None
        try:
            result = subprocess.run(
                ["podman", *args],
                capture_output=True,
                text=True,
                timeout=ContainerSandbox._DISCOVERY_TIMEOUT,
                check=True,
            )
            return result.stdout
        except (OSError, subprocess.SubprocessError):
            return None

    @classmethod
    def _machine_socket_values(cls, machine: Any) -> Iterable[str]:
        """Read socket locations emitted by old and new Podman inspect schemas."""
        if not isinstance(machine, dict):
            return

        connection = machine.get("ConnectionInfo")
        sources = [connection, machine]
        keys = (
            "PodmanSocket",
            "RootfulPodmanSocket",
            "SocketPath",
            "PodmanSocketPath",
        )
        for source in sources:
            if not isinstance(source, dict):
                continue
            for key in keys:
                value = source.get(key)
                if isinstance(value, str):
                    yield value
                elif isinstance(value, dict):
                    # Schema variants have used Path, path, URI, and Uri.
                    for child_key in ("Path", "path", "URI", "Uri", "uri"):
                        child = value.get(child_key)
                        if isinstance(child, str):
                            yield child

    @classmethod
    def _discover_socket_candidates(
        cls, include_environment: bool = True
    ) -> Iterable[str]:
        """Yield de-duplicated endpoints in strict discovery priority order."""
        seen = set()

        def accept(raw: Optional[str], require_file: bool = False) -> Optional[str]:
            endpoint = cls._normalise_socket(raw)
            if not endpoint or endpoint in seen:
                return None
            if require_file and endpoint.startswith("unix://"):
                if not Path(endpoint[len("unix://") :]).exists():
                    return None
            seen.add(endpoint)
            return endpoint

        # Layer 1: an explicit, syntactically usable environment endpoint.
        if include_environment:
            endpoint = accept(os.environ.get("DOCKER_HOST"))
            if endpoint:
                yield endpoint

        # Layer 2: query the running engine.  This is Podman's most authoritative
        # cross-platform answer and works for local services and machines.
        output = cls._run_podman(
            ["info", "--format", "{{.Host.RemoteSocket.Path}}"]
        )
        endpoint = accept(output)
        if endpoint:
            yield endpoint

        # Layer 3: inspect machine state across Podman schema versions.
        output = cls._run_podman(["machine", "inspect"])
        if output:
            try:
                machines = json.loads(output)
                if isinstance(machines, dict):
                    machines = [machines]
                if isinstance(machines, list):
                    for machine in machines:
                        for raw in cls._machine_socket_values(machine):
                            endpoint = accept(raw)
                            if endpoint:
                                yield endpoint
            except (ValueError, TypeError):
                pass

        # Layer 4: local OS conventions.  File endpoints must exist; named pipes
        # are probed by docker-py because ordinary Windows file checks are not a
        # reliable way to determine whether a pipe server is accepting clients.
        system = platform.system()
        if system == "Windows":
            for raw in (
                r"\\.\pipe\podman-machine-default",
                r"\\.\pipe\docker_engine",
            ):
                endpoint = accept(raw)
                if endpoint:
                    yield endpoint
            return

        paths = []
        if system == "Darwin":
            machine_root = (
                Path.home() / ".local" / "share" / "containers" / "podman" / "machine"
            )
            paths.extend(
                [
                    machine_root / "applehv" / "podman.sock",
                    machine_root / "applehv" / "podman-machine-default" / "podman.sock",
                    machine_root / "qemu" / "podman.sock",
                    machine_root / "qemu" / "podman-machine-default" / "podman.sock",
                    machine_root / "podman-machine-default" / "podman.sock",
                ]
            )
            try:
                paths.extend(sorted(machine_root.glob("**/*.sock")))
            except OSError:
                pass
        elif system == "Linux":
            try:
                uid = os.getuid()
            except AttributeError:
                uid = None
            if uid is not None:
                paths.append(Path(f"/run/user/{uid}/podman/podman.sock"))

        paths.append(Path("/var/run/docker.sock"))
        for path in paths:
            endpoint = accept(str(path), require_file=True)
            if endpoint:
                yield endpoint

    @classmethod
    def _discover_podman_socket(cls) -> Optional[str]:
        """Return the best auto-discovered Docker-compatible API endpoint."""
        return next(iter(cls._discover_socket_candidates()), None)

    @staticmethod
    def _connection_error_message(errors: list[str]) -> str:
        system = platform.system()
        if system in ("Darwin", "Windows"):
            guidance = (
                "Start Podman with `podman machine start`, or start Docker Desktop, "
                "then restart CodeMan."
            )
        elif system == "Linux":
            guidance = (
                "Start rootless Podman with `systemctl --user enable --now "
                "podman.socket`, or start Docker with `sudo systemctl start docker`, "
                "then restart CodeMan."
            )
        else:
            guidance = "Start a Podman API service or Docker daemon, then restart CodeMan."
        details = "; ".join(errors)
        return (
            "Sandbox auto-discovery could not connect to Podman or Docker. "
            f"{guidance} Docker is not required when Podman is available."
            + (f" Connection attempts: {details}" if details else "")
        )

    def run_command_in_sandbox(self, command: str) -> dict:
        """Mount the workspace, run a command, then remove the container."""
        workspace_dir = str(Path.cwd().resolve())
        container = None
        try:
            container = self.client.containers.create(
                image=self.image_name,
                command=["sh", "-c", command],
                working_dir="/workspace",
                volumes={workspace_dir: {"bind": "/workspace", "mode": "rw"}},
                mem_limit="512m",
                nano_cpus=1_000_000_000,
            )
            container.start()
            result = container.wait(timeout=30)
            exit_code = result.get("StatusCode", 1)
            logs = container.logs().decode("utf-8", errors="ignore")
            return {"exit_code": exit_code, "output": logs}
        except Exception as exc:
            return {
                "exit_code": 1,
                "output": f"Sandbox execution environment failure ({self.runtime}): {exc}",
            }
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass


# Backwards compatibility for imports in third-party extensions.
DockerSandbox = ContainerSandbox
