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

## p01-4-evidence-ci-startup-a24c71f

**Tür:** `startup`.
**Özgün JSON SHA-256:** `fcde6c87c89d69f550177f1629efcd8127508f4dbdeaf4c602f8a241dfa5323d`.
**Yerel arşiv:** `raw/p01-4-evidence-ci-startup-a24c71f.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 225.49458100002084, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 163.49130399999012, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 43.87156899997535, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 42.31549899998299, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 222.37509100000352, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 161.3148749999027, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 38.83290199996736, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 36.38817700004893, "passed": true, "samples": 30}}, "source_commit": null}`.

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

## p01-4-merge-805f8bd-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `91288f45ba0f62fd0f577ceea4ad1c73f55a34229acd5452abe56114092308dc`.
**Yerel arşiv:** `raw/p01-4-merge-805f8bd-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 193.8822750000213, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 153.7080840000158, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.69161699995993, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.465445000042564, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 191.56937200000357, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 153.25847500002965, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 35.09405400001242, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 33.15877099998943, "passed": true, "samples": 30}}, "source_commit": null}`.

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

## p01-6-adr19-cancelled-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `e9329e6b2fe55786721e1afe8dc010a10680b783dc51fa605fee83a204ead919`.
**Yerel arşiv:** `raw/p01-6-adr19-cancelled-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "cancelled_before_measurement", "source_commit": "b3249e4dfbaa49608e22cfe9432183cc20c10890"}`.

## p01-6-adr19-ci-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `fefb19ca8efa059a7e6131852fc0721f32ec34ccd77f67884df9c4293433e166`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_acceptance_passed", "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90"}`.

## p01-6-adr19-ci-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `8af93e86897e52ff2e390eb53f9380602ba42c8f5a3ce5c5b0b48232fdf276b8`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90"}`.

## p01-6-adr19-ci-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `1bf23c19ab08f23c75f5c65846cf1cd6f1f14492d7b8c8daf0f1be56d44aea16`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90"}`.

## p01-6-adr19-ci-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `011f90ad95436bade8ab0242c1482a9c0cc043a0acc796c182094326170df0bd`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90"}`.

## p01-6-adr19-ci-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `1a572d328057c5700a90d7b7bac6dced34f5eccd30629b9bcccb174e19162ebe`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 230.35565199995744, "baseline/context": 187.58868600002643, "baseline/help": 41.174779000016315, "baseline/version": 39.81733000000531, "candidate/cache": 229.37555999999404, "candidate/context": 184.94302900001003, "candidate/help": 42.59323400003723, "candidate/version": 40.073809999967125}, "passed": false, "reason": "validated", "report_sha256": "fbb80330930f0f508ca96230b5200256d15875744037319ad90c7ce20bfb2bac", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/40967036681", "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90"}`.

## p01-6-adr19-ci-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `fbb80330930f0f508ca96230b5200256d15875744037319ad90c7ce20bfb2bac`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 230.35565199995744, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 187.58868600002643, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 41.174779000016315, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 39.81733000000531, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 229.37555999999404, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 184.94302900001003, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 42.59323400003723, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 40.073809999967125, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90"}`.

## p01-6-adr19-ci-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `56fdda1367ba749aa03835cdd3a1f242c3fd0acd86948685f61bc9b13c7902ae`.
**Yerel arşiv:** `raw/p01-6-adr19-ci-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45654016, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.168302302000029, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46309376, "pretransfer_peak_rss_bytes": 45654016, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51400704, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08738177800000813, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 233472, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51634176, "pretransfer_peak_rss_bytes": 51634176, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45428736, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3542488169999842, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46084096, "pretransfer_peak_rss_bytes": 45428736, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [233472, 655360, 655360]}, "source_commit": "e59d5b31e0a702c0a054836fdfc5635dd4908f90", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-final-body-cancel-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `f9a635102bcb511851dde7b527fcb8424e661f94b77cb236d63ffc0bc99e8dca`.
**Yerel arşiv:** `raw/p01-6-adr19-final-body-cancel-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "cancelled_before_startup", "source_commit": "b5853dc292ef1c818dea523a2d61c2069e7614ee"}`.

## p01-6-adr19-final-doc-ci-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `a2dceb6f9f079db54f03adc3392ccac89eafd41334fb22a8d50ff15ffc2f388b`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_acceptance_passed", "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9"}`.

## p01-6-adr19-final-doc-ci-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `a866ccaaddb2d3b959d33f6048c0f83e8e69cef7b445d1c58e30638b91a834eb`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9"}`.

## p01-6-adr19-final-doc-ci-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `7d58cbe9c5298eab692a0843bdbcc8f05e8da73fa8a06e6c3bfb3b853413fa33`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9"}`.

## p01-6-adr19-final-doc-ci-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `ab3dea5c9a36380e31272fa97566c5d089ef24c8b793754059707c64d6ceaa76`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9"}`.

## p01-6-adr19-final-doc-ci-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `8b13fbc93fedea28a07eaf41beaeebf324c1678897d73d8f18db9571526fa197`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 164.8760839999568, "baseline/context": 130.32150699996237, "baseline/help": 29.999412999984543, "baseline/version": 29.295296000043436, "candidate/cache": 168.2600789999924, "candidate/context": 130.18013800001427, "candidate/help": 31.36388299998316, "candidate/version": 30.586046999985683}, "passed": true, "reason": "validated", "report_sha256": "5b05e3919d574808817a49ef735f137fe1d0ffb71f10e54e1ff46aa5f367d6cd", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/40972342635", "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9"}`.

## p01-6-adr19-final-doc-ci-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `5b05e3919d574808817a49ef735f137fe1d0ffb71f10e54e1ff46aa5f367d6cd`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 164.8760839999568, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 130.32150699996237, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 29.999412999984543, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 29.295296000043436, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 168.2600789999924, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 130.18013800001427, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 31.36388299998316, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.586046999985683, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9"}`.

## p01-6-adr19-final-doc-ci-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `ccc27c643221d34aeeff051cb03ada8ffb4949cc1991e5e3c5271b422d6be454`.
**Yerel arşiv:** `raw/p01-6-adr19-final-doc-ci-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46190592, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.999336529000061, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46845952, "pretransfer_peak_rss_bytes": 46190592, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52060160, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.04908466899996711, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 217088, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52277248, "pretransfer_peak_rss_bytes": 52277248, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46284800, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7456814149999218, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46940160, "pretransfer_peak_rss_bytes": 46284800, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [217088, 655360, 655360]}, "source_commit": "e907e995667b0eeac0b588050a18f54d2f289ad9", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-initial-runtime-aa-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `e59ee8ed7e690457dc76bdd29450b5a1604545589354d93d9673b97f6b0a6b82`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-aa-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0", "kind": "startup_baseline_selection", "mode": "initial_runtime_same_source_control", "pinned_baseline_commit": "6ec4b160e215599afcb24a416c7f796839cbe44a", "report_sha256": "616457d77d2318efe3c2379c03045094956a44f4cb3c15b8de740b83940cc8a1", "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0"}`.

## p01-6-adr19-initial-runtime-aa-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `616457d77d2318efe3c2379c03045094956a44f4cb3c15b8de740b83940cc8a1`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-aa-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 131.1375421937555, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 79.79141594842076, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.181124987080693, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.69745897501707, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 132.7950421255082, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 80.40158404037356, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 27.461959049105644, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.772458847612143, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0"}`.

## p01-6-adr19-initial-runtime-ci-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `9cbeca0c711a3d729e5174f9e86f91f99c4bf6ff544285f42f2ec95d0a44658f`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_acceptance_passed", "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `e1d559aeba8b69e2dd49ae1dd870d9439ea59843d0b4f10c745ce1f790110c32`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `611b8ca0852a9722e3cb79fc7f00af9f3c911b83b7145dcebca8384ced756269`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `7fff3c1d3ee12b285c0bd2915bd56973c79c63f3341aad36b05b7ed5cc3890b7`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `c68a3fdb349e65ea9e98d1703fcc50063b3ed01ced6f3d6771f3dc362b2f9204`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "805f8bd418847da6463408404a85675bdcb4173e", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "805f8bd418847da6463408404a85675bdcb4173e", "report_sha256": "e50b55257be5167539d7399502ebbb1d68058730bdb58f66989858a1cbec9239", "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `0d0646f041304862348977eb9b5921d6a85b7cd082963ebd66a1f35b00f47ad7`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 207.47257100003935, "baseline/context": 163.3830980000539, "baseline/help": 34.95000999998865, "baseline/version": 33.943129000022054, "candidate/cache": 205.28789400009373, "candidate/context": 163.57260899997073, "candidate/help": 36.463140000023486, "candidate/version": 36.67756599998029}, "passed": false, "reason": "validated", "report_sha256": "e50b55257be5167539d7399502ebbb1d68058730bdb58f66989858a1cbec9239", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/40975685731", "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `e50b55257be5167539d7399502ebbb1d68058730bdb58f66989858a1cbec9239`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 207.47257100003935, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 163.3830980000539, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 34.95000999998865, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 33.943129000022054, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 205.28789400009373, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 163.57260899997073, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 36.463140000023486, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 36.67756599998029, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2"}`.

