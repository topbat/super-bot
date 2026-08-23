from __future__ import annotations

import socket
from pathlib import Path

import pytest
from superbot_worker.browser import BrowserPolicy, BrowserTargetDenied
from superbot_worker.sandbox import DockerSandbox, SandboxConfig, UnsafeSandboxConfig


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/admin",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data",
        "file:///C:/Windows/System32/config/SAM",
    ],
)
def test_browser_blocks_local_and_non_http_targets(url: str) -> None:
    with pytest.raises(BrowserTargetDenied):
        BrowserPolicy().validate(url)


def test_browser_domain_allowlist_is_exact() -> None:
    policy = BrowserPolicy(allowed_domains={"docs.example.com"})

    assert policy.validate("https://docs.example.com/guide") == "https://docs.example.com/guide"
    with pytest.raises(BrowserTargetDenied):
        policy.validate("https://docs.example.com.attacker.test/")


async def test_browser_can_explicitly_trust_a_dns_proxy_fake_ip_range(monkeypatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.145", 0))
        ],
    )

    with pytest.raises(BrowserTargetDenied):
        await BrowserPolicy().validate_resolved("https://public.example/")

    policy = BrowserPolicy(trusted_dns_proxy_cidrs={"198.18.0.0/15"})
    assert await policy.validate_resolved("https://public.example/") == "https://public.example/"
    with pytest.raises(BrowserTargetDenied):
        policy.validate("http://198.18.0.145/")


def test_docker_sandbox_uses_non_root_minimal_privileges(tmp_path: Path) -> None:
    sandbox = DockerSandbox(
        SandboxConfig(
            image="superbot/browser-worker:local",
            workspace=tmp_path,
            allowed_images={"superbot/browser-worker:local"},
        )
    )

    command = sandbox.command(["python", "job.py"])

    assert command[:3] == ["docker", "run", "--rm"]
    assert ["--user", "65532:65532"] == command[
        command.index("--user") : command.index("--user") + 2
    ]
    assert "--read-only" in command
    assert ["--cap-drop", "ALL"] == command[
        command.index("--cap-drop") : command.index("--cap-drop") + 2
    ]
    assert ["--network", "none"] == command[
        command.index("--network") : command.index("--network") + 2
    ]
    assert command[-2:] == ["python", "job.py"]


def test_docker_sandbox_rejects_unapproved_image(tmp_path: Path) -> None:
    with pytest.raises(UnsafeSandboxConfig):
        DockerSandbox(SandboxConfig(image="latest", workspace=tmp_path))
