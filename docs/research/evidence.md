# Ham ölçüm kanıtları

Bu indeks manifest ve özgün JSON baytlarından üretilir.
Arşiv biçimi ve sınırlar [kanıt standardındadır](../standards/research-evidence.md).
Eski başarısız ölçümler ve tanılar korunur; güncel kabul ayrıca incelenir.
Gzip dosyaları Git checkout'unda tutulur; sdist/wheel içine girmez.

## p01-3-followup-merged-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `8938a2827a3000a6983d39d734da60653cea8421e1f0393a3534f0dd5068802b`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-3-followup-merged-startup.json); yerel arşiv `raw/p01-3-followup-merged-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"candidate/cache": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 200.0, "p95_ms": 218.223, "passed": false, "samples": 30}, "candidate/context": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 200.0, "p95_ms": 174.407, "passed": true, "samples": 30}, "candidate/help": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 500.0, "p95_ms": 45.871, "passed": true, "samples": 30}, "candidate/version": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 500.0, "p95_ms": 44.031, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-cache-parse-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `24a45124230e90bd728e5109238cbfa92d87607f11f7fd13408c00ede7686ce0`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-cache-parse-operation-budget.json); yerel arşiv `raw/p01-4-cache-parse-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 5034.169083, "outcomes": {"ok": 24, "state_busy": 3}, "source_commit": "5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5"}`.

## p01-4-ci-startup-40807762132

**Tür:** `startup`.
**Özgün JSON SHA-256:** `b7da75f2680cce2813d0a12197978668b06578beeb434499d43658c6981115d2`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-ci-startup-40807762132.json); yerel arşiv `raw/p01-4-ci-startup-40807762132.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 119.01860200001124, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 93.38375499999074, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.742677000006097, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.760992999996233, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 116.57509900001628, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 91.73733599999423, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 21.959119999991117, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 21.349657999991223, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-ci-startup-40808159684

**Tür:** `startup`.
**Özgün JSON SHA-256:** `594f7305ef1f398298c051c1d00f7359a483ee860e2961c36f5e419bd500923e`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-ci-startup-40808159684.json); yerel arşiv `raw/p01-4-ci-startup-40808159684.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 355.91988900000615, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 121.93917500002271, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 32.087685999954374, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 30.982848000007834, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 392.3889300000383, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 119.64243199997782, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.465944999993553, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 27.52818499999421, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-closing-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `cb154c8d655f47fed9169c507570dcc8abdbe4711add58b560b40eddf7b02619`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-closing-jobs-budget.json); yerel arşiv `raw/p01-4-closing-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 178.063125, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 120.208084, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 124.486167, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 121.778791, "passed": true, "samples": 30}}, "source_commit": "9600416e58ac3f7e604feef7ba25fff0dbfeff2f"}`.

## p01-4-final-installations

**Tür:** `installation`.
**Özgün JSON SHA-256:** `f851a28d0e25ed56f1f4b11f83bc7462d06c400fb6516d77b341bcfa43f98d44`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-final-installations.json); yerel arşiv `raw/p01-4-final-installations.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation", "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `66b89e1d31189cc48f9d587e9fc602d13e04f79ecb1c0b0c509a0851a28e88e2`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-final-jobs-budget.json); yerel arşiv `raw/p01-4-final-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 166.939, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 104.432042, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 120.620875, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 105.247583, "passed": true, "samples": 30}}, "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `43edb6deafec81ff7d5ef0aec0dde7b5f6f2bf95198f3454d291b7cd1250e405`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-final-migration-budget.json); yerel arşiv `raw/p01-4-final-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4316.419583, "outcomes": {"ok": 24}, "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `6171238f6d54e4e5b592364f20bb71ff4b1f81f40e5d6e58ae83c223da4be5de`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-final-operation-budget.json); yerel arşiv `raw/p01-4-final-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4931.328083, "outcomes": {"ok": 27}, "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `d0e48803b4a7cb35cf4ba9194bf4e73863a86ac5af1721f614b100c13580e58e`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-final-startup.json); yerel arşiv `raw/p01-4-final-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 123.77254199236631, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 77.75479182600975, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.277000153437257, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.19595799781382, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 114.53570914454758, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 90.23562516085804, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.374042008072138, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 21.44575002603233, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-hotpath-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `cd2f6968a80c64c86c27a71caa60f950a734569ca1a5f0001623417ffb603889`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-hotpath-operation-budget.json); yerel arşiv `raw/p01-4-hotpath-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 5034.559042, "outcomes": {"ok": 21, "state_busy": 6}, "source_commit": "ad6cb924f6b0a3abc71655b7eb1afa9d6655e340"}`.

## p01-4-hotpaths-ab-full