## p01-6-adr19-initial-runtime-ci-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `b4944dad592419fb14caa386ca7efe208a7e67a76ed093dd4137ac627407d9d0`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-ci-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46125056, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 4.3838391880000245, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46780416, "pretransfer_peak_rss_bytes": 46125056, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52080640, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.07354297200004112, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 81920, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52162560, "pretransfer_peak_rss_bytes": 52162560, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46256128, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.093589824999981, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46911488, "pretransfer_peak_rss_bytes": 46256128, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [81920, 655360, 655360]}, "source_commit": "a7560ef72cf340027e8a7ccc943b9bede3025ec2", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-initial-runtime-final-body-cancel-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `b826cdcd1e47275f76d63ca5d1d6d8b34ad28c26e65cc400befa7e1dd8e0cbc3`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-body-cancel-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "cancelled_before_startup", "source_commit": "de312dcb95688a685089da8809e54478e6e99e68"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `f9171e4308eb7d5a50e9cb8e9bc13a14efa74c6d05afd3693bcf10cb7e3755be`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_acceptance_passed", "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `b5d00d7c3f54831c640bd9fb9c61a3be2b032592032c4d1b64550d5ca0941572`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `472412573df37af8e5990e3ea249213fec220058b1b5d164f32e8eeae0213252`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `2d49737dc8fb1f6db53ff94a2430539f1e2908daec38404718ee7ad335b991b5`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `4379d82161a762f33dfe463e1168ce0fbeecc01ee82f9ec47914f129e3160eef`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "805f8bd418847da6463408404a85675bdcb4173e", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "805f8bd418847da6463408404a85675bdcb4173e", "report_sha256": "2a8bb35dc9ad49ccca06464cbc6a121e62eb8d1c70f9cf29bf1be2604b931e24", "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `e5dc04c6d3ec9f01a71bf5d73785b51533eac6b7f678bae22eee3f7b8d5c8b81`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 218.42766500003563, "baseline/context": 172.57594800003062, "baseline/help": 35.662575000060315, "baseline/version": 35.00746199995319, "candidate/cache": 225.04251499992733, "candidate/context": 174.7218770000245, "candidate/help": 37.155496999957904, "candidate/version": 36.14659299989853}, "passed": false, "reason": "validated", "report_sha256": "2a8bb35dc9ad49ccca06464cbc6a121e62eb8d1c70f9cf29bf1be2604b931e24", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/40977307994", "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `2a8bb35dc9ad49ccca06464cbc6a121e62eb8d1c70f9cf29bf1be2604b931e24`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 218.42766500003563, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 172.57594800003062, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 35.662575000060315, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 35.00746199995319, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 225.04251499992733, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 174.7218770000245, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 37.155496999957904, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 36.14659299989853, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59"}`.

## p01-6-adr19-initial-runtime-final-doc-ci-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `8f93410abffb8b47bc8604df409c9c707bf78e0c55c7e017ceffed79d2f13a24`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-final-doc-ci-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46342144, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 4.4300471560000005, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46997504, "pretransfer_peak_rss_bytes": 46342144, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51957760, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.07211211100002402, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 20480, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51978240, "pretransfer_peak_rss_bytes": 51978240, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46194688, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.1352508200000102, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46850048, "pretransfer_peak_rss_bytes": 46194688, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [20480, 655360, 655360]}, "source_commit": "cf0016e7301fbfd3462e5f8ec9238d101c736e59", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-initial-runtime-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `9c8cb02368b1528a7b144ff85def2d2e60c55b95ac7d4162240ea89c91e244da`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0"}`.

## p01-6-adr19-initial-runtime-local-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `f9fee5e5372dd48d2f587083b4bb57948efa2dc6f99938daae9c462bc9dc9f61`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-local-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "local_source_acceptance_passed", "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0"}`.

## p01-6-adr19-initial-runtime-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `75ea3643c1c9c5fe920ef2fdce4b7531048e88704a075d895b71ce3bce5cb917`.
**Yerel arşiv:** `raw/p01-6-adr19-initial-runtime-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 50331648, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5834054159931839, "extra_rss_lower_bound_bytes": 131072, "extra_rss_upper_bound_bytes": 131072, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50462720, "pretransfer_peak_rss_bytes": 50331648, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57475072, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02598779182881117, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57475072, "pretransfer_peak_rss_bytes": 57475072, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49807360, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39665708295069635, "extra_rss_lower_bound_bytes": 163840, "extra_rss_upper_bound_bytes": 163840, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49971200, "pretransfer_peak_rss_bytes": 49807360, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 163840, 131072], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 163840, "upper_bound_bytes": [0, 163840, 131072]}, "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `8ce96db54b27d23993aa9081a016295d88fd7dc692e375c6106fb8be52a53fd5`.
**Yerel arşiv:** `raw/p01-6-adr19-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "47af27362f8f7f40bde72fb5d27ab6a0c05d93c6"}`.

## p01-6-adr19-local-acceptance

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `ad4ffbb6a6eeda4d663aa4582f5b0b1c9fd14cfdb026c7c658f3fbfed04b4996`.
**Yerel arşiv:** `raw/p01-6-adr19-local-acceptance.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "local_reference_passed_ci_pending", "source_commit": "47af27362f8f7f40bde72fb5d27ab6a0c05d93c6"}`.

## p01-6-adr19-sonar-ci-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `360f79a21a59ab55610723bc3f356349a1f2b50b616da2c57ed36730acca8c5d`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_acceptance_passed", "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f"}`.

## p01-6-adr19-sonar-ci-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `926ea303f711ac52cda0d2aa69eba9fc0be7cfdc42d29d57b18f310708f8611b`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f"}`.

## p01-6-adr19-sonar-ci-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f654515ce68f67411360b4aabd58b259a772ea84afe280e845dd373bd169374b`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f"}`.

## p01-6-adr19-sonar-ci-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `59660c6e0896240672a625022b0e4f2a0b8961d39e335879f0bd5f99c193880a`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f"}`.

## p01-6-adr19-sonar-ci-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `343ae079d80cae2731b517204104522026263e943dc6f4a42aa8a7ad44055dd8`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 239.16193900004146, "baseline/context": 140.0379949999433, "baseline/help": 33.914048000042385, "baseline/version": 31.626694999999927, "candidate/cache": 242.96074299991233, "candidate/context": 141.38604400000077, "candidate/help": 35.32905400004438, "candidate/version": 33.742546999974365}, "passed": false, "reason": "validated", "report_sha256": "2626a14fc1fb750a76308995b60b64375864895c1f0398cf150f47ec9da75f3f", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/40969743467", "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f"}`.

## p01-6-adr19-sonar-ci-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `2626a14fc1fb750a76308995b60b64375864895c1f0398cf150f47ec9da75f3f`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 239.16193900004146, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 140.0379949999433, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 33.914048000042385, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 31.626694999999927, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 242.96074299991233, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 141.38604400000077, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 35.32905400004438, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 33.742546999974365, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f"}`.

## p01-6-adr19-sonar-ci-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `f3877d3721c5472afaa76879b73500af5a66578273eb90c8d9fa4fca00707782`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-ci-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46043136, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.9985388270000612, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46698496, "pretransfer_peak_rss_bytes": 46043136, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52019200, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.048768659999950614, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 106496, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52125696, "pretransfer_peak_rss_bytes": 52125696, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46034944, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7599819440000601, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46690304, "pretransfer_peak_rss_bytes": 46034944, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [106496, 655360, 655360]}, "source_commit": "fef2bb2d947e9671ee5b44d07d22e0384b84e35f", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-sonar-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `9738f93132e8916f70bc465d45c081bacf68de4ca3cb0dc99c9fb1295dbeea65`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "dabf6e4eb1ade4227292f01cf52b6d5c74529ade"}`.

## p01-6-adr19-sonar-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `c53e16d2c7be4c733506833eb2c27fc1346e2ff4f9e0158419969a1e85707d18`.
**Yerel arşiv:** `raw/p01-6-adr19-sonar-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49741824, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.56825629202649, "extra_rss_lower_bound_bytes": 147456, "extra_rss_upper_bound_bytes": 147456, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49889280, "pretransfer_peak_rss_bytes": 49741824, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57409536, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02551116608083248, "extra_rss_lower_bound_bytes": 16384, "extra_rss_upper_bound_bytes": 16384, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57425920, "pretransfer_peak_rss_bytes": 57409536, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49758208, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.3966219581197947, "extra_rss_lower_bound_bytes": 49152, "extra_rss_upper_bound_bytes": 49152, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49807360, "pretransfer_peak_rss_bytes": 49758208, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [16384, 49152, 147456], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 131072, "upper_bound_bytes": [16384, 49152, 147456]}, "source_commit": "dabf6e4eb1ade4227292f01cf52b6d5c74529ade", "source_unchanged_during_measurement": true}`.

## p01-6-adr19-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `1af1ff8c713b74806d4becd85528118d7a399d955d604a5e0aa0d4867cb5865b`.
**Yerel arşiv:** `raw/p01-6-adr19-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49790976, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5760389170609415, "extra_rss_lower_bound_bytes": 360448, "extra_rss_upper_bound_bytes": 360448, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50151424, "pretransfer_peak_rss_bytes": 49790976, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57262080, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025268333964049816, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57262080, "pretransfer_peak_rss_bytes": 57262080, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 50380800, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.40751749998889863, "extra_rss_lower_bound_bytes": 442368, "extra_rss_upper_bound_bytes": 442368, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50823168, "pretransfer_peak_rss_bytes": 50380800, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 442368, 360448], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 442368, "upper_bound_bytes": [0, 442368, 360448]}, "source_commit": "47af27362f8f7f40bde72fb5d27ab6a0c05d93c6", "source_unchanged_during_measurement": true}`.

## p01-6-ci-initial-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `9f20bb706219cc7474f5ffed46ebc221a08b64955aa2bc708c77baf00a0c5331`.
**Yerel arşiv:** `raw/p01-6-ci-initial-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "failed", "source_commit": "bcb254d6f8497716f88dd6ef86263cfaa3ae6629"}`.

## p01-6-ci-initial-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `10dd752b835462d58a1d797b34ec06376124fcd3ff0d1a53cde2d07a103df8a2`.
**Yerel arşiv:** `raw/p01-6-ci-initial-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "bcb254d6f8497716f88dd6ef86263cfaa3ae6629"}`.

## p01-6-ci-initial-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `b5ec1807623ed92d98ab1d6dc19472dd8af753c0075ca9903a0bd15fdb3a56ba`.
**Yerel arşiv:** `raw/p01-6-ci-initial-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 339.1999120000264, "passed": false, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 217.62176100003217, "passed": false, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 206.47446800001035, "passed": false, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 228.581413000029, "passed": false, "samples": 30}}, "passed": false, "source_commit": "bcb254d6f8497716f88dd6ef86263cfaa3ae6629", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-ci-initial-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `3bee494d821330d43a47982f5450947bed5cc494a8c4c9e6bbbbb841f2496f7c`.
**Yerel arşiv:** `raw/p01-6-ci-initial-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 182.08849600000576, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 134.0182310000273, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 31.851750999976502, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 30.56855999994923, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 178.21753099997295, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 134.52435400000695, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 33.13983000003873, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 31.523250999953234, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-ci-native-reviewed-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `91df0d6a67b53100e9b9777fe82b6d66ce4d016ebb6d959291179d3df0c5f11d`.
**Yerel arşiv:** `raw/p01-6-ci-native-reviewed-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "passed", "source_commit": "63aa1f42c113c2dc522d9195cd942fe53fc8d60c"}`.

