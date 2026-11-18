---
id: P02-4c
phase: P02
status: draft
size: M
depends_on: [P02-0a, P02-0c, P02-0d]
capabilities: [C05, C13]
---
# P02-4c — Katalog sözleşmesi: tipler, dar tüketici codec’leri ve çözüm kuralları

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 1; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) §2–§5, §8–§9.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı ve uygulama geliştiricisi, Platform modelleri/sürümleri/veri setleri ile LLM geçidi model listesinin hangi alanlarla okunduğunu, neyin kesin, neyin gözlemsel olduğunu ve hangi belirsizliğin açıkça gösterildiğini tek sözleşmeden öğrenir. Bugün katalog için tip, codec, tamlık kuralı, çözüm kuralı veya kanonik referans yoktur.

## Giren ve girmeyen kapsam

**Girer:**

- Tipler: katalog model, sürüm, veri seti; model referansı (Platform: `model_id`, `owner_username`, `slug`, `version_id`, `version_tag`; LLM: `model_id`); gözlem penceresi; tamlık durumu (`complete`, `partial`, `unknown`).
- Dar tüketici codec’leri (K9 önerisi; ADR-0035 §8):
  - LLM: `ModelListResponse` (`data` zorunlu), `ModelInfo` (zorunlu `created`, `id`, `task`; okunan diğer alanlar null olabilir), `ModelPricing` (yalnız gösterilen alanlar).
  - Platform: `Model` (liste ve detay; okunan alanlar: `id`, `owner_username`, `slug`, `name`, `modality`, `stage`, `visibility`, `versions_count`, `created_at`, `updated_at`, `architecture`); sürüm dizisi (`id`, `version_tag`, `framework`, `file_size_bytes`, `created_at`, biçim mevcudiyeti bayrakları); veri seti özeti (`id`, `name`, `slug`, `modality`, `item_count`, `visibility`, `updated_at`, `owner_username`).
  - Okunmayan alanlar yok sayılır ve hiçbir çıktıya girmez. Bu alanlar tek gözlemle tam bilinmediği için “tam şekil” iddiası kurulmaz.
  - Her ham yanıtın tüm ağacında seçili anahtar için literal-secret taraması çalışır (`scan_for_secret`).
- Tamlık: Platform modellerinde `(p-1)*s + n >= t` ise `complete`, değilse `partial`; veri setlerinde `X-Has-Next` başlığı yoksa veya ayrıştırılamazsa `unknown`, `false` ise `complete`, `true` ise `partial`; LLM tek yanıtı kapsam kanıtı yoksa `unknown`.
- Çözüm kuralları: `owner/slug` tam eşleşme; `owner_username` null ise `model_not_addressable`; `version_tag` için sıfır sonuç `model_not_visible`, çoklu sonuç `model_ambiguous` (en çok beş aday); LLM görev uyuşmazlığı `model_task_mismatch`.
- Adres biçimi: `owner`, `slug`, `model_id`, `version_id` `[A-Za-z0-9._-]{1,128}`; `.` ve `..` yasak; dışı karakter I/O öncesi `invalid_request`.
- Sanitizasyon: kontrol ve çift yönlü karakterler, uzunluk sınırı (ad ve slug 128, açıklama 512 gösterim karakteri; kesilen metinde işaret); depolama adresleri tipte taşınmaz.
- Kanonik referans `docs/reference/catalog.md` ve kullanıcı belgesinin ilgili bölümü.

**Girmez:** HTTP, sır okuma, `api.py`, CLI, state, önbellek, indirme, `datasets` yazma uçları ve canlı çağrı.

**Dosya önerisi** (uygulanmış sınıf iddiası değildir): `src/yorunge/domain/catalog.py` (tipler ve değişmezler), `src/yorunge/application/catalog.py` (dar codec ve kurallar).

**Kaynak bütçesi (kabul maddesi):** tek yanıt ≤1 MiB; LLM listesi ≤500 kayıt; Platform sayfası ≤100 kayıt; codec bellek kullanımı yanıt boyutuyla orantılı.

