# Katalog sözleşmesi (P02-4c)

**Durum:** Uygulandı (P02-4c): domain ve dar codec, çevrimdışı contract testleriyle. Ağ okuma (P02-4d), CLI yüzeyi (P02-4e) ve seçim bağı (P02-4f) ayrı adımlardır. **Karar kaynağı:** [ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) (Accepted, 2026-11-19). **Kod:** [domain/catalog.py](../../src/yorunge/domain/catalog.py), [application/catalog.py](../../src/yorunge/application/catalog.py); testler `tests/contracts/test_catalog_contract.py`.

## Kapsam

Katalog yalnız salt okumadır. Platform modelleri, sürümleri ve veri setleri; LLM geçidinin model listesi okunur. Önbellek, yazma, indirme ve çıkarım bu sözleşmenin dışındadır. Bu belge sayfa, tamlık, adres, çözüm ve okunan alanları tanımlar; ağ ve CLI davranışı ilgili adım kartlarındadır.

## Okunan alanlar (dar tüketici)

Sağlayıcı yanıtının okunmayan alanları yok sayılır ve hiçbir çıktıya girmez. Her ham yanıtın tüm ağacında (anahtar ve değerler, okunan veya okunmayan) seçili anahtar için gizli tarama yapılır. Görüntü temizliği tarama sonrasında çalıştığı için bitmiş kayıt bir kez daha taranır: temizlik sırasında birleşen bir anahtar da `invalid_response` olur. Kayıtlar çözücü tarafından kendi bayt girdisini alır; taramayı atlayan bir çağıran yoktur.

| Kaynak | Okunan alanlar | Zorunlu | Not |
|---|---|---|---|
| LLM `GET /v1/models` | `data` (dizi, en çok 500) | evet | sayfalama yok; tamlık `unknown` |
| LLM `ModelInfo` | `id`, `task`, `created` zorunlu; `modalities`, `context_length`, `default_max_output_tokens`, `precision`, `pricing` | `id`, `task`, `created` | `task` açık dize; kimlik ve görev ham tutulur |
| LLM `pricing` | `prompt_token_price`, `completion_token_price` (zorunlu, 0 veya üstü); `currency`, `free_until` | zorunlu iki fiyat | `free_until` yalnız bilgidir, maliyet kapısı değildir |
| Platform `GET /models` | `items`, `total` | evet | sayfa kuralı aşağıda |
| Platform `Model` (liste/detay) | `id`, `slug`, `name`, `modality`, `stage`, `visibility`, `versions_count`, `created_at`, `updated_at` zorunlu; `owner_username`, `description`, `license`, `architecture` | yukarıdakiler | `owner_username` null olabilir |
| Platform sürüm öğesi | `id`, `version_tag`, `created_at` zorunlu; `framework`, `file_size_bytes`; `weights_url`, `onnx_url`, `tflite_url` yalnız varlık bayrağı | yukarıdakiler | URL değeri tipte taşınmaz. Boş veya boşluk olan URL yoktur; null ve boş dışında tipteki her URL değeri `invalid_response` |
| Platform veri seti öğesi | `id`, `name`, `slug`, `modality`, `item_count`, `visibility`, `updated_at` zorunlu; `owner_username` | yukarıdakiler | kapsam etiketi K4 teyidine kadar `unknown` |

Zorunlu alan yoksa, tip yanlışsa (`true` bir sayı yerine geçemez; `1.0` bir tam sayı yerine geçemez), sayı eksi ise, boş veya duplicate anahtarlı JSON ya da sınırı aşan yanıt `invalid_response` döner. Tanımlayıcılar en çok 256 karakterdir. Zaman damgaları RFC 3339 tarih-saat biçimindedir (en çok 40 karakter); başka her biçim `invalid_response`.

## Görüntü metni ve kimlik

Sağlayıcı metinleri güvenilmez metindir. Ad, açıklama, lisans, mimari, modalite, aşama, görünürlük, biçim, para birimi ve fiyat tarihi çözümlenirken temizlenir: kontrol ve çift yönlü geçersiz kılma karakterleri düşer, satır sonu ve sekme boşluk olur, uzunluk sınırı aşılırsa sonda `…` bulunur. Sınırlar: ad ve biçim alanları 128, açıklama 512 gösterim karakteri.

Kimlikler (`id`, `slug`, `owner_username`, `version_tag`, LLM `id`) temizlenmez; temizlenmiş bir kimlik başka bir modele dönüşebilir. Satır sonu benzeri Unicode ayraçlar (U+2028, U+2029) boşluğa çevrilir. Kimlik ham tutulur, yalnız görüntülenirken temizlenir ve görüntüden alınan değer hiçbir zaman argüman olarak kullanılmaz.

## Adres alfabesi

`owner`, `slug`, `model_id` ve `version_id` argümanları `[A-Za-z0-9._-]{1,128}` ile sınırlıdır; `.` ve `..` yasaktır (URL’de gezinme anlamına gelirler). `...` gibi noktalardan oluşan diğer adlar bu alfabede olağan adlardır. Dışarıdaki her değer ağ isteğinden önce `invalid_request` ile reddedilir.