## p01-6-ci-native-reviewed-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `df11ed5c8977fe2bcffda1bafe262ab4dafbfd676b12459e1d288008b7394fdc`.
**Yerel arşiv:** `raw/p01-6-ci-native-reviewed-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "63aa1f42c113c2dc522d9195cd942fe53fc8d60c"}`.

## p01-6-ci-native-reviewed-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `c5e272ee748b09de5367dd41d54008d363f88d179178f33951c07345a917c937`.
**Yerel arşiv:** `raw/p01-6-ci-native-reviewed-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "63aa1f42c113c2dc522d9195cd942fe53fc8d60c"}`.

## p01-6-ci-native-reviewed-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `2c04535627a237de7f3e711e0c3d00ecc383e469a016e70671e09a33316f4372`.
**Yerel arşiv:** `raw/p01-6-ci-native-reviewed-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "63aa1f42c113c2dc522d9195cd942fe53fc8d60c"}`.

## p01-6-ci-native-reviewed-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `76fe14f64b080edd6768aaa8ead89db068e5f5445c3e6a68f9578281c811e017`.
**Yerel arşiv:** `raw/p01-6-ci-native-reviewed-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 168.3179750000363, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 133.93312000005153, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 30.96135900000263, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 29.680820000010044, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 168.27070699997648, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 135.62233999999762, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 32.792287999996006, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.93949800000928, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-ci-native-reviewed-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `4329a7a32cc66f88dc048238d2c6db1d1e3112dd2a024e282c7fb5da1d48e520`.
**Yerel arşiv:** `raw/p01-6-ci-native-reviewed-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46637056, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.968742943000052, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 47292416, "pretransfer_peak_rss_bytes": 46637056, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 53080064, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.053998559000035584, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 53080064, "pretransfer_peak_rss_bytes": 53080064, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46243840, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7476274630000148, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46899200, "pretransfer_peak_rss_bytes": 46243840, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "63aa1f42c113c2dc522d9195cd942fe53fc8d60c", "source_unchanged_during_measurement": true}`.

## p01-6-ci-reviewed-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `0dc2dd7e06ecf141b2c39e42de472e2f6fc27d5e79d288a6c896b149cbc843a2`.
**Yerel arşiv:** `raw/p01-6-ci-reviewed-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "passed", "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd"}`.

## p01-6-ci-reviewed-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `d79a5c62edaa922771209fb57d8460bd7a8d77ad84262bd76b403195a20edc51`.
**Yerel arşiv:** `raw/p01-6-ci-reviewed-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd"}`.

## p01-6-ci-reviewed-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `0be36b4fd82057b272592eb9aba376dfaf66a7dd55a8fdb843b905beeec575fb`.
**Yerel arşiv:** `raw/p01-6-ci-reviewed-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd"}`.

## p01-6-ci-reviewed-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `9e9b8773f14a118248cd5bea792df66522b19ba1f45a1e6561704672962517bf`.
**Yerel arşiv:** `raw/p01-6-ci-reviewed-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd"}`.

## p01-6-ci-reviewed-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `179f9edca8ddd8ad88f20fbd1e3b6e6ab631be309a2e4f313126662359efe179`.
**Yerel arşiv:** `raw/p01-6-ci-reviewed-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 146.15893299998106, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 112.88636500000848, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.770967000028122, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 25.68236400003343, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 153.99202800000467, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 157.1354710000037, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 30.732112000009693, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 25.588882999954876, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-ci-reviewed-stream

**Tür:** `raw_stream_budget_v1`.
**Özgün JSON SHA-256:** `a22a99f52a9e87dc1821d69889d5f5da0bb7855694d96ec9b0f85c6890ab9eba`.
**Yerel arşiv:** `raw/p01-6-ci-reviewed-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v1", "measurements": {"1024MiB": {"baseline_rss_bytes": 45318144, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.2258955419999893, "extra_rss_bytes": 1179648, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46497792, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52035584, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.035955392000005304, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52035584, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 44961792, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.5757685410000022, "extra_rss_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45617152, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "fresh client process high-water maxRSS after imports, source verification and fixed 32KiB TLS warmup; not instantaneous RSS", "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_native_unit": "KiB", "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd", "source_unchanged_during_measurement": true}`.

## p01-6-development-merge-ci-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `0e53654e411e8ba9b7558225a9db43c11c394b791a91ad0b71d0a836fd1469ca`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "development_merge_acceptance_passed", "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `c4f09778948c9831632e913349da8f69580e9b0e8ea96baa897bf0326924f8f1`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `8dff7888a0cda16a31b173b291de76ee5e0f1e80dc5e4f4cda70b5e347efb2c6`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `bd816d88f3ea9ebdd8cb19f472ccc285159330f68d3f35686fdfef4b011dde6d`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `453c4673c30cb080cd931ed1d9ad47fffddc1ada42cf7ffe7cf1033dd1c878c8`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "805f8bd418847da6463408404a85675bdcb4173e", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "805f8bd418847da6463408404a85675bdcb4173e", "report_sha256": "5871ca34ae6a8f3d28ef46e5b2f5e984c7a2664ba02bb5ffa216133f7a4f82ec", "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `b4c869daad9f691ea5836703d7686ad19f5ae3951eff7096d4f2948197cdab64`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 217.92387300001792, "baseline/context": 180.22763599992686, "baseline/help": 39.07224200008841, "baseline/version": 38.39724199997363, "candidate/cache": 218.16122200004884, "candidate/context": 179.7994959999869, "candidate/help": 40.41636700003437, "candidate/version": 39.62697199995091}, "passed": false, "reason": "validated", "report_sha256": "5871ca34ae6a8f3d28ef46e5b2f5e984c7a2664ba02bb5ffa216133f7a4f82ec", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41005731985", "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `5871ca34ae6a8f3d28ef46e5b2f5e984c7a2664ba02bb5ffa216133f7a4f82ec`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 217.92387300001792, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 180.22763599992686, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.07224200008841, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.39724199997363, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 218.16122200004884, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 179.7994959999869, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 40.41636700003437, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 39.62697199995091, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027"}`.

## p01-6-development-merge-ci-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `51d4ba5b863d5d6745b42809d8b0ce24861b045a04d1973cea6d42d29fd899b9`.
**Yerel arşiv:** `raw/p01-6-development-merge-ci-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45522944, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.209033621999993, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46178304, "pretransfer_peak_rss_bytes": 45522944, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51175424, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08543226799997683, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 401408, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51576832, "pretransfer_peak_rss_bytes": 51576832, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45490176, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.2807533870000043, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46145536, "pretransfer_peak_rss_bytes": 45490176, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [401408, 655360, 655360]}, "source_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "source_unchanged_during_measurement": true}`.

## p01-6-final-cli-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `7e939685187011ad40e0414b742f410957ac65571f0bc43bcf6574117d1bb2b4`.
**Yerel arşiv:** `raw/p01-6-final-cli-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "30a3e28260df6bb249226dfd6641475b5ab98d74"}`.

## p01-6-final-cli-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `86ef3e81c97029be1aec6b48670b80031e23f56a64a73dbc1d6e295d21eb914b`.
**Yerel arşiv:** `raw/p01-6-final-cli-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 141.66941680014133, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 87.68395893275738, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 31.626584008336067, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 37.95841685496271, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 141.85712486505508, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 90.6360000371933, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 33.778417157009244, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 33.636749954894185, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-final-cli-stream

**Tür:** `raw_stream_budget_v1`.
**Özgün JSON SHA-256:** `347f324f8508990fbb4c1af2087863db4b13eb3a71f4b8c6a73c9006dabbc875`.
**Yerel arşiv:** `raw/p01-6-final-cli-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v1", "measurements": {"1024MiB": {"baseline_rss_bytes": 50036736, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.205894625047222, "extra_rss_bytes": 622592, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50659328, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57294848, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.03551541594788432, "extra_rss_bytes": 131072, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57425920, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49922048, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.5081543331034482, "extra_rss_bytes": 688128, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50610176, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "fresh client process high-water maxRSS after imports, source verification and fixed 32KiB TLS warmup; not instantaneous RSS", "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_native_unit": "bytes", "source_commit": "30a3e28260df6bb249226dfd6641475b5ab98d74", "source_unchanged_during_measurement": true}`.

## p01-6-final-doc-ci-failed-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `31b69ce4087028fcd3c8370723fd1a684729369bdd931cc332ebed4cfbcd3819`.
**Yerel arşiv:** `raw/p01-6-final-doc-ci-failed-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "failed", "source_commit": "f9eb21586acce23ef53176464093547a5cb027e3"}`.

## p01-6-final-doc-startup-failed

**Tür:** `startup`.
**Özgün JSON SHA-256:** `b215cbe6805e213d24ab28ed64c32f04c9b7479454d730fbfabf98069d77e057`.
**Yerel arşiv:** `raw/p01-6-final-doc-startup-failed.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 218.99762700002157, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 182.2675270000218, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.28417600002376, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 37.13054000002103, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 232.64124400009223, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 169.5197569999891, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 40.90816600000835, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 47.50473899991903, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-final-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `465716b10a46307d61436862105af87addb2fd9c1aca7ec0bdce16e578f7f840`.
**Yerel arşiv:** `raw/p01-6-final-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "bcb254d6f8497716f88dd6ef86263cfaa3ae6629"}`.

## p01-6-final-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `be1852d6bdf01f8f25cf6325692ef100a52e2d3681e3ae35183352cf2005c638`.
**Yerel arşiv:** `raw/p01-6-final-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 156.72024991363287, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 107.40312514826655, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 109.32820802554488, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 110.45695887878537, "passed": true, "samples": 30}}, "passed": true, "source_commit": "bcb254d6f8497716f88dd6ef86263cfaa3ae6629", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-final-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `d60bfc4e8dd93ed7fe27b629a3cbb1b6f80736938dc954f82e4e5f5830288cee`.
**Yerel arşiv:** `raw/p01-6-final-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 3881.899125, "outcomes": {"ok": 24}, "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd"}`.

