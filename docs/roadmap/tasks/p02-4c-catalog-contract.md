---
id: P02-4c
phase: P02
status: verified
size: M
depends_on: [P02-0a, P02-0c, P02-0d]
capabilities: [C05, C13]
---
# P02-4c — Katalog sözleşmesi: tipler, dar tüketici codec’leri ve çözüm kuralları

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 1; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted (Karar 1–5, 7–9).

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı ve uygulama geliştiricisi, Platform modelleri/sürümleri/veri setleri ile LLM geçidi model listesinin hangi alanlarla okunduğunu, neyin kesin, neyin gözlemsel olduğunu ve hangi belirsizliğin açıkça gösterildiğini tek sözleşmeden öğrenir. Bugün katalog için tip, codec, tamlık kuralı, çözüm kuralı veya kanonik referans yoktur.

## Giren ve girmeyen kapsam

**Girer:**

- Tipler: katalog model, sürüm, veri seti; model referansı (Platform: `model_id`, `owner_username`, `slug`, `version_id`, `version_tag`; LLM: `model_id`); gözlem penceresi; tamlık durumu (`complete`, `partial`, `last_page`, `unknown`).
- Dar tüketici codec’leri (ADR-0035 Karar 8):
  - LLM `ModelListResponse`: `data` zorunlu dizi. `ModelInfo`: zorunlu `id`, `task`, `created`; okunan `modalities` (dizi), `context_length`, `default_max_output_tokens`, `precision`, `pricing` (null olabilir; `prompt_token_price`, `completion_token_price`, `currency`, `free_until` okunur). `capabilities` okunmaz.
  - Platform `Model` (liste ve detay): `id`, `owner_username` (null olabilir), `slug`, `name`, `description` (null olabilir), `license` (null olabilir), `modality`, `stage`, `visibility`, `versions_count`, `architecture`, `created_at`, `updated_at`.
  - Platform sürüm öğesi: `id`, `version_tag`, `framework`, `file_size_bytes`, `created_at`; `weights_url`, `onnx_url`, `tflite_url` yalnız “null değil” bayrağı olarak okunur, değeri tipte taşınmaz.
  - Platform veri seti öğesi: `id`, `name`, `slug`, `modality`, `item_count`, `visibility`, `updated_at`, `owner_username` (null olabilir).
  - Okunmayan alanlar yok sayılır ve hiçbir çıktıya girmez. Tek gözlemle tam şekil iddiası kurulmaz.
  - Ham yanıtın tüm ağacında seçili anahtar için literal-secret taraması yapılır (`scan_for_secret`); tüketilen dizeler `check_response_secrets` ile ayrıca denetlenir.
- Platform sayfa kuralı (Karar 2): `t` negatif olmayan tam sayı; `n = max(0, min(s, t - (p-1)*s))`; `n` eşleşmezse `invalid_response`; `has_next = p*s < t`.
- Tamlık etiketleri (Karar 3): Platform modelleri `complete` (`p=1`, `has_next` yok), `partial` (`has_next` var), `last_page` (`p>1`, `has_next` yok). Veri setleri: `X-Has-Next` tam bir kez ve `0` veya `1` olmalıdır (K4 canlı biçimi); değilse `unknown`; `X-Total-Count` varsa aynı satır kuralı. Sürüm listesi: `versions_count` eşitse `complete`, değilse `unknown`. LLM: `unknown`.
- Gözlem penceresi: ilk ağ isteğinin başlangıcı ile son yanıtın tamamlanması.
- Çözüm kuralları (Karar 5): `owner/slug` tam eşleşme; `owner_username` null ise `model_not_addressable`; detay `versions_count` ile dizi uyuşmazsa `invalid_response`; `version_tag` için sıfır sonuç `model_not_visible` (metin: “bu anahtara görünmüyor (kesin yokluk değil)”), çoklu sonuç `model_ambiguous` (en çok beş aday); LLM görev uyuşmazlığı `model_task_mismatch`.
- Adres alfabesi: `owner`, `slug`, `model_id`, `version_id` için `[A-Za-z0-9._-]{1,128}`; `.` ve `..` yasak. Alfabe dışı API değerleri listede temizlenmiş metin olarak gösterilir; `show`/`download` için argüman olarak kabul edilmez. `version_tag`: 1–128 karakter, kontrol karakteri yok, URL’ye girmez.
- Sanitizasyon: kontrol ve çift yönlü karakterler temizlenir; ad ve slug 128, açıklama 512 gösterim karakteri (kesilen metinde işaret); depolama adresleri tipte taşınmaz.
- Kanonik referans `docs/reference/catalog.md` ve kullanıcı belgesinin ilgili bölümü.

**Girmez:** HTTP, sır okuma, `api.py`, CLI, state, önbellek, indirme, `datasets` yazma uçları ve canlı çağrı.

**Dosya önerisi** (uygulanmış sınıf iddiası değildir): `src/yorunge/domain/catalog.py` (tipler ve değişmezler), `src/yorunge/application/catalog.py` (dar codec ve kurallar).

