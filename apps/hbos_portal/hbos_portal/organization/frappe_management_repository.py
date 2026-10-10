"""Default-closed policy current reads/writes under the existing relation lock.

No RPC, implicit bootstrap, caching, commit or dependency on a Frappe role.
"""
from dataclasses import dataclass
import hashlib
import re

from hbos_portal.authorization.errors import ContractError
from .frappe_source_loader import FrappeLockedSourceLoader
from .management_storage import (
    POLICY, POLICY_FIELDS, POLICY_REVISION, REVISION_FIELDS,
    PinnedPolicyApprovalVerifier, policy_from_record, policy_record, stored_time, validate_policy_record,
)
from .source_adapter import _department_chain
from .storage_schema import canonical_json, digest, revision_key
from .write_guard import _controlled_write


def validate_policy_sources(policy, snapshot):
    """Current native existence/activity only; Employee Date is still unresolved."""
    for user in (policy.subject_user, policy.approval.approved_by if policy.approval else None):
        if user is not None and (user == "Guest" or user not in snapshot.rows["User"] or not snapshot.rows["User"][user]["enabled"]):
            raise ContractError("POLICY_SOURCE_UNAVAILABLE", "policy.user")
    for rule in policy.rules:
        if rule.company_id not in snapshot.rows["Company"]:
            raise ContractError("POLICY_SOURCE_UNAVAILABLE", "policy.company")
        departments = set(rule.target_department_ids)
        if rule.person_scope is not None:
            departments.update(rule.person_scope.department_ids)
        for department in sorted(departments):
            chain = _department_chain(snapshot, department, rule.company_id)
            if chain[0]["company"] != rule.company_id:
                raise ContractError("POLICY_SOURCE_UNAVAILABLE", "policy.department")


