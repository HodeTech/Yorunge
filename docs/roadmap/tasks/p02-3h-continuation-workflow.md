---
id: P02-3h
phase: P02
status: ready
size: M
depends_on: [P02-3r]
capabilities: [C03, C12]
---
# P02-3h — Continuation üreticisi: `resume` raporu ve `--prepare`

**Tarih:** 2026-11-07 (bölünme güncellemesi; ilk metin 2026-11-06). [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 6. Gerçek TLS/HTTP ile **salt okuma** üretici; public CLI/API P02-3i’dedir. Kartın ilk metni üreticiyi, etkili aşama yürütücüsünü, başlatma/proof’u ve reconcile bağlamasını tek kartta topluyordu; ölçülen kapsam dört ayrı risk alanı olduğundan büyüme kuralıyla bölündü: üretici bu kart, aşama yürütücüsü [P02-3w](p02-3w-continuation-stage-executor.md), başlatma [P02-3y](p02-3y-continuation-start.md), reconcile bağlaması [P02-3x](p02-3x-continuation-reconcile.md).

## Kullanıcı sonucu ve mevcut eksik

Depoda continuation kapıları vardır (P02-3r) ama kimse kaynağın günlüğünü ve uzak durumu okuyup dosyaları sınıflamıyor, kullanıcıya raporu göstermiyor ve devam planını yazmıyor. Bu kart, kesintiye uğramış bir yüklemenin “neyi doğruladım, neyi göndereceğim, neden olmaz” cevabını ve onaya gidecek devam planını üretir; hiçbir uzak yazma yapmaz.

## Giren ve girmeyen kapsam

Girer: (1) **Günlük engelleri** `StateUploads.chain_snapshot(kaynak, stamp)` ile alınır (kaynak journal’ları kökten kaynağa, `SourceFacts` ve torun olguları tek okuma anlık görüntüsünden); `source_blockers`, `descendant_verdict` ve `chain_blockers` biri bile varsa **hiçbir uzak okuma yapılmaz** (rapor `observation: null`, `--prepare` reddedilir). (2) Günlük engeli yoksa uzak okuma: mevcut okuyucunun create/link’siz kullanımı — bağlam (`me`, proje), dataset detayı ↔ kökün baseline’ı, proje üyeliği ve `my-role` (eylem `upload_created_dataset`; sonuç `denied`/`unavailable`/`invalid` ise v2 gibi `remote_access_denied`/okumanın kendi kodu/`invalid_response`) — ve sayfalı öğe envanteri (`read_inventory`: ≤128 sayfa, ≤1.024 öğe); `classify` sonucuna çağıranın engelleri (`membership_unobserved`, `local_changed`) `Classification.with_blockers` ile eklenir ve **aynı manifestle** `resume_report` kurulur (kota: `quota_used`, `continuation_added_payload_bytes`). (3) `--prepare`: engelsiz sonuçta lease’i dolmuş `running` kaynağı `freeze_source` ile dondurur (zaten `unknown` olana dokunulmaz; engeller önce değerlendirildiğinden dondurmanın `operation_conflict`ı yalnız bir yarışın sonucudur), yerel root/Manifest’i **tam** yeniden hash’ler (`capture_upload_input(expected_root)`; fark `input_changed`/`input_invalid`), mevcut içerik uygunluğunu (`require_distinct_upload_content`: `upload_duplicate_content`) uygular, planı P02-3f’nin saf işlevleriyle kurar (`continuation_limits`, engelsiz sınıflandırmadan `continuation_binding`, `prepare_continuation_v3`: ömür = çalışma penceresi ve kanıtların en erken bitişi, digest, seçilen bayt doğrulaması; çalışma penceresi ve `ContinuationCostWork` bileşimi v2 `_work`/`_limits` gibi üretici adaptöründedir) ve `save` ile yazar; v3 plan canonical boyutu 16 KiB’a çok yakınsa `invalid_request`. (4) Hata eşlemesi: `source_active` → `operation_conflict` (torunun kimliği ve `resume --operation-id <torun>` önerisi), diğer her engel → `continuation_not_possible` (kapalı sıralı `blockers`), `pending_uncertain>0` iken onay bayrağı yoksa plan yazmadan `approval_required`, bayrak gereksizse `invalid_request`, Manifest başvurusu planlananla uyuşmuyorsa `input_changed`, dolu store `upload_capacity_exceeded` (raporda hata değil). (5) Salt okuma uzak bütçesi (`UploadBudget` read-only: ≤512 istek, ≤1.024 deneme, 4/16 MiB gövde) ve 30 sn tazelik/süre kuralları v2 ile aynıdır. (6) `ObservedUploadReader`ın baseline’a bağlı salt okuma gözlemi için gereken genişletme (plan olmadan `upload_created_dataset`/`read_created_dataset` gözlemi). Girmez: uzak yazma ve başlatma ([P02-3y](p02-3y-continuation-start.md)), aşama yürütücüsü ([P02-3w](p02-3w-continuation-stage-executor.md)), `reconcile` bağlaması ([P02-3x](p02-3x-continuation-reconcile.md)), public API/CLI (P02-3i), native ölçüm ve canlı kabul.

## Bağımlılıklar ve kararlar

P02-3e sınıflandırıcısı, P02-3t DTO’ları ve P02-3r yazma kapıları `verified`dır. Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §2/§3/§5 ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md); yeni replay, politika, TTL veya DDL yoktur. Açık karar yoktur.

