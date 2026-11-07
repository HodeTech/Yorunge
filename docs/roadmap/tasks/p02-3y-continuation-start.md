---
id: P02-3y
phase: P02
status: draft
size: M
depends_on: [P02-3w]
capabilities: [C03, C12]
---
# P02-3y — Continuation başlatma: taze envanter, M=0 ve N-dosya proof, hata eşlemesi

**Tarih:** 2026-11-07. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6 (devam); P02-3h’nin ölçülen kapsamından ayrıştırıldı. Onaylı bir devam planını uçtan uca çalıştıran özel (private) iş akışı; public `start` yüzeyi P02-3i’dedir.

## Kullanıcı sonucu ve mevcut eksik

Plan onaylandıktan sonra gerçekten başlatan, başlatmadan hemen önce uzak durumu yeniden sınıflayıp kayıtlı planla karşılaştıran, yalnız seçilen dosyaları gönderen ([P02-3w](p02-3w-continuation-stage-executor.md)) ve tüm dataset’i N dosyalık metadata kanıtıyla kapatan bir bileşim yoktur. `M=0` (yalnız doğrulama) yolu ve hata/iptal/belirsizlik eşlemesi de bu bileşimin parçasıdır.

## Giren ve girmeyen kapsam

Girer: (1) `run_upload_continuation` (özel adaptör): mevcut operation aynı plan için ağ olmadan döner (iptal edilmiş olabilir: çağıran `status`a bakar), plan/onay penceresi ve `draft`/onay denetimi, yerel root/Manifest’in tam yakalanması, kapsam denetimleri (`UploadResumeRuntime._check_scope`: adsız; v2’nin `_scope`u dataset adının ad alanını da denetler ve devam planının adı kökünküdür, bu yüzden bir devam için `operation_conflict` verir). (2) **Pre-admission taze envanter ve yeniden sınıflama**: zincir journal’ı ve taze uzak envanterle `classify` yeniden koşar; `source_blockers` ve çağıranın engelleri `with_blockers` ile birleşir (dataset’in baseline olarak gösterilememesi — `BaselineCheck.dataset_observed=False`, üretici bunu `membership_unobserved` sayar — sınıflandırmadan önce durur ve burada da sınıflandırılmaz, bu `continuation_remote_changed`tır; çağıran `reader.baseline`ın verdiği `BaselineCheck.authorization.require_current`i çağırmalıdır, aksi `me`deki bir 401 yanlışlıkla `dataset_observed=False` görünür); herhangi bir engel ya da `binding_matches` farkı (seçim ya da iki özet) **`continuation_remote_changed`/2** verir (istek ve yerel yazı yoktur); ulaşım/erişim hataları kendi kodlarıyla (`transport_*`, `remote_*`, `invalid_response`) hata olarak kalır. (3) `admit(plan_id, fresh)` → aşama yürütme ([P02-3w](p02-3w-continuation-stage-executor.md)) → **kapanış okuması**: `prepare_initial_read` (M=0 kayıt `admitted` iken), kapanış yetki okuması, bütün dataset’in öğe okuması (`read_items`: Manifest dışı ya da boyutu/sha256’sı farklı öğe `invalid_response`; depo proof içeriğini Manifest ile yazmadan önce karşılaştırmaz), `TransferVerificationV3` kurulumu (N dosya, açık okuma politikası, grant yok) ve `verified`; `M=0` yalnız doğrulama. (4) **Hata/iptal/belirsizlik eşlemesi** (`failure`): intent’siz kayıtta okuma hatası `read_failed` ile kaynağın kendi kodu ve `cancelled/local_cancelled`; SIGINT/Task iptali `request_cancelled`/6; geç proof `execution_timeout`; operation’dan önce gözlenmiş proof ve gönderilmemiş M>0 kayıtta erken proof `operation_conflict` (kayda dokunulmaz); ilk intent’ten sonra kesinti `unknown/request_uncertain` ve `operation_uncertain`/5; admission reddi (hepsi `operation_conflict`) için `source_active`/`source_superseded` ayrımı `chain_snapshot` ve `descendant_verdict` yeniden okumasıyla yapılır. Girmez: aşama yürütücüsü ([P02-3w](p02-3w-continuation-stage-executor.md)), `reconcile` ([P02-3x](p02-3x-continuation-reconcile.md)), public API/CLI, canlı kabul.

## Bağımlılıklar ve kararlar

P02-3w verified olmalıdır. Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §5 ve uç-durum tablosu; yeni replay, politika veya TTL yoktur.

## Sözleşme ve uygulama sınırı

Başarılı sonuç yalnız metadata seviyesidir ve `remote_bytes_verified=false`; authority/pricing yükseltilmez. Taze envanter sınıf özeti kayıtlı plandan farklıysa admission öncesi `continuation_remote_changed`/2; PUT sırasında veya proof öncesinde uzak envanter beklenenden sapmışsa mevcut unknown kuralı (yeni etki yok).