API’den gelen ve bu alfabeye uymayan kimlikler listede temizlenmiş metin olarak gösterilir; onlarla `show` veya `download` yapılamaz. Bu bilinçli bir sınırdır.

`version_tag` URL’ye girmez; yalnız istemci tarafında tam eşleşmede kullanılır. Kurallar: 1–128 karakter ve kontrol karakteri yok.

## Sayfa kuralları

Platform modelleri: istek `page ≥ 1` ve `1 ≤ page_size ≤ 100` ile gönderilir (varsayılan 20; üst sınır K4 ile teyit edilecek). Yanıtta `total` negatif olmayan tam sayı olmalıdır. Döndürülen kayıt sayısı `n`, şu değere eşit olmalıdır:

`n = max(0, min(page_size, total - (page - 1) * page_size))`

Eşit değilse `invalid_response` (sunucu sayfa boyutunu sessizce düşürmüş olabilir). `has_next = page * page_size < total`.

Tamlık etiketleri:

| Etiket | Ne demek |
|---|---|
| `complete` | tüm liste bu tek sayfada (`page = 1`, sonraki sayfa yok) |
| `partial` | sonraki sayfa var; komut sonraki sayfayı verir |
| `last_page` | `page > 1` ve sonraki sayfa yok; önceki sayfalar gösterilmedi |
| `unknown` | kanıtlanamıyor |

Veri setleri sayfa bilgisini başlıkta taşır. `X-Has-Next` tam olarak bir kez ve `true` veya `false` olarak bulunmalıdır; başka her durum `unknown`. `X-Total-Count` bulunursa düz bir ondalık sayı olmalıdır: tekrarlanmış, eksi, biçimi bozuk veya okunamayan bir değer sayfayı `unknown` yapar (tamlık iddiası kurulmaz). Okunabilen bir `X-Total-Count` satır sayısıyla ve `X-Has-Next` ile çelişirse `invalid_response`. Veri seti isteğinde `limit`, `offset` ve `sort` kullanılmaz.

Sürüm listesinde sayfalama yoktur: detay yanıtındaki `versions_count` dizi uzunluğuyla eşitse `complete`, değilse `unknown`. `model_id` yolunda detay olmadığı için `versions_count` bilinmez ve tamlık `unknown`dur. Çözümde eşitlik zorunludur; değilse `invalid_response`. `versions_count` bool, ondalık veya eksi ise her yerde `invalid_response`.

## Çözüm

- `owner/slug` tek detay isteğiyle çözülür; sahip ve slug tam eşleşmelidir (büyük/küçük harf duyarlı). Yanıt farklı bir modeli dönerse `invalid_response`.
- `owner_username` null ise `model_not_addressable`.
- `version_tag` için sürüm dizisinde tam eşleşme aranır. Sıfır sonuç `model_not_visible` (kesin yokluk değil); birden fazla sonuç `model_ambiguous` ve en çok beş aday. Seçim asla yapılmaz; “en son” veya “varsayılan” yoktur.
- LLM görevi beklenenle eşleşmezse `model_task_mismatch`. Bilinmeyen görev dizesi listelemede reddedilmez.

## Hata kodları

| Kod | Çıkış | Anlam |
|---|---|---|
| `model_not_visible` | 1 | uzak sonuç: model veya sürüm bu anahtara görünmüyor; kesin yokluk değildir |
| `model_ambiguous` | 2 | aynı etiketle birden fazla sürüm; seçim yapılmadı |
| `model_task_mismatch` | 2 | model beklenen görevle eşleşmiyor |
| `model_not_addressable` | 2 | modelin sahip adı yok; `owner/slug` ile adreslenemez |

Mevcut `invalid_request`, `invalid_response` ve `remote_access_denied` kodları değişmez. Çıkış sınıflaması ADR-0035 Karar 9’dadır; CLI tablosu P02-4e’de güncellenir.

## Bütçeler

Tek yanıt en çok 1 MiB. LLM listesi en çok 500 kayıt; Platform sayfası en çok `page_size` kayıt; sürüm listesi en çok 500 kayıt. Katalog komutu toplamı en çok 30 s; her komut için ağ isteği sayısı sabittir (liste 1; detay 1; sürümlerle detay 2; veri seti listesi 1).

## Gözlem penceresi

`observed_from`: komutun ilk ağ isteğinin başladığı an. `observed_until`: son yanıtın tamamlandığı an. Aynı komutta birden fazla istek varsa tek pencere bunları kapsar.

## Canlı teyit (K4)

Şu maddeler gerçek hesapla salt okuma ile doğrulanmadan kesin sayılmaz: Platform sayfa üst sınırı, sunucunun istenen sayfa boyutunu düşürme davranışı, `X-Has-Next` ve `X-Total-Count` biçimi, `scope=owned` filtresinin etkisi, LLM kimlik alfabesi, okunan alanların canlı örnekte bulunması ve en büyük gerçek sayfanın boyutu.
