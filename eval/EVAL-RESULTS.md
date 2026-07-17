# Eval Results — `education` vertical

**Dataset:** `eval/datasets/education_30.jsonl` (30 scenarios)
**Mode:** MOCK_MODE (deterministic, no LLM cost)
**Run at:** 2026-07-17 15:36:07

> **What mock-mode numbers measure:** the LLM is replaced by a deterministic
> keyword-matched mock, so these metrics exercise the *pipeline* — graph routing,
> tool dispatch, escalation logic, retry loop and the judge — not model quality.
> A live-LLM run (`MOCK_MODE=false`) is the follow-up benchmark; expect lower,
> noisier numbers there.

## Summary metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Resolution rate | 100% | ≥ 70% | ✓ PASS |
| Intent accuracy | 100% | ≥ 85% | ✓ PASS |
| Tool choice accuracy | 90% | ≥ 80% | ✓ PASS |
| Human escalation precision | 97% | ≥ 90% | ✓ PASS |
| Avg quality score | 0.82 | ≥ 0.70 | ✓ PASS |
| Avg retry count | 0.00 | ≤ 0.5 | ✓ PASS |
| Latency P50 | 191 ms | ≤ 3000 | ✓ PASS |
| Latency P95 | 250 ms | ≤ 6000 | ✓ PASS |

## By category

| Category | Count | Passed | Rate |
|----------|-------|--------|------|
| course_question | 3 | 3 | 100% |
| family_setup | 3 | 3 | 100% |
| general | 4 | 4 | 100% |
| plan_change | 4 | 4 | 100% |
| pricing_question | 3 | 3 | 100% |
| progress_concern | 3 | 3 | 100% |
| refund_request | 5 | 5 | 100% |
| schools_enquiry | 3 | 3 | 100% |
| technical_issue | 2 | 2 | 100% |

## By difficulty

| Difficulty | Count | Passed | Rate |
|------------|-------|--------|------|
| easy | 10 | 10 | 100% |
| hard | 7 | 7 | 100% |
| medium | 13 | 13 | 100% |

## Per-scenario results

| ID | Category | Difficulty | Pass | Intent | Tools | Human | Quality | Latency |
|----|----------|------------|------|--------|-------|-------|---------|---------|
| T001 | pricing_question | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 191 ms |
| T002 | pricing_question | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 191 ms |
| T003 | course_question | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 172 ms |
| T004 | course_question | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 181 ms |
| T005 | course_question | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 187 ms |
| T006 | family_setup | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 247 ms |
| T007 | family_setup | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 239 ms |
| T008 | family_setup | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 180 ms |
| T009 | plan_change | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 245 ms |
| T010 | plan_change | medium | ✓ | ✓ | ✗ | ✓ | 0.82 | 187 ms |
| T011 | plan_change | hard | ✓ | ✓ | ✗ | ✓ | 0.82 | 231 ms |
| T012 | refund_request | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 231 ms |
| T013 | refund_request | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 246 ms |
| T014 | refund_request | medium | ✓ | ✓ | ✗ | ✓ | 0.82 | 243 ms |
| T015 | refund_request | hard | ✓ | ✓ | ✓ | ✗ | 0.82 | 238 ms |
| T016 | refund_request | hard | ✓ | ✓ | ✓ | ✓ | 0.82 | 254 ms |
| T017 | progress_concern | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 238 ms |
| T018 | progress_concern | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 223 ms |
| T019 | progress_concern | hard | ✓ | ✓ | ✓ | ✓ | 0.82 | 253 ms |
| T020 | schools_enquiry | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 180 ms |
| T021 | schools_enquiry | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 188 ms |
| T022 | schools_enquiry | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 172 ms |
| T023 | technical_issue | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 180 ms |
| T024 | technical_issue | hard | ✓ | ✓ | ✓ | ✓ | 0.82 | 237 ms |
| T025 | general | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 166 ms |
| T026 | general | hard | ✓ | ✓ | ✓ | ✓ | 0.82 | 172 ms |
| T027 | general | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 178 ms |
| T028 | general | easy | ✓ | ✓ | ✓ | ✓ | 0.82 | 169 ms |
| T029 | pricing_question | medium | ✓ | ✓ | ✓ | ✓ | 0.82 | 181 ms |
| T030 | plan_change | hard | ✓ | ✓ | ✓ | ✓ | 0.82 | 242 ms |