## p01-6-final-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `65b803f27c7af1b141e5e4f89b2a8f3d9e324dc9893620e4a69a789b9ba7c5a6`.
**Yerel arşiv:** `raw/p01-6-final-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4447.145167, "outcomes": {"ok": 27}, "source_commit": "3d4f341569af72176b0bb0625e22b12bed1633bd"}`.

## p01-6-final-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `8a0c3995f4abac127fbc70b97b2d1c84aa42287edb66619237d6769ea6a53475`.
**Yerel arşiv:** `raw/p01-6-final-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 132.48687493614852, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 85.54279198870063, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.417792050167918, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.609957959502935, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 124.19333285652101, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 79.72541591152549, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.609583033248782, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.311665980145335, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-final-stream

**Tür:** `raw_stream_budget_v1`.
**Özgün JSON SHA-256:** `35baa25405bde4b6962e3d08382758afd399632594b6fc40d60a8ecdc1a00c87`.
**Yerel arşiv:** `raw/p01-6-final-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v1", "measurements": {"1024MiB": {"baseline_rss_bytes": 49725440, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5951262079179287, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49725440, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57344000, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.0260968750808388, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57344000, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 50003968, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39860679185949266, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50003968, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "fresh client process high-water maxRSS after imports, source verification and fixed 32KiB TLS warmup; not instantaneous RSS", "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_native_unit": "bytes", "source_commit": "bcb254d6f8497716f88dd6ef86263cfaa3ae6629", "source_unchanged_during_measurement": true}`.

## p01-6-native-counter-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `03fb0546556eff8bbabcca0768c7d4b25116a6a2231153d93baa2d5b444a2acb`.
**Yerel arşiv:** `raw/p01-6-native-counter-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "2551a1f129255bcb31559e281cbc20e8cbd1053d"}`.

## p01-6-native-counter-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `98f1be55a4d2221eeaf4b23fa2ae598158e1527bc75f6087caadec887703d762`.
**Yerel arşiv:** `raw/p01-6-native-counter-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 122.80900008045137, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 78.52554181590676, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.923334062099457, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.410750018432736, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 133.69562500156462, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 79.0805839933455, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 26.98508300818503, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.388709105551243, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-native-counter-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `2b1a00e4218b9e30361a725f2f87ce51e1add33747f9daf75f3d5463ba10f050`.
**Yerel arşiv:** `raw/p01-6-native-counter-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49790976, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5638667501043528, "extra_rss_lower_bound_bytes": 49152, "extra_rss_upper_bound_bytes": 49152, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49840128, "pretransfer_peak_rss_bytes": 49790976, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57802752, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.026770208030939102, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57802752, "pretransfer_peak_rss_bytes": 57802752, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49840128, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.3962404588237405, "extra_rss_lower_bound_bytes": 49152, "extra_rss_upper_bound_bytes": 49152, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49889280, "pretransfer_peak_rss_bytes": 49840128, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 49152, 49152], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 49152, "upper_bound_bytes": [0, 49152, 49152]}, "source_commit": "2551a1f129255bcb31559e281cbc20e8cbd1053d", "source_unchanged_during_measurement": true}`.

## p01-6-pr-review-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `c6c5b9812417f04661f37ab934e9fb13ca2ccc9aa8ac47c8d75ffe8dac7cd1cc`.
**Yerel arşiv:** `raw/p01-6-pr-review-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "fca5b1403606343eac865572140ed45869e33a45"}`.

## p01-6-pr-review-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `722236ea272a795c01d0e7900f64a48603591c3c49d7807c3ff200af4e82e4f9`.
**Yerel arşiv:** `raw/p01-6-pr-review-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 113.49099990911782, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 98.1603330001235, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 28.015749994665384, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.584333946928382, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 122.68837494775653, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 92.78499986976385, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 33.82795793004334, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.007749976590276, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-pr-review-stream

**Tür:** `raw_stream_budget_v1`.
**Özgün JSON SHA-256:** `12caa14cfdd76e9c9f82f74ac54a1c0288b886a5b0120b8c01f4001a02ec361d`.
**Yerel arşiv:** `raw/p01-6-pr-review-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v1", "measurements": {"1024MiB": {"baseline_rss_bytes": 49528832, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.574452041182667, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49528832, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57245696, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025732541922479868, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57245696, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49823744, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4007510831579566, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49823744, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "fresh client process high-water maxRSS after imports, source verification and fixed 32KiB TLS warmup; not instantaneous RSS", "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_native_unit": "bytes", "source_commit": "fca5b1403606343eac865572140ed45869e33a45", "source_unchanged_during_measurement": true}`.

## p01-6-pre-adr19-ci-failed-checkpoint

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `f21746c5ed2d9cabd625c92279e47c06ba2172120db12c713723e39298b8f7ca`.
**Yerel arşiv:** `raw/p01-6-pre-adr19-ci-failed-checkpoint.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "failed", "source_commit": "b3249e4dfbaa49608e22cfe9432183cc20c10890"}`.

## p01-6-pre-adr19-startup-failed

**Tür:** `startup`.
**Özgün JSON SHA-256:** `670e08368ead54b78583fbc6ea9890428ba7eebb3f84ac740c36dc086fe6ad3a`.
**Yerel arşiv:** `raw/p01-6-pre-adr19-startup-failed.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 246.64352100000997, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 190.53115400004117, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 40.96158100003322, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 40.549567999960345, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 241.751726000075, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 188.18413999997574, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 42.81950799997958, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 41.846262000035495, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-reference-jobs-adr19-initial-runtime

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `eaccdea384b6f4e6438d5ebe8a0f6cfd954177ed538defcad184c89f36275243`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-adr19-initial-runtime.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 185.50462485291064, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 106.9726669229567, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 129.19966713525355, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 118.17104206420481, "passed": true, "samples": 30}}, "passed": true, "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-adr19-sonar

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `1c63440529828b5a823c070c698c964ca8a7eb1dea6e08f54d9900a8da7f3989`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-adr19-sonar.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 169.3803749512881, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 103.70924999006093, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 111.532999901101, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 104.47479202412069, "passed": true, "samples": 30}}, "passed": true, "source_commit": "dabf6e4eb1ade4227292f01cf52b6d5c74529ade", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-adr19

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `c34070b6d4d0a479bb5284228bd8da9a4098edb8a9de85999ac03908b4bfde93`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-adr19.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 153.68700004182756, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 105.60658294707537, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 101.67037509381771, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 100.34279199317098, "passed": true, "samples": 30}}, "passed": true, "source_commit": "47af27362f8f7f40bde72fb5d27ab6a0c05d93c6", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-final

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `965b1bebf793d322a8e768a0c53a0d2f26010c0314544dad8bb3af6b20bfe59e`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-final.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 186.87270814552903, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 140.04766615107656, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 127.5727089960128, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 126.58470892347395, "passed": true, "samples": 30}}, "passed": true, "source_commit": "30a3e28260df6bb249226dfd6641475b5ab98d74", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-idle

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `c861b321a8c1dc0f8740e756c33f7f1e2a97e869672d2fb7877672116a4306d3`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-idle.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 160.01574997790158, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 111.04537500068545, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 100.32166610471904, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 104.82287500053644, "passed": true, "samples": 30}}, "passed": true, "source_commit": "c3d43ea970127fb52781fe79d06fc352bbe2a774", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-linux-harness

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `1844c41284da21f4f60c3a4abd0f3368628c7896d51148c6fd48735469bd7bbb`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-linux-harness.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 159.97266699559987, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 111.6408749949187, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 106.99249990284443, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 120.94733398407698, "passed": true, "samples": 30}}, "passed": true, "source_commit": "2551a1f129255bcb31559e281cbc20e8cbd1053d", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-pr-review

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `7e556e3e46a8da375b9097ab1d60809a9b4b1388f318e1a05777d512a7843b64`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-pr-review.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 143.84491695091128, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 104.91274995729327, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 105.30758299864829, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 98.27445819973946, "passed": true, "samples": 30}}, "passed": true, "source_commit": "fca5b1403606343eac865572140ed45869e33a45", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-rss-lint

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `6452a030de06ddc790b9f13336d70c854cf3db8672153413f2b0602701eb95fb`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-rss-lint.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 156.1163750011474, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 108.59099985100329, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 118.86104103177786, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 108.68079215288162, "passed": true, "samples": 30}}, "passed": true, "source_commit": "fbcbb32d4d6feb001656d09699ac6a86c33f8351", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs-rss-v2

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `0d93ee2b7ce424bbe3b74e8f4607cd8b503fd46b1a2f1635422ed679e3bfca35`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-rss-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 144.06812516972423, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 121.24808295629919, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 105.61716719530523, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 98.26329117640853, "passed": true, "samples": 30}}, "passed": true, "source_commit": "14d6a9bf26debdd8eee22a3984b51505c874ba6a", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `79483408be518b908bc5f77e4d65509a05f0d0e859bc4210cdf49890ac1923bb`.
**Yerel arşiv:** `raw/p01-6-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 207.63795892708004, "passed": false, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 111.68862506747246, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 106.78958310745656, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 191.42820918932557, "passed": true, "samples": 30}}, "passed": false, "source_commit": "55dbe64bf9f3e5944d89ddbd71caeadbdd2bf50e", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-startup-adr19-initial-runtime

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `9150e50592ea68b3338fdbb89aae83c345cfe65fd35e29561b92dfdf2335ae98`.
**Yerel arşiv:** `raw/p01-6-reference-startup-adr19-initial-runtime.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 131.2064160592854, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 79.85595799982548, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.83708381280303, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.056042147800326, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 114.23812503926456, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 73.80037498660386, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 26.79387480020523, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.71658298559487, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "e5846ceb6cc7e117db103e33603b9c65586531b0"}`.

## p01-6-reference-startup-adr19-sonar

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `a447cab1fe2f688d0a90a92f3b31a403071970d7529e84a182e9fa4b7ab7af14`.
**Yerel arşiv:** `raw/p01-6-reference-startup-adr19-sonar.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 118.64699982106686, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 73.05766688659787, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.339209146797657, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 21.775875007733703, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 120.16900000162423, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 74.21233295463026, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.889084044843912, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.559499833732843, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "dabf6e4eb1ade4227292f01cf52b6d5c74529ade"}`.

