---
id: P02-3x
phase: P02
status: verified
size: M
depends_on: [P02-3y]
capabilities: [C03, C12]
---
# P02-3x — Continuation `reconcile` bağlaması

**Tarih:** 2026-11-07. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6 (devam); P02-3h’nin ölçülen kapsamından ayrıştırıldı. Mevcut `reconcile` komutunun v3 kayıtlar ve devam edilmiş kaynaklar için bağlanması.

## Kullanıcı sonucu ve mevcut eksik

3M makbuzu tam ama proof’u eksik kalan bir v3 `unknown` kaydın kullanıcı yeni bir devam planı yapmadan, aynı operation’da kanıtlanıp kapanabilmesi gerekir; bugün `reconcile` yalnız v2 plan ve kayıtlarını tanır. Ayrıca bir devam admit edildikten sonra kaynağın okuma lease’i ve yerel `reconcile` yazıcısı hâlâ çalışır; bunun kararı verilmemiştir.

## Giren ve girmeyen kapsam

Girer: (1) `upload_reconcile_local.load_read_input`, `upload_reconciliation` ve metadata kapanışı v3 plan/kayıt/proof birleşimini tanır: kök baseline **zincir çözümleyicisiyle** (kaynak → kök görünümü → `CreateReceiptV2`), 3M graf (`acknowledged_stages`), detail↔baseline karşılaştırması, `TransferVerificationV3` (N dosya, açık okuma politikası) ve `read_failed` v3’te `unknown/read_unavailable`; 3M makbuzu tam ama proof’u eksik unknown kayıt aynı operation’da `succeeded/metadata_verified` olur, graf eksikse `operation_uncertain` (unknown kalır). (2) **Karar ve uygulama:** `acquire_read` ve yerel `reconcile`ın yazıcısı (`load_read_input`un `cleanup_expired` çağrısı) kaynağın iptal edilmemiş torunu varken ne yapar — reddetmek (`operation_conflict`, torunu işaret etmek) ya da bugünkü davranışı (fence/revision artışı, `read_unavailable`/`identity_reset` nedeninin ezilmesi; geçerliliği bozmaz) belgelemek; seçilen davranış testlidir. Girmez: aşama yürütücüsü ([P02-3w](p02-3w-continuation-stage-executor.md)), başlatma ([P02-3y](p02-3y-continuation-start.md)), public API/CLI, canlı kabul.

## Bağımlılıklar ve kararlar

P02-3y verified olmalıdır (kapanış okuması ve proof kurucusu orada yazılır). Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §5 ve [sözleşme](../../reference/dataset-upload-continuation.md) (“Mevcut `reconcile`, 3M makbuzu tam ama proof’u eksik v3 unknown kaydı için aynı operation’da çalışır”); ADR değişmez.

## Sözleşme ve uygulama sınırı

v2 `reconcile` ve v2 original yolu davranışsal olarak aynı kalır; torunu olmayan v1/v2 kaynaklarda `acquire_read` ve `cleanup_expired` aynı kararı, kaydı ve hata kodunu verir (torun taraması deponun bütün operation/plan satırlarını çözer: çözülemeyen ilgisiz bir satır `state_invalid` verir, değişmezlik kapısı güvenli tarafta kapanır). Kök baseline çözümleyicisi `require_created_baseline` ile paylaşılır; `created_dataset` bir devam için hata verir.

**P02-3h devri (sürüm dağıtım listesi).** [`tests/fixtures/version-dispatch-sites.json`](../../../tests/fixtures/version-dispatch-sites.json) bu karta beş v2-yalnız noktayı atar: `upload_reconcile_local.read_policy` ve `load_read_input` (üç nokta) ile `upload_reconciliation._ReadEnvironment.acquire` ve `commit`. Kart bunları v3’ü tanıyacak ya da bilinçli reddedecek biçimde günceller ve listedeki sahibini `done` (ya da gerekçeyle `v2-only`) yapar; liste yeşil kalmadan kart kapanmaz.

**P02-3r R2 devri.** `acquire_read` bir devam admit edildikten sonra kaynakta okuma lease’i alabilir ve yerel `reconcile`ın `cleanup_expired` çağrısı kaynağın fence/revision’ını artırıp nedenini ezebilir; tam grafli bir kaynağa devam edilemediğinden ve eksik grafli kaynak `reconcile` ile `succeeded` olamadığından bu geçerliliği bozmaz (R2-A/R2-B probları). Karar bu kartta verilir.

## Kabul

1. Gerçek TLS/SQLite ile: 3M makbuz tam + proof eksik v3 unknown kayıt → `reconcile` → `succeeded/metadata_verified` (aynı operation kimliği, N dosya proof, kök baseline eşliği); graf eksik → `operation_uncertain` ve kayıt `unknown`; yanlış dataset/baseline ya da içerik farkı → mevcut hata kodları ve kayıt `unknown/read_unavailable` kalır (fence ve revision v2'deki gibi birer artar, proof yoktur); v3 `read_failed` → `unknown/read_unavailable`.
2. Devam edilmiş kaynak kararı: seçilen davranış her iki yönde testlidir (kaynağın fence/revision/nedeni ya da reddin kodu ve torun kimliği); torunsuz v1/v2 kaynaklarda `reconcile` ve `acquire_read` (torun taramasının tüm operation satırlarını çözmesi istisnası dışında) mevcut testlerle aynı sonucu verir.
3. v2 original yolu ve v2 `reconcile` mevcut testlerle değişmeden geçer; sır/yol sızıntısı yoktur; `tests/contracts` ve sürüm dağıtım listesi yeşildir.

## Doğrulama

Gerçek TLS/süreç/SQLite integration testleri, v1/v2 farklı-ikili karşılaştırması, Ruff ve strict mypy.

**Gerçekleşen kapsam (P02-3x).** `upload_reconcile_local`: `ReadInput` v2 ya da v3 plan/kayıt taşır, `read_policy` ikisinin `explicit_attempt` politikasını kabul eder, `load_read_input` devam için baseline’ı kökün zincirinden alır; `upload_reconciliation._ReadEnvironment` ve `application/upload_reconciliation` iki kayıt ailesiyle çalışır; `upload_reconcile_metadata` devam için `continuation_proof` ile N dosyalık `TransferVerificationV3` kurar. Beş v2-yalnız dağıtım noktası çözüldü (liste `done`). **Karar (2):** iptal edilmemiş torunu olan kaynak reddedilir — `StateUploads.require_no_successor` (yerel, okuma-yalnız) `load_read_input`un başında, `_no_successor` ise `acquire_read` ve `cleanup_expired` işlemlerinin içinde işler; hata `SourceHasSuccessor` (`operation_conflict`, torunun kimliği) ve `_reconcile`ın hata yeniden bağlamasından geçer. Public `recover_upload` devamı ilk sürümde `show_upload` ile reddediyordu (`state_invalid`: sonuç tipleri genişleyene kadar kayıt kapatılıp özeti reddedilmesin); P02-3i sonuç tiplerini genişletti ve bu korumayı kaldırdı. Testler: `tests/integration/test_upload_continuation_reconcile_kill.py` (4: çocuk süreç okuma lease'inden sonra, metadata alındığında, proof commit'inden önce ve sonra SIGKILL; ölü süreç lease'i tutarken kimse okumaz, lease dolunca aynı operation kanıtlanır) ve `tests/integration/test_upload_continuation_reconcile.py` (26; v1/v2 farklı-ikili karşılaştırması incelemede elle yapıldı ve genel `recover_upload` v1/v2 yanıtları bu dosyada sabitlendi: gerçek TLS/SQLite; kapanış okuması bozulmuş devam → aynı operation’da kanıt, anahtar döndürülmüş durum, graf eksik → belirsiz, 7 okuma hatası, iptal, onay bayrağı, gönderim yapmamış kayıt, torunu olan kaynak iki yönde ve depo kapıları, public koruma) ve v1/v2 reconcile testleri değişmeden geçer. R1 sonrası ek: `tests/integration/test_upload_continuation_reconcile_gaps.py` (hâl: kapının yazma transaction’ının içinde olduğu, lease’i dolmuş `admitted` torunun sayılmadığı, `acquire_read`in tek başına reddi, 3M makbuzlu `running` devamın lease dolunca kanıtlanması, probe/liste hatası, iki derinlikli zincir, altı GET ve kilitsiz bekleme) — toplam 26 + 4 + 13 test. R2 sonrası: torun taramasında çözülemeyen satır (planı silinmiş bir operation satırı dahil) kapıyı `state_invalid` ile ve **o satırın** kimliğiyle kapatır (`upload_plan_not_found` sağlam kaynağın adıyla dönmez); `tests/integration/test_upload_continuation_reconcile_r2.py` (8): bozuk/eksik satırlı depo, kapının `phase` içinde `state_busy` verdiği, torunu olan kaynağın public cevabının torunun kimliği olduğu, kanıtın ilk items GET’inden önce damgalandığı ve oturum içinde bayatlayan kontrolün listeden önce durduğu.

## Teslim kaydı

- PR/commit: tek development PR’ı ([PR #15](https://github.com/HodeTech/Yorunge/pull/15)) bu daldan açıldı ve 2026-11-12’de [69efc8d](https://github.com/HodeTech/Yorunge/commit/69efc8d465078257257d6494e15fda0e360b01e2) merge commit’iyle development’a alındı; adım commit’leri artık development tarihçesindedir: uygulama [9f4efa2](https://github.com/HodeTech/Yorunge/commit/9f4efa2985d4616e481544476953deeca85b5b8a); R1 düzeltmeleri [dd00024](https://github.com/HodeTech/Yorunge/commit/dd00024ba6f615c58f3977c61018991d04e9a57c), [fc0137c](https://github.com/HodeTech/Yorunge/commit/fc0137c5675cedf52a3c83844d95b0ca1684dc29); R2 düzeltmeleri [d364030](https://github.com/HodeTech/Yorunge/commit/d3640303b914ba3a068c4c51ed6a3bbb01455bd7), [2533f47](https://github.com/HodeTech/Yorunge/commit/2533f47d4d851451bef375dcbc6c4e31fbcd3e12).
- Sonuç: `reconcile` 3M makbuzu tam ama proof’u eksik bir v3 kaydı aynı operation’da kanıtlar (`succeeded/metadata_verified`; graf eksikse `operation_uncertain`); devam edilmiş kaynak tarihsel ve değişmez kalır (`SourceHasSuccessor`: `operation_conflict`, hata kimliği torunun kimliği; kapı yazma işleminin içindedir); beş sürüm dağıtım noktası çözüldü (R1 ve R2 kapandı; Adım 19). Tam paket: 12.785 geçti, 1 atlandı, 0 düştü (`10b19be`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, `f82d789`un Linux koşusu ext4’ün inode numarasını hemen geri vermesine dayanan beş test hatası buldu (testin yardımcısıydı, ürün değil), düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Canlı sağlayıcı gözlenmedi (gerçek listeleme/sayfalama, ikinci presign, `actual_count`); gerçek CLI SIGINT/TTY denenmedi (CLI P02-3i’de sınandı); torun taraması bütün operation satırlarını çözer ve güvenli tarafta kapanır (ilgisiz tek bozuk satır `state_invalid` verir; belgeli); Linux CI ve Python ≥ 3.12 asyncio SIGINT semantiği PR aşamasında sınanır.
