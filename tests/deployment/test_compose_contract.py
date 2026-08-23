from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def compose() -> dict:
    return yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))


def test_required_services_and_stateful_volumes_are_declared() -> None:
    document = compose()

    required = {
        "api",
        "worker",
        "scheduler",
        "postgres",
        "valkey",
        "seaweedfs",
        "browser-worker",
        "playwright-server",
    }
    assert required <= set(document["services"])
    assert {"postgres-data", "valkey-data", "seaweedfs-data", "bot-workspaces"} <= set(
        document["volumes"]
    )
    assert document["services"]["browser-worker"]["profiles"] == ["browser"]
    assert document["services"]["playwright-server"]["profiles"] == ["browser"]


def test_remote_playwright_services_are_internal_versioned_and_health_checked() -> None:
    document = compose()
    server = document["services"]["playwright-server"]
    gateway = document["services"]["browser-worker"]

    assert server["image"] == "superbot/playwright-server:1.61.0"
    assert server["build"]["dockerfile"] == "Dockerfile.playwright"
    assert "run-server" in " ".join(server["command"])
    assert "ports" not in server
    assert server["expose"] == [3000]
    assert server["healthcheck"]["test"]
    assert server["cap_drop"] == ["ALL"]
    assert server["security_opt"] == ["no-new-privileges:true"]
    assert "noexec" in server["tmpfs"][0]

    assert (
        gateway["environment"]["SUPERBOT_PLAYWRIGHT_WS_ENDPOINT"] == "ws://playwright-server:3000/"
    )
    assert gateway["expose"] == [8430]
    assert "ports" not in gateway
    assert gateway["depends_on"]["playwright-server"]["condition"] == "service_healthy"
    assert "http://127.0.0.1:8430/health" in " ".join(gateway["healthcheck"]["test"])

    api_environment = document["services"]["api"]["environment"]
    assert api_environment["SUPERBOT_BROWSER_GATEWAY_URL"] == "http://browser-worker:8430"


def test_application_containers_are_non_root_bounded_and_health_checked() -> None:
    document = compose()
    for name in ("api", "worker", "scheduler", "browser-worker", "playwright-server"):
        service = document["services"][name]
        assert service["user"] not in {"0", "root", "0:0"}
        assert service["read_only"] is True
        assert service["security_opt"] == ["no-new-privileges:true"]
        assert service["cap_drop"] == ["ALL"]
        assert service["healthcheck"]["test"]
        limits = service["deploy"]["resources"]["limits"]
        assert limits["memory"]
        assert limits["cpus"]


def test_dependencies_wait_for_healthy_infrastructure() -> None:
    document = compose()

    for name in ("api", "worker", "scheduler"):
        dependencies = document["services"][name]["depends_on"]
        assert dependencies["postgres"]["condition"] == "service_healthy"
        assert dependencies["valkey"]["condition"] == "service_healthy"
        assert dependencies["seaweedfs"]["condition"] == "service_healthy"


def test_no_secret_is_baked_into_compose_or_images() -> None:
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "docker-compose.yml",
            "Dockerfile.api",
            "Dockerfile.worker",
            "Dockerfile.playwright",
        )
    )

    assert "sk-" not in source
    assert "AKIA" not in source
    assert "changeme" not in source.casefold()
    assert "SUPERBOT_DS_MASTER_KEY=" not in source
    assert "${POSTGRES_PASSWORD:?" in source
    assert "${S3_SECRET_KEY:?" in source


def test_windows_scripts_are_strict_and_use_compose_v2() -> None:
    for name in ("dev.ps1", "build-windows.ps1", "verify-compose.ps1"):
        source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "Set-StrictMode -Version Latest" in source
        assert "$ErrorActionPreference = 'Stop'" in source
        assert "docker compose" in source


def test_dockerfiles_pin_python_and_drop_privileges() -> None:
    for name in ("Dockerfile.api", "Dockerfile.worker"):
        source = (ROOT / name).read_text(encoding="utf-8")
        assert source.startswith("FROM python:3.12-slim")
        assert "uv sync --frozen" in source
        assert "USER 65532:65532" in source


def test_python_playwright_client_matches_remote_server_version() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    compose_source = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile.playwright").read_text(encoding="utf-8")

    assert "playwright==1.61.0" in pyproject
    assert "superbot/playwright-server:1.61.0" in compose_source
    assert dockerfile.startswith("FROM mcr.microsoft.com/playwright:v1.61.0-noble")
    assert "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1" in dockerfile
    assert "playwright@1.61.0" in dockerfile