## p01-6-reference-startup-adr19

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `b8f1148cfdf5e9d756d27c1079b1240a24e5c9f51885d85258b861d105bd1cdd`.
**Yerel arşiv:** `raw/p01-6-reference-startup-adr19.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 197.40433408878744, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 83.1789590884, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.612749995663762, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.23383286036551, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 149.96633306145668, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 74.4366250000894, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 25.15420806594193, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.4957091268152, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "47af27362f8f7f40bde72fb5d27ab6a0c05d93c6"}`.

## p01-6-reviewed-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `55248d69f313da1bfe1a314efc089032eda42a4bc5e92e59652401b29b682eb7`.
**Yerel arşiv:** `raw/p01-6-reviewed-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "55dbe64bf9f3e5944d89ddbd71caeadbdd2bf50e"}`.

## p01-6-reviewed-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `9741c0288e3a48af2127f0e2af7a0113d151178056793519df6e697eab072428`.
**Yerel arşiv:** `raw/p01-6-reviewed-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 124.84737485647202, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 74.4534160476178, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.844291921705008, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.96149986796081, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 116.71808292157948, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 74.90575010888278, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.518541991710663, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.866667015478015, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-reviewed-stream

**Tür:** `raw_stream_budget_v1`.
**Özgün JSON SHA-256:** `cddea31167bbeb8d31c02f74a714f7b72044161f85ba0442a6f20d49a52b8903`.
**Yerel arşiv:** `raw/p01-6-reviewed-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v1", "measurements": {"1024MiB": {"baseline_rss_bytes": 49414144, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5931844578590244, "extra_rss_bytes": 704512, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50118656, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57294848, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025762417120859027, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57294848, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49643520, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39515329198911786, "extra_rss_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49643520, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "fresh client process high-water maxRSS after imports, source verification and fixed 32KiB TLS warmup; not instantaneous RSS", "rss_method": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_native_unit": "bytes", "source_commit": "c3d43ea970127fb52781fe79d06fc352bbe2a774", "source_unchanged_during_measurement": true}`.

## p01-6-rss-lint-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `de2780167081755991a361ce697941d8378d7967c0092354a3b6ab69a3f71db5`.
**Yerel arşiv:** `raw/p01-6-rss-lint-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49823744, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.590270249871537, "extra_rss_lower_bound_bytes": 1097728, "extra_rss_upper_bound_bytes": 1097728, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50921472, "pretransfer_peak_rss_bytes": 49823744, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50184192, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.026803583139553666, "extra_rss_lower_bound_bytes": 49152, "extra_rss_upper_bound_bytes": 49152, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50233344, "pretransfer_peak_rss_bytes": 50184192, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49823744, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.401059958152473, "extra_rss_lower_bound_bytes": 114688, "extra_rss_upper_bound_bytes": 114688, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49938432, "pretransfer_peak_rss_bytes": 49823744, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [49152, 114688, 1097728], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1048576, "upper_bound_bytes": [49152, 114688, 1097728]}, "source_commit": "fbcbb32d4d6feb001656d09699ac6a86c33f8351", "source_unchanged_during_measurement": true}`.

## p01-6-user-review-ci-initial-failure

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `19e4d9a29642da3a583d42fbf4abdd994484742aed8fb5463cd0b36b2c73cf3a`.
**Yerel arşiv:** `raw/p01-6-user-review-ci-initial-failure.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "failed", "source_commit": "68fe43da7b3c6098ad2e0fc00d8ac81881c16c9f"}`.

## p01-6-user-review-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `382abe33272c54e083f4b41d654bcc0f22d42c6743f2f7adf434c95cd1e564fc`.
**Yerel arşiv:** `raw/p01-6-user-review-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "14d6a9bf26debdd8eee22a3984b51505c874ba6a"}`.

## p01-6-user-review-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `b0e45e157d9f93a66f317a545a4376924ddd2bd9bf4a9d93d1d0140c2d60a584`.
**Yerel arşiv:** `raw/p01-6-user-review-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 112.20937501639128, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 75.10383310727775, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.940624997019768, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.535833064466715, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 111.8834160733968, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 81.0802080668509, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.231041971594095, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.05729198269546, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-6-user-review-stream-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `7b73f505eb4e81ca08a00c299cc2be869b06ef1feb076254c5a665208e2ca9af`.
**Yerel arşiv:** `raw/p01-6-user-review-stream-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49790976, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6364617920480669, "extra_rss_lower_bound_bytes": 1261568, "extra_rss_upper_bound_bytes": 1261568, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51052544, "pretransfer_peak_rss_bytes": 49790976, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57360384, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02599691692739725, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57360384, "pretransfer_peak_rss_bytes": 57360384, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49790976, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39485416701063514, "extra_rss_lower_bound_bytes": 180224, "extra_rss_upper_bound_bytes": 180224, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49971200, "pretransfer_peak_rss_bytes": 49790976, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 180224, 1261568], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1261568, "upper_bound_bytes": [0, 180224, 1261568]}, "source_commit": "14d6a9bf26debdd8eee22a3984b51505c874ba6a", "source_unchanged_during_measurement": true}`.

## p02-0-delivery-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `73a4419f9769ecf7f336b8aca661cf15a293a8732c7fc5ca3d8913d785de45d6`.
**Yerel arşiv:** `raw/p02-0-delivery-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "fba5c510b1f64af02bb36d1a6eee204da9eb217c"}`.

## p02-0-delivery-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `40422a5cbf7ac2953765948816b7292a4487e9bca0e1330e7526866296d9f9b9`.
**Yerel arşiv:** `raw/p02-0-delivery-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 142.19325012527406, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 107.67145920544863, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 122.62029107660055, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 100.90670897625387, "passed": true, "samples": 30}}, "passed": true, "source_commit": "bfd43a80de0c7ad9492005185554196646ca6f5c", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-delivery-reference-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `20457d4da9ef6e2bc64aab05329cfad270a8d0615ce9e601333dceb7363d8974`.
**Yerel arşiv:** `raw/p02-0-delivery-reference-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 115.40675000287592, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 74.19116701930761, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 22.873707814142108, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.232958978042006, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 117.59837483987212, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 75.35200007259846, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.530124919489026, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.622999968007207, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "bfd43a80de0c7ad9492005185554196646ca6f5c"}`.

## p02-0-final-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `b85d2818b61f02dd0a05b9629bc74844c2332d10062f2c027a99a2f23610c006`.
**Yerel arşiv:** `raw/p02-0-final-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "15aa8a1635ef9475deedd3fac6cdfad6f8f29010"}`.

## p02-0-final-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `445e6adb0f057693bbaa432875e324246f3e602bebf8df831f313a6c8f8a6707`.
**Yerel arşiv:** `raw/p02-0-final-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 151.33233414962888, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 110.7819159515202, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 107.84574993886054, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 111.42391595058143, "passed": true, "samples": 30}}, "passed": true, "source_commit": "15aa8a1635ef9475deedd3fac6cdfad6f8f29010", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-final-reference-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `f9938ee45e68a16d476e0613d0ea661e4320f53a1a7362dbc47813513feacd9f`.
**Yerel arşiv:** `raw/p02-0-final-reference-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 115.93499989248812, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 83.21850001811981, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.114625062793493, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.978165816515684, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 118.84095915593207, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 80.85383381694555, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.976624943315983, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.87583302333951, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "15aa8a1635ef9475deedd3fac6cdfad6f8f29010"}`.

## p02-0-final-reference-v2-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `3b6e8da93bad4e84fbad8150c8946bc5902fb91e4970f598714162f64e7c0a70`.
**Yerel arşiv:** `raw/p02-0-final-reference-v2-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 169.24879211001098, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 116.97975010611117, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 132.65449996106327, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 151.06858289800584, "passed": true, "samples": 30}}, "passed": true, "source_commit": "abc862e6be34080346209ebb35da78cf897b50b1", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-final-reference-v2-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `214297667c0ef68ddb5dc50ad160d5cd41da6b912b4ce901ec9344376fa1d804`.
**Yerel arşiv:** `raw/p02-0-final-reference-v2-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 128.03649995476007, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 94.47837504558265, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 28.628707863390446, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 29.118250124156475, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 160.78479192219675, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 90.64137493260205, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.778791893273592, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.467333970591426, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "abc862e6be34080346209ebb35da78cf897b50b1"}`.

## p02-0-final-v2-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `50c4a204e5e4361daeb5ee6e3fc6b3e0812d00d5f5c2fc586f4b6b08ee3056b5`.
**Yerel arşiv:** `raw/p02-0-final-v2-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "0d0f0d8759d8863a2963124b33b4843e948b79b4"}`.

## p02-0-llm-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `94acb18ebc58e63019c0c2fa75c55add9fc8458a44a670b7d0ada484ff43d83a`.
**Yerel arşiv:** `raw/p02-0-llm-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "0e0d2b747d23976c46f196b02266a3ba1f6d6d8a"}`.

## p02-0-llm-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `60a70e0cddf6b7544a66eac95b84eec2068c050742b5424003810c3e7a11cc6f`.
**Yerel arşiv:** `raw/p02-0-llm-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 172.38770797848701, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 137.5950421206653, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 116.63170903921127, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 140.4238329268992, "passed": true, "samples": 30}}, "passed": true, "source_commit": "0e0d2b747d23976c46f196b02266a3ba1f6d6d8a", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-llm-reference-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `f24239c217eb510444538843fe0e49e9d0678286a0e595d87685577441af0353`.
**Yerel arşiv:** `raw/p02-0-llm-reference-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 117.95975011773407, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 84.73012503236532, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 34.15016597136855, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 27.91529195383191, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 119.36179199256003, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 87.10941718891263, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 30.81095893867314, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 27.6138330809772, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "0e0d2b747d23976c46f196b02266a3ba1f6d6d8a"}`.

## p02-0-platform-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `c7a2b29f4de3a49d240ab15f8a5383fdfe45fa7ed78dcaa3c2f46924211fafae`.
**Yerel arşiv:** `raw/p02-0-platform-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "0b05a64178fcae03a846fff5a9f68a36fa032005"}`.

## p02-0-platform-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `2dfd34b6140fbdca249139aa41087a772a357747cb50f583755434680699638f`.
**Yerel arşiv:** `raw/p02-0-platform-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 155.28249996714294, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 124.9817090574652, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 117.4791248049587, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 113.09454101137817, "passed": true, "samples": 30}}, "passed": true, "source_commit": "0b05a64178fcae03a846fff5a9f68a36fa032005", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-platform-reference-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `c22174a6a9658b10e54ebfe5cfd9c1668d3b5187c3c2e49153de1533176f1329`.
**Yerel arşiv:** `raw/p02-0-platform-reference-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 126.5594158321619, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 92.97679201699793, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.29283396527171, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 31.814791029319167, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 127.98366602510214, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 89.2820421140641, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 27.385124936699867, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 29.39833397977054, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "0b05a64178fcae03a846fff5a9f68a36fa032005"}`.

