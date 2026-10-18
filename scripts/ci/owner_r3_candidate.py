"""Compose only pushed, frozen business commits; never resolve or patch conflicts."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


SCRIPT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = SCRIPT_DIR / "owner_r3_manifest.json"


def manifest():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == 1
    assert data["repository"] == "zjl327707743/HBOS-Platform"
    assert data["target_branch"] == "feature/hbos-portal-product"
    pairs = [data["base"]["sha"], data["base"]["tree"], data["upstream"]["hrms_sha"]]
    allowed = {"attendance": 42, "production": 46, "inventory-transactions": 39}
    for domain, entry in data["candidates"].items():
        assert entry["pr"] == allowed[domain]
        pairs.extend(entry[key] for key in ("source_sha", "source_tree", "expected_tree"))
    assert all(re.fullmatch(r"[a-f0-9]{40}", value) for value in pairs)
    return data


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compose(root, domain, evidence):
    data = manifest()
    base, entry = data["base"], data["candidates"][domain]
    evidence.mkdir(parents=True, exist_ok=True)
    inputs = {
        "repository": data["repository"], "target_branch": data["target_branch"],
        "domain": domain, "base": base, "candidate": entry,
        "runner_sha": git(SCRIPT_DIR, "rev-parse", "HEAD"),
        "runner_tree": git(SCRIPT_DIR, "rev-parse", "HEAD^{tree}"),
        "composition": "git merge --no-ff --no-edit; no conflict resolver or business overlay",
    }
    write_json(evidence / "inputs.json", inputs)
    assert not git(root, "status", "--porcelain"), "Candidate checkout must be clean"
    assert git(root, "rev-parse", "HEAD") == base["sha"], "Wrong checked-out product HEAD"
    assert git(root, "rev-parse", "HEAD^{tree}") == base["tree"], "Product tree mismatch"
    assert git(root, "rev-parse", entry["source_sha"] + "^{commit}") == entry["source_sha"]
    assert git(root, "rev-parse", entry["source_sha"] + "^{tree}") == entry["source_tree"]
    command = [
        "git", "-C", str(root), "-c", "user.name=HBOS Cloud Validation",
        "-c", "user.email=hbos-cloud-validation@users.noreply.github.com",
        "merge", "--no-ff", "--no-edit", entry["source_sha"],
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (evidence / "merge.txt").write_text(result.stdout, encoding="utf-8")
    print("[OWNER-R3] ordinary_merge_exit=" + str(result.returncode))
    if result.returncode:
        print(result.stdout)
    result.check_returncode()
    authority = {
        **inputs, "commit": git(root, "rev-parse", "HEAD"),
        "tree": git(root, "rev-parse", "HEAD^{tree}"),
        "parents": git(root, "show", "-s", "--format=%P", "HEAD").split(),
    }
    write_json(evidence / "authority.json", authority)
    assert authority["parents"] == [base["sha"], entry["source_sha"]], "Unexpected merge parents"
    assert authority["tree"] == entry["expected_tree"], "Ordinary merge tree differs from frozen review"
    assert not git(root, "status", "--porcelain"), "Composition changed uncommitted files"
    # Record existing source formatting separately; this runner cannot repair
    # historical documentation or silently change the frozen business tree.
    whitespace = subprocess.run(
        ["git", "-C", str(root), "diff", "--check", base["sha"], "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    (evidence / "whitespace.txt").write_text(whitespace.stdout, encoding="utf-8")
    authority["whitespace_check"] = "PASS" if whitespace.returncode == 0 else "WARN_EXISTING_SOURCE"
    write_json(evidence / "authority.json", authority)
    (evidence / "changed-files.txt").write_text(
        git(root, "diff", "--name-status", base["sha"], "HEAD") + "\n", encoding="utf-8"
    )
    print("[OWNER-R3] authority=" + json.dumps(authority, ensure_ascii=False))


def stage_runtime(root, domain, evidence):
    data = manifest()
    assert git(root, "rev-parse", "HEAD^{tree}") == data["candidates"][domain]["expected_tree"]
    git(root, "diff", "--exit-code", "HEAD", "--")
    assert hashlib.sha256((SCRIPT_DIR / "owner_r3_legacy_runtime.py").read_bytes()).hexdigest() == data["legacy"]["sha256"], "Pinned legacy audit changed"
    portal = root / "apps/hbos_portal/hbos_portal"
    files = [
        (SCRIPT_DIR / "owner_r3_runtime.py", portal / "_owner_r3_runtime.py"),
        (SCRIPT_DIR / "owner_r3_legacy_runtime.py", portal / "_owner_r3_legacy_runtime.py"),
        (MANIFEST_PATH, portal / "_owner_r3_manifest.json"),
        (SCRIPT_DIR / "owner_r3_site_bootstrap.sh", root / "scripts/ci/owner_r3_site_bootstrap.sh"),
    ]
    if domain == "production":
        files.append((root / "scripts/ci/owner_production_runtime.py", portal / "_owner_production_audit.py"))
    elif domain == "inventory-transactions":
        files.append((root / "scripts/ci/owner_inventory_transactions_runtime.py", portal / "_owner_inventory_transactions_runtime.py"))
    overlay = []
    for source, target in files:
        assert source.is_file(), "Missing runtime input: " + str(source)
        shutil.copyfile(source, target)
        overlay.append({
            "source": str(source.relative_to(root) if source.is_relative_to(root) else source.relative_to(SCRIPT_DIR)),
            "target": str(target.relative_to(root)),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "purpose": "runner-only audit; not a product source fix",
        })
    write_json(evidence / "runtime-overlay.json", overlay)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("select", "compose", "stage-runtime"))
    parser.add_argument("--domain", required=True)
    parser.add_argument("--candidate", type=Path, default=Path("candidate"))
    parser.add_argument("--evidence", type=Path, default=Path("/tmp/owner-r3"))
    args = parser.parse_args()
    data = manifest()
    entry = data["candidates"][args.domain]
    if args.action == "select":
        for key, value in {
            "base_sha": data["base"]["sha"], "source_sha": entry["source_sha"],
            "hrms_sha": data["upstream"]["hrms_sha"], "pr": entry["pr"],
        }.items():
            print(f"{key}={value}")
    elif args.action == "compose":
        compose(args.candidate.resolve(), args.domain, args.evidence)
    else:
        stage_runtime(args.candidate.resolve(), args.domain, args.evidence)


if __name__ == "__main__":
    main()
