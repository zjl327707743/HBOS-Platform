"""Preflight must refuse on the facts that decide whether a swap is safe.

No Docker is involved: the lock, the compose files and the rollback record are
temporary files, and image inspection is injected.
"""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import preflight  # noqa: E402


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def compose_entry(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def test_lock_fingerprint_matches_every_pinned_file(tmp_path):
    a = write(tmp_path / 'a.yml', 'services: {}\n')
    b = write(tmp_path / 'b.yml', 'services: {}\n')
    lock = {'composition': {'files': [compose_entry(a), compose_entry(b)]}}

    assert preflight.compose_hash_problems(lock) == []


def test_changed_compose_file_is_a_problem_not_a_warning(tmp_path):
    a = write(tmp_path / 'a.yml', 'services: {}\n')
    lock = {'composition': {'files': [compose_entry(a)]}}
    write(a, 'services: {bff: {}}\n')

    problems = preflight.compose_hash_problems(lock)

    assert len(problems) == 1
    assert 'changed since the deploy lock' in problems[0]
    assert a.name in problems[0]


def test_missing_compose_file_is_a_problem(tmp_path):
    a = write(tmp_path / 'a.yml', 'services: {}\n')
    lock = {'composition': {'files': [compose_entry(a)]}}
    a.unlink()

    problems = preflight.compose_hash_problems(lock)

    assert len(problems) == 1
    assert 'compose file missing' in problems[0]


def test_lock_without_compose_files_refuses(tmp_path):
    try:
        preflight.locked_files({'composition': {'files': []}})
    except SystemExit as exit:
        assert exit.code == 2
    else:
        raise AssertionError('a lock that pins nothing must refuse')


def test_relative_lock_path_resolves_against_the_task_root(tmp_path, monkeypatch):
    write(preflight.ROOT / 'work/deploy/candidate/.probe-compose.yml', 'services: {}\n')
    try:
        entry = compose_entry(preflight.ROOT / 'work/deploy/candidate/.probe-compose.yml')
        entry['path'] = 'work/deploy/candidate/.probe-compose.yml'
        assert preflight.compose_hash_problems({'composition': {'files': [entry]}}) == []
    finally:
        (preflight.ROOT / 'work/deploy/candidate/.probe-compose.yml').unlink()


def test_all_rollback_images_present_passes(tmp_path):
    record = write(tmp_path / 'rollback.json',
                   json.dumps({'bff': 'sha256:aaaa', 'service': 'sha256:bbbb'}))

    assert preflight.rollback_image_problems(record, inspect=lambda ref: True) == []


def test_missing_rollback_image_refuses_with_a_hint(tmp_path):
    record = write(tmp_path / 'rollback.json',
                   json.dumps({'bff': 'sha256:aaaa', 'service': 'sha256:bbbb'}))

    problems = preflight.rollback_image_problems(
        record, inspect=lambda ref: ref == 'sha256:aaaa')

    assert len(problems) == 1
    assert 'service' in problems[0]
    assert 'not on this machine' in problems[0]
    assert 'tag the running image' in problems[0]


def test_rollback_record_without_an_image_is_a_problem(tmp_path):
    record = write(tmp_path / 'rollback.json', json.dumps({'bff': None}))

    problems = preflight.rollback_image_problems(record, inspect=lambda ref: True)

    assert len(problems) == 1
    assert 'no image for bff' in problems[0]
