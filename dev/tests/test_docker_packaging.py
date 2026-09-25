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


def test_the_wheel_contains_the_content_the_app_needs():
    """`pip install .` shipped 40 files of Python and none of the data: no
    scenarios, no explain topics, no web page — an installed copy starts and
    has nothing to serve. Nothing caught it because the repo always runs from
    a source checkout, where the files are simply there. Building the wheel is
    the only way to see it, so the build is the test.
    """
    import glob
    import os
    import subprocess
    import sys
    import tempfile
    import zipfile

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with tempfile.TemporaryDirectory() as out:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'wheel', '--no-deps', '-q', root, '-w', out],
            capture_output=True, text=True)
        if result.returncode != 0:
            import pytest
            pytest.skip(f'wheel build unavailable: {result.stderr[-200:]}')
        wheels = glob.glob(os.path.join(out, '*.whl'))
        assert wheels, 'no wheel produced'
        names = zipfile.ZipFile(wheels[0]).namelist()

    scenarios = [n for n in names if 'scenarios/data' in n and n.endswith('.json')]
    assert len(scenarios) == 80, f'{len(scenarios)} scenario files in the wheel'
    assert any(n.endswith('explain_topics.json') for n in names)
    assert any('/static/' in n and n.endswith('.html') for n in names)
