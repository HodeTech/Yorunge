"""SQL-only schema-7 declarations; all transfer consumers start empty."""

TRANSFER_SQL = (
    """CREATE TABLE upload_namespaces (
intent_digest TEXT PRIMARY KEY CHECK(length(intent_digest)=64),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=8192),
create_operation_id TEXT UNIQUE REFERENCES upload_operations(operation_id) ON DELETE RESTRICT
) STRICT""",
    """CREATE TABLE upload_manifests (
digest TEXT PRIMARY KEY CHECK(length(digest)=64),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=262144)
) STRICT""",
    """CREATE TABLE upload_plans (
plan_id TEXT PRIMARY KEY CHECK(length(plan_id)=36),
intent_digest TEXT NOT NULL REFERENCES upload_namespaces(intent_digest) ON DELETE RESTRICT,
manifest_digest TEXT NOT NULL REFERENCES upload_manifests(digest) ON DELETE RESTRICT,
prepared_at TEXT NOT NULL CHECK(length(prepared_at)=27),
expires_at TEXT NOT NULL CHECK(length(expires_at)=27),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=16384)
) STRICT""",
    "CREATE INDEX upload_plan_order ON upload_plans(prepared_at,plan_id)",
    "CREATE INDEX upload_plan_expiry ON upload_plans(expires_at,plan_id)",
    """CREATE TABLE upload_approvals (
plan_id TEXT PRIMARY KEY REFERENCES upload_plans(plan_id) ON DELETE RESTRICT,
approval_id TEXT NOT NULL UNIQUE CHECK(length(approval_id)=36),
expires_at TEXT NOT NULL CHECK(length(expires_at)=27),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=16384)
) STRICT""",
    "CREATE INDEX upload_approval_expiry ON upload_approvals(expires_at,plan_id)",
    """CREATE TABLE upload_operations (
operation_id TEXT PRIMARY KEY CHECK(length(operation_id)=36),
plan_id TEXT NOT NULL UNIQUE REFERENCES upload_plans(plan_id) ON DELETE RESTRICT,
intent_digest TEXT NOT NULL REFERENCES upload_namespaces(intent_digest) ON DELETE RESTRICT,
revision INTEGER NOT NULL CHECK(revision>0),
lease_expires_at TEXT CHECK(lease_expires_at IS NULL OR length(lease_expires_at)=27),
reservation INTEGER NOT NULL CHECK(reservation>0),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=16384)
) STRICT""",
    "CREATE INDEX upload_lease_expiry ON upload_operations(lease_expires_at,operation_id)",
    """CREATE TABLE upload_stage_intents (
intent_id TEXT PRIMARY KEY CHECK(length(intent_id)=36),
operation_id TEXT NOT NULL REFERENCES upload_operations(operation_id) ON DELETE RESTRICT,
sequence INTEGER NOT NULL CHECK(sequence BETWEEN 1 AND 386),
kind TEXT NOT NULL CHECK(kind IN ('create','project_link','presign','put','confirm')),
file_index INTEGER NOT NULL CHECK(file_index BETWEEN -1 AND 127),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=2048),
UNIQUE(operation_id,sequence),UNIQUE(operation_id,kind,file_index)
) STRICT""",
    """CREATE TABLE upload_stage_receipts (
intent_id TEXT PRIMARY KEY REFERENCES upload_stage_intents(intent_id) ON DELETE RESTRICT,
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=2048)
) STRICT""",
    """CREATE TABLE upload_controls (
operation_id TEXT NOT NULL REFERENCES upload_operations(operation_id) ON DELETE RESTRICT,
kind TEXT NOT NULL CHECK(kind IN ('recovery','terminal')),
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=2048),
PRIMARY KEY(operation_id,kind)
) STRICT""",
    """CREATE TABLE upload_verifications (
operation_id TEXT PRIMARY KEY REFERENCES upload_operations(operation_id) ON DELETE RESTRICT,
payload TEXT NOT NULL CHECK(length(CAST(payload AS BLOB))<=131072)
) STRICT""",
)
