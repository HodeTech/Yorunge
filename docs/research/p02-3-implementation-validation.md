# P02-3 uygulama ve kabul kaydı

**Tarih:** 2026-11-06 Europe/Istanbul. **Dal/taban:** `feat/p02-3-dataset-recovery`, development `94aaaf0`. **Durum:** Uygulama sürüyor (adım 1 incelemede); ADR-0031/0032/0033 kullanıcı 2026-11-06 talimatıyla Accepted. **Canlı kabul kaydı yoktur**; hazırlık belge turları R1/R2/R3 [readiness incelemesinde](p02-3-readiness-review.md#review-ve-doğrulama-kaydı), uygulama adımları ve kod review turları aşağıdaki başlıklarda kayıtlıdır. Bu belge adımlar tamamlandıkça gerçek commit, kontrol, review ve ölçüm sonuçlarıyla büyür; başarısız sonuçlar silinmez. Plan: [P02-3 teslim planı](../roadmap/p02-3-delivery-plan.md); hazırlık: [readiness incelemesi](p02-3-readiness-review.md).

## Adım durumu

| Adım | Kart | Durum |
|---|---|---|
| 0 | Hazırlık (ADR/referans/kart/plan) | Belge turları R1/R2/R3 ve üç harici review işlendi; ADR-0031/0032/0033 Accepted (2026-11-06) |
| 1–7 | P02-3d, e, f, g, r, h, i (resume) | Adım 1 (P02-3d) `in_review`: karakterizasyon ve refaktör commit’lendi, R1 kapandı, R2 bekliyor; sonraki adımlar başlamadı |
| 8 | P02-3s (ortak no-clobber artifact yayıncısı) | Başlamadı; plan sırasıyla adım 8 |
| 9–14 | P02-3j–o (indirme) | Başlamadı; model yoklama kapısı K6a girdisi verilmediğinden “yapılmadı” kaydıyla geçilir |
| 15–16 | P02-3p–q (sürüm) | Başlamadı |
| 17 | P02-3a/b/c üst kartlar, son kaynak referans serisi, PR | Başlamadı |
| — | Model indirme yoklaması (K6a, adım 9 öncesi) | **Yapılmadı** (tarih: —; kullanıcı yetkisi ve model sürümü kimliği bekleniyor) |
| — | Resume canlı kabulü ve `actual_count` gözlemi (K6b) | **Yapılmadı** (tarih: —; kullanıcı yetkisi bekleniyor) |
| — | Sürüm okuma canlı kabulü (K6c) | **Yapılmadı** (tarih: —; kullanıcı yetkisi ve dataset kimliği bekleniyor) |

Her adım için commit, kontrol çıktıları, R1/R2 reviewer eksenleri ve doğrulanmış bulguların kapanışı burada kendi başlığıyla kaydedilir.

## Adım 1 — P02-3d aşama grafiği tek belirtimi

**Commit’ler:** karakterizasyon `a881aca` (ürün kodu değişmeden), refaktör `8308ae9`, R1 düzeltmeleri sonraki commit. **Kart:** [P02-3d](../roadmap/tasks/p02-3d-stage-graph-spec.md) `in_review`.

**Karakterizasyon (kabul 1).** Gerçek spawn + SIGKILL matrisi sekiz sınırdan 19 duruma çıktı: `link_intent/response/commit`, `presign_intent`, `put_intent`, `put_commit`, `confirm_intent`, `confirm_response`, iki-worker PUT batch’i (`two_put_response`, `two_put_commit`) ve üç dosyalı ikinci batch PUT intent’i. Her durumda aynı-ID kayıt latch’li `running` kalır, yeniden başlatma yolu ağa çıkmaz, `provider.events` tam sırası ile intent/makbuz sayıları beklenenle birebirdir, süre dolumunda kayıt `unknown` olur ve ikinci etki sıfırdır. **Güçlendirilmiş testler hem refaktör öncesi ürün koduyla (`650258c` `src`, `PYTHONPATH` ile) hem sonrasıyla 19/19 geçti** (ilk sürüm 12/12’ydi; R1 bulguları üzerine genişletildi).

**Eşdeğerlik (kabul 2, 3, 5).** `tests/contracts/test_upload_graph.py`: eski formüllerin donmuş kopyalarıyla N=1..128 × plan sürümü 1/2 için aşama kümesi, öncül, rezerv, istek tavanları ve PUT batch’leri; bilinmeyen sürüm/dosya sayısı reddi; DDL, `StageIntent.sequence` ve `MAX_EFFECT_INTENTS` sabitlerinin belirtime bağlanması. `tests/contracts/test_upload_graph_wiring.py`: çağrı noktaları (hazırlanan istek limitleri, `_arm_input`, `StageIntent` dosya indeksi eşleşmesi, `request_digest` kaynakları, `_receipt_key`) donmuş formüllerle farksızdır; `graph_of` gerçek v1/v2 plan fixture’larıyla sınanır. Hiçbir golden/fixture değişmedi.

**Kontroller.** Refaktör commit’inde tam pytest: 6635 passed, 1 skipped (Linux native sayaç); sonraki çağrı noktası düzenlemelerinden sonra upload ile ilgili 56 test dosyası 2178 passed; R1 düzeltmelerinden sonra `tests/contracts` + temel upload integration paketleri 4390 passed, 1 skipped. Ruff, strict mypy, `check-docs` ve `check-agent-guides` temiz. Son tam koşu adım kapanışında bu başlığa eklenir.

**R1 (iki bağımsız sonnet/yüksek-effort reviewer: refaktör eşdeğerliği; kill testi güvenilirliği ve süreç).** P1 yok. Doğrulanan bulgular işlendi: iki-worker commit penceresi, tam `provider.events` doğrulaması, latch ve cleanup sonrası değişmezlik, sayımdan önce loopback sunucusunun yerleşmesi (kesilen istek yarışı), ek gerçek-kill sınırları, plan sürümü sabiti (`CURRENT_PLAN_VERSION`), literal oracle aralığı, döngüsel kontrolün kaldırılması, çağrı noktası eşdeğerlik testleri ve kartın teslim kaydı. Bir bulgu kod okumasıyla çürütüldü: iki-worker kill’inde intent sayısının yarışa bağlı olduğu iddiası geçersizdir, çünkü makbuz yayını yalnız batch boşaltmasından (`_drain`) çalışır ve o noktada iki PUT intent’i de yazılmıştır. **Açık:** R2.
