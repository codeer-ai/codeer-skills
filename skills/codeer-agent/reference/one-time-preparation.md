# One-time preparation and manual rollout

This is an operator runbook, not a migration framework. Do not execute it merely
because a coding agent updated its tools. Actual customer files, API operations
and switching the everyday CLI require explicit authorization and reviewed scope.

## Inspect the current contract

The runtime supports project.toml schema 2 and evidence contract 2 for current
operations. Other objects retain their existing contracts:

| Object | Required current information | Preparation |
| --- | --- | --- |
| project.toml | schema 2, name, configured paths; no inline target | Keep conforming bytes. Unsupported projects stop before HTTP; review with the pinned old tool offline |
| Binding target/state | API/workspace/Agent identity, resource IDs, scope, bases, statuses, receipt references | Keep IDs and checkpoints exactly; optional cached labels/profile fields do not constrain credentials |
| Agent/Case/Tester/pair sync receipt | resource, saved scope/ID, payload, local checkpoint, token, response/readback/outcome | Extra preview comparison fields may remain; no bulk receipt rewrite |
| KB/attachment/FAQ/delete recovery | original request and IDs, responses, file/hash/snapshot proofs, completed/inflight operations or prior deletion state | Preserve the actual operation's consumer-required fields; FAQ replay requires its remote preimage |
| Old runs/audits/reviews/baselines/releases/deliveries and embedded project.toml | original paths, bytes and hashes | Read-only; no schema/evidence-contract upgrade or new pass/clearance |

A schema 1 state/resources/FAQ/target object is not a schema 1 project. Do not
raise every JSON version. Conforming current data can be a zero-change rollout.
Binding terminology does not require moving `.codeer/deployments` or the local
`.codeer/deployment` selector. Existing design/log/release paths remain supported.

## Prepare an exact reviewed copy

1. Limit the inventory to the approved project directories, currently the known
   `customer-agents/projects` projects. Stop ordinary CLI, old tools, direct
   audit/pin/file editors and other operators. The local lock covers cooperative
   current CLI commands only. Record the installed CLI/skill version and editable
   source path; preserve a Git revision plus locked dependencies sufficient to
   reproduce the old tool in an isolated environment. Do not switch a live editable
   source tree while preparation is in progress.
2. Hash every project file and save the manifest outside the projects, including
   hidden `.codeer/`, raw history, all runs, archived evidence and inputs. Make a
   full backup and verify its manifest equals the source. Use an approved secure
   location; no key collection, cloud upload or credential export is implied.
3. Make a separate work copy. Produce a list of required current-state corrections
   and a zero-change list. Diagnose only actual unsupported fields/references;
   unknown outcomes and missing capability are facts to preserve, not reasons to
   mark success, discard state or recreate resources. If API/workspace/ID cannot be
   established from recorded evidence, stop and ask the operator.
4. Apply only the exact reviewed local differences to the copy. For an active
   unknown KB with a known server ID and recorded response, carry the same request,
   ID/status and response forward without any HTTP request or new upload. When a
   fixed evidence reference requires keeping the source receipt immutable, create
   a current derivative recording `original_path` and `original_sha256`; update only
   the active state reference. Do not edit the pinned original. A full-format
   receipt with extra diagnostic fields usually needs no conversion at all.
5. Compare the complete before/after manifests. Review every changed/new/deleted
   path; IDs, API/workspace/Agent scope, bases, local proposal, content revision and
   unresolved status must stay the same except a justified reference correction.
   All fixed history, embedded configs, old delivery and originals must match their
   source bytes/hashes. Check every active reference resolves. Run offline status,
   bindings, validation and stored-history inspection; distinguish pre-existing
   design/evidence gaps from conversion defects.
6. Repeat preparation on the resulting copy: no additional file changes or new
   derivative should occur. In a separate synthetic fixture, exercise current
   reconcile using MockTransport, exact-ID run/audit/publication/delivery and clean;
   do not use real customer APIs to make a preparation test pass.

## Review, switch and recover

Before applying a reviewed difference to an actual project, recompute the source
manifest and compare it to the reviewed source manifest. **Any source change
invalidates the old difference**, including a newly added receipt or changed
reference. Reinventory and re-review; never apply a stale state copy. Actual writes
and CLI/skill installation switch need the separately authorized operator action.
Do not automatically normalize all projects: zero-change items stay byte-identical.

Recheck the changed files, references and fixed-history manifest after the local
change. If interrupted before completion, do not switch the normal entry point;
use the verified backup or resume only the remaining reviewed local corrections.
Keep the old tool reproducible, but use it offline for old evidence only.

Before the first new remote dispatch, restoration of the exact full backup is
possible while all writers remain stopped, provided no subsequent work has
changed the reviewed copy. Recheck hashes after restoration and rehearse preparation
again. After a new remote dispatch, **do not restore stale state**: retain all new
receipts/known IDs/unknown outcomes, inspect the exact operation, and reconcile
forward. Returning to the old executable is not permission to discard new state.
A timeout is not proof of failure and never authorizes a repeated create.

Record the reviewed source/backup/difference hashes, operator authorization,
installed revisions, zero-change items and remaining unknowns outside fixed
historical evidence. This runbook does not certify actual customer rollout.
