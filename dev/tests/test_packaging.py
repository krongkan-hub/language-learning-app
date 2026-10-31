"""Packaging: what a wheel ships, and the deployment facts docs/DEPLOYMENT.md
rests on (the mlx import chain), so an edit that quietly invalidates that
page's claims fails a fast, deterministic check. No Docker, no MLX.
"""
import pathlib


def _project_root():
    """Where pyproject.toml is. See test_main.py for why not a relative parent count."""
    return next(p for p in pathlib.Path(__file__).resolve().parents
                if (p / 'pyproject.toml').exists())


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
    scenarios, no explain topics — an installed copy starts and has nothing
    to practise. Nothing caught it because the repo always runs from
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
    parts = {n.rsplit('/', 1)[-1] for n in names if 'scenarios/parts/' in n}
    assert parts == {'archetypes.json', 'places.json', 'characters.json', 'events.json'}, parts
    assert any(n.endswith('explain_topics.json') for n in names)
    assert any(n.endswith('app/cli/game.py') for n in names)
