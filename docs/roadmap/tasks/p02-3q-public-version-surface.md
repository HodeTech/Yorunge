---
id: P02-3q
phase: P02
status: verified
size: M
depends_on: [P02-3p, P02-3s]
capabilities: [C04, C13]
---
# P02-3q — Public `datasets versions` yüzeyi ve bağ artifact’ı

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 16. [ADR-0033](../../decisions/0033-dataset-version-references.md); ortak CLI/Python, P02-3s’in ortak no-clobber artifact yayıncısı.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir dataset’in sürümlerini görmek, bir sürüme değişmez referans üretmek ve sonra o referansın hâlâ geçerli olduğunu denetlemek ister.

## Giren ve girmeyen kapsam

`datasets versions list|show|bind|check` için ortak API/CLI; bağ artifact’ının P02-3s ortak artifact yayıncısıyla no-clobber yayını (`--binding-out`); `--manifest` ile sayı eşliği; text/JSON/NDJSON, yardım, hata/exit eşlemesi; referans, CLI sözleşmesi, user-journeys, yetenek matrisi ve modül belgeleri girer. Sürüm oluşturma (P02-R4), eğitim planı bağı (P03-1) ve içerik üyeliği iddiası girmez.

## Bağımlılıklar ve kararlar

P02-3p ve P02-3s (ortak artifact yayıncısı) verified olmalıdır. CLI/API için yorunge-contract-change disiplini uygulanır. [ADR-0033](../../decisions/0033-dataset-version-references.md) §1 sınırı: salt okuma.

## Sözleşme ve uygulama sınırı

[sürüm referansı sözleşmesi](../../reference/dataset-versions.md) içindeki yüzey. Yayın P02-3s’in ortak artifact yayıncısını kullanır (kopya yok); `binding_*` hata kodları ayrıdır. Python karşılıkları senkron köprü kapılarını mevcut ailelerle aynı uygular. Genel `--output` yalnız biçimdir; hedef dosya `--binding-out`tur. Çıktı sır, ham gövde, `created_by`, `description` ve URL taşımaz.

## Kabul

1. `list` istenen sayfayı, `has_next` ve toplamı doğru gösterir; `show` detail+splits çapraz doğrulamasını; `bind` aynı sürüm ve aynı `--manifest` seçiminde aynı digest’i üretir (artifact yalnız `observed_at` ile ayrışır; 0600, mevcut hedefi ezmeden yazılır); `check` unchanged=0 (`DatasetVersionCheck v1`), changed/missing=7, hedef uyuşmazlığı `state_changed`/2 (ilk istekten önce: başka sağlayıcının bağı için hiç istek yapılmaz), unavailable=mevcut kodlar; JSON/NDJSON’da `unchanged` dışındaki her sonuç hata zarfıdır (kod ve kapalı ayrıntı; sonuç zarfının `status` alanı hata taşımaz). **NDJSON notu:** `streams.error_payload` kapalı ayrıntıyı (`changed_fields`, `annotation_only`) taşımaz, yalnız stderr zarfı taşır; bu yüzden `check` hüküm gelmeden NDJSON olayı yayımlamamalıdır. **Canlı yoklama (P02-3c) ilk maddesi:** sağlayıcı zamanları bölge taşıyor mu (bölgesiz zaman bütün yanıtları `invalid_response` yapar).
2. Kısmi yayın sonrası belirsizlik `binding_write_uncertain`/5, kesin EEXIST `binding_output_exists`/2; parent/symlink yarışları ve hedef var senaryoları (P02-3s kapılarıyla).
3. JSON/NDJSON saf, TTY dışında prompt yok; kapalı stdout `output_closed`/6, SIGINT `request_cancelled`/6 (ölçüldü: her sınırda 6; yayının içinde `binding_write_uncertain`/5), `asyncio.to_thread` iptali iş parçacığını durdurmaz (belgelendi); link sonrası hata dosyayı geri almaz ve yeniden `bind` `binding_output_exists` verir; sentinel testleri `list` ve `bind` için vardır (`check`in sentinel’i hüküm gelmeden NDJSON olayı olmadığıyla sabittir).
4. Kurulu CLI yolculuğu loopback üzerinde; belgeler çalışan komutlarla uyumlu.

## Doğrulama

CLI/API integration testleri, kurulu paket yolculuğu, belge/rehber kontrolleri, Ruff, strict mypy ve yorunge-contract-change denetim listesi.

