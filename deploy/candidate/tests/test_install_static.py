"""The static bundle switch must be one rename, never a partial copy."""
import pathlib
import sys

import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import install_static  # noqa: E402


def bundle(root, marker):
    (root / 'assets').mkdir(parents=True, exist_ok=True)
    (root / 'index.html').write_text(
        f'<script src="/assets/hbos_portal/portal/assets/{marker}.js"></script>')
    (root / 'assets' / f'{marker}.js').write_text(marker)
    return root


def test_a_complete_staged_bundle_is_accepted(tmp_path):
    assert install_static.staged_ok(bundle(tmp_path / 'staged', 'new')) is None


def test_staged_bundle_without_index_is_refused(tmp_path):
    staged = tmp_path / 'staged'
    (staged / 'assets').mkdir(parents=True)
    assert 'index.html' in install_static.staged_ok(staged)


def test_staged_bundle_for_another_base_path_is_refused(tmp_path):
    staged = tmp_path / 'staged'
    (staged / 'assets').mkdir(parents=True)
    (staged / 'index.html').write_text('<script src="/static/app.js"></script>')
    assert 'does not reference' in install_static.staged_ok(staged)


def test_swap_keeps_the_previous_bundle_for_rollback(tmp_path):
    target = bundle(tmp_path / 'public' / 'portal', 'old')
    staged = bundle(tmp_path / 'build' / 'frontend-staged', 'new')

    install_static.atomic_swap(staged, target)

    assert (target / 'assets' / 'new.js').exists()
    assert not (target / 'assets' / 'old.js').exists()
    previous = target.with_name('portal.previous')
    assert (previous / 'assets' / 'old.js').exists()
    assert not staged.exists()


def test_swap_replaces_an_earlier_previous_bundle(tmp_path):
    target = bundle(tmp_path / 'public' / 'portal', 'v1')
    previous = target.with_name('portal.previous')
    bundle(previous, 'v0')
    staged = bundle(tmp_path / 'build' / 'frontend-staged', 'v2')

    install_static.atomic_swap(staged, target)

    assert (previous / 'assets' / 'v1.js').exists()
    assert not (previous / 'assets' / 'v0.js').exists()


def test_rollback_puts_the_previous_bundle_back(tmp_path):
    target = bundle(tmp_path / 'public' / 'portal', 'old')
    staged = bundle(tmp_path / 'build' / 'frontend-staged', 'new')
    install_static.atomic_swap(staged, target)

    install_static.restore(target)

    assert (target / 'assets' / 'old.js').exists()
    assert not target.with_name('portal.previous').exists()


def test_rollback_without_a_previous_bundle_refuses(tmp_path):
    target = bundle(tmp_path / 'public' / 'portal', 'only')
    with pytest.raises(SystemExit) as exit:
        install_static.restore(target)
    assert exit.value.code == 2
