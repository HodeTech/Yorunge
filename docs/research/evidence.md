# Ham ölçüm kanıtları

Bu indeks manifest ve özgün JSON baytlarından üretilir.
Arşiv biçimi ve sınırlar [kanıt standardındadır](../standards/research-evidence.md).
Eski başarısız ölçümler ve tanılar korunur; güncel kabul ayrıca incelenir.
`p02-3-reference-*-N` serilerinden yalnız en yüksek numaralı olan bugünkü kaynağa bağlıdır; öncekiler tarihsel kayıttır ve doğrulayıcıları bugünkü kaynağa karşı bilerek geçmez.
Gzip dosyaları Git checkout'unda tutulur; sdist/wheel içine girmez.

## p01-3-followup-merged-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `8938a2827a3000a6983d39d734da60653cea8421e1f0393a3534f0dd5068802b`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/fae087ba4eeff30e178e76174cd092b6bd805fad/docs/research/p01-3-followup-merged-startup.json); yerel arşiv `raw/p01-3-followup-merged-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"candidate/cache": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 200.0, "p95_ms": 218.223, "passed": false, "samples": 30}, "candidate/context": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 200.0, "p95_ms": 174.407, "passed": true, "samples": 30}, "candidate/help": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 500.0, "p95_ms": 45.871, "passed": true, "samples": 30}, "candidate/version": {"budget_decision_ambiguous_after_rounding": false, "budget_ms": 500.0, "p95_ms": 44.031, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-cache-parse-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `24a45124230e90bd728e5109238cbfa92d87607f11f7fd13408c00ede7686ce0`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/552d3e3e9861b7dac24a1135e8925adcaf7a8075/docs/research/p01-4-cache-parse-operation-budget.json); yerel arşiv `raw/p01-4-cache-parse-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 5034.169083, "outcomes": {"ok": 24, "state_busy": 3}, "source_commit": "5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5"}`.

## p01-4-ci-startup-40807762132

**Tür:** `startup`.
**Özgün JSON SHA-256:** `b7da75f2680cce2813d0a12197978668b06578beeb434499d43658c6981115d2`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/ad6cb924f6b0a3abc71655b7eb1afa9d6655e340/docs/research/p01-4-ci-startup-40807762132.json); yerel arşiv `raw/p01-4-ci-startup-40807762132.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 119.01860200001124, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 93.38375499999074, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.742677000006097, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.760992999996233, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 116.57509900001628, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 91.73733599999423, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 21.959119999991117, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 21.349657999991223, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-ci-startup-40808159684

**Tür:** `startup`.
**Özgün JSON SHA-256:** `594f7305ef1f398298c051c1d00f7359a483ee860e2961c36f5e419bd500923e`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/ad6cb924f6b0a3abc71655b7eb1afa9d6655e340/docs/research/p01-4-ci-startup-40808159684.json); yerel arşiv `raw/p01-4-ci-startup-40808159684.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 355.91988900000615, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 121.93917500002271, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 32.087685999954374, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 30.982848000007834, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 392.3889300000383, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 119.64243199997782, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.465944999993553, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 27.52818499999421, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-closing-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `cb154c8d655f47fed9169c507570dcc8abdbe4711add58b560b40eddf7b02619`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/182f695f656c374530d9a496a59d9e7ee714932f/docs/research/p01-4-closing-jobs-budget.json); yerel arşiv `raw/p01-4-closing-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 178.063125, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 120.208084, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 124.486167, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 121.778791, "passed": true, "samples": 30}}, "source_commit": "9600416e58ac3f7e604feef7ba25fff0dbfeff2f"}`.

## p01-4-evidence-ci-startup-a24c71f

**Tür:** `startup`.
**Özgün JSON SHA-256:** `fcde6c87c89d69f550177f1629efcd8127508f4dbdeaf4c602f8a241dfa5323d`.
**Yerel arşiv:** `raw/p01-4-evidence-ci-startup-a24c71f.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 225.49458100002084, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 163.49130399999012, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 43.87156899997535, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 42.31549899998299, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 222.37509100000352, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 161.3148749999027, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 38.83290199996736, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 36.38817700004893, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-final-installations

**Tür:** `installation`.
**Özgün JSON SHA-256:** `f851a28d0e25ed56f1f4b11f83bc7462d06c400fb6516d77b341bcfa43f98d44`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/410c29ed230cc3ae2a2706441f6a6c37645445b5/docs/research/p01-4-final-installations.json); yerel arşiv `raw/p01-4-final-installations.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation", "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `66b89e1d31189cc48f9d587e9fc602d13e04f79ecb1c0b0c509a0851a28e88e2`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/410c29ed230cc3ae2a2706441f6a6c37645445b5/docs/research/p01-4-final-jobs-budget.json); yerel arşiv `raw/p01-4-final-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 166.939, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 104.432042, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 120.620875, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 105.247583, "passed": true, "samples": 30}}, "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `43edb6deafec81ff7d5ef0aec0dde7b5f6f2bf95198f3454d291b7cd1250e405`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/410c29ed230cc3ae2a2706441f6a6c37645445b5/docs/research/p01-4-final-migration-budget.json); yerel arşiv `raw/p01-4-final-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4316.419583, "outcomes": {"ok": 24}, "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `6171238f6d54e4e5b592364f20bb71ff4b1f81f40e5d6e58ae83c223da4be5de`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/410c29ed230cc3ae2a2706441f6a6c37645445b5/docs/research/p01-4-final-operation-budget.json); yerel arşiv `raw/p01-4-final-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4931.328083, "outcomes": {"ok": 27}, "source_commit": "17de9652372f1ebd0fd4725d8616d16efa1ee169"}`.

## p01-4-final-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `d0e48803b4a7cb35cf4ba9194bf4e73863a86ac5af1721f614b100c13580e58e`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/410c29ed230cc3ae2a2706441f6a6c37645445b5/docs/research/p01-4-final-startup.json); yerel arşiv `raw/p01-4-final-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 123.77254199236631, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 77.75479182600975, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.277000153437257, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.19595799781382, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 114.53570914454758, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 90.23562516085804, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.374042008072138, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 21.44575002603233, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-hotpath-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `cd2f6968a80c64c86c27a71caa60f950a734569ca1a5f0001623417ffb603889`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5/docs/research/p01-4-hotpath-operation-budget.json); yerel arşiv `raw/p01-4-hotpath-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 5034.559042, "outcomes": {"ok": 21, "state_busy": 6}, "source_commit": "ad6cb924f6b0a3abc71655b7eb1afa9d6655e340"}`.

## p01-4-hotpaths-ab-full

**Tür:** `comparison`.
**Özgün JSON SHA-256:** `12497116bb00e34f32b3af1613650036118df60371a2581684c68dc6c716e602`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5/docs/research/p01-4-hotpaths-ab-full.json); yerel arşiv `raw/p01-4-hotpaths-ab-full.json.gz`.
**Özet:** `{"cases": 6, "diagnostic_only": true, "kind": "comparison", "outcomes": {"ok": 6}, "source_commit": null}`.

## p01-4-initial-help-parity

**Tür:** `help-parity`.
**Özgün JSON SHA-256:** `74d2fd9fe5b564007e9c465b496cdef607ffcd2e7f743878a2f704de375bd559`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/5c7ad8c959448b6c746871274365c9d8b7d676fd/docs/research/p01-4-initial-help-parity.json); yerel arşiv `raw/p01-4-initial-help-parity.json.gz`.
**Özet:** `{"cases": 30, "checks": {"equal": {"false": 1, "true": 29}, "matches_initial_p014": {"not_recorded": 30}, "root_expected_jobs_addition": {"false": 29, "true": 1}}, "diagnostic_only": false, "kind": "help-parity", "source_commit": null}`.

## p01-4-merge-805f8bd-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `91288f45ba0f62fd0f577ceea4ad1c73f55a34229acd5452abe56114092308dc`.
**Yerel arşiv:** `raw/p01-4-merge-805f8bd-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 193.8822750000213, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 153.7080840000158, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.69161699995993, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.465445000042564, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 191.56937200000357, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 153.25847500002965, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 35.09405400001242, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 33.15877099998943, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-noop-installations

**Tür:** `installation`.
**Özgün JSON SHA-256:** `f19ea619ca4c7e6e64579ecdb62c3cede50a6e39923fec3eb68cf2f248b7e694`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-installations.json); yerel arşiv `raw/p01-4-noop-installations.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation", "source_commit": "182f695f656c374530d9a496a59d9e7ee714932f"}`.

## p01-4-noop-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `0d16c259bec38102f7002ac664e30096410ad01ae24abf180b8e412fb7fbe483`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-jobs-budget.json); yerel arşiv `raw/p01-4-noop-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 175.711583, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 122.114375, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 133.52175, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 118.805833, "passed": true, "samples": 30}}, "source_commit": "bc0d3c9a3f8c8aa5fdfe20b1aa69dd375319538e"}`.

## p01-4-noop-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `3c6d36e4eecc2809cadf30ca7b21cfe3497e08212df6d186f97918a6c07d6bc2`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-migration-budget.json); yerel arşiv `raw/p01-4-noop-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4456.741375, "outcomes": {"ok": 24}, "source_commit": "bc0d3c9a3f8c8aa5fdfe20b1aa69dd375319538e"}`.

## p01-4-noop-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `9dd3a4e3f8f8fb26c9443f802a10d099dd28c21ae40b6c9a967809bda6225812`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-operation-budget.json); yerel arşiv `raw/p01-4-noop-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4851.707875, "outcomes": {"ok": 27}, "source_commit": "bc0d3c9a3f8c8aa5fdfe20b1aa69dd375319538e"}`.

## p01-4-noop-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `00b45552acdfd0a0252449d6aa7c36bbe8bba78f6ca3ad1d65d7012b692b9bb8`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/f186d27ac9b7313d5640877e574e9337fbd6b4ff/docs/research/p01-4-noop-startup.json); yerel arşiv `raw/p01-4-noop-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 123.78991581499577, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 84.49516608379781, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 27.706583961844444, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 27.38975011743605, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 123.1852921191603, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 82.74233294650912, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 26.896916795521975, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 25.322833796963096, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-quality-help-parity

**Tür:** `help-parity`.
**Özgün JSON SHA-256:** `aa3a82ea0007ae8326eb7525da666d0d2b06ad3ba9f92215858452f4de32248e`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/ad6cb924f6b0a3abc71655b7eb1afa9d6655e340/docs/research/p01-4-quality-help-parity.json); yerel arşiv `raw/p01-4-quality-help-parity.json.gz`.
**Özet:** `{"cases": 30, "checks": {"equal": {"not_recorded": 30}, "matches_initial_p014": {"true": 30}, "root_expected_jobs_addition": {"not_recorded": 30}}, "diagnostic_only": false, "kind": "help-parity", "source_commit": "e638194a37fecd273574cd84e415a1085479c943"}`.

## p01-4-quality-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `4434f6677c6aacf40dd49366980045b319616e2955f8a3a18d62d602597f0eb3`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/ad6cb924f6b0a3abc71655b7eb1afa9d6655e340/docs/research/p01-4-quality-operation-budget.json); yerel arşiv `raw/p01-4-quality-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 5033.784375, "outcomes": {"ok": 21, "state_busy": 6}, "source_commit": "e638194a37fecd273574cd84e415a1085479c943"}`.

## p01-4-quota-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `f603f216fa3dfa8d5d99cefa945a1cee786860d7bf1d61927911505d146b5387`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/9600416e58ac3f7e604feef7ba25fff0dbfeff2f/docs/research/p01-4-quota-migration-budget.json); yerel arşiv `raw/p01-4-quota-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4541.755791, "outcomes": {"ok": 24}, "source_commit": "dbdc9562c439091ae411246f006772e04460acce"}`.

## p01-4-quota-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `014a18940f859d4d91022c7e445ff39f48e8e1b4647b82b4d855410760e5fc7b`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/9600416e58ac3f7e604feef7ba25fff0dbfeff2f/docs/research/p01-4-quota-operation-budget.json); yerel arşiv `raw/p01-4-quota-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4965.896083, "outcomes": {"ok": 27}, "source_commit": "dbdc9562c439091ae411246f006772e04460acce"}`.

## p01-4-reset-diagnostic

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `67d0cc491804914c87ad9ea4ad3b51f044ca11811754a3d768b73c16c21e537e`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/552d3e3e9861b7dac24a1135e8925adcaf7a8075/docs/research/p01-4-reset-diagnostic.json); yerel arşiv `raw/p01-4-reset-diagnostic.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ok", "source_commit": "5d0b3a47f0ab3b2faec3be86bac6151c6eecfdb5"}`.

## p01-4-step-1-migration

**Tür:** `migration`.
**Özgün JSON SHA-256:** `0aede2bacaa72702a78f210e19b7a71ed446f9944d9df022f5f192a68d8f266f`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/a73608a889b38d82acb6819f6253c3e870dce0f1/docs/research/p01-4-step-1-migration.json); yerel arşiv `raw/p01-4-step-1-migration.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4528.112625, "outcomes": {"ok": 24}, "source_commit": "c3dbfe7b5e983d0075718edc065a8f815c1f8ff4"}`.

## p01-4-step-3-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `f297eeb3656a71903834d7a6e78b1900cea6ef911deab3db1e34946a2d1f57f3`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/83f55bcd23e213f6ee682443a863818366fad9b0/docs/research/p01-4-step-3-operation-budget.json); yerel arşiv `raw/p01-4-step-3-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4961.403375, "outcomes": {"ok": 27}, "source_commit": "0b8c2cf2990345af4bad2a73b630431055fb1117"}`.

## p01-4-step-3-reviewed-migration-budget

**Tür:** `migration`.
**Özgün JSON SHA-256:** `049703e60df29dd941f38ab6ab7018822673b10f8dba12c6bcade9dfbc6306b2`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/39251184d3a4fd742a8680f0edeb2d42c6880c1c/docs/research/p01-4-step-3-reviewed-migration-budget.json); yerel arşiv `raw/p01-4-step-3-reviewed-migration-budget.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "kind": "migration", "max_elapsed_ms": 4337.36875, "outcomes": {"ok": 24}, "source_commit": "0092d407f933246952a6da4e47d5145eeebf6d0d"}`.

## p01-4-step-3-reviewed-operation-budget

**Tür:** `operation`.
**Özgün JSON SHA-256:** `b19dc6718da161af6b51096dde0fb635171f0a0617548a939ad970f03d1c8dd7`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/39251184d3a4fd742a8680f0edeb2d42c6880c1c/docs/research/p01-4-step-3-reviewed-operation-budget.json); yerel arşiv `raw/p01-4-step-3-reviewed-operation-budget.json.gz`.
**Özet:** `{"cases": 27, "diagnostic_only": false, "kind": "operation", "max_elapsed_ms": 4936.653875, "outcomes": {"ok": 27}, "source_commit": "0092d407f933246952a6da4e47d5145eeebf6d0d"}`.

## p01-4-step-4-initial-installations

**Tür:** `installation`.
**Özgün JSON SHA-256:** `880d1784557069aac59c3847c8678c4e346e3a9220ab88f95fbec37e4660d95a`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/5c7ad8c959448b6c746871274365c9d8b7d676fd/docs/research/p01-4-step-4-initial-installations.json); yerel arşiv `raw/p01-4-step-4-initial-installations.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation", "source_commit": null}`.

## p01-4-step-4-initial-jobs-budget

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `919cd1a16d3caf73bcbb8d678f5b035d32070eee99b51afc35f1aad32a3158b9`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/5c7ad8c959448b6c746871274365c9d8b7d676fd/docs/research/p01-4-step-4-initial-jobs-budget.json); yerel arşiv `raw/p01-4-step-4-initial-jobs-budget.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 165.678333, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 104.372, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 111.118875, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 104.767333, "passed": true, "samples": 30}}, "source_commit": "39251184d3a4fd742a8680f0edeb2d42c6880c1c"}`.

## p01-4-step-4-initial-startup

**Tür:** `startup`.
**Özgün JSON SHA-256:** `c03ab360e04c457d1887a80c0c4b47f1fa7f820aafc656a3fce5f2dc65511d9f`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/5c7ad8c959448b6c746871274365c9d8b7d676fd/docs/research/p01-4-step-4-initial-startup.json); yerel arşiv `raw/p01-4-step-4-initial-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 124.26991597749293, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 74.06549993902445, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.93483293801546, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.77424987591803, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 112.88970895111561, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 72.32283311896026, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.766458896920085, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.005208931863308, "passed": true, "samples": 30}}, "source_commit": null}`.

## p01-4-wire-size-micro

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `5a005c1c7163038f318b0ffcb2c210c5783963ebf011c0fba5e2e79d5f157ae4`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/552d3e3e9861b7dac24a1135e8925adcaf7a8075/docs/research/p01-4-wire-size-micro.json); yerel arşiv `raw/p01-4-wire-size-micro.json.gz`.
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

## p02-1-final-raw-v2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `f595085851472b48b3e737974c30236f028f6fdd3b9a9e6561287a93390e8153`.
**Yerel arşiv:** `raw/p02-1-final-raw-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49954816, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6172382079530507, "extra_rss_lower_bound_bytes": 1228800, "extra_rss_upper_bound_bytes": 1228800, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51183616, "pretransfer_peak_rss_bytes": 49954816, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57393152, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025906374910846353, "extra_rss_lower_bound_bytes": 16384, "extra_rss_upper_bound_bytes": 16384, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57409536, "pretransfer_peak_rss_bytes": 57393152, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49692672, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.3949445409234613, "extra_rss_lower_bound_bytes": 409600, "extra_rss_upper_bound_bytes": 409600, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50102272, "pretransfer_peak_rss_bytes": 49692672, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [16384, 409600, 1228800], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1212416, "upper_bound_bytes": [16384, 409600, 1228800]}, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441", "source_unchanged_during_measurement": true}`.

