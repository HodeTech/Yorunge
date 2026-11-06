---
id: P02-3h
phase: P02
status: draft
size: M
depends_on: [P02-3r]
capabilities: [C03, C12]
---
# P02-3h — Continuation üreticisi, alt küme koordinatörü ve proof

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6. Gerçek TLS/HTTP bileşimi; public CLI/API sonraki dilimdedir.

## Kullanıcı sonucu ve mevcut eksik

Kalıcı v3 kapıları olsa bile sınıflandırmayı taze uzak durumla doğrulayıp yalnız seçili dosyaları güvenle gönderen ve N dosyalık metadata kanıtıyla kapatan bileşim yoktur. Ayrıca mevcut confirm kodlayıcısı `actual_count`’u “bu iş akışında kabul edilmiş confirm sayısı+1” bekler; dolu bir veri setine devamda sağlayıcı sayısı kümülatif olabilir (doğrulanmamış hipotez; yalnız taze veri setinde 1, 2 gözlendi) ve ilk confirm yanlış reddedilirdi.

## Giren ve girmeyen kapsam

Üretici önce yerel journal’dan günlük engellerini (`source_blockers`, `descendant_verdict`, `chain_blockers`) değerlendirir ve biri varsa uzak okuma yapmaz (rapor gözlemsizdir, `--prepare` reddedilir); yoksa üyelik, detail↔baseline ve envanteri okur, `classify` sonucuna çağıranın engellerini `with_blockers` ile ekler ve aynı manifestle `resume_report` kurar (`Classification.manifest_digest` karışıklığı reddeder). Üretici planı [P02-3f’nin saf işlevleriyle](../../reference/dataset-upload-continuation.md) kurar: `continuation_limits` (istek tavanı), engelsiz sınıflandırmadan `continuation_binding` (bağ) ve `prepare_continuation_v3` (mühür: ömür = pencere ve kanıtların en erken bitişi, digest, seçilen bayt doğrulaması); çalışma penceresi ve `ContinuationCostWork` bileşimi, v2 `_work`/`_limits` gibi, üretici adaptöründedir. Hata eşlemesi v2 üreticisiyle aynıdır: Manifest başvurusu planlananla uyuşmuyorsa `input_changed`; politika seçimi geçersizse veya tip doğrulayıcısı/16 KiB tel sınırı `ValueError` verirse `invalid_request` (v3 plan canonical boyutu v2’den en çok ~1,5 KiB büyük olduğundan 16 KiB’a çok yakın kaynak planlar böyle reddedilir; yeni kod yoktur); `binding_matches` manifesti karşılaştırmaz, manifest başvurusu eşitliği `validate_continuation_selection` içindedir; pre-admission taze envanter ve yeniden sınıflandırma (admission’da `classify` yeniden koşar, `source_blockers` ve çağıranın engelleri `with_blockers` ile birleşir; herhangi bir engel veya `binding_matches` farkı `continuation_remote_changed` verir, istek yoktur); `--prepare`da mevcut üretici içerik uygunluğunun (`upload_duplicate_content`) uygulanması; kaynak donma çağrısı; mevcut current producer’ın create/link’siz kullanımı (context, detail↔baseline, üyelik, my-role); alt küme koordinatörü (hepsi presign → en çok iki PUT → seri confirm, tek deneme, tek permit); confirm kodlayıcısına taban parametresi (plandaki `remote_present_count`) ve v3 oracle’ı (`created=1`, `batch_duplicates=0`, varsa `actual_count ∈ {remote_present_count + k + 1, k + 1}`; k = bu operation’da kabul edilmiş confirm sayısı; iki anlam da kabul edilir, kümenin dışı reddedilir); v3 için mevcut `reconcile` bağlaması (`load_read_input`/`verify_original` kök baseline çözümleyicisi ve 3M graf ile; 3M makbuzu tam ama proof’u eksik unknown kayıt aynı operation’da kapanır); `M=0` yalnız doğrulama yolu; N-dosya proof; hata/iptal/belirsizlik eşlemesi; [tüketici referansının](../../reference/platform-upload-consumer.md) `actual_count` tanımının düzeltilmesi girer. Public API/CLI, native ölçüm ve canlı kabul girmez.