**Tür:** `comparison`.
**Özgün JSON SHA-256:** `12497116bb00e34f32b3af1613650036118df60371a2581684c68dc6c716e602`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-hotpaths-ab-full.json); yerel arşiv `raw/p01-4-hotpaths-ab-full.json.gz`.
**Özet:** `{"cases": 6, "diagnostic_only": true, "kind": "comparison", "outcomes": {"ok": 6}, "source_commit": null}`.

## p01-4-initial-help-parity

**Tür:** `help-parity`.
**Özgün JSON SHA-256:** `74d2fd9fe5b564007e9c465b496cdef607ffcd2e7f743878a2f704de375bd559`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-initial-help-parity.json); yerel arşiv `raw/p01-4-initial-help-parity.json.gz`.
**Özet:** `{"cases": 30, "checks": {"equal": {"false": 1, "true": 29}, "matches_initial_p014": {"not_recorded": 30}, "root_expected_jobs_addition": {"false": 29, "true": 1}}, "diagnostic_only": false, "kind": "help-parity", "source_commit": null}`.

## p01-4-noop-installations

**Tür:** `installation`.
**Özgün JSON SHA-256:** `f19ea619ca4c7e6e64579ecdb62c3cede50a6e39923fec3eb68cf2f248b7e694`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-installations.json); yerel arşiv `raw/p01-4-noop-installations.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation", "source_commit": "182f695f656c374530d9a496a59d9e7ee714932f"}`.

## p01-4-noop-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `0d16c259bec38102f7002ac664e30096410ad01ae24abf180b8e412fb7fbe483`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-jobs-budget.json); yerel arşiv `raw/p01-4-noop-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 175.711583, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 122.114375, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 133.52175, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 118.805833, "passed": true, "samples": 30}}, "source_commit": "bc0d3c9a3f8c8aa5fdfe20b1aa69dd375319538e"}`.

## p01-4-noop-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `3c6d36e4eecc2809cadf30ca7b21cfe3497e08212df6d186f97918a6c07d6bc2`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-migration-budget.json); yerel arşiv `raw/p01-4-noop-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4456.741375, "outcomes": {"ok": 24}, "source_commit": "bc0d3c9a3f8c8aa5fdfe20b1aa69dd375319538e"}`.

## p01-4-noop-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `9dd3a4e3f8f8fb26c9443f802a10d099dd28c21ae40b6c9a967809bda6225812`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-operation-budget.json); yerel arşiv `raw/p01-4-noop-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4851.707875, "outcomes": {"ok": 27}, "source_commit": "bc0d3c9a3f8c8aa5fdfe20b1aa69dd375319538e"}`.

## p01-4-noop-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `00b45552acdfd0a0252449d6aa7c36bbe8bba78f6ca3ad1d65d7012b692b9bb8`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-startup.json); yerel arşiv `raw/p01-4-noop-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 123.78991581499577, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 84.49516608379781, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 27.706583961844444, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 27.38975011743605, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 123.1852921191603, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 82.74233294650912, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 26.896916795521975, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 25.322833796963096, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-quality-help-parity

**Tür:** `help-parity`.
**Özgün JSON SHA-256:** `aa3a82ea0007ae8326eb7525da666d0d2b06ad3ba9f92215858452f4de32248e`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-quality-help-parity.json); yerel arşiv `raw/p01-4-quality-help-parity.json.gz`.
**Özet:** `{"cases": 30, "checks": {"equal": {"not_recorded": 30}, "matches_initial_p014": {"true": 30}, "root_expected_jobs_addition": {"not_recorded": 30}}, "diagnostic_only": false, "kind": "help-parity", "source_commit": "e638194a37fecd273574cd84e415a1085479c943"}`.

## p01-4-quality-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `4434f6677c6aacf40dd49366980045b319616e2955f8a3a18d62d602597f0eb3`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-quality-operation-budget.json); yerel arşiv `raw/p01-4-quality-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 5033.784375, "outcomes": {"ok": 21, "state_busy": 6}, "source_commit": "e638194a37fecd273574cd84e415a1085479c943"}`.

## p01-4-quota-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `f603f216fa3dfa8d5d99cefa945a1cee786860d7bf1d61927911505d146b5387`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-quota-migration-budget.json); yerel arşiv `raw/p01-4-quota-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4541.755791, "outcomes": {"ok": 24}, "source_commit": "dbdc9562c439091ae411246f006772e04460acce"}`.

## p01-4-quota-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `014a18940f859d4d91022c7e445ff39f48e8e1b4647b82b4d855410760e5fc7b`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-quota-operation-budget.json); yerel arşiv `raw/p01-4-quota-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4965.896083, "outcomes": {"ok": 27}, "source_commit": "dbdc9562c439091ae411246f006772e04460acce"}`.