## Bağımlılıklar ve kararlar

P02-0a araştırması, P02-0c (LLM) ve P02-0d (Platform) verified ve development’ta. Karar kaynağı [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) (Proposed). **K1 ve K9 açık onay ister.** Dar tüketici deseni [ADR-0022](../../decisions/0022-observed-platform-consumer-contract.md)’nin Platform gözlem sözleşmesinden alınır; bu kart `decode_response` kuralını değiştirmez. Okunan alan kümesi K4 canlı okumasıyla teyit edilir; teyit edilmeyen alan kesin sözleşme sayılmaz.

## Sözleşme ve uygulama sınırı

- Model tipleri domain’de değişmezdir; HTTPX veya JSON kütüphanesi tipi domain’e girmez.
- Kanonik sınır `docs/reference/catalog.md`: her okunan alanın kaynağı, tipi, zorunluluğu, sınırı, tamlık kuralı ve çıktı biçimi.
- Sürüm listesinde depolama adresleri (`weights_url`, `onnx_url`, `tflite_url`) yalnız biçim mevcudiyeti bayrağına dönüşür; URL değeri tipte taşınmaz.
- Veri setleri K2 kararına göre `scope=owned` kapsamıyla anılır; kapsam teyidi olmadan “görünen” denmez.
- Yeni kararlı hata kodları ([ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Karar 9): `model_not_visible` (çıkış 1), `model_ambiguous`, `model_task_mismatch`, `model_not_addressable` (çıkış 2). Kod tanımı bu kartta referansa yazılır; CLI tablosuna P02-4e’de işlenir.

## Kabul

1. Her okunan alan için olumlu oracle ve tip/zorunluluk negatifi; LLM `pricing` null, `free_until` null ve dize durumları; Platform `items`/`total` ve sürüm dizisi biçimleri.
2. Zorunlu alan eksikliği, yanlış tip, duplicate key, NaN ve sınır aşımı `invalid_response`; okunmayan bilinmeyen alan yok sayılır ve çıktıda görünmez (negatif oracle: bilinmeyen alan sonucu değiştirmez, ama değeri çıktıya girmez).
3. Tamlık: Platform için `(p-1)*s + n >= t` formülü sınır değerlerinde (son sayfa, tam bölünme, boş sayfa) doğru; veri seti başlıkları eksik, değersiz veya tutarsızsa `unknown`; LLM tek yanıtı `unknown`.
4. Çözüm: sıfır sonuç `model_not_visible` (kesin yokluk iddiası yok); tek sonuç başarılı; çoklu sonuç `model_ambiguous` ve en çok beş aday; büyük/küçük harf farkı veya kısmi eşleşme sonuç vermez; `owner_username` null → `model_not_addressable`; `.`, `..`, `/`, `%`, `?`, `#`, boşluk ve kontrol içeren segment `invalid_request`.
5. LLM görev uyuşmazlığı `model_task_mismatch`; bilinmeyen görev dizesi listelemede reddedilmez, “bilinmeyen görev” olarak işaretlenir.
6. Sanitizasyon: kontrol karakterleri, çift yönlü geçersiz kılma karakterleri ve sınır üstü metin her çıktı yolunda aynı kuralla işlenir; URL benzeri ad düz metin olarak kalır ve takip edilmez.
7. Sentinel: depolama adresi, `download_url` ve önizleme/metrik bağlantısı hiçbir DTO alanında bulunmaz.
8. Kanonik referans (`docs/reference/catalog.md`, P02-4c ile yazılır) ve test oracle’ları aynı okunan alan kümesini ve aynı hata kodlarını gösterir.

## Doğrulama

[Doğrulama matrisine](../../../CONTRIBUTING.md#doğrulama-seçimi) göre runtime satırı: hedefli contract ve unit testleri, Ruff format/lint, strict mypy, `check-docs.py`, `check-agent-guides.py` ve `git diff --check`. Ağ, canlı çağrı ve native ölçüm bu kartta yoktur.

## Teslim kaydı

Hazırlık; uygulama ve kabul kaydı yoktur.