## p02-1-final-reference-v2-datasets

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `fcd688b0f32b4ba2fcf2c4f54a4bad5929a893ae95b047f8bb09f4632441ea85`.
**Yerel arşiv:** `raw/p02-1-final-reference-v2-datasets.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 4292608}, "verify": {"passed": true, "span_upper_bound_bytes": 4292608}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7893618748057634, "max_extra_rss_upper_bound_bytes": 20529152, "passed": true, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

## p02-1-final-reference-v2-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `2dc713df202b7fdcd33987ddd3b67f0ba2cc2ee4094b292803dcc3330c2cfa40`.
**Yerel arşiv:** `raw/p02-1-final-reference-v2-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 164.96062488295138, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 114.57379092462361, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 161.77991614677012, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 114.2907498870045, "passed": true, "samples": 30}}, "passed": true, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-1-final-reference-v2-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `4f747f2455f620eb0132431f7dbd72a1565bc98d355814975af45c1327196f17`.
**Yerel arşiv:** `raw/p02-1-final-reference-v2-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 154.69616698101163, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 112.68883314915001, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 28.99120911024511, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 28.854291886091232, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 146.55666705220938, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 108.88745891861618, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.696499997749925, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 28.29966600984335, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

## p02-1-first-task-v2

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `c0355d7c6fa17a9a8f5b1d4df17e72ac2bcc625bd75193e43e8bc5a5da9cfb8c`.
**Yerel arşiv:** `raw/p02-1-first-task-v2.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "installed_first_task_timing_passed", "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

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

## p02-1-installation-v3

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `c5abd19b42da83b9e5f8677515050c6d3aec2d5d4e24237cef31022fbb7deac0`.
**Yerel arşiv:** `raw/p02-1-installation-v3.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

## p02-1-jobs-budget-failed-v2

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `0cfbbe0916147e068b59de4160e9eadd765553d62ff52657633e8797aef27406`.
**Yerel arşiv:** `raw/p02-1-jobs-budget-failed-v2.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 158.73454185202718, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 280.2371249999851, "passed": false, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 115.69524998776615, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 131.1312911566347, "passed": true, "samples": 30}}, "passed": false, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-1-jobs-confirmation-v2a

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `1d59a552bff7c608b84830c2bd17c7a2974053db66c9ad7103b301cd05bb0e2b`.
**Yerel arşiv:** `raw/p02-1-jobs-confirmation-v2a.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 153.8672079332173, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 118.10750002041459, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 119.90566714666784, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 125.43620797805488, "passed": true, "samples": 30}}, "passed": true, "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-1-jobs-cpu-diagnostic-v2

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `5bed00d81059eff8491e59c123696cb62e109f893b25619deffc9f88b8b03376`.
**Yerel arşiv:** `raw/p02-1-jobs-cpu-diagnostic-v2.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "jobs_failed_run_followup_diagnostic_not_acceptance", "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

## p02-1-jobs-profile-diagnostic-v2

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `0c3748130fd3b0025c589cf6a6d423eaca27d7fdbd70881a15201e7ad086e835`.
**Yerel arşiv:** `raw/p02-1-jobs-profile-diagnostic-v2.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "jobs_single_profile_not_acceptance", "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

## p02-1-jobs-two-cohort-protocol-v2-report

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `87299fc532dd15b205d84cb6722e209281df515ae348c1e3bcb3d77972a4a778`.
**Yerel arşiv:** `raw/p02-1-jobs-two-cohort-protocol-v2-report.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "jobs_two_cohort_protocol_predeclared", "source_commit": "3c20216683dc506d55ae02381fcd72a65b383441"}`.

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

## p02-1-pr13-attribution-metadata-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `9c9bda6d9e2d6f02eff1337c8ee518a44c38f3c5988bade6baac85e3d1016f6b`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "417c2751720127dd65e80e08b26c82c10611a8df6e779402d559c48fbffd032d", "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-metadata-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `d4191bc340229bf44521be200ef78cb131de7364212b41d0af5cacf6180810fa`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 234.23586700005217, "baseline/context": 182.15636399997948, "baseline/help": 44.887706000054095, "baseline/version": 44.07767399993645, "candidate/cache": 231.03902200000448, "candidate/context": 184.83742399996572, "candidate/help": 46.06733000002805, "candidate/version": 44.49274700004935}, "passed": false, "reason": "validated", "report_sha256": "417c2751720127dd65e80e08b26c82c10611a8df6e779402d559c48fbffd032d", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41362301747", "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-metadata-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `417c2751720127dd65e80e08b26c82c10611a8df6e779402d559c48fbffd032d`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 234.23586700005217, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 182.15636399997948, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 44.887706000054095, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 44.07767399993645, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 231.03902200000448, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 184.83742399996572, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 46.06733000002805, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 44.49274700004935, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-metadata-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `2d3422f1f5aa19f41828e11fd695da627650f3603686d1907b5cbd17e8411cc4`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45858816, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 4.066038445999993, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46514176, "pretransfer_peak_rss_bytes": 45858816, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52637696, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.06735011199998553, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52637696, "pretransfer_peak_rss_bytes": 52637696, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45895680, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.021645489999969, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46551040, "pretransfer_peak_rss_bytes": 45895680, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-attribution-metadata-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `78c3f6b10e4832a47f6b66d63c118e8f5b6301d1b5e3dd0da39bb24b456adb2d`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-metadata-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `e108abbb20fce9f7a05a9827964d364867a2949a2152ef238d631ef9cae46528`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-metadata-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `a59f4e4cfab1e212d18e20091db94b088b581bf10b602f582365cf1b65a31013`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-metadata-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `cc374fc43c7c3908c14795821fe1f7e80f111298dcaaad2245e785f6d8e827c4`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "ca8274df5c269209bee2833ba9badaad743779c192db4c5cfaa5de7688109672", "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `41d25e45a892a3a9b561f121257c3c039a64f38d869c3b58a3b22a8c9be08c68`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 228.53932800001076, "baseline/context": 182.15765800005101, "baseline/help": 39.38455200000135, "baseline/version": 39.9670319999359, "candidate/cache": 229.46871099998134, "candidate/context": 184.10014000005503, "candidate/help": 38.66146600000775, "candidate/version": 39.87677200007056}, "passed": false, "reason": "validated", "report_sha256": "ca8274df5c269209bee2833ba9badaad743779c192db4c5cfaa5de7688109672", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41362141850", "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `ca8274df5c269209bee2833ba9badaad743779c192db4c5cfaa5de7688109672`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 228.53932800001076, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 182.15765800005101, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.38455200000135, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 39.9670319999359, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 229.46871099998134, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 184.10014000005503, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 38.66146600000775, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 39.87677200007056, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `6698532c9ac08fe8ef003dd6ad85625e9ab7e97dde253a6526b5a1ebdb2cffc6`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45379584, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.165193269999918, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46034944, "pretransfer_peak_rss_bytes": 45379584, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52387840, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08301613300000099, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52387840, "pretransfer_peak_rss_bytes": 52387840, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45613056, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.2976646869999513, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46268416, "pretransfer_peak_rss_bytes": 45613056, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-attribution-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f984585b096a21e2a2b893557beb5f105cf0b0d054604073694095fb668c1d15`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `55a47cfcede15b472dcce1fe1a63853137e77f1e497db46b3a20c5df7d053e20`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-attribution-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `970171a0cafbf5af5a830c608df8f09bb09778fe4e344b26357d2493b93bc5b7`.
**Yerel arşiv:** `raw/p02-1-pr13-attribution-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-closing-doc-metadata-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `47c61a10612e92e179788ec3f87e0a71a1a27c5bb00efff6a6f2ac817d2fe2fa`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "c0a8e4cb52ab30d44d23aecf49cf8fb61f7d8477899a331e7b8025b55643e01a", "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-metadata-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `edb41d76e0fba539ff6c8996be7b17cea9cf2f12a976665b2bfe2f0368353dbf`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 217.19071699999404, "baseline/context": 169.73907500005225, "baseline/help": 38.666841999997814, "baseline/version": 37.46523500001331, "candidate/cache": 218.74395299994376, "candidate/context": 175.21457999998802, "candidate/help": 38.85751799998616, "candidate/version": 37.76736899999378}, "passed": false, "reason": "validated", "report_sha256": "c0a8e4cb52ab30d44d23aecf49cf8fb61f7d8477899a331e7b8025b55643e01a", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41360846538", "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-metadata-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `c0a8e4cb52ab30d44d23aecf49cf8fb61f7d8477899a331e7b8025b55643e01a`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 217.19071699999404, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 169.73907500005225, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 38.666841999997814, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 37.46523500001331, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 218.74395299994376, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 175.21457999998802, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 38.85751799998616, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 37.76736899999378, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-metadata-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `1be33a90b7a3c63106d0cfa985f42412c570e8ef4ac2f958bc8aa62f60ee2204`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45572096, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.111685913999963, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46227456, "pretransfer_peak_rss_bytes": 45572096, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52269056, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08178235700006553, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52269056, "pretransfer_peak_rss_bytes": 52269056, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45518848, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3283861720000232, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46174208, "pretransfer_peak_rss_bytes": 45518848, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-closing-doc-metadata-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f33e5e20ceb0c15e00a2c6a9b16ddb3f8b4f85b95889ff878e6425bc49db962a`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-metadata-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `940b58b7ddd54847b5acc74f907567a09ff8f58000ccd16219ac80eb1293d1bb`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-metadata-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `1629033bf10ecc0feb8ea2f5ba624488701cc55dbb5346e20882bd296fff1dfc`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-metadata-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `d14fbdcb7eb5b4a3accb6f7b2e414b54009ab38837b2da4f839b57dcc692611e`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "c657327593abcc5eb45b9f51b46d97d2ded18bc9d483693a33a3bdf54c09c913", "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `1cce7201a399b524f5d4983bd2f2d37ba2a20a5b481f7b8fd37ac4d98f0a3f52`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 219.35144399992623, "baseline/context": 174.29799300009563, "baseline/help": 39.961588000096526, "baseline/version": 39.678168999898844, "candidate/cache": 219.21617199996035, "candidate/context": 173.98411800002123, "candidate/help": 39.31768600000396, "candidate/version": 38.50735399998939}, "passed": false, "reason": "validated", "report_sha256": "c657327593abcc5eb45b9f51b46d97d2ded18bc9d483693a33a3bdf54c09c913", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41360483175", "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `c657327593abcc5eb45b9f51b46d97d2ded18bc9d483693a33a3bdf54c09c913`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 219.35144399992623, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 174.29799300009563, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.961588000096526, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 39.678168999898844, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 219.21617199996035, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 173.98411800002123, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 39.31768600000396, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 38.50735399998939, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `bdcf01aff72ba7628668867f21c0ea26df821481c16efac836e07906cbb15c81`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46145536, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.077145986000005, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46800896, "pretransfer_peak_rss_bytes": 46145536, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52711424, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08355703500001255, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52711424, "pretransfer_peak_rss_bytes": 52711424, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46022656, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.2954434810000066, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46678016, "pretransfer_peak_rss_bytes": 46022656, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-closing-doc-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f949fcc30a352df5d724b88360bef1f6b2f2cda88d335f3f1e40ddcc7e5f9f29`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `1afabdfd469f536edf335fdbb042c8d7302b566041d002ddca405b899caba500`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-closing-doc-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f17de6da303166bf567bcf1fc6e4af9b11485bb670adeaff8a35363556409faf`.
**Yerel arşiv:** `raw/p02-1-pr13-closing-doc-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "cba539e44f96b16c14a2876e1f13e21a5412e063"}`.

## p02-1-pr13-development-merge-ci-summary

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `37d5695399143a6a4593fb946a0984c24ecdb9c073d5e1f2134ca8ad4c2e48d7`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-ci-summary.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "merge_ci_and_source_bindings_retained", "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-development-merge-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `04d9661ba10be52b1ebd1c4f553e8b3e41a6f8eb23375aca6fb902554be762bc`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "ea5790a17a86d7781e23e109028397513d0fc42cf86076633abd30282f5967d7", "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-development-merge-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `49e0211339889f0eb9263f405e3aac65006365bccea2f7c67c6035e40c8aa970`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 139.35366600003363, "baseline/context": 111.47840299997824, "baseline/help": 28.002960999970128, "baseline/version": 27.51091900006486, "candidate/cache": 146.37343499998678, "candidate/context": 112.16361900005722, "candidate/help": 28.160005000017918, "candidate/version": 26.593791999971472}, "passed": true, "reason": "validated", "report_sha256": "ea5790a17a86d7781e23e109028397513d0fc42cf86076633abd30282f5967d7", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41421700834", "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-development-merge-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `ea5790a17a86d7781e23e109028397513d0fc42cf86076633abd30282f5967d7`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 139.35366600003363, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 111.47840299997824, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 28.002960999970128, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 27.51091900006486, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 146.37343499998678, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 112.16361900005722, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.160005000017918, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 26.593791999971472, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-development-merge-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `e9b1b270b60f20d45b0207e5d8a6302fb7de84f14f3a889147192fa8f1292f68`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45789184, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.2756296500000417, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46313472, "pretransfer_peak_rss_bytes": 45789184, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51552256, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.05609997499993824, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 294912, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51847168, "pretransfer_peak_rss_bytes": 51847168, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45731840, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.5576960699999063, "extra_rss_lower_bound_bytes": 786432, "extra_rss_upper_bound_bytes": 786432, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46518272, "pretransfer_peak_rss_bytes": 45731840, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 786432, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 786432, "upper_bound_bytes": [294912, 786432, 524288]}, "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-development-merge-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `4d6d9dfc7fca20bcd14d827f1092252115073a215cc9088df6d12bc547980f37`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-development-merge-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `57c4aa74fd181f40fe3e2a08a2892085fbb8784bb9659357c921bbac21c846aa`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-development-merge-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `0f5b296599f75a2856dc7fef4b602474a7e5ed06bff0756f9b02e1fa6a3518e8`.
**Yerel arşiv:** `raw/p02-1-pr13-development-merge-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "50d68b1deab80d6fe14749d556efde1f103b5759"}`.

## p02-1-pr13-metadata-cancelled-a-cancelled

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `3aef45ddaf90d35ef9bd84629e44a869defb06abff493345b98071ff2615c8bc`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-cancelled-a-cancelled.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_cancelled_before_native_measurement", "source_commit": "d4f4e82f7a8bcc8302f959b681d531c99a9e2611"}`.

## p02-1-pr13-metadata-cancelled-b-cancelled

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `7e1affc3a26e662e05158ccb21dbeba5b52980d7cebb62b87f528a29496880c3`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-cancelled-b-cancelled.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_cancelled_before_native_measurement", "source_commit": "d4f4e82f7a8bcc8302f959b681d531c99a9e2611"}`.