## p02-0-pr12-closure-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `525ed63329100c6992c511726758bcb44da800e420cc27d380254fbc9af62622`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "04e41d9e96e4f70b0f34b5dd16c2cb7e9cb9be9c458fb7928aa158c5d33dfd0d", "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e"}`.

## p02-0-pr12-closure-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `f7f994e05e4583d175ab98904fc2d663a71de2cccd6e103e6809dd9d5b2af24e`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 142.87774299998546, "baseline/context": 126.83820500001275, "baseline/help": 26.86620099996162, "baseline/version": 26.799620000019786, "candidate/cache": 144.3631040000355, "candidate/context": 125.65642800007026, "candidate/help": 30.457597000008718, "candidate/version": 27.151290000006156}, "passed": true, "reason": "validated", "report_sha256": "04e41d9e96e4f70b0f34b5dd16c2cb7e9cb9be9c458fb7928aa158c5d33dfd0d", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41282647619", "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e"}`.

## p02-0-pr12-closure-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `04e41d9e96e4f70b0f34b5dd16c2cb7e9cb9be9c458fb7928aa158c5d33dfd0d`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 142.87774299998546, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 126.83820500001275, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.86620099996162, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 26.799620000019786, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 144.3631040000355, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 125.65642800007026, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 30.457597000008718, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 27.151290000006156, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e"}`.

## p02-0-pr12-closure-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `11482d4ccf72db726c8617eb6677b925052b3b92a4dca455fa2e738c0a43af34`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46170112, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.318178909999915, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46694400, "pretransfer_peak_rss_bytes": 46170112, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52723712, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.036148883000009846, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52723712, "pretransfer_peak_rss_bytes": 52723712, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46022656, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.5467821790000471, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46678016, "pretransfer_peak_rss_bytes": 46022656, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 524288]}, "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-closure-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `89c7b2058e174434c90c5c518559d3977c3534ce64ed2634d8e82975d8d09de0`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e"}`.

## p02-0-pr12-closure-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f7d7f9eaf6ff982f19782ea6d79abdfc49ed1e2d95c92dc7caf3061fdbb3c4fe`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e"}`.

## p02-0-pr12-closure-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `d54a72c13451b5c58f4a2afef18117163fb066401bd2b0f1c587ef43d1e94797`.
**Yerel arşiv:** `raw/p02-0-pr12-closure-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "5e09657d9cf152258dc2fb085a97ea444f3b983e"}`.

## p02-0-pr12-delivery-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `a5528200e443acc8fe62c9c5afa9c47d3a03130488924fb4ee2b998ae412c7cc`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "0c0cffe776a5d009763a236fcda38ed4cbd549ecdcaa3b1bcb05f51ebdfeefe8", "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012"}`.

## p02-0-pr12-delivery-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `92a3b1ae25ada2e0226b897bca44f062a801d3a95de5e2a2289451d4383b5cc8`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 226.711851999994, "baseline/context": 178.84075900008156, "baseline/help": 40.10546899996825, "baseline/version": 38.947315000086746, "candidate/cache": 225.74131600003966, "candidate/context": 182.15268900007686, "candidate/help": 40.712246999987656, "candidate/version": 39.37228500001311}, "passed": false, "reason": "validated", "report_sha256": "0c0cffe776a5d009763a236fcda38ed4cbd549ecdcaa3b1bcb05f51ebdfeefe8", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41280791049", "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012"}`.

## p02-0-pr12-delivery-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `0c0cffe776a5d009763a236fcda38ed4cbd549ecdcaa3b1bcb05f51ebdfeefe8`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 226.711851999994, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 178.84075900008156, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 40.10546899996825, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.947315000086746, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 225.74131600003966, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 182.15268900007686, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 40.712246999987656, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 39.37228500001311, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012"}`.

## p02-0-pr12-delivery-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `a7a2f3914b5d1b07e32671b7f25a11a9b3a6d25b3da0580ea94c1fa7a8d326ed`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45514752, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.133175181999945, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46170112, "pretransfer_peak_rss_bytes": 45514752, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52092928, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08401612900001965, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52092928, "pretransfer_peak_rss_bytes": 52092928, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45506560, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3009130340000183, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46161920, "pretransfer_peak_rss_bytes": 45506560, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-delivery-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `1d3ac64684a3cbfb06f5477cb9a3e33a3bb754e41aea9701e4805dc02fd2ca14`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012"}`.

## p02-0-pr12-delivery-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `dbb6c605a09520e791c2de2618075fb4182c6ebd260a5e759f416d23dd3f4bef`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012"}`.

## p02-0-pr12-delivery-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `61d3d032d75c0d2837af9cd91d8f682f649d2078eb0cb6ac1696f315a5e5311e`.
**Yerel arşiv:** `raw/p02-0-pr12-delivery-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "ba45a2e8b019632d0b48a9af5034b93c9ceb1012"}`.

## p02-0-pr12-development-merge-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `10f4884fc869823446f8ace4f78e29100db51ae9cd6b779ac4d932a8f6515a3a`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "7f3915bdfc4daaa3726616681807e7adcb81ec5eed36e56e05d7c1b7603231c9", "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07"}`.

## p02-0-pr12-development-merge-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `563bd608d25c5aea8a299514917932ba91a644cce5b32f83039c7df3e8f2d20c`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 217.77716300005068, "baseline/context": 168.38031800000408, "baseline/help": 39.305651000063335, "baseline/version": 38.17833300001894, "candidate/cache": 216.7609260000063, "candidate/context": 169.5322100000567, "candidate/help": 39.29238299997451, "candidate/version": 37.700647999940884}, "passed": false, "reason": "validated", "report_sha256": "7f3915bdfc4daaa3726616681807e7adcb81ec5eed36e56e05d7c1b7603231c9", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41337826876", "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07"}`.

## p02-0-pr12-development-merge-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `7f3915bdfc4daaa3726616681807e7adcb81ec5eed36e56e05d7c1b7603231c9`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 217.77716300005068, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 168.38031800000408, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.305651000063335, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.17833300001894, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 216.7609260000063, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 169.5322100000567, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 39.29238299997451, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 37.700647999940884, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07"}`.

## p02-0-pr12-development-merge-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `5c5fb85e0ffcc25231ee37e0f79bdf21ec300c5be0f6391d2a0d0eb3681e7588`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45957120, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.1198697290000155, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46612480, "pretransfer_peak_rss_bytes": 45957120, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51159040, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08519950000004428, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 876544, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52035584, "pretransfer_peak_rss_bytes": 52035584, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45846528, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3022562559999642, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46501888, "pretransfer_peak_rss_bytes": 45846528, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [876544, 655360, 655360]}, "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-development-merge-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `5d96f5d18e8069765c151b4e9b89fb1b08b8d3a79f1db92b3b63f9370abed729`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07"}`.

## p02-0-pr12-development-merge-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `35a7b3ee2c687076b5fe4ae85cc4576eb3b33e7ae40f3417d4e8314d3e0cc784`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07"}`.

## p02-0-pr12-development-merge-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `99b3fe93632cb0e8647fb014cdbd48d54bdde494e471c9eea40d3b02921816db`.
**Yerel arşiv:** `raw/p02-0-pr12-development-merge-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07"}`.

## p02-0-pr12-doc-edit-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `097e173a19de92e382869d00753206b6c421921a569ece083d36adc2743c3a80`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "0349f36f8043284f682cd93774550c7429e1009c804114cf9717068e2c1492de", "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-edit-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `e6464ec63864ed83a03369132182a71d177eaee2a96fc05d8f7d7ad68ad85b68`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 223.9035850000164, "baseline/context": 174.64518099995985, "baseline/help": 39.84162599999763, "baseline/version": 38.6946370001624, "candidate/cache": 222.80222800009142, "candidate/context": 173.50322199990842, "candidate/help": 40.79790800005867, "candidate/version": 39.33525799993731}, "passed": false, "reason": "validated", "report_sha256": "0349f36f8043284f682cd93774550c7429e1009c804114cf9717068e2c1492de", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41312120362", "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-edit-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `0349f36f8043284f682cd93774550c7429e1009c804114cf9717068e2c1492de`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 223.9035850000164, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 174.64518099995985, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.84162599999763, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.6946370001624, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 222.80222800009142, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 173.50322199990842, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 40.79790800005867, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 39.33525799993731, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-edit-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `0e8cc3b607746a6ea10572e0a9e4882d6df3afaf71c37c7e856fc389641d0804`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45580288, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.18299475699996, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46235648, "pretransfer_peak_rss_bytes": 45580288, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50798592, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08449038499998096, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 761856, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51560448, "pretransfer_peak_rss_bytes": 51560448, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45735936, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.2873734729998887, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46391296, "pretransfer_peak_rss_bytes": 45735936, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [761856, 655360, 655360]}, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-doc-edit-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `aa31a42c7f6793276db5c632a73fdaed187d5b11208a47ee55eb8b5b82012d51`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-edit-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `89fefc984ae31b9e9ddd2584d1f22c5f1e7906d8aad7c076798e9fd5d023cc7c`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-edit-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `57bf31297de6a75ba5fa7181756a766c738859fa3d62e81497477e4c09bd79c9`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-edit-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `d6b5dd3860c876e2856e85873f4e6d2e1d174a1fab092d421d9fb3cb7a568793`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "5731b99c21dd65af005da618ed51387480632225bced6dcaf50c04c721f741ed", "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `d7f9c6c90ebcb44bb3a80213faba94fd57488daa21ee613605263a469d561472`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 217.66447899995, "baseline/context": 169.7810580000123, "baseline/help": 38.926824999975906, "baseline/version": 37.818322000021, "candidate/cache": 218.8404260000425, "candidate/context": 170.95804099994893, "candidate/help": 39.6543599999859, "candidate/version": 37.74145900001713}, "passed": false, "reason": "validated", "report_sha256": "5731b99c21dd65af005da618ed51387480632225bced6dcaf50c04c721f741ed", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41312090002", "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `5731b99c21dd65af005da618ed51387480632225bced6dcaf50c04c721f741ed`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 217.66447899995, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 169.7810580000123, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 38.926824999975906, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 37.818322000021, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 218.8404260000425, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 170.95804099994893, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 39.6543599999859, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 37.74145900001713, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `50e08bcbf02cb87df0d3f8421921115628f219ae9a928f5272782b16e70518f7`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45211648, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.140456022999956, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45867008, "pretransfer_peak_rss_bytes": 45211648, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50692096, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08458127000005788, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 811008, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51503104, "pretransfer_peak_rss_bytes": 51503104, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45461504, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3172553919999928, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46116864, "pretransfer_peak_rss_bytes": 45461504, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [811008, 655360, 655360]}, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-doc-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `6f1fa7a1051b923c510deb5b31ea2efaa69b6902f7a074ad3007c40fe44a1927`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `aa419ee32039054cc9c4614bd90625262f958802b67ad26f8a3a182bcba34529`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-doc-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `246049dbb2490cb94ab15378085e5735304464bde6d3792e4462420ea7d8ae9b`.
**Yerel arşiv:** `raw/p02-0-pr12-doc-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "09d866369c73c2ecc8048e3c14b43cd2a61a972c"}`.

