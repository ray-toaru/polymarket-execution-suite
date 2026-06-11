# Offline independent review manual - v0.28.0 non-live canary

## Purpose

This manual defines the offline dual-control review process for one controlled
real-funds canary attempt when GitHub cannot enforce required reviewers.

The process separates three roles:

- The operator prepares the review packet and may later execute the approved
  canary.
- The independent reviewer verifies the packet on a separate trust path and
  signs the approval evidence.
- The verifier rechecks the reviewer identity, signature, hashes, expiry, and
  package bindings before producing a reviewed-go package.

The reviewer must be a real person who is not the operator. An AI agent,
sub-agent, second terminal, or second account controlled by the operator does
not satisfy this requirement.

An approved dual-control review is not production authorization. It can support
only the exact, single-attempt `REAL_FUNDS_CANARY` package that it binds.
The current repository release decision remains no-go for production and live
trading. This manual documents a future approval procedure; it does not change
that decision or enable live execution by itself.

## Safety boundary

The review packet and draft template do not authorize remote side effects.
Until the reviewed-go package is created and all runtime gates pass:

- `live_submit_authorized` remains `false`;
- `live_cancel_authorized` remains `false`;
- `real_funds_canary_authorized` remains `false`;
- `remote_side_effects_authorized` remains `false`;
- production deployment remains unauthorized.

Never place private keys, API secrets, passphrases, raw signatures, raw signed
orders, or signed order envelopes in the packet, review JSON, evidence files,
GitHub issues, or chat.

## Reviewer qualification

Before accepting a review, the operator records the reviewer in a local,
access-controlled reviewer registry. The registry must contain:

```json
{
  "reviewer_identity_ref": "reviewer://alice/example",
  "allowed_signing_method": "gpg",
  "signing_key_fingerprint": "FULL_FINGERPRINT",
  "registered_at": "2026-06-11T00:00:00Z",
  "registered_by": "operator://primary",
  "status": "active"
}
```

The reviewer must:

- control the registered signing key independently;
- receive no trading secret or operator signing key;
- understand the candidate market, risk limits, rollback, alerting, and
  reconciliation requirements;
- have authority to reject the attempt without operator override;
- use a different `reviewer_identity_ref` from `operator_identity_ref`.

Revoke a reviewer entry immediately after key compromise, loss of independence,
or role termination. Do not accept signatures created after revocation.

## Signing-key setup

### GPG

The reviewer generates and protects their own signing key:

```bash
gpg --quick-generate-key "Canary Reviewer <reviewer@example.invalid>" ed25519 sign 1y
gpg --list-secret-keys --keyid-format LONG
gpg --fingerprint <KEY_ID>
gpg --armor --export <KEY_ID> > reviewer-public-key.asc
```

The operator verifies the full fingerprint over a separate channel before
adding the public key to the reviewer registry. The private key and passphrase
never enter the repository or review packet.

### SSH signing

SSH signing is acceptable only if the verifier uses a fixed allowed-signers
file that binds the reviewer identity to the public key:

```text
reviewer@example.invalid namespaces="pmx-canary-review" ssh-ed25519 AAAA...
```

The reviewer retains the private key. The operator stores only the public key,
fingerprint, and registry record.

## Step 1: Operator prepares the packet

The operator first generates current release, candidate, runtime-truth, and
approval material. All CI run IDs and the credentialed SDK evidence ID must be
explicit and current.

Create the dual-control template:

```bash
python scripts/prepare_dual_control_review_template.py \
  --approval-request-file <approval-request.json> \
  --output <dual-control-review.template.json>
```

Create the self-contained review packet:

```bash
python scripts/prepare_dual_control_review_packet.py \
  --output-dir <review-packet-dir> \
  --release-zip <release.zip> \
  --candidate-market-file <candidate-market.json> \
  --runtime-truth-file <runtime-truth.json> \
  --approval-request-file <approval-request.json> \
  --dual-control-review-template-file <dual-control-review.template.json>
```

The command verifies the packet bindings and writes:

- `packet.json`;
- `approval-request.json`;
- `dual-control-review.template.json`;
- the release zip and detached sidecars;
- candidate market and runtime-truth documents;
- a packet README.

The operator then produces a transport manifest outside the packet directory:

```bash
(
  cd <review-packet-dir>
  find . -type f -print0 | sort -z | xargs -0 sha256sum
) > review-packet.transport.sha256
```

Transfer the packet and transport manifest over a channel that does not modify
file contents. The reviewer must not accept a packet sent only as screenshots
or pasted JSON.

## Step 2: Reviewer verifies transport integrity

The reviewer works from a fresh directory and performs:

```bash
(cd <review-packet-dir> && \
  sha256sum --check ../review-packet.transport.sha256)
python scripts/prepare_dual_control_review_packet.py \
  --output-dir <independent-rebuild-dir> \
  --release-zip <review-packet-dir/release.zip> \
  --candidate-market-file <review-packet-dir/candidate-market.json> \
  --runtime-truth-file <review-packet-dir/runtime-truth.json> \
  --approval-request-file <review-packet-dir/approval-request.json> \
  --dual-control-review-template-file \
    <review-packet-dir/dual-control-review.template.json>
```

The reviewer compares the rebuilt `packet.json` bindings with the received
packet. Any missing file, hash mismatch, unexpected file, unresolved
placeholder outside the draft review template, or secret-like material is a
hard rejection.

## Step 3: Reviewer performs the nine required checks

For each check, the reviewer creates a short evidence file. Each evidence file
states the reviewed inputs, method, conclusion, reviewer identity, and UTC
time. It contains references and hashes, not secrets.

### 1. Artifact hash

Confirm:

- the release zip hash matches its `.sha256` sidecar;
- the `.evidence.json` sidecar names the same artifact and hash;
- the artifact passes `scripts/check_release_artifact.py`;
- the source commit and submodule commits match the intended review target.

Record this as `artifact_hash_reviewed`.

### 2. Evidence manifest hash

Confirm:

- workspace and archived manifest hashes match the release sidecar;
- only `polymarket-execution-engine/evidence/current/manifest.json` is treated
  as canonical current evidence;
- CI URLs and run IDs refer to the exact reviewed commits;
- no historical evidence is presented as current proof.

Record this as `evidence_manifest_hash_reviewed`.

### 3. Market candidate

Confirm:

- side is `BUY`;
- order type is `GTC`;
- `post_only` is `true`;
- condition, token, outcome, price, and target size describe the intended
  market;
- the exchange-rule snapshot is fresh;
- price does not cross the book;
- target size satisfies minimum size and tick rules;
- candidate notional equals price multiplied by target size.

Record this as `market_candidate_reviewed`.

### 4. Runtime truth

Confirm that runtime truth:

- binds the reviewed account, condition, artifact, and manifests;
- reports `posted=false` and `remote_side_effects=false`;
- provides concrete evidence references for kill switch, worker health,
  geoblock, reservation, idempotency, reconciliation, cancel-only fallback,
  and balance or allowance checks;
- has no stale or contradictory runtime state.

Record this as `runtime_truth_reviewed`.

### 5. Risk limits

Confirm:

- `max_order_notional_usd` covers the candidate but does not exceed the agreed
  canary cap;
- `max_daily_notional_usd` matches the single-attempt policy;
- order count is one;
- no automatic retry or second order is permitted;
- approval expiry leaves enough time for one controlled attempt only.

Record this as `risk_limits_reviewed`.

### 6. Secret custody

Confirm:

- secrets are supplied only by the approved external provider or explicit
  runtime secrets file;
- the review packet contains no secret values;
- the adapter does not possess signing or CLOB credentials;
- the reviewer has no access to the operator's trading secrets;
- logs and reports redact sensitive material.

Record this as `secret_custody_reviewed`.

### 7. Alerting

Confirm:

- an operator-visible alert route exists for post, cancel, unknown remote
  outcome, worker degradation, and reconciliation failure;
- the route can be used during the review window;
- alert evidence is not merely a placeholder.

Record this as `alerting_reviewed`.

### 8. Rollback

Confirm:

- the kill switch is available;
- the rollback or incident runbook is current;
- the operator can stop further attempts;
- production deployment remains unauthorized;
- rollback does not depend on exposing secrets or raw signed payloads.

Record this as `rollback_reviewed`.

### 9. Reconcile and cancel fallback

Confirm:

- successful post must be followed by cancel and readback;
- unknown post result triggers account-level investigation, not retry;
- cancel-only fallback is available;
- unresolved `operator_required` state prevents clean closeout;
- consumption and closeout are required before any later attempt.

Record this as `reconcile_and_cancel_fallback_reviewed`.

If any check is incomplete, the reviewer returns `REJECT` and does not edit the
template to `approved`.

## Step 4: Reviewer creates the approval JSON

Copy `dual-control-review.template.json` to
`dual-control-review.approved.json`. Preserve all bound hashes and risk values.
Change only the reviewer-controlled fields:

- set `status` to `approved`;
- set a unique `review_ref`;
- set `reviewer_identity_ref` to the registered identity;
- set `reviewer_identity_sha256` to the SHA-256 of the exact UTF-8 identity
  string;
- set `reviewed_at` to the current RFC 3339 UTC time;
- keep `expires_at` unchanged;
- set every completed reviewer check to `true`;
- add one concrete evidence reference and SHA-256 for every check;
- bind the registered signing-key attestation in the signature evidence fields.

Compute the identity hash:

```bash
printf '%s' 'reviewer://alice/example' | sha256sum
```

The approved JSON must keep all authorization flags `false`. The later
reviewed-go package creates the narrowly scoped authorization after validating
the review.

Create an immutable signing-key attestation before signing:

```json
{
  "schema_version": 1,
  "reviewer_identity_ref": "reviewer://alice/example",
  "signing_method": "gpg",
  "signing_key_fingerprint": "FULL_FINGERPRINT",
  "public_key_sha256": "64_HEX_DIGEST",
  "review_namespace": "pmx-canary-review",
  "registry_ref": "reviewer-registry://alice/example",
  "status": "active"
}
```

Set:

```text
review_signature_evidence_ref=<controlled reference to the signing-key attestation>
review_signature_evidence_sha256=<SHA-256 of the signing-key attestation>
```

The signature evidence fields bind the independently registered signing
identity. The detached signature created below proves that identity signed the
final review JSON. This avoids an impossible self-reference in which a file
would need to contain the hash of its own signature.

## Step 5: Reviewer signs the final approval

Do not embed signature bytes in JSON. Canonicalize the fully populated final
approval JSON, then sign that exact byte sequence.

For GPG:

```bash
jq -S . dual-control-review.approved.json \
  > dual-control-review.approved.canonical.json
gpg --armor --detach-sign \
  --local-user <REVIEWER_KEY_FINGERPRINT> \
  --output dual-control-review.approved.canonical.json.asc \
  dual-control-review.approved.canonical.json
```

For SSH:

```bash
jq -S . dual-control-review.approved.json \
  > dual-control-review.approved.canonical.json
ssh-keygen -Y sign \
  -f <REVIEWER_PRIVATE_KEY> \
  -n pmx-canary-review \
  dual-control-review.approved.canonical.json
```

The reviewer returns:

- `dual-control-review.approved.json`;
- `dual-control-review.approved.canonical.json`;
- the detached signature;
- the signing-key attestation;
- all nine evidence files;
- a SHA-256 manifest covering those files.

## Step 6: Operator verifies the independent signature

The operator first confirms that the JSON canonicalizes to the signed file:

```bash
jq -S . dual-control-review.approved.json \
  > /tmp/dual-control-review.rebuilt.json
cmp /tmp/dual-control-review.rebuilt.json \
  dual-control-review.approved.canonical.json
```

Verify a GPG signature:

```bash
python scripts/verify_dual_control_review_signature.py \
  --approved-dual-control-review-file dual-control-review.approved.json \
  --canonical-dual-control-review-file \
    dual-control-review.approved.canonical.json \
  --review-signature-file dual-control-review.approved.canonical.json.asc \
  --reviewer-registry-file <reviewer-registry.json> \
  > review-signature-verification.txt
```

The verifier imports only the registered reviewer public key, checks the
registered fingerprint, confirms the signing-key attestation hash, rejects
inactive or revoked registry entries, and verifies that the canonical JSON
matches the approved review JSON.

Verify an SSH signature:

```bash
python scripts/verify_dual_control_review_signature.py \
  --approved-dual-control-review-file dual-control-review.approved.json \
  --canonical-dual-control-review-file \
    dual-control-review.approved.canonical.json \
  --review-signature-file dual-control-review.approved.canonical.json.sig \
  --reviewer-registry-file <reviewer-registry.json> \
  > review-signature-verification.txt
```