**Kaynak bütçesi (kabul maddesi):** tek yanıt ≤1 MiB; LLM listesi ≤500 kayıt; Platform sayfası ≤100 kayıt; codec bellek kullanımı yanıt boyutuyla orantılı.

## Bağımlılıklar ve kararlar

P02-0a, P02-0c (LLM) ve P02-0d (Platform) verified ve development’ta. Karar kaynağı ADR-0035 (Accepted, 2026-11-19). Dar tüketici deseni ADR-0022’nin Platform gözlem sözleşmesinden alınır; bu kart `decode_response` kuralını değiştirmez. Okunan alan kümesi ve tamlık başlıkları K4 canlı okumasıyla teyit edilir; teyit edilmeyen alan kesin sözleşme sayılmaz.

## Sözleşme ve uygulama sınırı

- Model tipleri domain’de değişmezdir; HTTPX veya JSON kütüphanesi tipi domain’e girmez.
- Kanonik sınır `docs/reference/catalog.md`: her okunan alanın kaynağı, tipi, zorunluluğu, sınırı, tamlık kuralı ve çıktı biçimi.
- Veri setleri `scope` etiketi K4 teyidine kadar `unknown` taşır (K2).
- Yeni kararlı hata kodları (ADR-0035 Karar 9): `model_not_visible` (çıkış 1), `model_ambiguous`, `model_task_mismatch`, `model_not_addressable` (çıkış 2). Kod tanımı bu kartta referansa yazılır; CLI tablosuna P02-4e’de işlenir.

## Kabul

1. Her okunan alan için olumlu oracle ve tip/zorunluluk negatifi; LLM `pricing` null ve `free_until` null/dize durumları; Platform `items`/`total` ve sürüm dizisi biçimleri.
2. Zorunlu alan eksikliği, yanlış tip, duplicate key, NaN ve sınır aşımı `invalid_response`. Okunmayan bilinmeyen alan yok sayılır ve hiçbir çıktıda görünmez; alanın değeri çıktıya sızmaz (negatif oracle).
3. Platform sayfa kuralı: `n` = beklenen satır sayısı olduğunda kabul; sunucunun sayfa boyutunu düşürdüğü (`n` < beklenen) veya `t` negatif/tam sayı değilse `invalid_response`; son sayfa, tam bölünme, `t=0` ve boş sayfa sınır durumları doğru.
4. Tamlık etiketleri: `complete`, `partial`, `last_page` doğru atanır; `p>1` ve `has_next` yok `complete` olmaz. Veri seti başlıkları eksik, değersiz veya yanlış biçimdeyse `unknown`; sürüm dizisi `versions_count` ile uyuşmazsa `unknown` (çözümde `invalid_response`).
5. Çözüm: sıfır sonuç `model_not_visible` (kesin yokluk iddiası yok, metin doğru); tek sonuç başarılı; çoklu sonuç `model_ambiguous` ve en çok beş aday; büyük/küçük harf farkı veya kısmi eşleşme sonuç vermez; `owner_username` null → `model_not_addressable`; `.`, `..`, `/`, `%`, `?`, `#`, boşluk ve kontrol içeren argüman `invalid_request` (ağ isteği yok).
6. LLM görev uyuşmazlığı `model_task_mismatch`; bilinmeyen görev dizesi listelemede reddedilmez, “bilinmeyen görev” olarak işaretlenir.
7. Sanitizasyon: kontrol karakterleri, çift yönlü geçersiz kılma karakterleri ve sınır üstü metin her çıktı yolunda aynı kuralla işlenir; URL benzeri ad düz metin olarak kalır ve takip edilmez.
8. Sentinel: depolama adresi, `download_url`, önizleme ve metrik bağlantısı hiçbir DTO alanında bulunmaz.
9. Alfabe dışı API değeri listede gösterilir ama `show`/`download` argümanı olarak kabul edilmez (negatif oracle).
10. Kanonik referans (`docs/reference/catalog.md`, P02-4c ile yazılır) ve test oracle’ları aynı okunan alan kümesini, tamlık etiketlerini ve hata kodlarını gösterir.

## Doğrulama

[Doğrulama matrisine](../../../CONTRIBUTING.md#doğrulama-seçimi) göre runtime satırı: hedefli contract ve unit testleri, Ruff format/lint, strict mypy, `check-docs.py`, `check-agent-guides.py` ve `git diff --check`. Ağ, canlı çağrı ve native ölçüm bu kartta yoktur.

## Teslim kaydı

- PR/commit: [PR #18](https://github.com/HodeTech/Yorunge/pull/18) (`feat/p02-4-catalog-and-selection`, `development` hedefi).
- Sonuç: katalog tipleri, kapalı codec'ler, sayfa/tamlık/çözüm/görev kuralları ve kanonik referans ([katalog başvurusu](../../reference/catalog.md)) uygulandı; sözleşme testleri geçti; K4 ile düzeltilen veri seti başlık biçimi (`X-Has-Next` `0`/`1`) kanıtlı.
- Kalan sınır: 100 üstü platform sayfası ve `model_id` ile sürüm listesi canlı teyit edilmedi (hesapta model yok).
