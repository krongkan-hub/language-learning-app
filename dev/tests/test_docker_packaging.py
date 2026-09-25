"""Structural checks on the Docker packaging files.

Deliberately does not build or run anything — no Docker, no MLX. It locks in
the facts docs/DEPLOYMENT.md documents (the mlx import chain, the missing
package-data) so a future edit to Dockerfile/.dockerignore/pyproject.toml
that quietly invalidates that page's claims fails a fast, deterministic
check instead of being caught by someone reading prose.
"""
import pathlib


def _project_root():
    """Where pyproject.toml is. See test_main.py for why not a relative parent count."""
    return next(p for p in pathlib.Path(__file__).resolve().parents
                if (p / 'pyproject.toml').exists())


def test_dockerfile_exists_and_targets_the_web_front_end():
    text = (_project_root() / 'Dockerfile').read_text()
    assert 'app.web' in text
    assert 'EXPOSE 8000' in text
    assert 'FROM python:3.11' in text


def test_dockerignore_excludes_required_paths():
    text = (_project_root() / '.dockerignore').read_text()
    for required in ('venv/', '.eval_logs/', '.git/', '__pycache__', '*.db', 'scratch/'):
        assert required in text, f'{required!r} missing from .dockerignore'


def test_deployment_doc_exists_and_names_the_real_blocker():
    text = (_project_root() / 'docs' / 'DEPLOYMENT.md').read_text()
    # The two independent facts this page's honesty rests on: mlx-lm's own
    # Darwin-only marker on `mlx`, and the resulting ModuleNotFoundError.
    # If either goes stale (mlx-lm is upgraded, client.py starts guarding the
    # import), this test should fail alongside the prose, not silently agree
    # with an outdated page.
    assert 'platform_system ==' in text
    assert 'Darwin' in text
    assert 'ModuleNotFoundError' in text
    assert 'Metal' in text


def test_pyproject_still_has_no_scenario_package_data():
    """Documents a real gap rather than asserting a fix.

    docs/DEPLOYMENT.md explains that `pip install .` drops
    app/scenarios/data/*.json and app/static/index.html because pyproject.toml
    declares no package-data and there is no MANIFEST.in. This pins that
    absence down: if another change adds package-data (fixing the gap, which
    would be welcome), this test's failure is the signal to update the
    Dockerfile comment and docs/DEPLOYMENT.md that route around it, not a
    regression.
    """
    text = (_project_root() / 'pyproject.toml').read_text()
    assert 'package-data' not in text
    assert not (_project_root() / 'MANIFEST.in').exists()