## p01-4-reset-diagnostic

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `67d0cc491804914c87ad9ea4ad3b51f044ca11811754a3d768b73c16c21e537e`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-reset-diagnostic.json); yerel arşiv `raw/p01-4-reset-diagnostic.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ok", "source_commit": "5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5"}`.

## p01-4-step-1-migration

**Tür:** `migration`.
**Özgün JSON SHA-256:** `0aede2bacaa72702a78f210e19b7a71ed446f9944d9df022f5f192a68d8f266f`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-1-migration.json); yerel arşiv `raw/p01-4-step-1-migration.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4528.112625, "outcomes": {"ok": 24}, "source_commit": "c3dbfe7b5e983d0075718edc065a8f815c1f8ff4"}`.

## p01-4-step-3-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `f297eeb3656a71903834d7a6e78b1900cea6ef911deab3db1e34946a2d1f57f3`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-3-operation-budget.json); yerel arşiv `raw/p01-4-step-3-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4961.403375, "outcomes": {"ok": 27}, "source_commit": "0b8c2cf2990345af4bad2a73b630431055fb1117"}`.

## p01-4-step-3-reviewed-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `049703e60df29dd941f38ab6ab7018822673b10f8dba12c6bcade9dfbc6306b2`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-3-reviewed-migration-budget.json); yerel arşiv `raw/p01-4-step-3-reviewed-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4337.36875, "outcomes": {"ok": 24}, "source_commit": "0092d407f933246952a6da4e47d5145eeebf6d0d"}`.

## p01-4-step-3-reviewed-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `b19dc6718da161af6b51096dde0fb635171f0a0617548a939ad970f03d1c8dd7`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-3-reviewed-operation-budget.json); yerel arşiv `raw/p01-4-step-3-reviewed-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4936.653875, "outcomes": {"ok": 27}, "source_commit": "0092d407f933246952a6da4e47d5145eeebf6d0d"}`.

## p01-4-step-4-initial-installations

**Tür:** `installation`.
**Özgün JSON SHA-256:** `880d1784557069aac59c3847c8678c4e346e3a9220ab88f95fbec37e4660d95a`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-4-initial-installations.json); yerel arşiv `raw/p01-4-step-4-initial-installations.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation", "source_commit": null}`.

## p01-4-step-4-initial-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `919cd1a16d3caf73bcbb8d678f5b035d32070eee99b51afc35f1aad32a3158b9`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-4-initial-jobs-budget.json); yerel arşiv `raw/p01-4-step-4-initial-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 165.678333, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 104.372, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 111.118875, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 104.767333, "passed": true, "samples": 30}}, "source_commit": "39251184d3a4fd742a8680f0edeb2d42c6880c1c"}`.

## p01-4-step-4-initial-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `c03ab360e04c457d1887a80c0c4b47f1fa7f820aafc656a3fce5f2dc65511d9f`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-step-4-initial-startup.json); yerel arşiv `raw/p01-4-step-4-initial-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 124.26991597749293, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 74.06549993902445, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.93483293801546, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.77424987591803, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 112.88970895111561, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 72.32283311896026, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.766458896920085, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.005208931863308, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-wire-size-micro

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `5a005c1c7163038f318b0ffcb2c210c5783963ebf011c0fba5e2e79d5f157ae4`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-wire-size-micro.json); yerel arşiv `raw/p01-4-wire-size-micro.json.gz`.
**Özet:** `{"cases": 3, "diagnostic_only": true, "kind": "diagnostic", "source_commit": "5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5"}`.

## startup-ci-control

**Tür:** `startup`.
**Özgün JSON SHA-256:** `9cb35022e9ec958c1ae1c5f4190e4dfefd964b7c0dc7ec4a5ae151811d51c1c7`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/startup-ci-control.json); yerel arşiv `raw/startup-ci-control.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 121.04508304037154, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 97.559834131971, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 92.26295817643404, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 26.12408297136426, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 123.00616595894098, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 85.22891695611179, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 57.37687484361231, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.313292000442743, "passed": true, "samples": 30}}, "source_commit": null}`.

## startup-ci-paired

**Tür:** `startup`.
**Özgün JSON SHA-256:** `e111e614c9fd5d3ad58b53d99678c4733130b2e1d93fa7085ee689998d971db7`.
[İlk kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/startup-ci-paired.json); yerel arşiv `raw/startup-ci-paired.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 115.89816701598465, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 76.45354187116027, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.900457916781306, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 25.615291204303503, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 114.30612509138882, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 83.85437494143844, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.29741690866649, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.593999980017543, "passed": true, "samples": 30}}, "source_commit": null}`.