class FrappeManagementPolicyRepository:
    def __init__(self, relation_repository, *, expected_site=None, expected_database_sha256=None, enabled=False):
        self.relations = relation_repository
        self.expected_site = expected_site
        self.expected_database_sha256 = expected_database_sha256
        self.enabled = enabled is True

    def native(self):
        if not self.enabled:
            raise ContractError("POLICY_STORAGE_DISABLED", "policy")
        if (not isinstance(self.expected_site, str) or not self.expected_site.strip()
                or self.expected_site != self.expected_site.strip()
                or not isinstance(self.expected_database_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.expected_database_sha256)):
            raise ContractError("POLICY_BINDING_REQUIRED", "policy")
        native = self.relations.require_locked_source_context()
        if native.local.site != self.expected_site:
            raise ContractError("POLICY_SITE_MISMATCH", "policy")
        if native.conf.get("db_type", "mariadb") != "mariadb":
            raise ContractError("UNSUPPORTED_SOURCE_DATABASE", "policy")
        database, isolation = native.db.sql("SELECT DATABASE(), @@tx_isolation")[0]
        if hashlib.sha256(database.encode()).hexdigest() != self.expected_database_sha256:
            raise ContractError("POLICY_DATABASE_MISMATCH", "policy")
        if isolation != "REPEATABLE-READ":
            raise ContractError("UNSUPPORTED_SOURCE_ISOLATION", "policy")
        tables = ("tab" + POLICY, "tab" + POLICY_REVISION)
        engines = native.db.sql("SELECT table_name,engine FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name IN (%s,%s)", tables)
        if dict(engines) != {table: "InnoDB" for table in tables}:
            raise ContractError("POLICY_STORAGE_NOT_READY", "policy")
        return native

    def _read(self, kind, fields, where, values):
        # kind/fields/where are internal constants, never supplied by callers.
        return self.native().db.sql("SELECT " + ",".join("`" + key + "`" for key in fields)
            + f" FROM `tab{kind}` WHERE {where} ORDER BY name FOR UPDATE", values, as_dict=True)

    def _checked(self, row):
        policy = policy_from_record(row["record_key"], row.get)
        if policy.site_id != self.expected_site:
            raise ContractError("POLICY_SITE_MISMATCH", "policy")
        key = revision_key(POLICY, policy.policy_id, policy.revision)
        revisions = self._read(POLICY_REVISION, REVISION_FIELDS, "name=%s", (key,))
        if len(revisions) != 1:
            raise ContractError("POLICY_HISTORY_MISSING", "policy")
        version = revisions[0]
        validate_policy_record(POLICY_REVISION, key, version.get)
        if version["snapshot_json"] != canonical_json(policy_record(policy)):
            raise ContractError("POLICY_HISTORY_MISMATCH", "policy")
        return policy

    def get_current(self, policy_id):
        rows = self._read(POLICY, POLICY_FIELDS, "name=%s", (policy_id,))
        return None if not rows else self._checked(rows[0])

    def current_for_subject(self, subject):
        # Include revoked/inactive heads: never filter to an old active revision.
        rows = self._read(POLICY, POLICY_FIELDS, "subject_user=%s", (subject,))
        return tuple(self._checked(row) for row in rows)

    def save(self, policy, *, expected_revision, actor, reason, approval_source_ref, now_utc):
        native = self.native()
        record = policy_record(policy)
        if expected_revision == 0:
            doc = native.get_doc({"doctype": POLICY, **record})
            with _controlled_write(POLICY, policy.policy_id):
                doc.insert(ignore_permissions=True)
        else:
            doc = native.get_doc(POLICY, policy.policy_id, for_update=True)
            if doc.revision != expected_revision:
                raise ContractError("POLICY_REVISION_CONFLICT", "policy")
            doc.update(record)
            with _controlled_write(POLICY, policy.policy_id):
                doc.save(ignore_permissions=True)
        key = revision_key(POLICY, policy.policy_id, policy.revision)
        revision = dict(record_key=key, policy=policy.policy_id, revision=policy.revision,
            previous_revision=expected_revision, snapshot_json=canonical_json(record), snapshot_digest=digest(record),
            actor=actor, reason=reason, approval_source_ref=approval_source_ref, recorded_at_utc=stored_time(now_utc))
        validate_policy_record(POLICY_REVISION, key, revision.get)
        doc = native.get_doc({"doctype": POLICY_REVISION, **revision})
        with _controlled_write(POLICY_REVISION, key):
            doc.insert(ignore_permissions=True)


@dataclass(frozen=True, slots=True)
class PolicyWriteResult:
    policy_id: str
    revision: int
    authority_generation: int
    transaction_pending: bool = True
    authorization_effect: str = "none"
    runtime_verified: bool = False