Record the verifier command, exit status, reviewer fingerprint, canonical JSON
SHA-256, signature file SHA-256, verification time, and result in
`review-signature-verification.txt`.

Confirm that the attestation hash matches
`review_signature_evidence_sha256`, its identity matches
`reviewer_identity_ref`, and its fingerprint matches the key reported by the
successful verification. Retain the detached signature and verification report
beside the attestation.

The repository validator now requires this cryptographic verification before a
reviewed-go package can be created. A valid signature from an inactive,
revoked, expired, unregistered, or identity-mismatched reviewer is a rejection.

## Step 7: Produce the reviewed-go package

Only after successful signature verification:

```bash
python scripts/prepare_canary_reviewed_go_bundle.py \
  --review-packet-dir <review-packet-dir> \
  --approved-dual-control-review-file \
    <dual-control-review.approved.json> \
  --canonical-dual-control-review-file \
    <dual-control-review.approved.canonical.json> \
  --review-signature-file <dual-control-review.signature> \
  --reviewer-registry-file <reviewer-registry.json> \
  --external-references-file <external-references.json> \
  --output-dir <reviewed-go-package-dir> \
  --decision-reason "approved by offline independent reviewer"
```

This command rejects:

- expired review;
- reviewer and operator identity equality;
- identity-hash mismatch;
- missing, failed, inactive, revoked, expired, or wrong-identity signature;
- unresolved placeholders;
- missing reviewer checks or evidence hashes;
- changed artifact, manifest, candidate, runtime-truth, approval, or risk
  bindings;
- secret-bearing review material.

Successful output has status
`reviewed_go_package_ready_single_attempt`. It authorizes only the bound canary
scope and does not authorize production deployment.

## Step 8: Pre-execution verification

Immediately before any armed step, the operator rechecks:

- current UTC time is before approval expiry;
- the reviewed-go directory is neither consumed nor closed;
- all package file hashes match `review.json`;
- runtime account and profile match the package;
- candidate and runtime truth have not changed;
- kill switch, reconciliation, alerting, and cancel fallback are available;
- no second attempt or automatic retry is configured.

Any change after review invalidates the approval. Rebuild and re-review the
whole packet; do not patch hashes manually.

## Step 9: Consumption and closeout

After the first armed invocation, regardless of success:

- mark the approval consumed;
- prohibit reuse;
- persist post, cancel, readback, and stage-history evidence;
- reconcile fills, activity, open orders, and positions;
- record operator recovery for any `operator_required` state;
- close the package before preparing another attempt.

An unknown post result must not trigger another order. Investigate account-level
activity and use the incident-recovery path.

## Rejection conditions

The reviewer or verifier must reject when:

- reviewer independence cannot be established;
- the signing key is unregistered, expired, revoked, or compromised;
- signature verification fails or was not performed;
- the review or approval is expired;
- any bound file or hash differs;
- CI evidence targets another commit;
- risk values changed after review;
- a required check lacks concrete evidence;
- a secret or raw signed payload appears in review material;
- the market or runtime state is unclear;
- cancel, reconciliation, alerting, or rollback is unavailable;
- the operator requests a retry, second order, broader scope, or production
  deployment under the same approval.

Silence, chat acknowledgment, an AI recommendation, or an unsigned edited JSON
is not approval.

## Evidence retention

Store the following in an access-controlled external review archive:

- reviewer registry snapshot and public-key fingerprint;
- received packet transport manifest;
- approved review JSON and canonical signed copy;
- detached signature;
- signature verification report;
- nine reviewer evidence files and their hashes;
- reviewed-go package hash manifest;
- consumption marker and closeout package;
- rejection record, if applicable.

Do not commit external signature files or secret-bearing operational material
to this repository. Preserve only reference identifiers and SHA-256 bindings in
repository-governed JSON.

## Automated secondary review

An AI agent or sub-agent may inspect the packet and produce a non-authorizing
report:

```json
{
  "review_kind": "automated_secondary_review",
  "independent_human_review": false,
  "authorization_effect": "none"
}
```

This report may support the human reviewer. It cannot populate the independent
reviewer identity, sign the approval, or replace the process above.