**P02-3w devri (aşama yürütücüsü).** `adapters.upload_continuation.run_stages(runtime, plan, bound, inputs, baseline, end, algorithm)` bir oturumda planın limitleriyle tek bütçe, tek port ve `ContinuationStages` ortamı kurar ve `algorithm(environment)`i yürütür; hata `environment.failure` ile operation’ın kendi hatasına çevrilir. Başlatmanın algoritması şudur: `environment.admission()` (M>0 için yükleme, `M=0` için dataset’i okuma izni; ikincisi `ObservedUploadReader.current`in `read_created_dataset` kolu ve bu adımda hazırdır; `prepare_initial_read` bu kartındır) → `environment.admit(check)` (onay ayrı bir adımdır) → `application.upload_workflow.continue_files(environment)` (yazma erişimi başkasında olan kayıtta hiçbir şey göndermez, aşama hatasını kendisi operation’ın hatasına çevirir; dıştaki bir `_guarded` aynı hatayı bir kez daha işler, v2 ile aynı) → kapanış okuması. `baseline` çağırandan gelir (kökün baseline’ı, `resume_source(...).baseline`) ve planın dataset’iyle eşit olmalıdır (aksi `invalid_request`, hiçbir okuma yapılmadan). Özgün yükleme her dosyayı presign ettiğinden devam seçtiği dosyaları ikinci kez presign eder (yeni operation, yeni nesne anahtarı): gerçek platformun buna izin verdiği **gözlenmemiştir** (canlı kabul “yapılmadı”; fixture `represign=True` ister). Confirm sayacı iki anlamlıdır (`confirm_ack(base=)`, her confirm için ayrı; operation boyunca kilitleme denendi ve bırakıldı); kümenin dışı kontrollü unknown’dır. Kapanış okuması `ContinuationStages._renew_for_probe()` (v2 `verify_original` de aynısını çağırır; gerekirse herkese açık bir ada alınır) ve v2 `_deadline(environment, check, access)` işlevinin v3 karşılığını (`environment.record`, `runtime.clock`, `end`, `plan` ve `access` herkese açıktır) kendisi kurar.

**P02-3h devri (sürüm dağıtım listesi).** [`tests/fixtures/version-dispatch-sites.json`](../../../tests/fixtures/version-dispatch-sites.json) bu karta v2-yalnız `upload_original_read.verify_original` noktasını atar (özgün iş akışının kapanış okuması). Kapanış okuması (öğe okuması, proof) bir devam için kendi yolunu kurar ya da bu işlevi v3’ü tanıyacak biçimde genişletir; liste yeşil kalmadan kart kapanmaz.

**P02-3r devir notu (başlatma sırası).** `admit(plan_id, fresh)` mevcut operation’ı kontrolsüz döndürür (iptal edilmiş olabilir); depo admission retleri nedenleri ayırmaz. Check-only akışta okuma hatası `read_failed` ile `cancelled/local_cancelled` yapar ve okumanın kendi kodu döner; reddedilen geç proof `execution_timeout` ile iptal eder (işaretçi yazılamazsa kayıt `admitted` kalır, hata yine `execution_timeout` ve lease temizliği iptal eder); gönderilmemiş kayıtta `verified`/`read_failed` `operation_conflict` verir. Confirm sayaç tabanı `show(operation_id=…).plan.continuation.remote_present_count` alanındadır.

## Kabul

1. Gerçek loopback TLS sunucusuyla uçtan uca: M>0 başarı (kayıt `succeeded/metadata_verified`, proof N dosya, `remote_bytes_verified=false`); `M=0` (hiçbir etkili istek yok); plan–start arası drift (envanter ya da özet farklı → `continuation_remote_changed`, istek ve yerel yazı yok); PUT sırasında item ekleme/silme; confirm `created=0`; her aşamada 401/403/429/5xx ve kayıp cevap; her durumda sunucu sayacı create ve project_link isteği **sıfır**, effectful istek sayısı ≤ 3M.
2. Gerçek SIGKILL sınırları (admission, her aşama intent/receipt, iki-worker PUT, proof) v3’te de ikinci etkisiz ve aynı-ID kalır; devam yine bir sonraki continuation ya da `reconcile` iledir.
3. `M=0` uç-durum tablosunun her satırı ([ADR-0031 §5](../../decisions/0031-upload-continuation.md#5-yürütme)): admission → proof → `succeeded`; okuma hatası → kaynağın kendi kodu (exit 1/3) ve `cancelled/local_cancelled`, hiçbir zaman `unknown`; SIGINT/Task iptali → `request_cancelled`/6 ve `cancelled/local_cancelled`; lease kaybı/SIGKILL → `cleanup_expired` ile `cancelled/lease_expired`; hiçbirinde intent yok; aynı plan yeniden başlatılamaz.
4. Mevcut operation (aynı plan ikinci kez) ağsız döner; başka süreç kazanmışsa bu süreç yazma erişimi iddia etmez.
5. Başarılı sonuç yalnız metadata seviyesidir; authority/pricing yükseltilmez; signed URL, ham anahtar, `created_dataset` ve literal credential canary’leri DB/log/istisna/çıktıda yoktur; bütçe ve deadline kuralları v2 ile aynıdır; v2 original yolu ve altın dosyalar değişmez.

## Doğrulama

Gerçek TLS/süreç/SQLite integration testleri, bütçe sayaç testleri, `tests/contracts`, Ruff ve strict mypy. Kurulu yolculuk ve native ölçüm P02-3i/P02-3a’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
