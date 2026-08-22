from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class UnsafeSandboxConfig(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    image: str
    workspace: Path
    allowed_images: set[str] = field(default_factory=set)
    network: str = "none"
    memory: str = "2g"
    cpus: str = "2"
    pids_limit: int = 256


class DockerSandbox:
    def __init__(self, config: SandboxConfig) -> None:
        if config.image not in config.allowed_images:
            raise UnsafeSandboxConfig("sandbox image must be explicitly allowlisted")
        if config.network not in {"none", "superbot-egress"}:
            raise UnsafeSandboxConfig("sandbox network is not approved")
        if config.pids_limit < 16 or config.pids_limit > 1024:
            raise UnsafeSandboxConfig("sandbox pids limit is outside safe bounds")
        self.config = config

    def command(self, process: list[str]) -> list[str]:
        if not process or any("\x00" in argument for argument in process):
            raise UnsafeSandboxConfig("sandbox process arguments are invalid")
        workspace = self.config.workspace.resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        mount = f"type=bind,source={workspace},target=/workspace"
        return [
            "docker",
            "run",
            "--rm",
            "--user",
            "65532:65532",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--network",
            self.config.network,
            "--memory",
            self.config.memory,
            "--cpus",
            self.config.cpus,
            "--pids-limit",
            str(self.config.pids_limit),
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=256m",
            "--mount",
            mount,
            "--workdir",
            "/workspace",
            self.config.image,
            *process,
        ]