**Gerçekleşen kapsam (P02-3q).** `api.list_dataset_versions`/`show_dataset_version`/`bind_dataset_version`/`check_dataset_version` (adaptör bileşimi `adapters/dataset_version_api.py`; kullanım senaryoları `application/dataset_versions.py`, paylaşılan `exchange` üstünde; okuyucu `adapters/dataset_version_exchange.py`), `cli/versions.py` (`datasets versions list|show|bind|check`; `datasets` altında tembel yüklenir), `adapters/binding_files.py` (açık-önce, yayın-sonra bağ hedefi: ortak artifact yayıncısı + `binding_*` ailesi; `adapters/target_directory.py` indirmeyle paylaşılan dizin tutucusudur), `adapters/small_files.py` (symlink’siz, sınırlı, değişmemiş küçük dosya okuyucusu: `--manifest` ve `check`in bağı), `DatasetVersionBound` sonuç modeli. Anlatım [referansın “Yüzey ayrıntıları (P02-3q)” bölümündedir](../../reference/dataset-versions.md#yüzey-ayrıntıları-p02-3q). Testler: `tests/integration/test_dataset_version_surface.py` (56 öğe; gerçek CLI süreçleri + gerçek loopback TLS sağlayıcı; test-only `tests/fixtures/version_network.py`/`version_console.py`), `test_dataset_version_surface_gaps.py` (68), `tests/integration/test_binding_files.py` (42 öğe), `test_dataset_version_r2.py` (kökte `--project`, iki `bind`in aynı digest’i, liste satırı bayrakları, tutulan dizinin kapanışı ve her yayın sınırında gerçek SIGINT; test-only `tests/fixtures/version_signal_console.py`) ve `tests/integration/test_dataset_version_r2b.py` (R2-B: link() retleri tek tek, ortak argüman yardımcılarının ve küçük dosya okuyucusunun koruları, eylemden önceki seçenekler, metin satırları, hedef dizin tanıtıcısının gerçek kapanışı) ve `tests/contracts/test_version_surface_reference.py` (referanstaki sayı ve errno listeleri), kabul 1–3 maddeleri. R2 sonrası kod: stage’in yaratılması sırasında SIGINT bekletilir (yaratılan stage’i bırakmaz), `link()` için `ENOSYS` da kesin ret sayılır, FAT/exFAT’ta başarısız yazım stage’i bırakmaz, `--project` kökte de reddedilir. Hedef yol sonucun taşıyabileceği bir yol olmalıdır (kontrol karakteri, UTF-8 olmayan ad, 4096 bayt üstü yol reddedilir): sonuç link’ten sonra kurulursa reddedilen bir yol dosya bırakıp komutu hataya düşürürdü; bu yüzden hedef açılırken (indirme için de, aynı `open_target_directory`) yargılanır ve `bind` özeti link’ten önce kurar. Kurulu paket yolculuğu (kabul 4) ve belge uyumu: referans, CLI sözleşmesi ve kart; kurulu-paket CI satırı son M5 turuna bırakıldı.

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: uygulama [87ca862](https://github.com/HodeTech/Yorunge/commit/87ca86231d07bd49935c073e171e9f26d9699b38); R1 düzeltmeleri [971f8a3](https://github.com/HodeTech/Yorunge/commit/971f8a3a118985eba18b23cb7623dfe18a982623), [fa52334](https://github.com/HodeTech/Yorunge/commit/fa5233468ee93ca2048b5d4421080fc73f74a2af); R2 düzeltmeleri [386bae8](https://github.com/HodeTech/Yorunge/commit/386bae8de52b1c1ccef81f0097394d8d20b10d3a).
- Sonuç: `datasets versions list|show|bind|check` ve `api.*_dataset_version`: tek credential snapshot’ı ile salt okuma; bağ artifact’ının no-clobber yayını (`bind`), hedef dizinin sağlayıcıya sorulmadan önce açılıp link’e kadar tutulması; `unchanged` dışındaki her `check` sonucu hata zarfı; her başarılı sonuç `provider_metadata_only` uyarısı taşır (R1 ve R2 kapandı; Adım 18). Tam paket: 12.716 geçti, 1 atlandı, 0 düştü (`9ab9d6a`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Canlı salt okuma kabulü yapılmadı (P02-3c; canlı yoklama listesi kartta); kurulu paket yolculuğu `versions_smoke` ile P02-3z’de yerelde geçti; FAT/exFAT’ta `0600` tutulmaz ve `link()` `ENOTSUP` verir (`bind` sağlayıcı okumalarından sonra `binding_write_failed` ile biter; belgelendi); Linux hücreleri PR CI’ında sınanır.
