# Validation

Verified on 2026-10-29 on Stable Studionet, chain **61999**, RPC `https://studio.genlayer.com/api`. No other network was used.

Canonical contract: `0xFd69830d264aA81B108FAF5631347a104E53dDC9`.

Source SHA-256: `15b4baab3dda43919a2dc54870174d576675c6c8a910be483e78210d6fea18ba`.

## Local checks

- **21 mocked-host tests passed**, executing the actual deployable file. The suite covers all 64 binary directed graphs on three nodes, compares acyclicity against an independent permutation oracle, and verifies readiness for all completion subsets. It also covers parallel AND joins, chain transitivity, cycles, ambiguity, executor permissions, immutable plans, replay, digest binding, malformed relations, exact quote grounding, reference bounds and independent validator disagreement.
- Official `genvm-lint check` passed: three lint checks, validation, five public methods (three writes, two views). `schema.json` is the generated ABI.
- SDK Direct Mode passed with real pinned SDK storage and calldata: compile, independent validator accept/reject, blocked early acknowledgement, actor switching and COMPLETE state. LLM responses are mocked. Direct Mode is native Python, not a live Wasm/network consensus test.
- Environment: Python 3.12.14, genvm-linter 0.11.0, genlayer-test 0.29.2, genlayer-py 0.16.3, GenLayerJS 1.1.8, viem 2.57.8. The contract header pins the exact Python runner. Stable RPC identity and actual deployment/source readback were checked; a newer runner advisory was not treated as evidence of compatibility.

## Finalized canonical run

Every transaction below reached FINALIZED with MAJORITY_AGREE and `leader_only:false`. The deliberate early-publish attempt has ERROR/rollback `PREREQUISITES_PENDING`; all other actions have successful leader execution. Every submitted write uses zero value.

| Action | Transaction | Execution |
|---|---|---|
| deploy | `0x52848e99fa928970dd5b0557aaa297dc4614ff3a3f4aad65e7617641e92525d1` | SUCCESS |
| open | `0xe37b8ab0cddc15846a5dc3840482050d8d3b80075c6d592ee3f17e49b3539c8a` | SUCCESS |
| compile | `0x93b55ce44d7f1fdcab44302cbb1d8121cbf5d1873f4bc77a7772359812434cc0` | SUCCESS |
| assemble | `0xa4261ca8f96dbd17babdf8cfa602e8217017d8aa47e0a81fcc16705c2c50ce48` | SUCCESS |
| reject_early_publish | `0xa46c88983432940017bf4c468ccdbb5e8bd1b7c76660fafdd680a9b2d7fc282f` | ERROR |
| review | `0x0027c127320efc2fa69c26a58b8cac111b65393b82c544e3650f241cc94cccf8` | SUCCESS |
| publish | `0x7b3f26bcd67ab4ae4b549b44a24e5f01f35c32d5cdb6c498564ea1f244bb0950` | SUCCESS |

The compiled graph contains exactly `assemble → publish` and `review → publish`, with parallel layers `[[assemble, review], [publish]]`. After acknowledging assembly, `available` was only `[review]`. The attempted publish rolled back and the one-entry journal stayed unchanged. Acknowledging review then unlocked publish. The final run is **COMPLETE**, with journal order assemble, review, publish and no available steps.

The accepted compile receipt records 3 agree and 2 idle votes. Idle votes are not counted as independent acceptance. Internal leader rotations are network processing of the same transaction, not a client resend.

The read-only verifier re-fetches source, finalized state and all seven transaction receipts. It binds each receipt to its signer, contract, decoded method and exact binary calldata arguments, verifies full-consensus mode and execution, and compares the full final record to saved evidence. Receipt evidence is projected: node configurations, timing logs and redundant byte arrays are omitted. Transaction hashes retrieve the complete public RPC responses.

The run uses synthetic release instructions and two test wallets controlled by one operator. The journal is signed completion assertions only, not proof that an archive was generated, checked or distributed. No user wallet keys, funds or private data were used. No paid model API was configured.

## Earlier unsuccessful instance

An initial source version at `0x32A89A221DdF9A94cA16F5251340bdEcbD4A2115` deployed and registered successfully, but compilation `0x14bc837399028f21236cfa78a28bb637f1dc48d89fbc2e9010cbc77251c90412` ended UNDETERMINED with MAJORITY_DISAGREE. Its final leader/validator execution rolled back with UNSUPPORTED_QUOTE: free-form model quotations did not reliably match original text. No acknowledgements were sent to that instance.

The canonical source replaces model-generated quotations with bounded rule-line references and deterministic quote extraction. Validators still independently reproduce every category and audit substantive evidence; acceptance was not reduced to a format check. The source changed, so a distinct deployment was necessary. Existing successful deployment/registration transactions were not resent, and the failed compile was not blindly retried or appealed. [Initial attempt references](evidence/initial-attempt.json) preserve its address, source digest and hashes. Only the canonical instance above is the successful example.

## Coverage boundaries

Cycles, REVIEW, unsupported input bounds, wrong-executor rejection, digest mismatch, repeated acknowledgement, alternate valid parallel order and independent disagreement are local coverage only, not all observed on chain. Self-pair constraints are outside the supported semantic domain. No browser wallet signing, live operational connector, production runbook, independent organizations, real work completion or safety certification is claimed. Majority agreement can still be semantically wrong.

Official references:

- https://docs.genlayer.com/developers/networks
- https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- https://docs.genlayer.com/api-references/genlayer-js/contracts
