from __future__ import annotations


def test_expected_service_packages_are_importable() -> None:
    import superbot_api
    import superbot_worker

    assert superbot_api.__version__ == superbot_worker.__version__
    assert superbot_api.__version__ == "0.1.0"