## p02-1-pr13-metadata-completed-ci-summary

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `78bf9fd3bfa5e19f5e21bfef18d1a71b40ae2c005fb029430f07de2cdce8aa11`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-ci-summary.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "three_environment_metadata_ci_passed", "source_commit": "d4f4e82f7a8bcc8302f959b681d531c99a9e2611"}`.

## p02-1-pr13-metadata-completed-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `34ddce171a4ef24838f1600fb72be8e6785957a8f472f25a29e3da79c1ed277c`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "403daaebf5755d0f45f29c30312abe5eacb6a62793b9aac3dde343f2a323360f", "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-metadata-completed-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `d25b194e45b256e16c07b5be7e6328c34e3d83f2e3f9b767504b745f0e3e3c9d`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 236.06825600006687, "baseline/context": 183.70350600002894, "baseline/help": 40.42499499996666, "baseline/version": 39.60524000001442, "candidate/cache": 239.67205700000704, "candidate/context": 184.3269199999895, "candidate/help": 40.91216599999825, "candidate/version": 40.709708000008504}, "passed": false, "reason": "validated", "report_sha256": "403daaebf5755d0f45f29c30312abe5eacb6a62793b9aac3dde343f2a323360f", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41358876501", "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-metadata-completed-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `403daaebf5755d0f45f29c30312abe5eacb6a62793b9aac3dde343f2a323360f`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 236.06825600006687, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 183.70350600002894, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 40.42499499996666, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 39.60524000001442, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 239.67205700000704, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 184.3269199999895, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 40.91216599999825, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 40.709708000008504, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-metadata-completed-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `564190e0dd38db35fa7dee42c8166110507c9a16829a92198b5c1c583c511b89`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45506560, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.523858888999939, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46161920, "pretransfer_peak_rss_bytes": 45506560, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51007488, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.09043408100001216, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 438272, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51445760, "pretransfer_peak_rss_bytes": 51445760, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45494272, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3847442729999102, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46018560, "pretransfer_peak_rss_bytes": 45494272, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [438272, 524288, 655360]}, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-metadata-completed-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `23ef09b341125538683d09637edc086c4a70550d8c6dcd64f8864ed9a9bd456e`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-metadata-completed-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `60bd8df6b66122a7224c023edf0e124715325eb61a4ed8a3ba4d0de84956bbe6`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-metadata-completed-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `14eec57a52b1f169899830c90e745645182dbe182b4df217a09ca29a1e07e43d`.
**Yerel arşiv:** `raw/p02-1-pr13-metadata-completed-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-opened-ci-summary

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `e7df1e16458de587654edd9658997ad81d06beef10a596a55748744ec3523811`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-ci-summary.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "three_environment_source_ci_passed", "source_commit": "d4f4e82f7a8bcc8302f959b681d531c99a9e2611"}`.

## p02-1-pr13-opened-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `d77338b8f984cabce1111ddb66c552644a0bc7da287fdf9a5108c41a680c81ff`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "3512dfebe3a44530a8c4ff8036a47131f065435b4c461a9e22cca9fbbd68f2eb", "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-opened-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `97cf19f81c2fa35cf328deb4e856759a52b2bf2fd19ea91c0e1d20514c773277`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 341.91757100006726, "baseline/context": 131.04454899996654, "baseline/help": 31.080272999929548, "baseline/version": 30.647519000012835, "candidate/cache": 365.9347520000438, "candidate/context": 130.4210250000324, "candidate/help": 31.87316399998963, "candidate/version": 30.75104000004103}, "passed": false, "reason": "validated", "report_sha256": "3512dfebe3a44530a8c4ff8036a47131f065435b4c461a9e22cca9fbbd68f2eb", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41358541265", "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-opened-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `3512dfebe3a44530a8c4ff8036a47131f065435b4c461a9e22cca9fbbd68f2eb`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 341.91757100006726, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 131.04454899996654, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 31.080272999929548, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 30.647519000012835, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 365.9347520000438, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 130.4210250000324, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 31.87316399998963, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.75104000004103, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-opened-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `9c5ce9a14fe77f4bb16dbe39d23030eb68009950d01ba29edd0f394766091915`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46338048, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 3.0300421470000174, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46993408, "pretransfer_peak_rss_bytes": 46338048, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52228096, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.04983876500000406, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 167936, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52396032, "pretransfer_peak_rss_bytes": 52396032, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46305280, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7486634460000232, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46829568, "pretransfer_peak_rss_bytes": 46305280, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [167936, 524288, 655360]}, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-opened-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `204ea1ee2e6ff93852c5dc36f010a12877b5c1681c3096edda39c029547d37c3`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-opened-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `ff77c5a7e67d08559a13f0089e42408bfdff2d1736148b38f543de855c00ec5b`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-opened-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `23d6011b874a0af7f96ec833fb4142888b7d878c6979338b989ad05510d2b43d`.
**Yerel arşiv:** `raw/p02-1-pr13-opened-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "e79eff2bae77b895eda9c98143ce11922b535c4f"}`.

## p02-1-pr13-readme-closing-a-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `1adc0cf3d6133ebe1ec4f1d67723d98edaa5c716a44f287039dc7c0c63ad9c1a`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "b0e636d588d924c96c3a341c57efc8f993294d54d17887682782ad737287ef3b", "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-a-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `b91bebb57d45354ce78d5bffea4c84b011cb24f7dbddd7ac483612f41d1f90d4`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 124.43429400002515, "baseline/context": 99.51187699999764, "baseline/help": 23.100647999967805, "baseline/version": 23.421283999994102, "candidate/cache": 120.57150100008585, "candidate/context": 96.31136199999446, "candidate/help": 23.289928999986387, "candidate/version": 23.081579999995938}, "passed": true, "reason": "validated", "report_sha256": "b0e636d588d924c96c3a341c57efc8f993294d54d17887682782ad737287ef3b", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41415406202", "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-a-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `b0e636d588d924c96c3a341c57efc8f993294d54d17887682782ad737287ef3b`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 124.43429400002515, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 99.51187699999764, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.100647999967805, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.421283999994102, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 120.57150100008585, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 96.31136199999446, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.289928999986387, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.081579999995938, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-a-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `b19cc40aefaa3c0a86f6b1ff403013f10d43a6a048e97d6167aa91bcb7dc5059`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46043136, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.1618272040000193, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46567424, "pretransfer_peak_rss_bytes": 46043136, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51666944, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.03454391900004339, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 147456, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51814400, "pretransfer_peak_rss_bytes": 51814400, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46166016, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.5416449800000009, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46821376, "pretransfer_peak_rss_bytes": 46166016, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [147456, 655360, 524288]}, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-readme-closing-a-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f86890416ee52de27161d6d77e9abd7f7466d1c79192f92a3c901c20df37aea1`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-a-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `1b67a48c4d299054c7f174bfbcb89254f192d6254ae6c9f6fc37469fbe8438d5`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-a-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `df8307c3c5bc807f4c7e25dafd0edb44064f6bd2c2a978c0d4ddca29ae1431e5`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-a-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-b-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `38a33f6d0a03f83e824639012c2af8de283bdf0143552f52ae49c760e36da085`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "dbe7ae7a54f093c42b9f64235b0ffa839329f522dfc9e71ed95c5336add9bb2c", "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-b-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `c2b808a09b516dd20bd47ae5086edb0b7a3a7a9ac6f6d88e95eebeb0c4896777`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 202.4726949999831, "baseline/context": 157.654277000006, "baseline/help": 35.98029700003735, "baseline/version": 34.960554000008415, "candidate/cache": 198.92366700003095, "candidate/context": 157.91478699998152, "candidate/help": 36.19920200003435, "candidate/version": 36.078164999935325}, "passed": true, "reason": "validated", "report_sha256": "dbe7ae7a54f093c42b9f64235b0ffa839329f522dfc9e71ed95c5336add9bb2c", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41415407204", "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-b-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `dbe7ae7a54f093c42b9f64235b0ffa839329f522dfc9e71ed95c5336add9bb2c`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 202.4726949999831, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 157.654277000006, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 35.98029700003735, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 34.960554000008415, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 198.92366700003095, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 157.91478699998152, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 36.19920200003435, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 36.078164999935325, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-b-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `a9172f0e38fb991be103bd2b3b443510d54541ea0c09c6c966d4f84e5e552b95`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46010368, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 3.7744065580000097, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46534656, "pretransfer_peak_rss_bytes": 46010368, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51621888, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.06206540900006985, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 32768, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51654656, "pretransfer_peak_rss_bytes": 51654656, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45666304, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.958893503000013, "extra_rss_lower_bound_bytes": 393216, "extra_rss_upper_bound_bytes": 393216, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46059520, "pretransfer_peak_rss_bytes": 45666304, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 393216, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 524288, "upper_bound_bytes": [32768, 393216, 524288]}, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-readme-closing-b-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `c8adb0bef81f8d7b0a8946b4323e9f0bcb5940723b04ae2b8f6b15f538838aa7`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-b-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `be5c7770305c395882b5d7a4c528bd9bb6d7976374f5c9c81ca2ab54aa8b66e5`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-readme-closing-b-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `148d0e9e373621b89743191f12fe91d2164efb9fbb921d4ef012f1bbc70fb30b`.
**Yerel arşiv:** `raw/p02-1-pr13-readme-closing-b-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "c4bcf762af46f5cc4bb3b802cc4937c2ca05b1f8"}`.

## p02-1-pr13-review-followup-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `b6b1cf27d794b1314e311493f94a7cb12dea6dce10e9686d366638d7b3035f80`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "f7c881410645352e0c208f65218f1180b0dae858d8d4a8b90f849a1c712fbc5d", "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-review-followup-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `f1ddd160008166054ad7cd812c0ff630044bf3b582b5b6351f58294418f514be`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 220.71199199990588, "baseline/context": 179.7374679999848, "baseline/help": 41.216265999992174, "baseline/version": 39.71587499995621, "candidate/cache": 219.34909499998412, "candidate/context": 180.87091799998234, "candidate/help": 42.40574800007835, "candidate/version": 39.30313399996521}, "passed": false, "reason": "validated", "report_sha256": "f7c881410645352e0c208f65218f1180b0dae858d8d4a8b90f849a1c712fbc5d", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41399407663", "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-review-followup-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `f7c881410645352e0c208f65218f1180b0dae858d8d4a8b90f849a1c712fbc5d`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 220.71199199990588, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 179.7374679999848, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 41.216265999992174, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 39.71587499995621, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 219.34909499998412, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 180.87091799998234, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 42.40574800007835, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 39.30313399996521, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-review-followup-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `d6f45650e5c28f8bbd36f86440790d9a5e89efbf7c6ed8ca1d9824d18dab7e0d`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45461504, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.173974242000099, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46116864, "pretransfer_peak_rss_bytes": 45461504, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52322304, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08580184000004465, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52322304, "pretransfer_peak_rss_bytes": 52322304, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45617152, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.297981512999968, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46272512, "pretransfer_peak_rss_bytes": 45617152, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 655360]}, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-review-followup-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `dd40f73012b326994e9af9c9315ec9a6ccdcf78957b82cdeadd88769937c502c`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-review-followup-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `39fa9451fad8b90e9d333d189341c557623c560f1b53ab44ef4753921b35ed77`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-review-followup-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `179940a55bf653e9397a139bb0d6f4b09c415b548f4511b85a1d76772851967f`.
**Yerel arşiv:** `raw/p02-1-pr13-review-followup-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "613500ab0f3070648154b33b7f731707dc9c645f"}`.

## p02-1-pr13-review-retention-audit

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `bd3827ed8c95d1b02f3f0015abff0bae0a5d57263987bfbfa3bdc173c6b4a79a`.
**Yerel arşiv:** `raw/p02-1-pr13-review-retention-audit.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "pr13_review_retention_verified", "source_commit": "1765eeab78b3c033bb0412fc342869e94150d9ef"}`.

## p02-1-pr13-user-review-cancelled-metadata-cancelled

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `6912964e19b4020d843e5ba6c6d8d15a5537bb2df660b86a03152aa934c232ed`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-cancelled-metadata-cancelled.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_cancelled_before_native_measurement", "source_commit": "1bfd2b16adfa941b1786650360f22d7f7b06bb55"}`.

## p02-1-pr13-user-review-metadata-failed-failure

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `f46fdcd79cac4193b24f8bb2062d4afc64655125487a9be32dfa2634c8647d98`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-failure.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_test_failure_recorded", "source_commit": "1bfd2b16adfa941b1786650360f22d7f7b06bb55"}`.

## p02-1-pr13-user-review-metadata-failed-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `b59c6d24ba59b47ba2afa18497026842eef185d6839292c10393116b62630e05`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "d42d2b5ee5764c6ddba46cb9bf5d1fe4640be965ed1abd56803af5974b85ef92", "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-metadata-failed-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `7c1b877e1586712f0a26f5974c15d0f389e1a62942bb422e59f3cf637d4e38eb`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 145.7550639998999, "baseline/context": 114.88992199997483, "baseline/help": 24.12065300006816, "baseline/version": 25.082575999931578, "candidate/cache": 153.9492849999533, "candidate/context": 107.31571000007989, "candidate/help": 24.483952000082354, "candidate/version": 24.884375999931763}, "passed": true, "reason": "validated", "report_sha256": "d42d2b5ee5764c6ddba46cb9bf5d1fe4640be965ed1abd56803af5974b85ef92", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41403813118", "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-metadata-failed-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `d42d2b5ee5764c6ddba46cb9bf5d1fe4640be965ed1abd56803af5974b85ef92`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 145.7550639998999, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 114.88992199997483, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.12065300006816, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 25.082575999931578, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 153.9492849999533, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 107.31571000007989, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.483952000082354, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.884375999931763, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-metadata-failed-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `e9822c01ce1db7f445156dd701f04e25858bf15ea049683924f315e47db5d84c`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46514176, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.3009591989999763, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 47169536, "pretransfer_peak_rss_bytes": 46514176, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52133888, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.038698214000078224, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 151552, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52285440, "pretransfer_peak_rss_bytes": 52285440, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46546944, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.5792545790000077, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 47071232, "pretransfer_peak_rss_bytes": 46546944, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [151552, 524288, 655360]}, "source_commit": "935137518637773b58728dcfa4677e01d512f613", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-user-review-metadata-failed-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `e83aa2bd5bf596dcf96ae872f7189267ae1ec388883b31da88ab8bf06524a6e3`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-metadata-failed-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `ab97705ef04e8b76283aa980a28c577f893a999cbac667fdfbe8f683a53e3b6d`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-metadata-failed-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `68df3cda98cbefd6e7c24100d89013d800ceb919139a50b83f206fcb51eb5b38`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "95e754923084a71d6f7873538f951a412740ae0ada137951cb43e59539c1e72b", "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `ec0669c28c61fbfa199e13115ffaf50d531186b9f1c750c90fc405a4c85c2e64`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 216.77875199998198, "baseline/context": 177.5497840000071, "baseline/help": 39.06915400000344, "baseline/version": 38.990034999983436, "candidate/cache": 218.35750500008544, "candidate/context": 178.50424499999917, "candidate/help": 39.52099600007841, "candidate/version": 39.39444700006334}, "passed": false, "reason": "validated", "report_sha256": "95e754923084a71d6f7873538f951a412740ae0ada137951cb43e59539c1e72b", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41403463587", "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `95e754923084a71d6f7873538f951a412740ae0ada137951cb43e59539c1e72b`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 216.77875199998198, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 177.5497840000071, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 39.06915400000344, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.990034999983436, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 218.35750500008544, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 178.50424499999917, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 39.52099600007841, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 39.39444700006334, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `8bf3fc6a86590e6c866fc9f168932c19a165fc171c09ff22077b620a0f30a61c`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45940736, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.1454906080000455, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46465024, "pretransfer_peak_rss_bytes": 45940736, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51585024, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08335896900007356, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 319488, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51904512, "pretransfer_peak_rss_bytes": 51904512, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45981696, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.3139429870000185, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46505984, "pretransfer_peak_rss_bytes": 45981696, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 524288, "upper_bound_bytes": [319488, 524288, 524288]}, "source_commit": "935137518637773b58728dcfa4677e01d512f613", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-user-review-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `f3f15acd7e6c9612f5f1fe739fd8e4f8d8229a9f3a92194a0a4e91ec803d5dd1`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `4c7e8ae9de2a84dab263343905d3381c2b761054f842761d373d95e73cc7cf8d`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-user-review-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `909cb15fd9f74f64242ca3611c473462c7eb9f3bf5fb47bcb12069666e545b6a`.
**Yerel arşiv:** `raw/p02-1-pr13-user-review-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "935137518637773b58728dcfa4677e01d512f613"}`.

## p02-1-pr13-v3-cancelled-metadata-cancelled

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `4cbeb31f8458ac57bf95b5292e78ea0d1c260f0f6303690acb9f3d6a6b0d4727`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-cancelled-metadata-cancelled.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_cancelled_before_native_measurement", "source_commit": "015300ee12a81264e57fc5e8b18a635be8ae6923"}`.

## p02-1-pr13-v3-final-metadata-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `7ddc07367de924f8056c18dd977cd6a643d94eba382a57e015bd89f352cae240`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "3411fcf91bf560cd3f1392d94202d46b474324fc886af086ec815cb382e6e308", "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-metadata-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `389b683bc46115ec9192416d08ac3aed7f52a03b666be9fe4d34633641d98545`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 279.3125420000706, "baseline/context": 135.88601900005415, "baseline/help": 32.33362499997838, "baseline/version": 31.355860000076063, "candidate/cache": 261.3482760000352, "candidate/context": 136.51931999993394, "candidate/help": 32.71083999993607, "candidate/version": 31.548747999977422}, "passed": false, "reason": "validated", "report_sha256": "3411fcf91bf560cd3f1392d94202d46b474324fc886af086ec815cb382e6e308", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41409501030", "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-metadata-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `3411fcf91bf560cd3f1392d94202d46b474324fc886af086ec815cb382e6e308`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 279.3125420000706, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 135.88601900005415, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 32.33362499997838, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 31.355860000076063, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 261.3482760000352, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 136.51931999993394, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 32.71083999993607, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 31.548747999977422, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-metadata-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `7a82d9a546734fa45ff2e2eb818b6d57f259550044b5749d70178f387c559c28`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45969408, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 3.051376600000026, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46493696, "pretransfer_peak_rss_bytes": 45969408, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51970048, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.049864108000065244, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 188416, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52158464, "pretransfer_peak_rss_bytes": 52158464, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46256128, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.754227912000033, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46780416, "pretransfer_peak_rss_bytes": 46256128, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 524288, "upper_bound_bytes": [188416, 524288, 524288]}, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-v3-final-metadata-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `0492274a4c8fa015b3a708104b51712df968c465dfde54ec4abba1e2a71cca4d`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-metadata-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `72d4773662197c2edebf9d303e224ae6985c2e4ec8666c9700ce1b5d268448be`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-metadata-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `4061cd0da7796d0fc944e8ba83e991c52d025448773e57c8b846886f0a9c9b46`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-metadata-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-source-linux-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `05448ad4d4068a977195e9cebaad999dfe10f161dbf40fcf1d2d73638f062041`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-linux-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "9f30fd2bad7c3495120b127fefd588b4458d0f07", "report_sha256": "4f2e2365499978c6c7b2f55a60572e8b9d5ec1c531a1c83b9c0d2620f2b41d2c", "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-source-linux-receipt

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `5a82d5bf69c0520630b5397e67148512625be51182f3686c2daac1abf01756c8`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-linux-receipt.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 177.77227700003095, "baseline/context": 137.7587949999679, "baseline/help": 33.89685100000861, "baseline/version": 34.02849899998728, "candidate/cache": 180.66290000001572, "candidate/context": 137.82167200008644, "candidate/help": 34.36066799997661, "candidate/version": 34.148938999919665}, "passed": true, "reason": "validated", "report_sha256": "4f2e2365499978c6c7b2f55a60572e8b9d5ec1c531a1c83b9c0d2620f2b41d2c", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41409081674", "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-source-linux-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `4f2e2365499978c6c7b2f55a60572e8b9d5ec1c531a1c83b9c0d2620f2b41d2c`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-linux-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 177.77227700003095, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 137.7587949999679, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 33.89685100000861, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 34.02849899998728, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 180.66290000001572, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 137.82167200008644, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 34.36066799997661, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 34.148938999919665, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-source-linux-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `300829bf76031a14d381225edb5f8d75a34c55f4cf544edbc89d275d554ab10a`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-linux-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 46325760, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 3.013650847000008, "extra_rss_lower_bound_bytes": 1048576, "extra_rss_upper_bound_bytes": 1048576, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 47374336, "pretransfer_peak_rss_bytes": 46325760, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 52035584, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.04850757300005171, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 73728, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 52109312, "pretransfer_peak_rss_bytes": 52109312, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 46243840, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7536854890000768, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46768128, "pretransfer_peak_rss_bytes": 46243840, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 1048576], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1048576, "upper_bound_bytes": [73728, 524288, 1048576]}, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783", "source_unchanged_during_measurement": true}`.

## p02-1-pr13-v3-final-source-linux311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `0d3299d551a59c4dadd89f7f56529376a0ab106c380339786fd9f57aadbf9cfc`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-source-linux314-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `72bb561b03f39141ea9b46b5bc02b0a895312b8d76850aafb5374889629a0cf2`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-pr13-v3-final-source-macos311-installation

**Tür:** `installation_v2`.
**Özgün JSON SHA-256:** `11b2238506e98e617b84c175dbc1566603a062afeb53cc002ee869b34c7628b3`.
**Yerel arşiv:** `raw/p02-1-pr13-v3-final-source-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v2", "passed": true, "source_commit": "d0e96b8b7c2f590751f6d553eb4bb6d7dba2f783"}`.

## p02-1-review-raw-v3

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `9afb77f4d36417128db6a540a6bb342c1b4839391aa1f6347f62a6634ff78c75`.
**Yerel arşiv:** `raw/p02-1-review-raw-v3.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49856512, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5790082910098135, "extra_rss_lower_bound_bytes": 1228800, "extra_rss_upper_bound_bytes": 1228800, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51085312, "pretransfer_peak_rss_bytes": 49856512, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57409536, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025659083854407072, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57409536, "pretransfer_peak_rss_bytes": 57409536, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49987584, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39838004182092845, "extra_rss_lower_bound_bytes": 49152, "extra_rss_upper_bound_bytes": 49152, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50036736, "pretransfer_peak_rss_bytes": 49987584, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 49152, 1228800], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1228800, "upper_bound_bytes": [0, 49152, 1228800]}, "source_commit": "30c1dcb82ee89d511e4273bb91ce0f76ee03bb93", "source_unchanged_during_measurement": true}`.

## p02-1-review-reference-v3-datasets

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `740f40e5ecbb3f1e52f368509f9042a8ec07182a698dafe2ad76adcb9ac7f342`.
**Yerel arşiv:** `raw/p02-1-review-reference-v3-datasets.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 2949120}, "verify": {"passed": true, "span_upper_bound_bytes": 1064960}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7589513340499252, "max_extra_rss_upper_bound_bytes": 21397504, "passed": true, "source_commit": "30c1dcb82ee89d511e4273bb91ce0f76ee03bb93"}`.

## p02-1-review-reference-v3-jobs

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `6a888301e7e7732ecacb217cde2aa3e29534cdeaaf29686f8711f5001016b4b8`.
**Yerel arşiv:** `raw/p02-1-review-reference-v3-jobs.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 158.2760000601411, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 115.37400004453957, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 105.87099986150861, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 116.97816592641175, "passed": true, "samples": 30}}, "passed": true, "source_commit": "30c1dcb82ee89d511e4273bb91ce0f76ee03bb93", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-1-review-reference-v3-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `130aa2bd474b8329f0ce4d753281c15298962be7c1327e9164be9cd3ec7bb501`.
**Yerel arşiv:** `raw/p02-1-review-reference-v3-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 128.4682909026742, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 76.40124997124076, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 27.848958037793636, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 25.592333171516657, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 133.5624170023948, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 83.67175003513694, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 33.02625007927418, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.90487485192716, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "30c1dcb82ee89d511e4273bb91ce0f76ee03bb93"}`.

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

## p02-2-cache-profile-after08

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `1bdd9c7cc779b4d615b3eeac84f0ba29a7aac08d563b9b4325294f4b5214b558`.
**Yerel arşiv:** `raw/p02-2-cache-profile-after08.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "profiling_diagnostic_only", "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-ci41740901679-incomplete

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `e9de29aa1b93d7cb73b8424c335bc54018a6afd41bf87f5e39642e5d239c099c`.
**Yerel arşiv:** `raw/p02-2-ci41740901679-incomplete.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_ci_incomplete_linux_timeout", "source_commit": "72538f8d6d2550a353931ae45e56421e37692180"}`.

## p02-2-ci41740901679-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `f732def4210be7760ec537cbc1bc3e2089417e1a20686e1773719607d70a1556`.
**Yerel arşiv:** `raw/p02-2-ci41740901679-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "72538f8d6d2550a353931ae45e56421e37692180"}`.

## p02-2-ci41740901679-macos311-sdist-smoke

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `1e61391184de032db85dd22b0f24da63bc43262a5f14b8b9e6d066c12e85e95d`.
**Yerel arşiv:** `raw/p02-2-ci41740901679-macos311-sdist-smoke.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 15, "kind": "rejected-upload", "original_bytes": 220384, "source_commit": "72538f8d6d2550a353931ae45e56421e37692180"}`.

## p02-2-ci41740901679-macos311-wheel-smoke

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `409929b7803905cc93ac3477dea641a0a490c7401fb59dc78eb177b2e75f493d`.
**Yerel arşiv:** `raw/p02-2-ci41740901679-macos311-wheel-smoke.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 15, "kind": "rejected-upload", "original_bytes": 220362, "source_commit": "72538f8d6d2550a353931ae45e56421e37692180"}`.

## p02-2-ci41842539187-test-failure

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `9c967cf171ea0e7a5ab82dea359ae8b9f16231a0fa3f747c33e80014b01a2077`.
**Yerel arşiv:** `raw/p02-2-ci41842539187-test-failure.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_ci_failed_tests", "source_commit": "f749b57a0efc9461dbde66261bcabfbd7699d9f3"}`.

## p02-2-ci41842843032-test-failure

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `4bc0b3a4c995f06cc91de9cf67dbffe612406eee5c4ef6009052a10a8a490eeb`.
**Yerel arşiv:** `raw/p02-2-ci41842843032-test-failure.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "source_ci_failed_tests", "source_commit": "f749b57a0efc9461dbde66261bcabfbd7699d9f3"}`.

## p02-2-ci41854038211-attempt1-audit

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `ec7d67f965ad75ae6dcac2cd2ddd30c8b60485b8d1d1bd974b6991f4de9ebddd`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-attempt1-audit.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "linux_source_ci_passed_macos_runner_unavailable", "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-attempt2-macos-capacity

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `4757a1698e4d4426ac17184110e35b74f1ee1f451b9aface865e00977c4406ae`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-attempt2-macos-capacity.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "hosted_macos_runner_unavailable_again", "source_commit": "7e5675c0b1fc920abff81bd8c486bb4fbeeb8aa1"}`.

## p02-2-ci41854038211-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `2f0af257c2d5b870592367ff31409468297aedde38f99c9f6c67511f1dc481fb`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `bed8070ac0a5b8a8bcc383e9204b93f0c66ee77b81baaeab949b15a4365b7401`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "92ae0dc65009cccd486c4d0688442550809af098b64b1c524c1b8f3026398910", "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `61ec7237b85b574cfaca9fd270682b4864ed793f88ef35ce80cebeee44d24bb7`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 208.48226199996134, "baseline/context": 133.16683400012153, "baseline/help": 31.523758000048474, "baseline/version": 30.53999200005819, "candidate/cache": 348.07453300004454, "candidate/context": 130.22413700014113, "candidate/help": 31.586320999849704, "candidate/version": 30.58074199998373}, "passed": false, "reason": "validated", "report_sha256": "92ae0dc65009cccd486c4d0688442550809af098b64b1c524c1b8f3026398910", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41854038211", "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `92ae0dc65009cccd486c4d0688442550809af098b64b1c524c1b8f3026398910`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 208.48226199996134, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 133.16683400012153, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 31.523758000048474, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 30.53999200005819, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 348.07453300004454, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 130.22413700014113, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 31.586320999849704, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.58074199998373, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-linux311-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `b2b5d06c04e2d12242300c8d0b68ea291af879792054c26ff275c8182438a60b`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux311-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45424640, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 3.045671281000068, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46080000, "pretransfer_peak_rss_bytes": 45424640, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51036160, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.04850093000004563, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 221184, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51257344, "pretransfer_peak_rss_bytes": 51257344, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45563904, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7487915259998772, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46219264, "pretransfer_peak_rss_bytes": 45563904, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 655360], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [221184, 655360, 655360]}, "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19", "source_unchanged_during_measurement": true}`.

## p02-2-ci41854038211-linux311-upload

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `7b006b449589c0f1f0f46bdb46f4a24458eea8476a5e42ff0051cdaa68583674`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux311-upload.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 917504}, "kind": "upload-budget", "max_elapsed_seconds": 85.42642666500001, "max_extra_rss_upper_bound_bytes": 4849664, "passed": true, "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `1c45ea11c4e5a68d68a214ab841ca2c66c8394dcc05f0ca2310d948d26104f6c`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "354559dd5ed2a032ad11cfb19a291ef9241a1f19"}`.

## p02-2-ci41854038211-macos-capacity

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `7ce31194ab9f3e76a6c5425dcefa6c3c8e3685d42ab91a6de9950a8fb230a639`.
**Yerel arşiv:** `raw/p02-2-ci41854038211-macos-capacity.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "hosted_macos_runner_unavailable", "source_commit": "7e5675c0b1fc920abff81bd8c486bb4fbeeb8aa1"}`.

## p02-2-ci41915696824-test-failure

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `9a41f648266dc43cae25e254b16a9fc32e90b73dff8a00f27fd48a9f117e8898`.
**Yerel arşiv:** `raw/p02-2-ci41915696824-test-failure.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_test_failure_audit", "source_commit": "36f9442fbfaca17f07c2603bcc1376b0b92517af"}`.

## p02-2-ci41915766769-test-failure

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `bbbc0a40b0f897404a086242059b12af0527c61f38d2a23e95d57a2e08580b27`.
**Yerel arşiv:** `raw/p02-2-ci41915766769-test-failure.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "ci_test_failure_audit", "source_commit": "36f9442fbfaca17f07c2603bcc1376b0b92517af"}`.

## p02-2-ci41990771680-attempt1-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `6f022a2e62bf1dc69d9bde547534a512ac1d07a758a65348bd5f5ad940bf9c78`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt1-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt1-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `b88bec72d6f32e59071ad2feec014c970aeaee02c2b25f231abc09de9611ef4b`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt1-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "c5e7287b229749af93c3d73d59ebf70103749707f5a6cf65a046475dadc99423", "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt1-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `5b7a27cad0ebf4ddfd631fd4302422154d6e0b8f3db270b56888ade892ddba6f`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt1-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 228.97594899995966, "baseline/context": 180.42460700007723, "baseline/help": 44.92613100001108, "baseline/version": 43.479423000007955, "candidate/cache": 229.71992399993724, "candidate/context": 178.15466999991258, "candidate/help": 44.721668999955, "candidate/version": 42.256005000126606}, "passed": false, "reason": "validated", "report_sha256": "c5e7287b229749af93c3d73d59ebf70103749707f5a6cf65a046475dadc99423", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41990771680", "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt1-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `c5e7287b229749af93c3d73d59ebf70103749707f5a6cf65a046475dadc99423`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt1-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 228.97594899995966, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 180.42460700007723, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 44.92613100001108, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 43.479423000007955, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 229.71992399993724, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 178.15466999991258, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 44.721668999955, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 42.256005000126606, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt2-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `01229bfa89a2960f1f765b2becb28b350b95a44f8173a97b9956aa7ed3356beb`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt2-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt2-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `bf5eadf1fdb2541d4ff25fdd4b51689c6b6310b62bca9487578b8c3c3a36d7bd`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt2-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "7934b07e3f9b5b73f664771294d7518cb89ae97be9a18fc75270129905c3f83d", "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt2-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `41c8762bce4212100520c0f0f52cd9b5bca88735876913255668ff75e60d0897`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt2-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 151.10437800012733, "baseline/context": 136.10601499999575, "baseline/help": 29.855166000061217, "baseline/version": 27.433712999936688, "candidate/cache": 151.88382299993464, "candidate/context": 131.1047100000451, "candidate/help": 30.962948999786022, "candidate/version": 30.35844700002599}, "passed": true, "reason": "validated", "report_sha256": "7934b07e3f9b5b73f664771294d7518cb89ae97be9a18fc75270129905c3f83d", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/41990771680", "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-attempt2-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `7934b07e3f9b5b73f664771294d7518cb89ae97be9a18fc75270129905c3f83d`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-attempt2-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 151.10437800012733, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 136.10601499999575, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 29.855166000061217, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 27.433712999936688, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 151.88382299993464, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 131.1047100000451, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 30.962948999786022, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.35844700002599, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `d9c76d3d55d84ef4836ea7b91202cf1863cb8b310e7c79f287488ed450b4e262`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci41990771680-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `40a6ecca57ed02d44615737e8156ed5f27af230199a2940f703f5120f797b909`.
**Yerel arşiv:** `raw/p02-2-ci41990771680-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "19b65bcde84750d1b74a73ba59140689d59ec3bc"}`.

## p02-2-ci42058897706-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `a343f8c1e090449b9af46f78947101450d0cd6c4f4019d5403f41e32c3feb196`.
**Yerel arşiv:** `raw/p02-2-ci42058897706-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "27d90a126f19a304f71b7116a1c0fb4195c5b956"}`.

## p02-2-ci42058897706-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `5652c1b8f333c12de4b4e7f9f60f726ce9671deefe733ae9113e9cbec7a41220`.
**Yerel arşiv:** `raw/p02-2-ci42058897706-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "71bf0362765b8d49573c8f2330288c0e58809395641130f9212c1fb129233b5e", "source_commit": "27d90a126f19a304f71b7116a1c0fb4195c5b956"}`.

## p02-2-ci42058897706-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `f50212d725ce41e40bb4b3896767426ea650e5776bfe5c9eb61bfffb04fd1283`.
**Yerel arşiv:** `raw/p02-2-ci42058897706-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 237.44157999999516, "baseline/context": 188.2314709998809, "baseline/help": 44.317069000044285, "baseline/version": 43.7602770000467, "candidate/cache": 241.0654320001413, "candidate/context": 181.45453200008888, "candidate/help": 46.31947500001843, "candidate/version": 43.5284899999715}, "passed": false, "reason": "validated", "report_sha256": "71bf0362765b8d49573c8f2330288c0e58809395641130f9212c1fb129233b5e", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/42058897706", "source_commit": "27d90a126f19a304f71b7116a1c0fb4195c5b956"}`.

## p02-2-ci42058897706-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `71bf0362765b8d49573c8f2330288c0e58809395641130f9212c1fb129233b5e`.
**Yerel arşiv:** `raw/p02-2-ci42058897706-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 237.44157999999516, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 188.2314709998809, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 44.317069000044285, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 43.7602770000467, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 241.0654320001413, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 181.45453200008888, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 46.31947500001843, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 43.5284899999715, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "27d90a126f19a304f71b7116a1c0fb4195c5b956"}`.

## p02-2-ci42058897706-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `847de880ce65abe49de26cfbf963e5b2d4bc11ab5d532ac925e3ab16b756dbcf`.
**Yerel arşiv:** `raw/p02-2-ci42058897706-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "27d90a126f19a304f71b7116a1c0fb4195c5b956"}`.

## p02-2-ci42058897706-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `aa26770ff9692b7ab73f9694b7356e7f492e777031e7e190df73af2960745840`.
**Yerel arşiv:** `raw/p02-2-ci42058897706-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "27d90a126f19a304f71b7116a1c0fb4195c5b956"}`.

## p02-2-ci42071837939-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `4c3fdc18da27e020201116a1b0520b935ce6b1e36d466bfe81cf56c6bd9451a2`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42071837939-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `cc37516d18778787583e2ae8d6b86c4ef2d1bba9a97da3ca3a9c303b7e8220bd`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "0259b2a000c0b963e1acb22f0ec7a039dcf561ca53bf9320184363a5f1177f21", "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42071837939-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `5c884a5db6eb5079c80cc87042f721e381ab4ca86a1946ec4fced19fdfc47e89`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 166.2156810000397, "baseline/context": 131.5870900000391, "baseline/help": 31.461959999887767, "baseline/version": 30.600597000102425, "candidate/cache": 166.42328599982648, "candidate/context": 128.30226299979586, "candidate/help": 31.561845999931393, "candidate/version": 30.571293000093647}, "passed": true, "reason": "validated", "report_sha256": "0259b2a000c0b963e1acb22f0ec7a039dcf561ca53bf9320184363a5f1177f21", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/42071837939", "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42071837939-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `0259b2a000c0b963e1acb22f0ec7a039dcf561ca53bf9320184363a5f1177f21`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 166.2156810000397, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 131.5870900000391, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 31.461959999887767, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 30.600597000102425, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 166.42328599982648, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 128.30226299979586, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 31.561845999931393, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 30.571293000093647, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42071837939-linux311-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `cc05a3e2be82fd6fc5605108c2e2293f229d2bba4b261429e68aac1f7bb91561`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux311-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45674496, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 3.068494127000122, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 46198784, "pretransfer_peak_rss_bytes": 45674496, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51150848, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.05266792499992334, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 65536, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51216384, "pretransfer_peak_rss_bytes": 51216384, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45473792, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7454134730000987, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45998080, "pretransfer_peak_rss_bytes": 45473792, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 524288, "upper_bound_bytes": [65536, 524288, 524288]}, "source_commit": "102efefca4a617848ba73883aadd73be7b699233", "source_unchanged_during_measurement": true}`.

## p02-2-ci42071837939-linux311-upload

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `4b41c0576766de30dfb17e754eb2ff0d3c4e43fbebaaa849f8ad47d3dd818d1b`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux311-upload.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 786432}, "kind": "upload-budget", "max_elapsed_seconds": 83.80454336899993, "max_extra_rss_upper_bound_bytes": 4849664, "passed": true, "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42071837939-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `762cb7f630d4d9d7287bb866d03524105b95676ebfe1479cad9ccc7c7a21c539`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42071837939-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `cb5ff929e515436cee2b7c379fe2b769087cc07801c5105a2d9201b4f3204859`.
**Yerel arşiv:** `raw/p02-2-ci42071837939-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "102efefca4a617848ba73883aadd73be7b699233"}`.

## p02-2-ci42108426487-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `e2a6828ec6cc2ebca4412d84f63db0f33cffaf1290824024876312f219adcebe`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108426487-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `2a7f0f1fc59af151327484a70aaba29fff8f16082b050acd8602a986f8398d7b`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "4d16043ef2222354634f1ea3535f153996c40a27eace34aa83c7b81d55f48fa0", "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108426487-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `49367233ed47ce0c9495d96f622696048884ce3ef51170de54242faae2c14b47`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 180.1263930001369, "baseline/context": 145.03942100009226, "baseline/help": 35.51558100002694, "baseline/version": 34.17155199986155, "candidate/cache": 180.78397999988738, "candidate/context": 140.7674179999958, "candidate/help": 35.67434900014632, "candidate/version": 34.621618000073795}, "passed": true, "reason": "validated", "report_sha256": "4d16043ef2222354634f1ea3535f153996c40a27eace34aa83c7b81d55f48fa0", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/42108426487", "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108426487-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `4d16043ef2222354634f1ea3535f153996c40a27eace34aa83c7b81d55f48fa0`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 180.1263930001369, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 145.03942100009226, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 35.51558100002694, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 34.17155199986155, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 180.78397999988738, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 140.7674179999958, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 35.67434900014632, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 34.621618000073795, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108426487-linux311-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `dba6c213960c0ea94a030b0d67f14f04f34de107ad4d00841c0faba2cbca2970`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux311-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 44896256, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.969231495000031, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45420544, "pretransfer_peak_rss_bytes": 44896256, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 50786304, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.0491739740000412, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50786304, "pretransfer_peak_rss_bytes": 50786304, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 44961792, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.7396127570000317, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45617152, "pretransfer_peak_rss_bytes": 44961792, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 524288], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [0, 655360, 524288]}, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d", "source_unchanged_during_measurement": true}`.

## p02-2-ci42108426487-linux311-upload

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `4b6c3b2e267eaa979b5a1875f302ced3f1bf6cf0369c6f5944d780cc98290ebe`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux311-upload.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 917504}, "kind": "upload-budget", "max_elapsed_seconds": 87.84440199599999, "max_extra_rss_upper_bound_bytes": 4587520, "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108426487-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `df56b5d3af0eb0d138f80582ee9b303e0da58b913a8d9572e98c60b89ea65cf2`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108426487-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `a2f9cb8f78e43d802d9e8562647fc64c8fbe78c6b65b70acf3f0fbf34d624efb`.
**Yerel arşiv:** `raw/p02-2-ci42108426487-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `e2a6828ec6cc2ebca4412d84f63db0f33cffaf1290824024876312f219adcebe`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `9a5914ebd75ab36b8f08ad6e3a94d75de8de2413af5d7a2e2dd2dcca51cd5c1f`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "49382540cd30e778ce07717aff7b7acd74394af096d4b380d872d2c8c14298ca", "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `54f4d362383a6392a123daebf9592a3af1f17bdb59a3ebcc62d3de2f20e327cb`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "diagnostic_budget_exceeded", "p95_ms": {"baseline/cache": 216.11519400016732, "baseline/context": 173.2382250002047, "baseline/help": 38.95304599996052, "baseline/version": 38.2488039999771, "candidate/cache": 216.4422480000212, "candidate/context": 167.13666800001192, "candidate/help": 39.08866200004013, "candidate/version": 37.80447899998762}, "passed": false, "reason": "validated", "report_sha256": "49382540cd30e778ce07717aff7b7acd74394af096d4b380d872d2c8c14298ca", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/42108795043", "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `49382540cd30e778ce07717aff7b7acd74394af096d4b380d872d2c8c14298ca`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 216.11519400016732, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 173.2382250002047, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 38.95304599996052, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.2488039999771, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 216.4422480000212, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 167.13666800001192, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 39.08866200004013, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 37.80447899998762, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-linux311-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `a45cb7660330915e1073de435e86bbe97bf934c3aca4f236f0ff0bebf2b05ba6`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux311-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45604864, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 5.047764548000032, "extra_rss_lower_bound_bytes": 393216, "extra_rss_upper_bound_bytes": 393216, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45998080, "pretransfer_peak_rss_bytes": 45604864, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51286016, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.08153970100011065, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 348160, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51634176, "pretransfer_peak_rss_bytes": 51634176, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45297664, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 1.320314714999995, "extra_rss_lower_bound_bytes": 655360, "extra_rss_upper_bound_bytes": 655360, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45953024, "pretransfer_peak_rss_bytes": 45297664, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 655360, 393216], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 655360, "upper_bound_bytes": [348160, 655360, 393216]}, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d", "source_unchanged_during_measurement": true}`.

## p02-2-ci42108795043-linux311-upload

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `6731ad928d468e7c90b70b0f8f9d19da6d82e1f326923e7ef55c1748a27bf208`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux311-upload.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 393216}, "kind": "upload-budget", "max_elapsed_seconds": 106.8629969220001, "max_extra_rss_upper_bound_bytes": 4718592, "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `df56b5d3af0eb0d138f80582ee9b303e0da58b913a8d9572e98c60b89ea65cf2`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-ci42108795043-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `a2f9cb8f78e43d802d9e8562647fc64c8fbe78c6b65b70acf3f0fbf34d624efb`.
**Yerel arşiv:** `raw/p02-2-ci42108795043-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "edf563123a5584daa02dd318b69440ebd14d0d5d"}`.

## p02-2-final-installations-01

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `ebd4127fac0a29f09eb4449804d6f228eb488bf2988a1b94d3754faa9c04e79e`.
**Yerel arşiv:** `raw/p02-2-final-installations-01.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "eab79e6a2d9ab29b5726272de4e85b49ebda21af"}`.

## p02-2-final-installations-02

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `447c28879805c893365b67da072875979a3458746ccd1f051d8e590b0b736c78`.
**Yerel arşiv:** `raw/p02-2-final-installations-02.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "fad497745c74291efa96a518adf1d45fa9d5bebe"}`.

## p02-2-final-live-20261104-incomplete

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `4cd3344426902e25a55f048248137fe6db9cf8c6e5a452ccebdc1ea014aed1cd`.
**Yerel arşiv:** `raw/p02-2-final-live-20261104-incomplete.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "live_acceptance_incomplete_after_accepted_create", "source_commit": "b9f310168c23aa20117c621a7878d966d599a6c2"}`.

## p02-2-final-live-20261104-r2-incomplete

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `837e92f4e01481ac7a151f380b0f522bb6f7b4d98e26221cba51e7dfe44b3e4a`.
**Yerel arşiv:** `raw/p02-2-final-live-20261104-r2-incomplete.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "incomplete", "source_commit": "59ff11aeac026e06b8e62b39275d3d41ca0e8b0b"}`.

## p02-2-final-live-20261104-r3-incomplete

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `d27fe776236a47f90f10871c44f337212d257bea79b40dd3706280834dea8e0f`.
**Yerel arşiv:** `raw/p02-2-final-live-20261104-r3-incomplete.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "incomplete", "source_commit": "ee5afce496ffba64f1901fdfbacef424cb8ef175"}`.

## p02-2-final-live-20261104-r4-incomplete

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `298412df16d2a66d763f70f1a6ec28e920b867cc785643ab299e653e9c613036`.
**Yerel arşiv:** `raw/p02-2-final-live-20261104-r4-incomplete.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "incomplete", "source_commit": "b5f293bf31f92f2c2b8b648a3cf2a5b2a101e789"}`.

## p02-2-final-live-20261104-r5

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `55246cde953d7d15dca1d6dcd1c2b9fe8819bf67e1fdb97977f3d1d8fe787520`.
**Yerel arşiv:** `raw/p02-2-final-live-20261104-r5.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "metadata_succeeded", "source_commit": "ca0d29c8dd5c88da0e99ff3714235546a858f192"}`.

## p02-2-jobs-codec-profile-after08

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `e271b0539ea547b1f3cafb9f4c0166aef6d08545450586193ae830108aa79fd5`.
**Yerel arşiv:** `raw/p02-2-jobs-codec-profile-after08.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "profiling_diagnostic_only", "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-link-contract-20261104

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `d85e3558ec1ebdc1ab6de0d2ad40f4d7ae8086576af33199920fa33364e7b198`.
**Yerel arşiv:** `raw/p02-2-link-contract-20261104.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "evidence_collected", "source_commit": "f843e6f9be4ff0eeaf586cf535638d05d00989cf"}`.

## p02-2-live-runner-development-unverified

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `c4bdaa4ccd9b669abc787669d1892a70a17b02d185b6849070acc553aa555033`.
**Yerel arşiv:** `raw/p02-2-live-runner-development-unverified.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 3, "kind": "rejected-upload", "original_bytes": 70913, "source_commit": "da243e54d97b3f393e647fc08f427b766ddb83ff"}`.

## p02-2-native07-upload-preflight-rejected

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `a5722a61b5ed730c6fac3d22e7e966dee0bbe22b12f31acb66483b91aba9cb33`.
**Yerel arşiv:** `raw/p02-2-native07-upload-preflight-rejected.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "operator_preflight_rejected", "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734"}`.

## p02-2-native08-upload-preflight-rejected

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `38b92b3577535f979acd8a940e20f7c6c2617b8e75b820969eaa1bac1d5b5d30`.
**Yerel arşiv:** `raw/p02-2-native08-upload-preflight-rejected.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "operator_preflight_rejected", "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-native09-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `0c6a76e2d2e2c7e991ad9ab94e25199719a37a7d1490ea9f2fe50781953ccc77`.
**Yerel arşiv:** `raw/p02-2-native09-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-native11-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `0fb0dcec73f52f75b29651d28ac8f13550cbafd9661e034c2637436584b13a37`.
**Yerel arşiv:** `raw/p02-2-native11-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "e0ca52b363e9e3d97da26fa1ce8d0a1d0991ff64"}`.

## p02-2-owned-diagnostic-20261104-incomplete

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `62475baaf352998d7ca7d138103c2aa83b03f8403d566f4208b20197d1ae6b47`.
**Yerel arşiv:** `raw/p02-2-owned-diagnostic-20261104-incomplete.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "incomplete", "source_commit": "06c26508a6b1b430194557995c4c51d89b6607c4"}`.

## p02-2-owned-diagnostic-20261104-r2

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `84d9714eb44a8505898d48ed7ef83b293385760d105e8041b555b79903b3bfe7`.
**Yerel arşiv:** `raw/p02-2-owned-diagnostic-20261104-r2.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "evidence_collected", "source_commit": "70e787c74ad2381a52e4dd57896c70d1ab8c3019"}`.

## p02-2-pr14-development-merge-ci-summary

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `daeae8552ccc0278a586dd306ab5f10dcdb641fcea0086856c8408529952be01`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-ci-summary.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "merge_ci_and_source_bindings_retained", "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-linux311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `a374d01b6d7c0cbdd976b1a814d90f65c19a50af904b4115202c0f95128c83be`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-linux311-startup-baseline-selection

**Tür:** `startup_baseline_selection`.
**Özgün JSON SHA-256:** `c29b86cc0811597bab087a7283e023824456a8fd086bb4aa88a682495fda82a2`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux311-startup-baseline-selection.json.gz`.
**Özet:** `{"complete": true, "diagnostic_only": true, "effective_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "kind": "startup_baseline_selection", "mode": "pinned_runtime", "pinned_baseline_commit": "50d68b1deab80d6fe14749d556efde1f103b5759", "report_sha256": "ba03e75225d85d9cd685f5145607b0414d42300319a95db344f43de65e3b10d3", "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-linux311-startup-diagnostic

**Tür:** `startup_ci_diagnostic`.
**Özgün JSON SHA-256:** `d7625117c8f4afd935a9ad938170fd17fa168a698be94798af0e8bdbf029f4d1`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux311-startup-diagnostic.json.gz`.
**Özet:** `{"ci_classification_accepted": true, "diagnostic_only": true, "kind": "startup_ci_diagnostic", "outcome": "passed", "p95_ms": {"baseline/cache": 161.10791899996002, "baseline/context": 113.6779309999838, "baseline/help": 26.0268869999436, "baseline/version": 25.848850999864226, "candidate/cache": 140.82231599991246, "candidate/context": 109.30776500003958, "candidate/help": 25.989531000050192, "candidate/version": 26.286434999974517}, "passed": true, "reason": "validated", "report_sha256": "ba03e75225d85d9cd685f5145607b0414d42300319a95db344f43de65e3b10d3", "run_url": "https://github.com/HodeTech/Yorunge/actions/runs/42118850899", "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-linux311-startup

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `ba03e75225d85d9cd685f5145607b0414d42300319a95db344f43de65e3b10d3`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux311-startup.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 161.10791899996002, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 113.6779309999838, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.0268869999436, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 25.848850999864226, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 140.82231599991246, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 109.30776500003958, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 25.989531000050192, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 26.286434999974517, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-linux311-stream

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `9ab1e3ff969b1416f581f53a84df0d85c3978118ce240a8db5539f68407d6dfe`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux311-stream.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 45359104, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.3587339190000876, "extra_rss_lower_bound_bytes": 393216, "extra_rss_upper_bound_bytes": 393216, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45752320, "pretransfer_peak_rss_bytes": 45359104, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 51003392, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.03772960600008446, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 86016, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51089408, "pretransfer_peak_rss_bytes": 51089408, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 45342720, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.570717693000006, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 45867008, "pretransfer_peak_rss_bytes": 45342720, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "linux.proc_self_stat.rss_pages", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "KiB", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 524288, 393216], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 524288, "upper_bound_bytes": [86016, 524288, 393216]}, "source_commit": "94aaaf03e380381e95c9432de340378e23007e95", "source_unchanged_during_measurement": true}`.

## p02-2-pr14-development-merge-linux311-upload

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `b87b536fa6cf1439ea806c9925b36a7787df1a658c59589826d5e067908372b8`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux311-upload.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 917504}, "kind": "upload-budget", "max_elapsed_seconds": 58.35914032699998, "max_extra_rss_upper_bound_bytes": 4456448, "passed": true, "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-linux314-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `7f8ca88e0f0518bc5fd736e6072443bf89797fb6fe6da66027db180f5427a692`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-linux314-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-development-merge-macos311-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `4ff739feaafc83c74cc33abf4aed3b40aa3f0f14b0b0b241b6fc13474668eaf5`.
**Yerel arşiv:** `raw/p02-2-pr14-development-merge-macos311-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "94aaaf03e380381e95c9432de340378e23007e95"}`.

## p02-2-pr14-failed-ci-summary

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `38c215f2df796f0fe8274e163fdbcd42e77693668f204d37ae92dad847484b7b`.
**Yerel arşiv:** `raw/p02-2-pr14-failed-ci-summary.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "pr14_failed_reference_selection_ci_outputs_retained", "source_commit": "21dd9d39ea1cce3c0e660b5646db82f6dd8afbf6"}`.

## p02-2-pr14-final-ci-summary

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `46f95914e324e4ad6bf66af1fc7aa21f03c78ce547da4d71d67a61eacf737959`.
**Yerel arşiv:** `raw/p02-2-pr14-final-ci-summary.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "pr14_final_source_ci_and_native_outputs_retained", "source_commit": "b0fb1f1a6c5ef2648605267f122ccbff64b6cf13"}`.

## p02-2-reference-datasets-01

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `eaaec8b142b9e27c2d04b721110fe63bfde94e4de30eb199bb13f5874552f41d`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-01.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 32768}, "verify": {"passed": true, "span_upper_bound_bytes": 16384}}, "kind": "dataset-hash", "max_elapsed_seconds": 1.0354675000999123, "max_extra_rss_upper_bound_bytes": 20316160, "passed": true, "source_commit": "510de0a0986f5e7d086c1fac9cbcc18974314fe5"}`.

## p02-2-reference-datasets-02

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `d7bc22a61180352aa4b548783a2b41d7621bf7f63809d5992a6dd3d3a8c23d8b`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-02.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 1081344}, "verify": {"passed": true, "span_upper_bound_bytes": 4308992}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.8970487921033055, "max_extra_rss_upper_bound_bytes": 20611072, "passed": true, "source_commit": "f088cd7f37be201671b652fbfaab87cd7ab4acd1"}`.

## p02-2-reference-datasets-03

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `8c3e7bc7cd2efd93377c6da515701d3013534d26f459db17c3cb7c34659d77af`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-03.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 3276800}, "verify": {"passed": true, "span_upper_bound_bytes": 4292608}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.8141016662120819, "max_extra_rss_upper_bound_bytes": 21889024, "passed": true, "source_commit": "5509ea314a98a05a39be1b03485a134f84fc8683"}`.

## p02-2-reference-datasets-04

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `b26b77a2ccab4ad2d0170412390bad437f04abef4d661227b0a4c739aa00e579`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-04.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 4308992}, "verify": {"passed": true, "span_upper_bound_bytes": 1785856}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.8500754591077566, "max_extra_rss_upper_bound_bytes": 20643840, "passed": true, "source_commit": "aa542ba28df73d9dd2ddc625e9fca469ed46abda"}`.

## p02-2-reference-datasets-05

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `908abea6f653c5eb6c1e5978553cd8e6724eb3047937413163d492535eb6fbd6`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-05.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 622592}, "verify": {"passed": true, "span_upper_bound_bytes": 622592}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.9553306247107685, "max_extra_rss_upper_bound_bytes": 21053440, "passed": true, "source_commit": "fad497745c74291efa96a518adf1d45fa9d5bebe"}`.

## p02-2-reference-datasets-06

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `7e123b229a79e89fa7b197b7a413fc02cf85a32a05d227ed5983403edd906d37`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-06.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 622592}, "verify": {"passed": true, "span_upper_bound_bytes": 671744}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.9547958341427147, "max_extra_rss_upper_bound_bytes": 20725760, "passed": true, "source_commit": "6d0f1d143e10ff6a715fd0e0fb4056d610f165f2"}`.

## p02-2-reference-datasets-07

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `7f8f88568ba21881a5bbae3594e936ad03afcaff3e1f198063b3e322fab0d49d`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-07.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 622592}, "verify": {"passed": true, "span_upper_bound_bytes": 622592}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7862428328953683, "max_extra_rss_upper_bound_bytes": 20201472, "passed": true, "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734"}`.

## p02-2-reference-datasets-08

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `a18128f3d18a893ba25759e135c4925be3da8b66b80565af454f3796600955bf`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-08.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 622592}, "verify": {"passed": true, "span_upper_bound_bytes": 458752}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7542337090708315, "max_extra_rss_upper_bound_bytes": 20692992, "passed": true, "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-reference-datasets-09

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `e4decc828f034903427b0368240e8686db35e0d53a18dce5ce287a88211e6e0e`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-09.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 622592}, "verify": {"passed": true, "span_upper_bound_bytes": 442368}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.8472733329981565, "max_extra_rss_upper_bound_bytes": 21544960, "passed": true, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-reference-datasets-11

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `845c891a90a5ed8b7cf8e685c390c8c4eadc4432afe6e71030d3bac2064544cb`.
**Yerel arşiv:** `raw/p02-2-reference-datasets-11.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 344064}, "verify": {"passed": true, "span_upper_bound_bytes": 622592}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.711352291982621, "max_extra_rss_upper_bound_bytes": 20496384, "passed": true, "source_commit": "e0ca52b363e9e3d97da26fa1ce8d0a1d0991ff64"}`.

## p02-2-reference-jobs-01

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `c1f80a7841026da1fc28889359a1ff33cea5f0dc88a18fd47d9345b4d17fc035`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-01.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 144.52783414162695, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 112.91370796971023, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 104.87995808944106, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 106.31816694512963, "passed": true, "samples": 30}}, "passed": true, "source_commit": "510de0a0986f5e7d086c1fac9cbcc18974314fe5", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-02

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `faf40c318ad975a0375db842003a3ea4af60ffd0e89f7ae652e6ffc52b0df435`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-02.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 168.28820877708495, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 121.36633391492069, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 119.7386251296848, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 120.06087508052588, "passed": true, "samples": 30}}, "passed": true, "source_commit": "f088cd7f37be201671b652fbfaab87cd7ab4acd1", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-03

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `e9d5b9206434e85370936e9096d9671aee32f14bb7102e4d798e4af2e0f8d4de`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-03.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 160.6534579768777, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 135.0409579463303, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 307.3076670989394, "passed": false, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 108.19087503477931, "passed": true, "samples": 30}}, "passed": false, "source_commit": "5509ea314a98a05a39be1b03485a134f84fc8683", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-04

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `19115cc1ac7ba646374d0e2d10da1be6cbe1796f989848709a6cf92decfbf645`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-04.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 164.61591701954603, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 120.18816685304046, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 118.26795805245638, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 125.34087477251887, "passed": true, "samples": 30}}, "passed": true, "source_commit": "aa542ba28df73d9dd2ddc625e9fca469ed46abda", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-05

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `db37df3cfa63c441860b8ece85f1f669f8fdf683d4197a5fac3bc9d01636a1ac`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-05.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 177.8037496842444, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 130.19399996846914, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 126.19799980893731, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 128.50895803421736, "passed": true, "samples": 30}}, "passed": true, "source_commit": "fad497745c74291efa96a518adf1d45fa9d5bebe", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-06

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `cd7ff21a9c2a8f9d19de93bcc6b926352fbaceb2128cd787f6809366f37f2245`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-06.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 171.9344169832766, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 128.2095001079142, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 128.03324963897467, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 138.43549974262714, "passed": true, "samples": 30}}, "passed": true, "source_commit": "6d0f1d143e10ff6a715fd0e0fb4056d610f165f2", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-07

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `8abdaebfc012211c723ccc54a40570fc89c8a7560f074b779086b51d51795d35`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-07.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 163.26666669920087, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 112.93695913627744, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 125.14762487262487, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 112.8499167971313, "passed": true, "samples": 30}}, "passed": true, "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-08

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `b16698c5e5fbf359b055f14beb556e5ca53a68af73619d1ba26980da08ce8ec6`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-08.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 172.67104191705585, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 130.60254137963057, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 351.4427077025175, "passed": false, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 260.3295841254294, "passed": false, "samples": 30}}, "passed": false, "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-09

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `03ddcb72c05ed0adc7c6a3cc9bafda50511038d33a601f112e6481ce397fc266`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-09.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 902.6161250658333, "passed": false, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 315.5781668610871, "passed": false, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 920.976959168911, "passed": false, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 318.03058413788676, "passed": false, "samples": 30}}, "passed": false, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-jobs-11

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `0a0f151d4c1035bcd1aa4fc6649ad9d1bd12846a63a0f2aa3d9cba51a97021ff`.
**Yerel arşiv:** `raw/p02-2-reference-jobs-11.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 145.94716718420386, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 102.41129202768207, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 100.11145798489451, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 101.02129215374589, "passed": true, "samples": 30}}, "passed": true, "source_commit": "e0ca52b363e9e3d97da26fa1ce8d0a1d0991ff64", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-reference-raw-01

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `0eaa93a3883f6cfd38cbe36a0dc2c62910377d59a45f73cd334b90a3c9844c1c`.
**Yerel arşiv:** `raw/p02-2-reference-raw-01.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49823744, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5848159999586642, "extra_rss_lower_bound_bytes": 1196032, "extra_rss_upper_bound_bytes": 1196032, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51019776, "pretransfer_peak_rss_bytes": 49823744, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 58998784, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.0341619998216629, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 58998784, "pretransfer_peak_rss_bytes": 58998784, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49676288, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.40504945791326463, "extra_rss_lower_bound_bytes": 311296, "extra_rss_upper_bound_bytes": 311296, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49987584, "pretransfer_peak_rss_bytes": 49676288, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 311296, 1196032], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1196032, "upper_bound_bytes": [0, 311296, 1196032]}, "source_commit": "510de0a0986f5e7d086c1fac9cbcc18974314fe5", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-02

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `7963601eece92669e19d9d6b8ced009da881ef79efb49a8cf2e577d3e307152f`.
**Yerel arşiv:** `raw/p02-2-reference-raw-02.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 50085888, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.8585546661633998, "extra_rss_lower_bound_bytes": 1212416, "extra_rss_upper_bound_bytes": 1212416, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51298304, "pretransfer_peak_rss_bytes": 50085888, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57655296, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.028673291904851794, "extra_rss_lower_bound_bytes": 16384, "extra_rss_upper_bound_bytes": 16384, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57671680, "pretransfer_peak_rss_bytes": 57655296, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49889280, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4289654160384089, "extra_rss_lower_bound_bytes": 901120, "extra_rss_upper_bound_bytes": 901120, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50790400, "pretransfer_peak_rss_bytes": 49889280, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [16384, 901120, 1212416], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1196032, "upper_bound_bytes": [16384, 901120, 1212416]}, "source_commit": "f088cd7f37be201671b652fbfaab87cd7ab4acd1", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-03

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `2b1afe848eb22cae73af8830e34766914f98daaf840b41935c8dbc600bb33c3e`.
**Yerel arşiv:** `raw/p02-2-reference-raw-03.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 49938432, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6287582912482321, "extra_rss_lower_bound_bytes": 1196032, "extra_rss_upper_bound_bytes": 1196032, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51134464, "pretransfer_peak_rss_bytes": 49938432, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 57671680, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.028394707944244146, "extra_rss_lower_bound_bytes": 32768, "extra_rss_upper_bound_bytes": 32768, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57704448, "pretransfer_peak_rss_bytes": 57671680, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 50003968, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4194078748114407, "extra_rss_lower_bound_bytes": 1196032, "extra_rss_upper_bound_bytes": 1196032, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 51200000, "pretransfer_peak_rss_bytes": 50003968, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [32768, 1196032, 1196032], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1163264, "upper_bound_bytes": [32768, 1196032, 1196032]}, "source_commit": "5509ea314a98a05a39be1b03485a134f84fc8683", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-04

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `3aa593cb0587a8b24887365a771026044cd2c7a71a1b0b47fb49377978646db2`.
**Yerel arşiv:** `raw/p02-2-reference-raw-04.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48611328, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6091990410350263, "extra_rss_lower_bound_bytes": 1064960, "extra_rss_upper_bound_bytes": 1064960, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49676288, "pretransfer_peak_rss_bytes": 48611328, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56049664, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.026480499655008316, "extra_rss_lower_bound_bytes": 16384, "extra_rss_upper_bound_bytes": 16384, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56066048, "pretransfer_peak_rss_bytes": 56049664, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48447488, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39805129216983914, "extra_rss_lower_bound_bytes": 65536, "extra_rss_upper_bound_bytes": 65536, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 48513024, "pretransfer_peak_rss_bytes": 48447488, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [16384, 65536, 1064960], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1048576, "upper_bound_bytes": [16384, 65536, 1064960]}, "source_commit": "aa542ba28df73d9dd2ddc625e9fca469ed46abda", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-05

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `77f1c8272fbb70a8f4d86a635f736faff184b1615a6ec0b03977d64fd0b21948`.
**Yerel arşiv:** `raw/p02-2-reference-raw-05.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48644096, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.695370875298977, "extra_rss_lower_bound_bytes": 1245184, "extra_rss_upper_bound_bytes": 1245184, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49889280, "pretransfer_peak_rss_bytes": 48644096, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56573952, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.03280012495815754, "extra_rss_lower_bound_bytes": 917504, "extra_rss_upper_bound_bytes": 917504, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57491456, "pretransfer_peak_rss_bytes": 56573952, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48447488, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4227258749306202, "extra_rss_lower_bound_bytes": 393216, "extra_rss_upper_bound_bytes": 393216, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 48840704, "pretransfer_peak_rss_bytes": 48447488, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [917504, 393216, 1245184], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 851968, "upper_bound_bytes": [917504, 393216, 1245184]}, "source_commit": "fad497745c74291efa96a518adf1d45fa9d5bebe", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-06

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `82253e73516a062ecb75e86d593075aa49dad8c2a19a6d3233a6f150ea2b48dd`.
**Yerel arşiv:** `raw/p02-2-reference-raw-06.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48742400, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6933891251683235, "extra_rss_lower_bound_bytes": 1245184, "extra_rss_upper_bound_bytes": 1245184, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49987584, "pretransfer_peak_rss_bytes": 48742400, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56197120, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02772466605529189, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56197120, "pretransfer_peak_rss_bytes": 56197120, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 49020928, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.41935762483626604, "extra_rss_lower_bound_bytes": 475136, "extra_rss_upper_bound_bytes": 475136, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49496064, "pretransfer_peak_rss_bytes": 49020928, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 475136, 1245184], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1245184, "upper_bound_bytes": [0, 475136, 1245184]}, "source_commit": "6d0f1d143e10ff6a715fd0e0fb4056d610f165f2", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-07

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `0f8318051c799bfac25847962ecb5770b7267731c95e356374d1e77de33bb6ae`.
**Yerel arşiv:** `raw/p02-2-reference-raw-07.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48578560, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.7090586251579225, "extra_rss_lower_bound_bytes": 1097728, "extra_rss_upper_bound_bytes": 1097728, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49676288, "pretransfer_peak_rss_bytes": 48578560, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56360960, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.026562000159174204, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56360960, "pretransfer_peak_rss_bytes": 56360960, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48726016, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4168650000356138, "extra_rss_lower_bound_bytes": 1081344, "extra_rss_upper_bound_bytes": 1081344, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49807360, "pretransfer_peak_rss_bytes": 48726016, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 1081344, 1097728], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1097728, "upper_bound_bytes": [0, 1081344, 1097728]}, "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-08

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `cc6612e40e3bcf5596c2ae4ef9237a19badfe6ecec329b0f6380dc1796696c5a`.
**Yerel arşiv:** `raw/p02-2-reference-raw-08.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48513024, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.765873999800533, "extra_rss_lower_bound_bytes": 917504, "extra_rss_upper_bound_bytes": 917504, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49430528, "pretransfer_peak_rss_bytes": 48513024, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56459264, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.028453749604523182, "extra_rss_lower_bound_bytes": 229376, "extra_rss_upper_bound_bytes": 229376, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56688640, "pretransfer_peak_rss_bytes": 56459264, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48693248, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4443076252937317, "extra_rss_lower_bound_bytes": 524288, "extra_rss_upper_bound_bytes": 524288, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49217536, "pretransfer_peak_rss_bytes": 48693248, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [229376, 524288, 917504], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 688128, "upper_bound_bytes": [229376, 524288, 917504]}, "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-09

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `1189cd88cd04355cdfeb56983931a3cbb82d7175f130971cd927542d46ff6a5f`.
**Yerel arşiv:** `raw/p02-2-reference-raw-09.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48758784, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 2.131203250028193, "extra_rss_lower_bound_bytes": 917504, "extra_rss_upper_bound_bytes": 917504, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49676288, "pretransfer_peak_rss_bytes": 48758784, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56377344, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.028682250063866377, "extra_rss_lower_bound_bytes": 360448, "extra_rss_upper_bound_bytes": 360448, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56737792, "pretransfer_peak_rss_bytes": 56377344, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48857088, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.6865660832263529, "extra_rss_lower_bound_bytes": 966656, "extra_rss_upper_bound_bytes": 966656, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49823744, "pretransfer_peak_rss_bytes": 48857088, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [360448, 966656, 917504], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 606208, "upper_bound_bytes": [360448, 966656, 917504]}, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad", "source_unchanged_during_measurement": true}`.

## p02-2-reference-raw-11

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `2e6e8379c46cb4f16bfb5d817a5b72a2ab23744bf74d376b0db9da81d7c3dbf7`.
**Yerel arşiv:** `raw/p02-2-reference-raw-11.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48627712, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6453937077894807, "extra_rss_lower_bound_bytes": 1146880, "extra_rss_upper_bound_bytes": 1146880, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49774592, "pretransfer_peak_rss_bytes": 48627712, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 55934976, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02597454097121954, "extra_rss_lower_bound_bytes": 16384, "extra_rss_upper_bound_bytes": 16384, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 55951360, "pretransfer_peak_rss_bytes": 55934976, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48676864, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4138124999590218, "extra_rss_lower_bound_bytes": 786432, "extra_rss_upper_bound_bytes": 786432, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49463296, "pretransfer_peak_rss_bytes": 48676864, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [16384, 786432, 1146880], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1130496, "upper_bound_bytes": [16384, 786432, 1146880]}, "source_commit": "e0ca52b363e9e3d97da26fa1ce8d0a1d0991ff64", "source_unchanged_during_measurement": true}`.

## p02-2-reference-startup-01

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `745aba9ff63917b57eba2eb42ff46ef02556ad243ddefd23dfcf5ab3d5490feb`.
**Yerel arşiv:** `raw/p02-2-reference-startup-01.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 127.2879580501467, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 85.66679107025266, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.196000166237354, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.049917003139853, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 128.60008399002254, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 78.68604199029505, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.936333065852523, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.1265421025455, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "510de0a0986f5e7d086c1fac9cbcc18974314fe5"}`.

## p02-2-reference-startup-02

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `932fbc0562a0f2a2ca10785cf084edfec945b37c05bcc8b51f36b8146c7f7543`.
**Yerel arşiv:** `raw/p02-2-reference-startup-02.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 134.5193749293685, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 95.2112500090152, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 28.6418329924345, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 27.656709076836705, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 131.53770891949534, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 94.17333290912211, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 28.345624916255474, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 27.543917065486312, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "f088cd7f37be201671b652fbfaab87cd7ab4acd1"}`.

## p02-2-reference-startup-03

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `42057578541f91c06bbff57d095331eb9045035cc9298955fa4997e6be618806`.
**Yerel arşiv:** `raw/p02-2-reference-startup-03.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 148.45937490463257, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 126.85983441770077, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 49.10883400589228, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 31.29133302718401, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 176.0436249896884, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 94.92158330976963, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 36.06337495148182, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 49.610084388405085, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "5509ea314a98a05a39be1b03485a134f84fc8683"}`.

## p02-2-reference-startup-04

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `c954202f69980d8b8b8e5db7d4dfa4aa4c2abe05c76534aeeb069725edb51a40`.
**Yerel arşiv:** `raw/p02-2-reference-startup-04.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 136.10487524420023, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 88.20495894178748, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 32.27704204618931, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 26.38437505811453, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 130.9408750385046, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 78.95875023677945, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 35.266249906271696, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 26.16220898926258, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "aa542ba28df73d9dd2ddc625e9fca469ed46abda"}`.

## p02-2-reference-startup-05

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `3f5c653f4d342d3e2c7df1bba8e11fa01701333c3be5b3704b0ba8f0f809c5fb`.
**Yerel arşiv:** `raw/p02-2-reference-startup-05.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 158.6586246266961, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 114.77025039494038, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 34.90383364260197, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 32.22633386030793, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 206.82066632434726, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 131.6442503593862, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 37.40616701543331, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 34.898582845926285, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "fad497745c74291efa96a518adf1d45fa9d5bebe"}`.

## p02-2-reference-startup-06

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `fec311878ea26028eb71bfdaefcca3fa7ceeaeb5a7383fbf1718953f7bfe507d`.
**Yerel arşiv:** `raw/p02-2-reference-startup-06.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 160.57245805859566, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 110.60841707512736, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 32.83325023949146, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 38.439832627773285, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 147.01883308589458, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 100.1507081091404, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 32.26787503808737, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 35.40458297356963, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "6d0f1d143e10ff6a715fd0e0fb4056d610f165f2"}`.

## p02-2-reference-startup-07

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `64015fe38a906b58d11334a7250fa366dca30a8875b5d608f91a61ec6ff2dda0`.
**Yerel arşiv:** `raw/p02-2-reference-startup-07.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 212.075624614954, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 115.60308327898383, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 25.58249980211258, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.850375156849623, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 160.17087502405047, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 105.25674978271127, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 30.70979192852974, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 25.139375124126673, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734"}`.

## p02-2-reference-startup-08

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `a69fd8389c89108d8f89dc2055cbdd17f063607f21e380c72da16a2cd2b9d505`.
**Yerel arşiv:** `raw/p02-2-reference-startup-08.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 205.74499992653728, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 124.04470797628164, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 65.58004161342978, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 35.57129204273224, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 214.5575419999659, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 167.173583060503, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 71.90791703760624, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 41.23987536877394, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-reference-startup-09

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `be68bbc52acdfc13a402cdd05a8527f04154065e0b61bde15dfc740f429e4d34`.
**Yerel arşiv:** `raw/p02-2-reference-startup-09.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 549.7925416566432, "passed": false, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 170.7149581052363, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 37.37754235044122, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 36.96150006726384, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 330.5361671373248, "passed": false, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 148.45954114571214, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 34.69150001183152, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 35.02270905300975, "passed": true, "samples": 30}}, "outcome": "diagnostic_budget_exceeded", "passed": false, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-reference-startup-11

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `df1b424707462db0645b7e0efb4d336120642d45381115228cbe72c09e2e7bf9`.
**Yerel arşiv:** `raw/p02-2-reference-startup-11.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 113.48237516358495, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 79.0072912350297, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.404041796922684, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.920667055994272, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 119.76583302021027, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 74.27687477320433, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.50266696885228, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.615291971713305, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "e0ca52b363e9e3d97da26fa1ce8d0a1d0991ff64"}`.

## p02-2-reference-upload-01

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `ddfe2d0695b1f82437334ddd7e17704a3a39b93523564f4c44e38f7e2d20051d`.
**Yerel arşiv:** `raw/p02-2-reference-upload-01.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 3424256}, "kind": "upload-budget", "max_elapsed_seconds": 64.53961554192938, "max_extra_rss_upper_bound_bytes": 11796480, "passed": true, "source_commit": "510de0a0986f5e7d086c1fac9cbcc18974314fe5"}`.

## p02-2-reference-upload-02

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `d54c9cc464165e3ff11de64be334eebab12aa418c4b39ee8c0cdd83ac5b4154c`.
**Yerel arşiv:** `raw/p02-2-reference-upload-02.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 7421952}, "kind": "upload-budget", "max_elapsed_seconds": 64.8340523748193, "max_extra_rss_upper_bound_bytes": 14123008, "passed": true, "source_commit": "f088cd7f37be201671b652fbfaab87cd7ab4acd1"}`.

## p02-2-reference-upload-03

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `904860fb896fc1f2a69d3815a9869877a8bff4f0c8c622e918da5d97bcccad25`.
**Yerel arşiv:** `raw/p02-2-reference-upload-03.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 7634944}, "kind": "upload-budget", "max_elapsed_seconds": 62.740083958022296, "max_extra_rss_upper_bound_bytes": 12648448, "passed": true, "source_commit": "5509ea314a98a05a39be1b03485a134f84fc8683"}`.

## p02-2-reference-upload-04

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `2f813ad12a2aabd5497596425a3edb216377bddbd4f892f0e812b7c792758858`.
**Yerel arşiv:** `raw/p02-2-reference-upload-04.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": false, "span_upper_bound_bytes": 14614528}, "kind": "upload-budget", "max_elapsed_seconds": 71.91362408269197, "max_extra_rss_upper_bound_bytes": 19513344, "passed": false, "source_commit": "aa542ba28df73d9dd2ddc625e9fca469ed46abda"}`.

## p02-2-reference-upload-05

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `faf27b888676859dfaa35be09a30a3c7b9c5a278ac14bfd9e9f95f63eadeb381`.
**Yerel arşiv:** `raw/p02-2-reference-upload-05.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 868352}, "kind": "upload-budget", "max_elapsed_seconds": 65.1306690000929, "max_extra_rss_upper_bound_bytes": 4112384, "passed": true, "source_commit": "fad497745c74291efa96a518adf1d45fa9d5bebe"}`.

## p02-2-reference-upload-06

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `727c9c7ca4182b541c96ba0024804d31f174c00c88e47d1b3f4bf8c29a011da2`.
**Yerel arşiv:** `raw/p02-2-reference-upload-06.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 2260992}, "kind": "upload-budget", "max_elapsed_seconds": 73.26496516633779, "max_extra_rss_upper_bound_bytes": 2867200, "passed": true, "source_commit": "6d0f1d143e10ff6a715fd0e0fb4056d610f165f2"}`.

## p02-2-reference-upload-07

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `f550abcc5ab27cd7829304cb7bc8bb33703fb2f42267faa6d85e8fef5ac04000`.
**Yerel arşiv:** `raw/p02-2-reference-upload-07.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 2801664}, "kind": "upload-budget", "max_elapsed_seconds": 64.35536962514743, "max_extra_rss_upper_bound_bytes": 3080192, "passed": true, "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734"}`.

## p02-2-reference-upload-08

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `51f89d099254f27da4094df276479d955bc82c924ff519f296bde751b73dc1c2`.
**Yerel arşiv:** `raw/p02-2-reference-upload-08.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 1622016}, "kind": "upload-budget", "max_elapsed_seconds": 65.63126674992964, "max_extra_rss_upper_bound_bytes": 2424832, "passed": true, "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-reference-upload-09

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `e7d69f942dfbaa0eed0ec8b91e375b12aacd4ae1750966c5b22c2f0308ed0e4c`.
**Yerel arşiv:** `raw/p02-2-reference-upload-09.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 2015232}, "kind": "upload-budget", "max_elapsed_seconds": 87.0729992906563, "max_extra_rss_upper_bound_bytes": 4472832, "passed": true, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-reference-upload-11

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `eae9ce67228d69a55bf53fd366aaa709922148290018fb163d2bc7139d64aa37`.
**Yerel arşiv:** `raw/p02-2-reference-upload-11.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 1245184}, "kind": "upload-budget", "max_elapsed_seconds": 62.84713462507352, "max_extra_rss_upper_bound_bytes": 4669440, "passed": true, "source_commit": "e0ca52b363e9e3d97da26fa1ce8d0a1d0991ff64"}`.

## p02-2-review-final-installation-07

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `0a68f035efe3848a420bfd93d0c5564860f5fd7fb9551cce47c5d6d6c91fe249`.
**Yerel arşiv:** `raw/p02-2-review-final-installation-07.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "32109a7deb10a3073410f5922066fff24ee9a734"}`.

## p02-2-review-final-installation-08

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `c1e0ab51737854572eefbc80532bb8a4d5b43eb6638c62a33e79e4d7d888a583`.
**Yerel arşiv:** `raw/p02-2-review-final-installation-08.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "9b482ea2d1ed2d39a7974afc01d297c7dad625d9"}`.

## p02-2-review-final-installation-09

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `3608f2334b66551aea3139c981069901df08cd9416f630bfc4e47c14190527e2`.
**Yerel arşiv:** `raw/p02-2-review-final-installation-09.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-shared-load-conditions-10

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `b920ec6074fcccd186d0015e606e73ede4c59e15e8a28b5ec6d78aa479b7ecca`.
**Yerel arşiv:** `raw/p02-2-shared-load-conditions-10.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "explicit_shared_load_diagnostic", "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-shared-load-jobs-10

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `2bdc9eb7aa3893a068ce582aff356a1aab3f6feff5e393e8d274e9595bf2644d`.
**Yerel arşiv:** `raw/p02-2-shared-load-jobs-10.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 152.88337506353855, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 105.3735832683742, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 146.85133285820484, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 100.66349990665913, "passed": true, "samples": 30}}, "passed": true, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-2-shared-load-startup-10

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `6f888110b12a2504e612b6cf892e518499a574ce496bd3898e56de1df3c5d786`.
**Yerel arşiv:** `raw/p02-2-shared-load-startup-10.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 135.22529182955623, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 75.90933376923203, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.361041702330112, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 22.671165876090527, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 125.66891638562083, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 76.51270925998688, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.398082867264748, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.723209276795387, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "f180cb8ffc9004acc51b0264cb5e947e5d0564ad"}`.

## p02-2-storage-contract-different-20261104

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `682a78e917e7adfdb8d69938030e8688f19c81bff312f06f4be61e46d29acfee`.
**Yerel arşiv:** `raw/p02-2-storage-contract-different-20261104.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "evidence_collected", "source_commit": "998ee7d75f7db1b8b039b9362a19ab525b8dd2cf"}`.

## p02-2-storage-contract-first-20261104

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `77b458ad7134f0fdd203aaff4f76af90d5c2a357274cc8b9f41df26680ba4221`.
**Yerel arşiv:** `raw/p02-2-storage-contract-first-20261104.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "evidence_collected", "source_commit": "00658dfc18fb6f52067e4f68ccc72814fc1bae52"}`.

## p02-2-storage-contract-same-content-20261104

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `6867a74c8a888c39920ce9dfcaf3fe0884e2b295ab1e3e18928e1c49ba27a5d0`.
**Yerel arşiv:** `raw/p02-2-storage-contract-same-content-20261104.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "evidence_collected", "source_commit": "998ee7d75f7db1b8b039b9362a19ab525b8dd2cf"}`.

## p02-2-upload-v1-smoke-01-rejected

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `b6d89885bf198aab544e5136d587c46a86fd3883e46aa22a3f2bdee76d83b9e6`.
**Yerel arşiv:** `raw/p02-2-upload-v1-smoke-01-rejected.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 9, "kind": "rejected-upload", "original_bytes": 35954, "source_commit": "b80a55e840ec764165650eba7bb4cd368d28b02d"}`.

## p02-2-upload-v1-smoke-02-unverified

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `0b2dc33fd25947aca8649bfc5eec136a7827a8e17b2d70c0b78f46b466417ab0`.
**Yerel arşiv:** `raw/p02-2-upload-v1-smoke-02-unverified.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 9, "kind": "rejected-upload", "original_bytes": 69599, "source_commit": "b80a55e840ec764165650eba7bb4cd368d28b02d"}`.

## p02-2-upload-v1-smoke-03-unverified

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `4feb6cb2076d5e8f9d73866fbf283215c5339bb7d96b3620018184adc7328c73`.
**Yerel arşiv:** `raw/p02-2-upload-v1-smoke-03-unverified.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 9, "kind": "rejected-upload", "original_bytes": 71318, "source_commit": "6fb5b9b652417da98c2b50e56ea0e038be6b0b69"}`.

## p02-2-upload-v2-smoke-01-unverified

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `d814a0f89f07b62a37e1effd3e6749231690d2e478ea4b85472e82ea93587a43`.
**Yerel arşiv:** `raw/p02-2-upload-v2-smoke-01-unverified.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 11, "kind": "rejected-upload", "original_bytes": 153274, "source_commit": "5a90477ed56bebaaec488114718de37d18b4f9df"}`.

## p02-2-upload-v3-sdist-development-unverified

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `71d81db149f29f85a2975681e50ace5980d61388958342ff410d063888cffe01`.
**Yerel arşiv:** `raw/p02-2-upload-v3-sdist-development-unverified.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 15, "kind": "rejected-upload", "original_bytes": 218641, "source_commit": "5363423f48f182e5408067866c5b53eb5fb106d5"}`.

## p02-2-upload-v3-wheel-development-unverified

**Tür:** `rejected-upload`.
**Özgün JSON SHA-256:** `ac705153b9947fb596e920f83d8776747f7f9aa9b43fca412e121b8420ee2a06`.
**Yerel arşiv:** `raw/p02-2-upload-v3-wheel-development-unverified.json.gz`.
**Özet:** `{"accepted": false, "diagnostic_only": true, "files": 15, "kind": "rejected-upload", "original_bytes": 218655, "source_commit": "5363423f48f182e5408067866c5b53eb5fb106d5"}`.

## p02-2-v3-development-installation

**Tür:** `installation_v3`.
**Özgün JSON SHA-256:** `88a69265ecfd9d10c0d907cd48495df98f227c8525fc502716c4676ad1b1958f`.
**Yerel arşiv:** `raw/p02-2-v3-development-installation.json.gz`.
**Özet:** `{"cases": 2, "checks": {"cache_smoke": {"passed": 2}, "execution_smoke": {"passed": 2}, "http_smoke": {"passed": 2}, "jobs_smoke": {"passed": 2}, "ndjson_smoke": {"passed": 2}, "origin_verified": {"true": 2}, "smoke": {"passed": 2}, "stream_smoke": {"passed": 2}, "upload_smoke": {"passed": 2}}, "diagnostic_only": false, "kind": "installation_v3", "passed": true, "source_commit": "5363423f48f182e5408067866c5b53eb5fb106d5"}`.

## p02-3-native1-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `7a1e029b3fb91bf5d4af6ec7af9e5d34aaf914e209fa42606764c1561373c1db`.
**Yerel arşiv:** `raw/p02-3-native1-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb"}`.

## p02-3-native2-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `ada79d62c740a17a0606a0ec902d56875e634ce760684f8dbb34f2883a66759e`.
**Yerel arşiv:** `raw/p02-3-native2-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84"}`.

## p02-3-native3-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `9481feef95a151838ec15647cd7f65e9580ae0db91b25b9d36de33f51ee5e13d`.
**Yerel arşiv:** `raw/p02-3-native3-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c"}`.

## p02-3-native4-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `07fe4e21159bd99811a6c4f6eed479f399e391b4705f35cd59c9955fc0b87712`.
**Yerel arşiv:** `raw/p02-3-native4-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b"}`.

## p02-3-native5-conditions

**Tür:** `diagnostic`.
**Özgün JSON SHA-256:** `95bd5d81286fec2b6bba71fd1c74ae4e97e1e8e50a3e66aebfc95bce5999edff`.
**Yerel arşiv:** `raw/p02-3-native5-conditions.json.gz`.
**Özet:** `{"diagnostic_only": true, "kind": "diagnostic", "outcome": "native_conditions_observation", "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2"}`.

## p02-3-reference-datasets-1

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `bf642b59fa5bf18d6d2f382c94a9cb235b61a680a0568c30e79173629cd9f716`.
**Yerel arşiv:** `raw/p02-3-reference-datasets-1.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 475136}, "verify": {"passed": true, "span_upper_bound_bytes": 622592}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.886486915871501, "max_extra_rss_upper_bound_bytes": 20447232, "passed": true, "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb"}`.

## p02-3-reference-datasets-2

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `45d43bc6ddb1b7722eb000da39c7cf156f5cca28b41f5cf961c5af7088b13b13`.
**Yerel arşiv:** `raw/p02-3-reference-datasets-2.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 16384}, "verify": {"passed": true, "span_upper_bound_bytes": 0}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7065323330025421, "max_extra_rss_upper_bound_bytes": 20922368, "passed": true, "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84"}`.

## p02-3-reference-datasets-3

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `8380a24f340ea9a8d31855f6f6339de5e7f9a2e7872134672145e643e5dc033d`.
**Yerel arşiv:** `raw/p02-3-reference-datasets-3.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 327680}, "verify": {"passed": true, "span_upper_bound_bytes": 131072}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.6779787910054438, "max_extra_rss_upper_bound_bytes": 20856832, "passed": true, "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c"}`.

## p02-3-reference-datasets-4

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `0fa85d7123668b3cc12059a71da68014725747d42d29f8759f2c71302f9f41a1`.
**Yerel arşiv:** `raw/p02-3-reference-datasets-4.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 16384}, "verify": {"passed": true, "span_upper_bound_bytes": 311296}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7058594999980414, "max_extra_rss_upper_bound_bytes": 20660224, "passed": true, "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b"}`.

## p02-3-reference-datasets-5

**Tür:** `dataset-hash`.
**Özgün JSON SHA-256:** `45e88ec95d9fc0b7dda5cc83e7b800f75a0d0387a9718a7005280d989ad4cf91`.
**Yerel arşiv:** `raw/p02-3-reference-datasets-5.json.gz`.
**Özet:** `{"cases": 24, "diagnostic_only": false, "growth": {"inspect": {"passed": true, "span_upper_bound_bytes": 622592}, "verify": {"passed": true, "span_upper_bound_bytes": 475136}}, "kind": "dataset-hash", "max_elapsed_seconds": 0.7113557910051895, "max_extra_rss_upper_bound_bytes": 20594688, "passed": true, "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2"}`.

## p02-3-reference-download-1

**Tür:** `download-budget`.
**Özgün JSON SHA-256:** `00631ef1730c664dd1e5377e4ae48cda39fdf07b77cc056a7f8f7c2f290e2133`.
**Yerel arşiv:** `raw/p02-3-reference-download-1.json.gz`.
**Özet:** `{"accepted": true, "cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 704512}, "kind": "download-budget", "max_elapsed_seconds": 3.4168586670421064, "max_extra_rss_upper_bound_bytes": 1507328, "partial": false, "passed": true, "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb"}`.

## p02-3-reference-download-2

**Tür:** `download-budget`.
**Özgün JSON SHA-256:** `0884a1efc808830d41ecbae1469ba46cbab5c5d54aaaf2a535e6224e3cb69bda`.
**Yerel arşiv:** `raw/p02-3-reference-download-2.json.gz`.
**Özet:** `{"accepted": true, "cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 688128}, "kind": "download-budget", "max_elapsed_seconds": 2.9063553329979186, "max_extra_rss_upper_bound_bytes": 1556480, "partial": false, "passed": true, "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84"}`.

## p02-3-reference-download-3

**Tür:** `download-budget`.
**Özgün JSON SHA-256:** `d185619691e8db196cadd731b919f5477aa7845d0d838d365152d3fceacf19f5`.
**Yerel arşiv:** `raw/p02-3-reference-download-3.json.gz`.
**Özet:** `{"accepted": true, "cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 868352}, "kind": "download-budget", "max_elapsed_seconds": 7.80850729100348, "max_extra_rss_upper_bound_bytes": 3047424, "partial": false, "passed": true, "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c"}`.

## p02-3-reference-download-4

**Tür:** `download-budget`.
**Özgün JSON SHA-256:** `414ea19f67b7b7b7420eb7a24cd3133cadf67acb03fe55d79699921a4acf6ac7`.
**Yerel arşiv:** `raw/p02-3-reference-download-4.json.gz`.
**Özet:** `{"accepted": true, "cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 1015808}, "kind": "download-budget", "max_elapsed_seconds": 3.0670362079981714, "max_extra_rss_upper_bound_bytes": 2473984, "partial": false, "passed": true, "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b"}`.

## p02-3-reference-download-5

**Tür:** `download-budget`.
**Özgün JSON SHA-256:** `9351bef9ef31d33f36628b03e47ef681f53df1affa8e1e3049b03b77de7dd650`.
**Yerel arşiv:** `raw/p02-3-reference-download-5.json.gz`.
**Özet:** `{"accepted": true, "cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 1146880}, "kind": "download-budget", "max_elapsed_seconds": 3.350067167004454, "max_extra_rss_upper_bound_bytes": 2179072, "partial": false, "passed": true, "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2"}`.

## p02-3-reference-jobs-1

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `ae83fd330dd128f971d41fce0df8a768124ef19bfb86f0e9b877167cabed9240`.
**Yerel arşiv:** `raw/p02-3-reference-jobs-1.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 193.28004214912653, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 115.51416665315628, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 116.82666698470712, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 123.35562519729137, "passed": true, "samples": 30}}, "passed": true, "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-3-reference-jobs-2

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `512ead9ccfc1dca96a09efc97ef74445c01e18803e9c5b3f12a904cf45b776bb`.
**Yerel arşiv:** `raw/p02-3-reference-jobs-2.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 151.12966600281652, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 102.4295420065755, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 140.87587499670917, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 112.97245800233213, "passed": true, "samples": 30}}, "passed": true, "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-3-reference-jobs-3

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `a3b3066d2275211b14a43a17843b7b0a2b4560dd7706ae91f58f4140cbcc1f24`.
**Yerel arşiv:** `raw/p02-3-reference-jobs-3.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 168.88183398987167, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 101.15779199986719, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 105.40212500200141, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 99.4734999985667, "passed": true, "samples": 30}}, "passed": true, "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-3-reference-jobs-4

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `ca63de1518c9acc58768df550df2ee32eb74011fef10ffe9dd6da5127e7997d0`.
**Yerel arşiv:** `raw/p02-3-reference-jobs-4.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 145.67079200060107, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 108.9515830099117, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 100.59312501107343, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 113.96179199800827, "passed": true, "samples": 30}}, "passed": true, "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-3-reference-jobs-5

**Tür:** `jobs`.
**Özgün JSON SHA-256:** `f4561ae4f3053f9aae170a8b36e106c0a4f5c22041e9aa467ade2153bca15e70`.
**Yerel arşiv:** `raw/p02-3-reference-jobs-5.json.gz`.
**Özet:** `{"diagnostic_only": false, "fixtures_unchanged_during_measurement": true, "installed_unchanged_during_measurement": true, "isolated_python": true, "kind": "jobs", "measurements": {"dense/list": {"budget_ms": 200.0, "p95_ms": 149.61108300485648, "passed": true, "samples": 30}, "dense/show": {"budget_ms": 200.0, "p95_ms": 113.92329199588858, "passed": true, "samples": 30}, "normal/list": {"budget_ms": 200.0, "p95_ms": 105.57466599857435, "passed": true, "samples": 30}, "normal/show": {"budget_ms": 200.0, "p95_ms": 106.91979200055357, "passed": true, "samples": 30}}, "passed": true, "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2", "source_unchanged_during_measurement": true, "unchanged": true}`.

## p02-3-reference-raw-1

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `b700ce1f16962a40ae7cf920a008b3b0c540715f110bb5b64434d0c0765e8f58`.
**Yerel arşiv:** `raw/p02-3-reference-raw-1.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48578560, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6468780422583222, "extra_rss_lower_bound_bytes": 1310720, "extra_rss_upper_bound_bytes": 1310720, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49889280, "pretransfer_peak_rss_bytes": 48578560, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56246272, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02593229105696082, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56246272, "pretransfer_peak_rss_bytes": 56246272, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48431104, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4074687082320452, "extra_rss_lower_bound_bytes": 344064, "extra_rss_upper_bound_bytes": 344064, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 48775168, "pretransfer_peak_rss_bytes": 48431104, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 344064, 1310720], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 1310720, "upper_bound_bytes": [0, 344064, 1310720]}, "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb", "source_unchanged_during_measurement": true}`.

## p02-3-reference-raw-2

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `b9042db891ad622d06945967c0ac90ec698773e56206d1ed38790472a52afaae`.
**Yerel arşiv:** `raw/p02-3-reference-raw-2.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48709632, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5520848750020377, "extra_rss_lower_bound_bytes": 557056, "extra_rss_upper_bound_bytes": 557056, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49266688, "pretransfer_peak_rss_bytes": 48709632, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56311808, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025676999997813255, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56311808, "pretransfer_peak_rss_bytes": 56311808, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48840704, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4007930000007036, "extra_rss_lower_bound_bytes": 180224, "extra_rss_upper_bound_bytes": 180224, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49020928, "pretransfer_peak_rss_bytes": 48840704, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 180224, 557056], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 557056, "upper_bound_bytes": [0, 180224, 557056]}, "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84", "source_unchanged_during_measurement": true}`.

## p02-3-reference-raw-3

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `88a605c11f4dfa9923de5781ff7d5abd056c2c408e325553c319d7ca5557700b`.
**Yerel arşiv:** `raw/p02-3-reference-raw-3.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48758784, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6100344580045203, "extra_rss_lower_bound_bytes": 819200, "extra_rss_upper_bound_bytes": 819200, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49577984, "pretransfer_peak_rss_bytes": 48758784, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56147968, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.02499720900959801, "extra_rss_lower_bound_bytes": 0, "extra_rss_upper_bound_bytes": 0, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56147968, "pretransfer_peak_rss_bytes": 56147968, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48693248, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.3819274160050554, "extra_rss_lower_bound_bytes": 98304, "extra_rss_upper_bound_bytes": 98304, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 48791552, "pretransfer_peak_rss_bytes": 48693248, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [0, 98304, 819200], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 819200, "upper_bound_bytes": [0, 98304, 819200]}, "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c", "source_unchanged_during_measurement": true}`.

## p02-3-reference-raw-4

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `e08606962c7e5a02e3382db5ba0478a0d3b4360926a0cf06d1846d78f9528c16`.
**Yerel arşiv:** `raw/p02-3-reference-raw-4.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48676864, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.5885768750013085, "extra_rss_lower_bound_bytes": 1015808, "extra_rss_upper_bound_bytes": 1015808, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49692672, "pretransfer_peak_rss_bytes": 48676864, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56410112, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.025739625009009615, "extra_rss_lower_bound_bytes": 81920, "extra_rss_upper_bound_bytes": 81920, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 56492032, "pretransfer_peak_rss_bytes": 56410112, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48955392, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.39624708400515374, "extra_rss_lower_bound_bytes": 425984, "extra_rss_upper_bound_bytes": 425984, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49381376, "pretransfer_peak_rss_bytes": 48955392, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [81920, 425984, 1015808], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 933888, "upper_bound_bytes": [81920, 425984, 1015808]}, "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b", "source_unchanged_during_measurement": true}`.

## p02-3-reference-raw-5

**Tür:** `raw_stream_budget_v2`.
**Özgün JSON SHA-256:** `16c71f93732fa39fd6e28717509ad4c9bcfc8b6102cc4b2c685040cbf455d24a`.
**Yerel arşiv:** `raw/p02-3-reference-raw-5.json.gz`.
**Özet:** `{"diagnostic_only": false, "installed_source_matches": true, "kind": "raw_stream_budget_v2", "measurements": {"1024MiB": {"baseline_rss_bytes": 48873472, "chunk_count": 65536, "connection_count": 1, "elapsed_seconds": 1.6137933749996591, "extra_rss_lower_bound_bytes": 1376256, "extra_rss_upper_bound_bytes": 1376256, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 50249728, "pretransfer_peak_rss_bytes": 48873472, "received_bytes": 1073741824}, "16MiB": {"baseline_rss_bytes": 56541184, "chunk_count": 1024, "connection_count": 1, "elapsed_seconds": 0.03072729099949356, "extra_rss_lower_bound_bytes": 917504, "extra_rss_upper_bound_bytes": 917504, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 57458688, "pretransfer_peak_rss_bytes": 56541184, "received_bytes": 16777216}, "256MiB": {"baseline_rss_bytes": 48742400, "chunk_count": 16384, "connection_count": 1, "elapsed_seconds": 0.4117519160063239, "extra_rss_lower_bound_bytes": 1097728, "extra_rss_upper_bound_bytes": 1097728, "max_chunk_bytes": 16384, "passed": true, "peak_rss_bytes": 49840128, "pretransfer_peak_rss_bytes": 48742400, "received_bytes": 268435456}}, "passed": true, "rss_baseline": "native_current_rss_after_imports_and_fixed_tls_warmup", "rss_baseline_source": "darwin.MACH_TASK_BASIC_INFO.resident_size", "rss_interval": "new_high_water_exact_else_zero_to_upper", "rss_method": "instantaneous_baseline_and_lifetime_peak_interval_v2", "rss_native_unit": "bytes", "rss_peak_source": "resource.getrusage(RUSAGE_SELF).ru_maxrss", "rss_window": "after_pretransfer_peak_until_posttransfer_peak_including_instrumentation", "size_growth_acceptance": {"lower_bound_bytes": [917504, 1097728, 1376256], "method": "max_cross_size_upper_minus_lower", "passed": true, "size_bytes": [16777216, 268435456, 1073741824], "span_upper_bound_bytes": 458752, "upper_bound_bytes": [917504, 1097728, 1376256]}, "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2", "source_unchanged_during_measurement": true}`.

## p02-3-reference-startup-1

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `4f7e6e18f33a74eeea5716bccf74bb53f5bc45ae1828fb0777be6e11f0b1933a`.
**Yerel arşiv:** `raw/p02-3-reference-startup-1.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 132.03791715204716, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 82.34833367168903, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 126.79508375003934, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 35.384458024054766, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 129.68254229053855, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 107.12970932945609, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 59.454333037137985, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 26.76945785060525, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb"}`.

## p02-3-reference-startup-2

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `5318ccf3ab73c16068fbef2256b0ebca6a218a2a870e84b50e45eafb2f6290c4`.
**Yerel arşiv:** `raw/p02-3-reference-startup-2.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 113.64708300243365, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 72.65295799879823, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.109957997803576, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 24.788041999272536, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 116.51208400144242, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 73.14016699820058, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 22.87895799963735, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.487207999802195, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84"}`.

## p02-3-reference-startup-3

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `ad911e9c35453c6747ef278a3aff2a84ee333ac52501cba7d4ea303ec6b4e858`.
**Yerel arşiv:** `raw/p02-3-reference-startup-3.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 151.88404099899344, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 127.38491699565202, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.213999990024604, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.18024999112822, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 141.27129199914634, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 127.477625006577, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.802582993288524, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 23.73658299620729, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c"}`.

## p02-3-reference-startup-4

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `7202dbe0879117754322c5c9831f146e620feca2aa89e402f2fbf0ad43d00f10`.
**Yerel arşiv:** `raw/p02-3-reference-startup-4.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 114.69349999970291, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 73.39995799702592, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 23.398167002596892, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 23.071917006745934, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 115.28816599457059, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 74.68662499741185, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 23.681166989263147, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.803291998570785, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b"}`.

## p02-3-reference-startup-5

**Tür:** `startup_evidence`.
**Özgün JSON SHA-256:** `503418e0bc9d3a8dd30bf0a18d25e25b393aa3fdd54fed34e276f21462ae75db`.
**Yerel arşiv:** `raw/p02-3-reference-startup-5.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup_evidence", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 128.4494999999879, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 82.96479099954013, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 24.432791004073806, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 29.799582989653572, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 135.4264170076931, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 96.73545800615102, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.400583002716303, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 26.113375002751127, "passed": true, "samples": 30}}, "outcome": "passed", "passed": true, "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2"}`.

## p02-3-reference-upload-1

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `0f967fbaa194e6e53be7e90324a28105b3a4486e4f25fd8fc25429ae57a763f1`.
**Yerel arşiv:** `raw/p02-3-reference-upload-1.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 2588672}, "kind": "upload-budget", "max_elapsed_seconds": 65.45440366724506, "max_extra_rss_upper_bound_bytes": 2588672, "passed": true, "source_commit": "a574c5b9e178007a8d472a38eea1cf9c9d6042eb"}`.

## p02-3-reference-upload-2

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `4ad1377b0d2c8f9016a67115a31220623f343cd2c31983603a12635199db384a`.
**Yerel arşiv:** `raw/p02-3-reference-upload-2.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 983040}, "kind": "upload-budget", "max_elapsed_seconds": 66.0201647089998, "max_extra_rss_upper_bound_bytes": 4571136, "passed": true, "source_commit": "27a532c63201ed9b80b2498c1e63907e32314f84"}`.

## p02-3-reference-upload-3

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `a9a5fb0cbc0b61f681bfde9dacd220ec64b0c0f68562f1f9e5bc3a1eedd678f9`.
**Yerel arşiv:** `raw/p02-3-reference-upload-3.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 671744}, "kind": "upload-budget", "max_elapsed_seconds": 63.31467216700548, "max_extra_rss_upper_bound_bytes": 4571136, "passed": true, "source_commit": "50946ba0519efdf6bc27dad2ca18b694262ab84c"}`.

## p02-3-reference-upload-4

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `ba353ac6f22612b756fa8792829bae28cdf6107e6b34ae7c36d6f5e25a12c686`.
**Yerel arşiv:** `raw/p02-3-reference-upload-4.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 851968}, "kind": "upload-budget", "max_elapsed_seconds": 64.46807291600271, "max_extra_rss_upper_bound_bytes": 4521984, "passed": true, "source_commit": "9ab9d6a2d04dbfb4051e93fa244b36550ab25b4b"}`.

## p02-3-reference-upload-5

**Tür:** `upload-budget`.
**Özgün JSON SHA-256:** `53f2a3d680dd4bfdf6258beb2ebfe135678c778214a1ccb1d5b7d5ea6204dc4f`.
**Yerel arşiv:** `raw/p02-3-reference-upload-5.json.gz`.
**Özet:** `{"cases": 12, "diagnostic_only": false, "growth": {"passed": true, "span_upper_bound_bytes": 1179648}, "kind": "upload-budget", "max_elapsed_seconds": 67.09265533399594, "max_extra_rss_upper_bound_bytes": 4603904, "passed": true, "source_commit": "1b2cc1fb284fd22943d1c2fa06272e1970ebb7a2"}`.

## startup-ci-control

**Tür:** `startup`.
**Özgün JSON SHA-256:** `9cb35022e9ec958c1ae1c5f4190e4dfefd964b7c0dc7ec4a5ae151811d51c1c7`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/fc867fc686cefc09dbafae5642beeb59ea6c8796/docs/research/startup-ci-control.json); yerel arşiv `raw/startup-ci-control.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 121.04508304037154, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 97.559834131971, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 92.26295817643404, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 26.12408297136426, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 123.00616595894098, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 85.22891695611179, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 57.37687484361231, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 24.313292000442743, "passed": true, "samples": 30}}, "source_commit": null}`.

## startup-ci-paired

**Tür:** `startup`.
**Özgün JSON SHA-256:** `e111e614c9fd5d3ad58b53d99678c4733130b2e1d93fa7085ee689998d971db7`.
[İlk eşleşen kayıt baytları](https://github.com/HodeTech/Yorunge/blob/fc867fc686cefc09dbafae5642beeb59ea6c8796/docs/research/startup-ci-paired.json); yerel arşiv `raw/startup-ci-paired.json.gz`.
**Özet:** `{"diagnostic_only": false, "kind": "startup", "measurements": {"baseline/cache": {"budget_ms": 200.0, "p95_ms": 115.89816701598465, "passed": true, "samples": 30}, "baseline/context": {"budget_ms": 200.0, "p95_ms": 76.45354187116027, "passed": true, "samples": 30}, "baseline/help": {"budget_ms": 500.0, "p95_ms": 26.900457916781306, "passed": true, "samples": 30}, "baseline/version": {"budget_ms": 500.0, "p95_ms": 25.615291204303503, "passed": true, "samples": 30}, "candidate/cache": {"budget_ms": 200.0, "p95_ms": 114.30612509138882, "passed": true, "samples": 30}, "candidate/context": {"budget_ms": 200.0, "p95_ms": 83.85437494143844, "passed": true, "samples": 30}, "candidate/help": {"budget_ms": 500.0, "p95_ms": 24.29741690866649, "passed": true, "samples": 30}, "candidate/version": {"budget_ms": 500.0, "p95_ms": 22.593999980017543, "passed": true, "samples": 30}}, "source_commit": null}`.
