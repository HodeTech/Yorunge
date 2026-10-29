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

## p01-6-reference-jobs-pr-review

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `7e556e3e46a8da375b9097ab1d60809a9b4b1388f318e1a05777d512a7843b64`.
**Yerel arşiv:** `raw/p01-6-reference-jobs-pr-review.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 143.84491695091128, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 104.91274995729327, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 105.30758299864829, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 98.27445819973946, "passed": true, "samples": 30}}, "passed": true, "source_commit": "fca5b1403606343eac865572140ed45869e33a45", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p01-6-reference-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `79483408be518b908bc5f77e4d65509a05f0d0e859bc4210cdf49890ac1923bb`.
**Yerel arşiv:** `raw/p01-6-reference-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 207.63795892708004, "passed": false, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 111.68862506747246, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 106.78958310745656, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 191.42820918932557, "passed": true, "samples": 30}}, "passed": false, "source_commit": "55dbe64bf9f3e5944d89ddbd71caeadbdd2bf50e", "source_unchanged_during_measurement": true, "unchanged": true}`.

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