## p02-0-pr12-final-edit-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `df2015e52fa8d5778be0a8b86428be3c9f4a1d3329b7809cfed0a8800c189ed6`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "f7ac6dc55375453ee929f83ab170c9ff289327f83ff9b0d6893ae29b7efe978b", "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-edit-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `b7e55fa471ec13052c2a3bfde3ecaf7a972cb755a45b128d04677b7d65a281a5`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 157.47453000005862, "baseline/context": 112.83380299994406, "baseline/help": 25.226113999906374, "baseline/version": 24.358694999932595, "candidate/cache": 157.09767100008776, "candidate/context": 123.04426900004728, "candidate/help": 25.629647999949157, "candidate/version": 24.83118400004969}, "passed": true, "reason": "validated", "report_sha256": "f7ac6dc55375453ee929f83ab170c9ff289327f83ff9b0d6893ae29b7efe978b", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41310783296", "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-edit-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `f7ac6dc55375453ee929f83ab170c9ff289327f83ff9b0d6893ae29b7efe978b`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 157.47453000005862, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 112.83380299994406, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.226113999906374, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.358694999932595, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 157.09767100008776, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 123.04426900004728, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 25.629647999949157, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.83118400004969, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-edit-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `1be92878d0fa0c2ca89b2a27820bc78ba6ec670f2cd55a7841c242cfd3d3b4f8`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45785088, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.3003476880001017, "extra_rss_lower_bound_bytes": 786432, "extra_rss_upper_bound_bytes": 786432, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46571520, "pretransfer_peak_rss_bytes": 45785088, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51118080, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.042451760999938415, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 507904, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51625984, "pretransfer_peak_rss_bytes": 51625984, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45854720, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.6044314900000245, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46510080, "pretransfer_peak_rss_bytes": 45854720, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 786432], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 786432, "upper_bound_bytes": [507904, 655360, 786432]}, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-final-edit-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `a2b8d78d1f2cf20153af3e8cb306a0a16ffaa005c53e17a6e01d38060db90d98`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-edit-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `6a48de034c92b5db3165018525f4f8aad6052f2c6e85a3df8ee0b2b768f16852`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-edit-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `248ada2004a0b8ff145c4dcac377289e64c79db44b840f982fb65024e09f1eee`.
**Yerel arşiv:** `raw/p02-0-pr12-final-edit-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `358923e96ade85b3d058b5174855d33076f37479c62316d3ba0fd97d66e5acfc`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "17e7249dd8a9893c7f2fd6578d65ebd265837f3b49156c722aa26819a7a41c73", "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `20965dd04d6d3f1392313b205f64320995048366262b77dff052f5fcc8fe090e`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 218.7186409998958, "baseline/context": 170.59488000006695, "baseline/help": 41.229938000014954, "baseline/version": 38.35859299999811, "candidate/cache": 219.63745699997617, "candidate/context": 171.73602900004425, "candidate/help": 40.68929099992147, "candidate/version": 38.53260699997918}, "passed": false, "reason": "validated", "report_sha256": "17e7249dd8a9893c7f2fd6578d65ebd265837f3b49156c722aa26819a7a41c73", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41310772385", "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `17e7249dd8a9893c7f2fd6578d65ebd265837f3b49156c722aa26819a7a41c73`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 218.7186409998958, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 170.59488000006695, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 41.229938000014954, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.35859299999811, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 219.63745699997617, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 171.73602900004425, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 40.68929099992147, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 38.53260699997918, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `1d3e14a5ad6c5f305adcfcef062df34e614f8283a9960c6a8c03301b764bf8e0`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45735936, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.114569200000005, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46391296, "pretransfer_peak_rss_bytes": 45735936, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51089408, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.085632755000006, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 778240, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51867648, "pretransfer_peak_rss_bytes": 51867648, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45707264, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.2654612339999858, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46362624, "pretransfer_peak_rss_bytes": 45707264, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [778240, 655360, 655360]}, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-final-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `a6686fdd0b7e184f08a5fbb8cf06ff8882d8fbe1ec19ad6047d4454939e0fcef`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `312074009dac351b3937888c500900396edbe34ea02a9910e70f70b8bcbacdd8`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-final-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `36045829f31a392976803f6fbad66d97734805979d6557e7e6c72d3fb04bddd5`.
**Yerel arşiv:** `raw/p02-0-pr12-final-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "7b48256f79a8c66ccb9e4d0cf13c145d2ac9aeca"}`.

## p02-0-pr12-first-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `152fcde8c5e8ef1e2da0a4bab11115b3e484b9eb25a494b7c746745c6d9a7d25`.
**Yerel arşiv:** `raw/p02-0-pr12-first-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 216.552227999955, "baseline/context": 167.6867559999664, "baseline/help": 37.94237299996439, "baseline/version": 37.32789999992292, "candidate/cache": 221.4902110000594, "candidate/context": 169.63667499999247, "candidate/help": 38.24527599999783, "candidate/version": 37.213066999925104}, "passed": false, "reason": "validated", "report_sha256": "7ceb1d22c9e32847247048222cf3d3bc256dfc878753afec4ac93f6327757447", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41278900870", "source_commit": "29ec2562b985815184e1f15638178ef474a7710d"}`.

## p02-0-pr12-first-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `7ceb1d22c9e32847247048222cf3d3bc256dfc878753afec4ac93f6327757447`.
**Yerel arşiv:** `raw/p02-0-pr12-first-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 216.552227999955, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 167.6867559999664, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 37.94237299996439, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 37.32789999992292, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 221.4902110000594, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 169.63667499999247, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 38.24527599999783, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 37.213066999925104, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "29ec2562b985815184e1f15638178ef474a7710d"}`.

## p02-0-pr12-first-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `3c121f513c1d9fff371716d5dd1c3045089aa01a82f9a1fb74c1c8de34b881ab`.
**Yerel arşiv:** `raw/p02-0-pr12-first-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45502464, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.077794073999939, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46157824, "pretransfer_peak_rss_bytes": 45502464, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52060160, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.0810149530000217, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52060160, "pretransfer_peak_rss_bytes": 52060160, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45346816, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.294498026000042, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46002176, "pretransfer_peak_rss_bytes": 45346816, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "29ec2562b985815184e1f15638178ef474a7710d", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-first-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `8875790cf30fea0744070fdfee0ea2e88185016692c959305b812356275b7a4a`.
**Yerel arşiv:** `raw/p02-0-pr12-first-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "29ec2562b985815184e1f15638178ef474a7710d"}`.

## p02-0-pr12-first-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `0dd15b3809fee613d973c30ebb08b9ad49d1b78f19c64d8559f72b7d8092ae8e`.
**Yerel arşiv:** `raw/p02-0-pr12-first-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "29ec2562b985815184e1f15638178ef474a7710d"}`.

## p02-0-pr12-first-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `34a4545fa6256a814dc2d2bc28bce548e2583f6985a71995e060c7840ce68636`.
**Yerel arşiv:** `raw/p02-0-pr12-first-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "29ec2562b985815184e1f15638178ef474a7710d"}`.

## p02-0-pr12-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `6363445754e77e515bbf2ef372cae97bfbcf3ef37012b012b83d0d00c4441aee`.
**Yerel arşiv:** `raw/p02-0-pr12-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "7ceb1d22c9e32847247048222cf3d3bc256dfc878753afec4ac93f6327757447", "source_commit": "29ec2562b985815184e1f15638178ef474a7710d"}`.

## p02-0-pr12-static-edit-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `34ae4f8d5b43d632afb5b42e2583c93dc0e512603c00d3e97262e8c2ac8bf816`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "be52fe3324f6d9ca81a5adc0071c17a6d6400aee095be4e65e18769d83f79f57", "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-edit-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `44a8deeaa7afe03db439ed66f164feccb1928567a3b6f7f86d72481386f0589f`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 216.56102600002214, "baseline/context": 169.65484299998934, "baseline/help": 38.75596099999257, "baseline/version": 37.832008999998834, "candidate/cache": 217.4010859999953, "candidate/context": 170.40836300009232, "candidate/help": 38.71761800007789, "candidate/version": 37.71837700003289}, "passed": false, "reason": "validated", "report_sha256": "be52fe3324f6d9ca81a5adc0071c17a6d6400aee095be4e65e18769d83f79f57", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41308223513", "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-edit-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `be52fe3324f6d9ca81a5adc0071c17a6d6400aee095be4e65e18769d83f79f57`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 216.56102600002214, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 169.65484299998934, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 38.75596099999257, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 37.832008999998834, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 217.4010859999953, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 170.40836300009232, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 38.71761800007789, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 37.71837700003289, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-edit-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `9083f63e205c6aea49afb9d8ba27f0f71e4bf8ea2242e5b0c29c1d923bfdc853`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45506560, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.023976314000038, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46161920, "pretransfer_peak_rss_bytes": 45506560, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50724864, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08449225699996532, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 761856, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51486720, "pretransfer_peak_rss_bytes": 51486720, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45527040, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3016190629999755, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46182400, "pretransfer_peak_rss_bytes": 45527040, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [761856, 655360, 655360]}, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-static-edit-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `e3e7367165097f9296d709abfa0df5299ce6b7ad9a7ab9fefdfb97f56784e1c1`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-edit-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `92fc36d2c35f02a5dc8353739ffeefbcde2faa443e229f81eff93987c159a09b`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-edit-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `9b6896aeb54f9bbe2d7075a7bd4b34f3a4d4f52de7d747007f304d0ea3814fbe`.
**Yerel arşiv:** `raw/p02-0-pr12-static-edit-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `11d8d70e459cd70527d83d2d1dd109793d0ee4083334c7aa917950c80ed6a13b`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "6eb31de70b2b4668477aa8787737fa3f0f8c43aec31676954e0e0aeca1a0741f", "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `fcb1893491a8894d7abf0bd76cfd2459289327d907e8e70ade5502914f30cd3b`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 165.76069099994584, "baseline/context": 129.70935600003486, "baseline/help": 28.22344699995938, "baseline/version": 26.412061999963043, "candidate/cache": 161.77319000007628, "candidate/context": 128.84350500007713, "candidate/help": 29.598102000022664, "candidate/version": 26.299037999933716}, "passed": true, "reason": "validated", "report_sha256": "6eb31de70b2b4668477aa8787737fa3f0f8c43aec31676954e0e0aeca1a0741f", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41307921001", "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `6eb31de70b2b4668477aa8787737fa3f0f8c43aec31676954e0e0aeca1a0741f`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 165.76069099994584, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 129.70935600003486, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 28.22344699995938, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 26.412061999963043, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 161.77319000007628, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 128.84350500007713, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 29.598102000022664, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 26.299037999933716, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `936da43ba9bb9a56a42c999561b2c7f882121c97b4566d57553af94ecf7abaf7`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45735936, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.82800040099994, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46391296, "pretransfer_peak_rss_bytes": 45735936, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50974720, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.04529918600007932, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 499712, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51474432, "pretransfer_peak_rss_bytes": 51474432, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45600768, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7001451190000125, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46256128, "pretransfer_peak_rss_bytes": 45600768, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [499712, 655360, 655360]}, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-static-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `2e1c06340abf07fe785075efb476eeae65b484190e4076ec012fde67e9776452`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `e10ee4e93c217080251111bdc60cfdd798a3cbe431d2264e52606cabed2bee41`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-static-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `6d37bbe47c030ed1acc34298aaf305088b0bc2b98cc65cbf6a256055c5638d9a`.
**Yerel arşiv:** `raw/p02-0-pr12-static-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "8bd5e45d33d1355050b0393f697c8ecd73015db3"}`.

