---
id: P02-3v
phase: P02
status: ready
size: M
depends_on: [P02-3u]
capabilities: [C03, C12]
---
# P02-3v — Continuation v3 kapasite, bakım, reset önizlemesi ve projeksiyonlar

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 4 (devam). [P02-3g](p02-3g-continuation-persistence-read.md)’den ayrıştırılan üçüncü okuma dilimi: v3 geçmişi var iken store genelindeki hesapların (kapasite, bakım, reset önizlemesi) ve kullanıcıya dönük okuma projeksiyonlarının doğru çalışması.

## Kullanıcı sonucu ve mevcut eksik

Kapasite hesabı, reset önizlemesi ve bakım bütün plan satırlarını çözer: v3 satırı varken bu yollar iki tipli decode’la `state_invalid` verir ya da v3’ü yanlış sayar. `summary`/`review` projeksiyonu `isinstance(plan, DatasetUploadPlanV2)` ile bir v3 planı “legacy history” sayar (`legacy_history_only=True`, limitler ve maliyet kaybolur). Kullanıcı resume raporunun kota alanlarını dolduracak okuma da yoktur.

## Giren ve girmeyen kapsam

Girer: `capacity()` ve `require_capacity`ın v3 plan satırlarını doğru saymasıyla (128 plan, 128 operation, 4.096 dosya — her plan N’yi yeniden sayar —, 16 MiB payload; `operation_reservation` plan türüne göre, mevcut satırların rezerv doğrulaması değişmez); `upload_maintenance.invalidate_uploads`ın v3 kayıt ve kontrol tiplerini üç tipli decode’la yazması (latch’li → `unknown`, latch’siz → `cancelled`, `identity_reset`); `upload_snapshot`/`transfer_fingerprint` ve global expiry hesabının v3’ü tanıması; `validate_uploads` tam doğrulamasının v3 satırlarını kapsaması; `upload_projection.summary`nin v3 için `DatasetUploadSummaryV3` üretmesi (`continuation_of`, M, N−M, belirsiz dosya sayısı; `legacy_history_only=False`, `dataset_id` plandan) ve `review` projeksiyonu için gereken v3 verisinin (M, seçilen bayt toplamı, istek limitleri) okuma tarafı; resume raporunun `quota_used` değerini `capacity()` sayaçlarından veren okuma ve `quota_added.payload_bytes` üst sınırını hesaplayan saf işlev (v3 `operation_reservation` ve plan payload’ı tavanıyla; M bilinmiyorsa M=N); eski-binary etkisinin belgelenmesi (aynı state dizinini paylaşan eski binary’nin upload komutlarını ve reset önizlemesini yitirmesi; ADR-0031 §6). Girmez: kullanıcı kapsayıcı tipleri (`UploadIntentReview` v3, sayfa tipi) ve CLI/API (P02-3i), yazma kapıları (P02-3r), HTTP, DDL.

## Bağımlılıklar ve kararlar

P02-3u (v3 graf doğrulaması) verified olmalıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir. DDL gerekirse koddan önce kullanıcı kararı alınır. Restore/recover yasağı değişmez; upload tabloları geri yüklenebilir küme dışındadır.

## Sözleşme ve uygulama sınırı

v1/v2 yolları ve golden’lar değişmez; v1/v2 rezervasyon doğrulaması aynı kalır. Doğrulama doğrudan SQLite satırlarına yazılmış sentetik v3 geçmişleriyle yapılır.

**P02-3g devir notu.** Bu dilim şu kapalı başarısızlıkları gerçek davranışla değiştirir: `capacity()` yalnız iki tipli plan decode eder (saklı devam `state_invalid`; nedeni kodda yorumdur) ve devamı kota sayımına katar; `upload_maintenance.invalidate_uploads` bir v3 kaydını, v3 recovery/terminal kontrolü yazılana dek, değişiklik yapmadan `state_invalid` ile reddeder (kontrol iki tipli decode edilir ve payload’a kaydın `schema_version`ını kopyalar); `upload_projection.summary` v3 planı reddeder, `source_plan_schema`, `_cost` ve `_risks` v1/v2’ye göre yazılmıştır. Hepsi sahibi P02-3v olan noktalar olarak `tests/fixtures/version-dispatch-sites.json`dadır.

**P02-3u devir notu.** `read_any_view` artık her v3 planı için soyunu da çözer (plan başına kaynak yürüyüşü; en çok 128 plan × soy uzunluğu) ve `upload_snapshot` bunu zaten kullanır; `capacity()` kalktığında `validate_uploads` aynı okumayı yapar. Bir kaynağın birden çok canlı torunu saklı geçmiş olarak bugün yalnız rapor zamanında yakalanır: tam doğrulama bunu da denetlemelidir. Tam geçişler (`validate_uploads`, `upload_snapshot`, `list`) kaynak görünümlerini paylaşılan `views` önbelleğiyle bir kez okur; önbelleksiz okuma 128 operation’lık derin bir soyda O(n²)dir (127 zincir üyesiyle tüm planları okumak ~8 sn sürer, `open_store` bütçesi 5 sn) ve yeni yolların hepsi önbelleği geçirmelidir.

## Kabul

1. v3 satırı varken `require_capacity`, list/show okuması ve reset önizlemesi çalışır; kapasite continuation plan/operation 128/128, dosya 4.096 ve 16 MiB sınırlarına yeniden sayılır (bağımsız oracle ile); sınırı aşan v3 geçmişi `upload_capacity_exceeded`/bozuk durumda `state_invalid` verir.
2. Reset (`invalidate_uploads`) latch’li v3 kaydı `unknown/identity_reset`, latch’siz olanı `cancelled/identity_reset` yapar ve v3 kontrol kaydını yazar; önizleme parmak izi v3 satırının her alanındaki değişimde değişir, lease yenilemesinde değişmez.
3. `summary` v3 plan/operasyon için `legacy_history_only=false` ve doğru M/N−M/belirsiz sayılarıyla `DatasetUploadSummaryV3` üretir; `show`/`list` v3’ü kaybetmez.
4. Eski-binary benzeri 2 tipli decode v3 satırını mutasyonsuz `state_invalid` reddeder; restore/recover yasağı değişmez.
5. `quota_used` `capacity()`yle eşit sayaçlardan gelir; `quota_added.payload_bytes` üst sınırı v3 rezervasyon formülünden türetilir ve en az 16 KiB’dır.
6. v1/v2 geçmişi, golden’lar ve mevcut regresyon ağı (kota/maintenance/migration dahil) değiştirilmeden geçer.
7. Full doğrulama (`validate_uploads`) kök + zincirli v3 geçmişlerini geçirir (`tests/fixtures/continuation_history.py` kurucusuyla); bir kaynağın canlı (`cancelled` olmayan) en çok bir torun operation’ı vardır, fazlası `state_invalid`dir (`descendant_verdict` bunu yalnız rapor zamanında kontrol eder).

## Doğrulama

Gerçek SQLite integration/contract testleri, mevcut kota/maintenance/migration regresyonları, Ruff ve strict mypy. Ağ ve yazma kapısı iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