## Sözleşme ve uygulama sınırı

Üretici adaptörü v2 `UploadPreparationRuntime`ın aynı tohumlarını (oturum, saat, `_bind`, `_scope`, `_invocation`) kullanır; v1/v2 `prepare` ve rapor-olmayan yollar değişmez. Rapor ve `--prepare` aynı saf işlevleri aynı sırayla kullanır ([sözleşme: tek uygunluk ve eylem hesabı](../../reference/dataset-upload-continuation.md#rapor-ve-hata-ayrımı)). Yerel durum yalnız `--prepare`de ve yalnız `freeze_source` ile `save` ile değişir; rapor hiçbir şey yazmaz (lease’i dolmuş `running` kaynak `running` kalır).

**P02-3r devir notu (üretici sırası).** Önce `chain_snapshot` ile günlük engellerini değerlendir; engel varsa `--prepare` `continuation_not_possible`/`operation_conflict` ile biter ve dondurma çağrılmaz; yalnız kaynak `running` ve lease’i dolmuşsa `freeze_source(kaynak)` (lease’i dolmuş `running` kaynağı dondurur, zaten `unknown` olana dokunmaz, bayat `admitted` torunları iptal eder; kimlik bilgisi aramaz; terminal, latch’siz ve canlı lease’li `running` kaynakta `operation_conflict` verir — engeller önce değerlendirildiğinden bu yalnız bir yarışta ya da hatalı çağrıda görülür) → rapor/sınıflandırma → plan → `save(plan, manifest)`. Taze `UploadCurrentCheck`in eylemi planın ilk işidir (`adapters.upload_repository.continuation_action(plan)`); `quota_used` ve `continuation_added_payload_bytes` rapor kotasını doldurur (P02-3v).

**P02-3u devir notu.** Resume raporu ve `--prepare` kaynak journal’larını, `SourceFacts`i ve torun olgularını tek çağrıda `StateUploads.chain_snapshot(operation_id, stamp)` ile alır (`stamp` raporun kendi saat noktasıdır); ardından `merge_chain`, `descendant_verdict`, `source_blockers` ve `chain_blockers` saf işlevleri çağrılır. Journal listesi kökten kaynağa sıralıdır; hiçbir şey göndermeyen operation `graph_complete` sayılmaz.

**P02-3r R2 devri.** Yerel `reconcile`ın yazıcısı (`upload_reconcile_local.load_read_input`) ve `acquire_read` bir devam edilmiş kaynakta da çalışır; kararı [P02-3x](p02-3x-continuation-reconcile.md)’te verilir. Rapor bu yüzden kaynağın etkin okuma lease’ini `source_active` olarak gösterir.

## Kabul

1. Gerçek loopback TLS sunucusuyla rapor (exit 0, hiçbir yerel yazı yok): `confirmed`, `observed`, `pending_clean`, `pending_uncertain` (ve `unconfirmed_ack_required`), `drift_missing`, `conflict`, `extra_remote` (ad/sayı yok), `inventory_unreliable` (null `sha256_hash`, `total` kayması, tekrarlı cursor/kimlik) ve `inventory_too_large` (1.024 aşımı: iki engel) her birinin sınıf sayaçları, `send_files`/`send_bytes`, engelleri ve önerilen eylemi; `membership_unobserved` (üyelik ya da detail↔baseline uyuşmuyor), `local_changed` (yerel klasör/Manifest uyuşmuyor); rapor ile `--prepare` aynı gözlemden aynı sonucu verir.
2. Günlük engeli olan her kaynakta (`source_active`, `source_ineligible`, `source_superseded`, `source_terminal`, `reconcile_available`, `create_unknown`, `known_negative`) sunucuya **hiç istek gitmez** ve `observation` null’dır; lease’i dolmuş `running` kaynak raporda `running` kalır, `--prepare` onu `freeze_source` ile `unknown/request_uncertain` yapar (zaten `unknown` olana dokunmaz; iki eşzamanlı `--prepare` fence’i bir kez artırır).
3. `--prepare`: engelsiz M>0 sonuç, `M=0` ve `pending_uncertain>0` (ack ile) planları kaydedilir ve sözleşmenin plan alanlarını taşır (bağ: `file_indices`, `uncertain_indices`, `remote_present_count`, iki özet, `observed_at`; `request_limits` M ve seçilen bayt toplamı; ömür = pencere ve kanıtların en erken bitişi); aynı gözlemin planı raporla birebir uyumludur; `source_active` → `operation_conflict` (torun kimliği ve sonraki komut), diğer engeller → `continuation_not_possible` (kapalı sıralı `blockers`), `pending_uncertain>0` bayraksız → `approval_required` ve **plan yazılmaz**, gereksiz bayrak → `invalid_request`, 16 KiB tel sınırı → `invalid_request`, yerel kök/Manifest değişmiş → `input_changed`/`input_invalid`, dolu store → `upload_capacity_exceeded`.
4. Sunucu sayaçları: rapor ve `--prepare` boyunca **hiçbir etkili (yazma) istek yoktur**; okuma istekleri ≤512, deneme ≤1.024, sayfa ≤128, öğe ≤1.024; her istek tek deneme; 401/403/429/5xx ve kayıp cevap yerel durumu bozmaz (plan yazılmaz; hata kodları v2 okuma yoluyla aynı).
5. Sentinel: provider owner/org/name, receipt, baseline, signed URL, literal credential ve tam yol listesi DB/log/istisna/çıktıda yoktur; `examples` sınıf başına ≤8 sıralı göreli yoldur; `extra_remote` için ad ya da sayı verilmez.
6. v1/v2 `prepare`, `approve`, `start` ve rapor-olmayan yollar mevcut testlerle değişmeden geçer; `tests/contracts` ve sürüm dağıtım listesi yeşildir.

## Doğrulama

Gerçek TLS/SQLite integration testleri (`tests/fixtures/upload_provider.py` ve `http_server.TlsServer` genişletilerek: dolu veri seti, envanter bozulmaları, sayaçlar), bütçe sayaç testleri, `tests/contracts` (sürüm dağıtım listesi dahil), Ruff ve strict mypy. Kurulu yolculuk ve native ölçüm P02-3i/P02-3a’dadır.

## Teslim kaydı

Ready; uygulama, commit veya review kanıtı yoktur.
