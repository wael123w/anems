from pathlib import Path

from siteforge.services.ai_generation import AIGenerationService
from siteforge.services.site_builder import SiteBuilder
from siteforge.services.verification import verify_deployment


def test_generation_without_key_is_real_and_safe(tmp_path: Path):
    root = tmp_path / "generated"
    result = AIGenerationService(None).generate(root, "A clean business landing page")
    assert (root / "index.html").exists()
    assert result["files"]


def test_local_deployment_verification(tmp_path: Path):
    root = tmp_path / "site"
    SiteBuilder().create(root, name="Verify", description="verify")
    result = verify_deployment(root)
    assert result.ok is True
    assert result.missing_local_files == []