class ManagementPolicyStore:
    """Internal operations workflow. Caller owns outer rollback/commit.

    No operator list or approval verifier is configured by the application.
    Explicit trusted server dependencies are needed even for Administrator.
    """
    def __init__(self, repository, *, clock, operator_users=(), approval_verifier=None, enabled=False):
        self.repository = repository
        self.clock = clock
        if type(operator_users) not in (list, tuple) or any(
                not isinstance(user, str) or not user.strip() or user != user.strip()
                or len(user) > 140 or user == "Guest" for user in operator_users):
            raise ContractError("INVALID_POLICY_OPERATORS", "policy")
        self.operator_users = frozenset(operator_users)
        self.verifier = approval_verifier
        self.enabled = enabled is True

    def write(self, policy, *, expected_revision, reason):
        if not self.enabled or not self.repository.enabled:
            raise ContractError("POLICY_WRITES_DISABLED", "policy")
        if type(expected_revision) is not int or expected_revision < 0:
            raise ContractError("INVALID_VERSION", "policy.expected_revision")
        if not isinstance(reason, str) or not reason.strip() or reason != reason.strip() or len(reason) > 500:
            raise ContractError("INVALID_TEXT", "policy.reason")
        record = policy_record(policy)  # Validate before DB access.
        if policy.site_id != self.repository.expected_site:
            raise ContractError("POLICY_SITE_MISMATCH", "policy")
        with self.repository.relations.transaction():
            self.repository.relations.lock_writer()
            native = self.repository.native()
            actor = native.session.user
            if actor == "Guest" or actor not in self.operator_users:
                raise ContractError("POLICY_OPERATOR_DENIED", "policy")
            old = self.repository.get_current(policy.policy_id)
            if old is None:
                if expected_revision != 0 or policy.revision != 1 or policy.authority_generation != 1:
                    raise ContractError("POLICY_REVISION_CONFLICT", "policy")
            else:
                if old.revision != expected_revision or policy.revision != old.revision + 1:
                    raise ContractError("POLICY_REVISION_CONFLICT", "policy")
                if policy.subject_user != old.subject_user:
                    raise ContractError("POLICY_SUBJECT_IMMUTABLE", "policy")
                # Every new revision invalidates prior approval/management evidence.
                if policy.authority_generation != old.authority_generation + 1:
                    raise ContractError("POLICY_GENERATION_CONFLICT", "policy")
            snapshot = FrappeLockedSourceLoader(self.repository.relations, enabled=True,
                expected_site=self.repository.expected_site,
                expected_database_sha256=self.repository.expected_database_sha256)()
            if actor not in snapshot.rows["User"] or not snapshot.rows["User"][actor]["enabled"]:
                raise ContractError("POLICY_OPERATOR_DENIED", "policy")
            now = self.clock()
            stored_time(now)  # Reject naive clocks even for revocations/drafts.
            source_ref = None
            if policy.status == "active":
                validate_policy_sources(policy, snapshot)
                if type(self.verifier) is not PinnedPolicyApprovalVerifier:
                    raise ContractError("POLICY_APPROVAL_REQUIRED", "policy")
                source_ref = self.verifier.verify(policy,
                    database_sha256=self.repository.expected_database_sha256, now_utc=now)
                if now >= policy.valid_until_utc:
                    raise ContractError("POLICY_EXPIRED", "policy")
            self.repository.save(policy, expected_revision=expected_revision, actor=actor, reason=reason,
                approval_source_ref=source_ref, now_utc=now)
            return PolicyWriteResult(record["record_key"], policy.revision, policy.authority_generation)


class LockedManagementPolicyLoader:
    """Load current heads under the shared root lock, no cached decisions.

    Return policy DTOs only. This is not a RelationService management callback.
    Native identity and source qualification are rechecked on every invocation.
    """
    def __init__(self, repository, *, clock, approval_verifier=None, enabled=False):
        self.repository = repository
        self.clock = clock
        self.verifier = approval_verifier
        self.enabled = enabled is True

    def __call__(self):
        if not self.enabled:
            raise ContractError("POLICY_READS_DISABLED", "policy")
        native = self.repository.native()  # Requires existing tx/root capability.
        subject = native.session.user
        if subject == "Guest":
            raise ContractError("MANAGEMENT_DENIED", "policy")
        heads = self.repository.current_for_subject(subject)
        snapshot = FrappeLockedSourceLoader(self.repository.relations, enabled=True,
            expected_site=self.repository.expected_site,
            expected_database_sha256=self.repository.expected_database_sha256)()
        if subject not in snapshot.rows["User"] or not snapshot.rows["User"][subject]["enabled"]:
            raise ContractError("MANAGEMENT_DENIED", "policy")
        now = self.clock()
        stored_time(now)
        for policy in heads:
            if policy.status == "active":
                validate_policy_sources(policy, snapshot)
                if type(self.verifier) is not PinnedPolicyApprovalVerifier:
                    raise ContractError("POLICY_APPROVAL_REQUIRED", "policy")
                self.verifier.verify(policy, database_sha256=self.repository.expected_database_sha256, now_utc=now)
        return heads
