# Managed upload original and directory registration

With `maintenance_source_registry_enabled: true`, the normal authenticated
maintainer upload registers its original file and selected department directory
before creating the import batch. Upload, parse, review, publish and employee
retrieval verification remain distinct operations. A metadata entry is never an
authorization grant. Current HBOS role, version, binding, sharing and withdrawal
checks still gate original delivery and every catalog row.

Configure one deployment-owned writable registry directory containing an
existing `hbos-document-assets-v1` asset manifest and an existing version2 source
directory projection. Copy the current projections into it once before enabling
the feature; preserve their exact prior hashes. The two configured file paths
must have the same parent directory:

* `document_asset_manifest`: the managed asset manifest path.
* `source_directory_path`: the managed directory projection path.
* `maintenance_upload_root`: this deployment's private upload directory.
* `document_asset_roots.uploads`: exactly the same upload root.
* `HBOS_SOURCE_DIRECTORY_FILE`: the same configured source directory file,
  supplied to the BFF environment before startup. Its default preserves the
  existing `/run/hbos-reference/source-directory.json` deployment path.

Mount only that registry directory writable, plus the deployment's own upload
root at the same absolute path used by the single host parser controller. Keep
the original corpus and other reference configuration mounts read-only.

Uploads retain their private unique storage root. Inside each frozen upload's
source root the path begins with the selected HBOS department directory, so the
catalog can show the real relative source path without exposing the private
storage identifier. A PDF is registered as its original PDF preview; other
formats require a separately verified preview conversion. The original bytes
are not replaced by parser text or converted documents.

Registration verifies exact source SHA256 and regular, contained, non-symlink
paths. It serializes updates with one file lock, preserves existing versions,
retains every prior projection under `.source-registry-history`, and atomically
replaces each projection. If interrupted between the two projection writes,
exact replay completes the missing projection. It does not restore an old DB,
change roles, publish, restore a withdrawal or reactivate an old token.

Same-content duplicate uploads keep the current canonical original and do not
create a new business version. Original directory moves and alias deletion use
the separately reviewed source-occurrence propose/install CLI, with the exact
frozen source root for that version. File disappearance requires explicit review;
it does not automatically withdraw or restore a document.

## Locked native templates for new maintenance uploads

Set the private `maintenance_native_upload_profiles` dictionary to exactly
`plain` and `deepdoc`, using the full validated profiles from the immutable
Main parser profile lock. Both use explicit zero overlap, no parent/graph/auto
generation or diagram context and complete sources. The UI receives only
maintainer-facing choices and the configured per-file byte limit, not private
profiles. Default PDF uses DeepDOC; a maintainer may explicitly select text PDF.
DOCX/XLSX use native plain structure. Other formats retain their prior workflow
and must not be described as native template coverage. Duplicates are unchanged.

`UPDATE_CONFIRMED` parsing requires the exact logical document and expected
prior version, a traceable explicit relation and a complete original input.
This does not publish: the existing publisher still enforces current-version
CAS, quality, sharing and withdrawal. It cannot restore a withdrawn document.
Never reconfigure existing frozen batches.

The frontend uses `upload_policy.max_source_bytes`. The deployment must also
provide an exact upload-only reverse-proxy request limit that accommodates
multipart metadata; raising the per-file setting alone does not raise nginx.
The candidate uses at most64MiB per file and65MiB upload request bodies; other
routes retain their smaller bounds. Actual boundary probes are separate from
unit tests and cannot be inferred from the setting.