## p02-0-pr12-user-review-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `21afd4c11a113f6e255e6260a89a151284b7c44e4427b08324e415d527be5ffa`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "bc9532cd66c76dc4126162fabd4307c2fdaf4027", "report_sha256": "daddf499e234207517409559127ba2a5c20c5a043f235603d4294844f343c0f0", "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c"}`.

## p02-0-pr12-user-review-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `daa26a3951a22cbfba556b5a1d0467cae7309ac88907ea9b340006b5ec0f667e`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 217.9020019999598, "baseline/context": 173.99393799996687, "baseline/help": 39.143251000041346, "baseline/version": 38.195760000007795, "candidate/cache": 218.73677400003544, "candidate/context": 171.89147199997024, "candidate/help": 39.64956300001177, "candidate/version": 38.10417900001539}, "passed": false, "reason": "validated", "report_sha256": "daddf499e234207517409559127ba2a5c20c5a043f235603d4294844f343c0f0", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41305352805", "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c"}`.

## p02-0-pr12-user-review-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `daddf499e234207517409559127ba2a5c20c5a043f235603d4294844f343c0f0`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 217.9020019999598, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 173.99393799996687, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.143251000041346, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.195760000007795, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 218.73677400003544, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 171.89147199997024, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 39.64956300001177, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 38.10417900001539, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c"}`.

## p02-0-pr12-user-review-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `9049ef53e99938c367f79e9082851e3fb34b10980312a7391ddcab75ba5dce4d`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45477888, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 4.975377670000057, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46133248, "pretransfer_peak_rss_bytes": 45477888, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50692096, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08431373400003395, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 786432, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51478528, "pretransfer_peak_rss_bytes": 51478528, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45600768, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.2701296740000316, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46256128, "pretransfer_peak_rss_bytes": 45600768, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [786432, 655360, 655360]}, "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c", "source_unchanged_during_measurement": true}`.

## p02-0-pr12-user-review-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `a8d8f8ae53a42a4cf56c97442bd980c46f1bedcfda934eb5ef1e724c35ec4c8d`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c"}`.

## p02-0-pr12-user-review-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `d819fa474a5c724cc71a0765fe8d0cb27a866bed5b8c0c66575bd9b322b64250`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c"}`.

## p02-0-pr12-user-review-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `990d77e5e4871294832883d2b8fd1ffb8f4801d072d2f3c16bc865f272a33f64`.
**Yerel arşiv:** `raw/p02-0-pr12-user-review-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "31966204415e124e53cf27aa4b23340a8aad590c"}`.

## p02-0-review-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `987243e2d363c55062bdabfe226ab93063ae3a1822c53bb4dbc08ccc1393dbf5`.
**Yerel arşiv:** `raw/p02-0-review-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "3aa5903dee6328154b6a2e4fd070771588c7ab86"}`.

## p02-0-review-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `aa86cf78d09fa00d98f08606b2af336b4f725f543db0ca401a701559ed872c4a`.
**Yerel arşiv:** `raw/p02-0-review-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 150.53445799276233, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 101.9256659783423, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 103.35629200562835, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 100.80533311702311, "passed": true, "samples": 30}}, "passed": true, "source_commit": "042652c543e0a00b2128cc4e555fff44474dc3e4", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-review-reference-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `a01ea4315da040372e1cd763dd34a92d20564923dbe58ce6f005436082952680`.
**Yerel arşiv:** `raw/p02-0-review-reference-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 113.828832982108, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 72.70095800049603, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.530249949544668, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 21.815250162035227, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 119.78812492452562, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 74.72675014287233, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.412249982357025, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.404999937862158, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "042652c543e0a00b2128cc4e555fff44474dc3e4"}`.

## p02-0-sonar-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `2a93faeae0bbeac837a41ae4964d0902e8fbc011d37d1fb03ea9d56b9e179a5e`.
**Yerel arşiv:** `raw/p02-0-sonar-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "08c846bd798369e01e8f2c5fb7c2b294ff0aa2a8"}`.

## p02-0-sonar-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `c5dce9b066ef7cccbccfaffe8774effa55e2e60817be28dca212137e6dec3b97`.
**Yerel arşiv:** `raw/p02-0-sonar-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 185.9057501424104, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 129.94191702455282, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 133.23725014925003, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 118.50324994884431, "passed": true, "samples": 30}}, "passed": true, "source_commit": "c7895d57acac98acece58262c2dcb09b1105004c", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-0-sonar-reference-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `16b97f22b29c154730f52e2232ca87804fc8b1930cec695d34247ac205ac3c13`.
**Yerel arşiv:** `raw/p02-0-sonar-reference-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 142.0817500911653, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 93.19154196418822, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 36.93770803511143, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 28.341832803562284, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 133.862208109349, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 99.15220807306468, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 37.79600001871586, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 27.967125177383423, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "c7895d57acac98acece58262c2dcb09b1105004c"}`.

## p02-1-functional-journey-v1

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `d08345ee98671e80f6f8e1e3c1cbd1ec0480ac46f3cf7bd7918f07f98787518c`.
**Yerel arşiv:** `raw/p02-1-functional-journey-v1.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "readme_functional_journey_passed", "source_commit": "2729ea3c0cfba74390dcd6b71ad664d2fea3e459"}`.

## p02-1-installation-v1

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `823c942fc3f7222d9a27e8e0329219ed3c3040c40bdb49b569438e339445b12b`.
**Yerel arşiv:** `raw/p02-1-installation-v1.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e05eacb5ddb2a767ea9b2ad78afa7333b313d694"}`.

## p02-1-installation-v2

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `ef4cd73f5ad61d072887b7cb9b8c28e6cd633ac94b5f950cc45d7af2d9ce68fe`.
**Yerel arşiv:** `raw/p02-1-installation-v2.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "833a803d1802ae7d511a0fd16ef9ade15c6686b1"}`.

## p02-1-local-suite-v1

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `4a062b03d9900fd765b61064d98d0463b63d8ddfeabb455ae5f5d71b742ade1d`.
**Yerel arşiv:** `raw/p02-1-local-suite-v1.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "pytest_passed_4174_linux_native_skip_1", "source_commit": "e05eacb5ddb2a767ea9b2ad78afa7333b313d694"}`.

## p02-1-local-suite-v2

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `dd8082863d5f8ae33bf8e5e86948bb46240291bc2476563f503b93d5db307db6`.
**Yerel arşiv:** `raw/p02-1-local-suite-v2.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "pytest_passed_4202_linux_native_skip_1", "source_commit": "2729ea3c0cfba74390dcd6b71ad664d2fea3e459"}`.

## p02-1-startup-concurrent-v1

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `7d2a9d9010389f499b5ea411f4400916e85fde13918a12b8f1dc3273abb5455a`.
**Yerel arşiv:** `raw/p02-1-startup-concurrent-v1.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "startup_reference_ineligible_concurrent_external_test", "source_commit": "44d98de93b6bc3174c250696190a32444ba8b67d"}`.

## p02-1a-evidence-catalog-profile

**Tür:** `operation`.
**Özgün JSON SHA-256:** `73f1c0c83d78f607845514a23e4ac2206e0fd6e81ad37df2bd52726a43d06009`.
**Yerel arşiv:** `raw/p02-1a-evidence-catalog-profile.json.gz`.
**Özet:** `{"cases": 9, "diagnostic_only": true, "kind": "operation", "max_elapsed_ms": 1156.6550000570714, "outcomes": {"ok": 9}, "source_commit": "ec401641a5135976cbfc7e0a4d53f502ecb4f59c"}`.

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
