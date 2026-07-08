# sandbox.py
import os
import docker
from pathlib import Path
from typing import Union


class DockerSandbox:
    def __init__(self, image_name: str = "python:3.11-slim"):
        self.image_name = image_name
        try:
            self.client = docker.from_env()
            self.client.images.pull(self.image_name)
        except Exception as e:
            raise RuntimeError(
                f"❌ Cannot connect to Docker Daemon. Ensure Docker Desktop is running! Error: {e}"
            )

    def run_command_in_sandbox(self, command: str) -> dict:
        """Spins up a container, mounts the project directory, runs the code check, and deletes itself."""
        workspace_dir = str(Path.cwd().resolve())
        container = None

        try:
            container = self.client.containers.create(
                image=self.image_name,
                command=f"sh -c '{command}'",
                working_dir="/workspace",
                volumes={
                    workspace_dir: {
                        'bind': '/workspace',
                        'mode': 'rw'
                    }
                },
                mem_limit="512m",
                nano_cpus=1000000000,
            )

            container.start()
            result = container.wait(timeout=15)
            exit_code = result.get("StatusCode", 1)
            logs = container.logs().decode("utf-8", errors="ignore")

            return {
                "exit_code": exit_code,
                "output": logs
            }

        except Exception as e:
            return {
                "exit_code": 1,
                "output": f"❌ Sandbox execution environment failure: {str(e)}"
            }
        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass