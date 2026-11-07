---
id: P02-3w
phase: P02
status: draft
size: M
depends_on: [P02-3h]
capabilities: [C03, C12]
---
# P02-3w — Continuation aşama yürütücüsü: v3 port ve okuyucu, alt küme koordinatörü, confirm sayaç tabanı

**Tarih:** 2026-11-07. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6 (devam); P02-3h’nin ölçülen kapsamından ayrıştırıldı. Etkili HTTP aşamaları (presign, PUT, confirm) için v3 yürütme makinesi; başlatma ve proof [P02-3y](p02-3y-continuation-start.md)’dedir.

## Kullanıcı sonucu ve mevcut eksik

Onaylı ve admit edilmiş bir devam operation’ının yalnız seçilen dosyalarını güvenle göndermek için gereken port, okuyucu ve koordinatör bugün yalnız v2 planını tanır (create/link-ilk, bütün dosyalar, confirm sayacı tabanı 0). Dolu bir veri setine devamda sağlayıcı sayısı kümülatif olabilir (doğrulanmamış hipotez; yalnız taze veri setinde 1, 2 gözlendi) ve bugünkü kodlayıcı ilk confirm’i yanlış reddederdi.

## Giren ve girmeyen kapsam

Girer: (1) **v3 port ve okuyucu**: `ObservedUploadPort` ve `ObservedUploadReader.current` plan birleşimini (`DatasetUploadPlanV2 | DatasetContinuationPlanV3`) kabul eder; istek bütçesi `plan.request_limits`ten (create=link=0, presign=PUT=confirm=M, bayt tavanı seçilen dosyaların toplamı; `UploadBudget` bugün yalnız v2 limit tipini (`UploadRequestLimits`: create=link=1, M≥1) kabul eder ve `ContinuationRequestLimits`i de kabul edecek biçimde genişler (`UploadPreparationRuntime._http(limits: UploadRequestLimits, …)` parametresi onunla birlikte genişler; üretici bugün onu v2 tipiyle çağırır) — salt okuma üretici bütçesi (P02-3h) v2 tipiyle kurulur, çünkü etkili sayaçları kullanmaz), dosya bağlamları `files(operation_id, dataset_id)` ile yalnız seçilen dosyalar için ve dataset kimliği `plan.continuation.dataset_id`ten gelir; port tarafındaki istek özeti ([P02-3g devir notu](#sözleşme-ve-uygulama-sınırı)) dataset kimliğini plan bağından alır. (2) **Confirm oracle**: `confirm_ack(data, confirmed_count, secret, *, base=0)` ve port `prepare_confirm(upload, confirmed_count, base)`: `created=1`, `batch_duplicates=0` ve varsa `actual_count ∈ {base + k + 1, k + 1}` (k = bu operation’da kabul edilmiş confirm sayısı; `base = plan.continuation.remote_present_count`, admission sonrası `show(operation_id=…).plan.continuation.remote_present_count`); iki anlam da kabul edilir, kümenin dışı reddedilir; `base=0` iken tek değerdir ve v2 yolu byte-byte değişmez. (3) **Alt küme koordinatörü** (`application/upload_workflow.py`): ortam protokolünün plan/kayıt tipleri v2|v3 birleşimidir; yeni `continue_files(environment)` `graph_of(plan).files` ve `put_batches()` (alt küme) üzerinden hepsi presign → en çok iki PUT → seri confirm, tek deneme, tek permit uygular; create/link yoktur; `M=0` hiçbir şey göndermez. (4) **Aşama ortamı** (`adapters/upload_continuation.py`ın aşama kısmı): `current` (taze `UploadCurrentCheck`, eylem `upload_created_dataset`, beklenen dataset kökün baseline’ı), `arm`, `prepare`, `publish` (confirm sayacı), `validate_uploads` ve hata yolu (intent’siz kayıt yerel iptal, intent’li kayıt `operation_uncertain`). (5) [Tüketici referansının](../../reference/platform-upload-consumer.md) `actual_count` tanımının düzeltilmesi. Girmez: pre-admission taze envanter, kapanış okuması ve proof ([P02-3y](p02-3y-continuation-start.md)), `reconcile` ([P02-3x](p02-3x-continuation-reconcile.md)), public API/CLI, canlı kabul.

## Bağımlılıklar ve kararlar

P02-3h verified olmalıdır (kendi planlarını üretici kurar; testler ayrıca `lifecycle` düzeneğiyle admit edilmiş kayıtlar da kullanır). Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §5; yeni replay, politika veya TTL yoktur. v2 kodlayıcısının davranışı (taban 0) değişmez.

## Sözleşme ve uygulama sınırı

Mevcut presign/PUT/confirm codec’leri, bütçe sayaçları ve storage portu v2 yolunda değişmeden kalır; v3 yalnız confirm sayaç tabanını ve alt küme bağlamını ekler. `created≠1`, kopya, fazladan item ve yanlış toplam başarı değildir.

**P02-3d devir notu.** Orijinal koordinatör `graph.files` ve `graph.put_batches()` (demetler) üzerinden döner; continuation koordinatörü aynı iki-worker toplu PUT kalıbını `file_indices` alt kümesi için kullanır. `_Environment._context` ve `validate_uploads` bugün planın bütün dosya kümesiyle korunur (`graph_of(plan).files`); `validate_uploads` içindeki `range(len(self.contexts))` N tabanlıdır ve alt küme için seçili indekslerden türetilmelidir. Bu korumalar P02-3d R2’de testle kilitlenmiştir (`test_environment_*`); alt küme davranışı onları bilinçli günceller.

**P02-3g devir notu.** Depodaki `request_digest` v3’te dataset kimliğini plan bağından alır; port tarafındaki `upload_request_digest` çağıranları (`platform_upload_port.py`deki istek sarmalayıcısı ve `platform_upload_put.py`) dataset kimliğini üreticiden alır. v3 koordinatörü bu değeri `plan.continuation.dataset_id` olarak vermelidir; aksi halde port özeti ile depo doğrulaması ayrışır ve geçmiş `state_invalid` olur. Bir test, v3 plan için port özetini depodakiyle bağımsız olarak eşitler.

**P02-3r devir notu (aşama kapıları).** `arm` ve `receipt` admit edilmiş depo örneğinde (ya da eşit `write_access` ile) çağrılır — erişim süreç bağlıdır; create/link `invalid_request`, seçim dışı dosyanın presign’ı `invalid_request`, öncülü hiç kabul edilemeyecek put/confirm’i `operation_conflict`; check-only kayıt `arm` etmez (`operation_conflict`); makbuz yalnız `StageReceipt` (create makbuzu `invalid_request`); `arm` taze kontrolünün eylemi `upload_created_dataset`, dataset kimliği kaydınki.

## Kabul

1. Gerçek loopback TLS sunucusuyla M>0 (örn. 8 dosyadan 5’i): yalnız seçilen dosyalar presign → PUT → confirm sırasıyla gönderilir; sunucu sayacı create ve project_link isteği **sıfır**, effectful istek sayısı ≤ 3M. Dolu veri setinde (N−M>0 mevcut item) **her confirm sayaç kontrolünden geçer**: sunucu fixture’ı hem kümülatif (`taban+k+1`) hem yalnız-işlem (`k+1`) anlamını ayrı koşularda yansıtır; ikisi dışındaki sayı kontrollü unknown olur; taban 0 (v2 yolu) kodlayıcısı değişmez ve mevcut v2 testleri geçer.
2. İki-worker toplu PUT alt küme için v2 ile aynı kurallarla çalışır (bir worker başarısız → başka permit verilmez, SIGINT/Task iptali); sıra, öncül ve tazelik v2 kuralıyla aynıdır.
3. Her aşamada 401/403/429/5xx ve kayıp cevap: intent’li kayıt `unknown/request_uncertain` ve `operation_uncertain` (aynı operation kimliği), intent’siz kayıt yerel iptal; hiçbir replay yoktur.
4. Bütçe ve deadline kuralları v2 ile aynıdır (etkili deneme sayısı 3M, yüklenen bayt seçilen toplam, bekleyen yanıt 0).
5. Port istek özeti (dataset kimliği plan bağından) depo doğrulamasıyla bağımsız olarak eşittir; ayrışma `state_invalid` verirdi ve testle kilitlidir.
6. Gerçek SIGKILL: admission sonrası, her aşamanın intent’i ve makbuzu ve iki-worker PUT sırasında v3 geçmişi okunabilir kalır ve ikinci etki yoktur.
7. Signed URL, ham anahtar, `created_dataset` ve literal credential canary’leri DB/log/istisna/çıktıda yoktur; v1/v2 yolları ve altın dosyalar değişmez; `tests/contracts` ve sürüm dağıtım listesi yeşildir.

## Doğrulama

Gerçek TLS/süreç/SQLite integration testleri, bütçe sayaç testleri, Ruff ve strict mypy. Kurulu yolculuk ve native ölçüm P02-3i/P02-3a’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