## Bağımlılıklar ve kararlar

P02-3e sınıflandırıcısı ve P02-3r yazma kapıları verified olmalıdır. Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §5; yeni replay, politika veya TTL yoktur. v2 kodlayıcısının davranışı (taban 0) değişmez.

## Sözleşme ve uygulama sınırı

Mevcut presign/PUT/confirm codec’leri, bütçe sayaçları ve storage portu v2 yolunda değişmeden kalır; v3 yalnız confirm sayaç tabanını ekler. Taze envanter sınıf özeti kayıtlı plandan farklıysa admission öncesi `continuation_remote_changed`/2; PUT sırasında veya proof öncesinde uzak envanter beklenenden sapmışsa mevcut unknown kuralı (yeni etki yok). `created≠1`, kopya, fazladan item ve yanlış toplam başarı değildir.

**P02-3d devir notu.** Orijinal koordinatör `graph.files` ve `graph.put_batches()` (demetler) üzerinden döner; continuation koordinatörü aynı iki-worker toplu PUT kalıbını `file_indices` alt kümesi için kullanır. `_Environment._context` ve `validate_uploads` bugün planın bütün dosya kümesiyle korunur (`graph_of(plan).files`); `validate_uploads` içindeki `range(len(self.contexts))` N tabanlıdır ve alt küme için seçili indekslerden türetilmelidir. Bu korumalar P02-3d R2’de testle kilitlenmiştir (`test_environment_*`); alt küme davranışı onları bilinçli günceller.

**P02-3g devir notu.** Depodaki `request_digest` v3’te dataset kimliğini plan bağından alır; port tarafındaki `upload_request_digest` çağıranları (`platform_upload_port.py`deki istek sarmalayıcısı ve `platform_upload_put.py`) dataset kimliğini üreticiden alır. v3 koordinatörü bu değeri `plan.continuation.dataset_id` olarak vermelidir; aksi halde port özeti ile depo doğrulaması ayrışır ve geçmiş `state_invalid` olur. Bir test, v3 plan için port özetini depodakiyle bağımsız olarak eşitler.

## Kabul

1. Gerçek loopback TLS sunucusuyla: M>0 başarı (örn. 8 dosyadan 5’i); dolu veri setinde (N−M>0 mevcut item) **her confirm sayaç kontrolünden geçer** (sunucu fixture’ı hem kümülatif `taban+k+1` hem yalnız-işlem `k+1` anlamını ayrı koşularda yansıtır; ikisi dışındaki sayı → unknown); `M=0`; plan–start arası drift; PUT sırasında item ekleme/silme; confirm `created=0`; her aşamada 401/403/429/5xx ve kayıp cevap; her durumda sunucu sayacı create ve project_link isteği **sıfır**, effectful istek sayısı ≤ 3M.
2. Gerçek SIGKILL sınırları (admission, her aşama intent/receipt, iki-worker PUT, proof) v3’te de ikinci etkisiz ve aynı-ID kalır; devam yine bir sonraki continuation veya `reconcile` iledir.
3. Başarılı sonuç yalnız metadata seviyesi ve `remote_bytes_verified=false`; authority/pricing yükseltilmez.
4. Signed URL, ham anahtar, `created_dataset` ve literal credential canary’leri DB/log/exception/çıktıda yoktur; bütçe ve deadline kuralları v2 ile aynıdır.
5. v3 `reconcile`: 3M makbuz tam + proof eksik unknown kayıt → `reconcile` → `succeeded`; eksik graf → `operation_uncertain` (unknown); v2 original yolu ve v2 `reconcile` mevcut testlerle değişmeden geçer. Taze envanter sınıf özeti farklıysa `continuation_remote_changed`.

## Doğrulama

Gerçek TLS/süreç/SQLite integration testleri, bütçe sayaç testleri, Ruff ve strict mypy. Kurulu yolculuk ve native ölçüm P02-3i/P02-3a’dadır.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
