# Katalog sözleşmesi (P02-4c)

**Durum:** Uygulandı (P02-4c): domain ve dar codec, çevrimdışı contract testleriyle. Ağ okuma (P02-4d), CLI yüzeyi (P02-4e) ve seçim bağı (P02-4f) ayrı adımlardır. **Karar kaynağı:** [ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) (Accepted, 2026-11-19). **Kod:** [domain/catalog.py](../../src/yorunge/domain/catalog.py), [application/catalog.py](../../src/yorunge/application/catalog.py); testler `tests/contracts/test_catalog_contract.py`.

## Kapsam

Katalog yalnız salt okumadır. Platform modelleri, sürümleri ve veri setleri; LLM geçidinin model listesi okunur. Önbellek, yazma, indirme ve çıkarım bu sözleşmenin dışındadır. Bu belge sayfa, tamlık, adres, çözüm ve okunan alanları tanımlar; ağ ve CLI davranışı ilgili adım kartlarındadır.

## Okunan alanlar (dar tüketici)

Sağlayıcı yanıtının okunmayan alanları yok sayılır ve hiçbir çıktıya girmez. Her ham yanıtın tüm ağacında (anahtar ve değerler, okunan veya okunmayan) seçili anahtar için gizli tarama yapılır. Görüntü temizliği tarama sonrasında çalıştığı için bitmiş kayıt bir kez daha taranır: temizlik sırasında birleşen bir anahtar da `invalid_response` olur. Kayıtlar çözücü tarafından kendi bayt girdisini alır; taramayı atlayan bir çağıran yoktur.

| Kaynak | Okunan alanlar | Zorunlu | Not |
|---|---|---|---|
| LLM `GET /v1/models` | `data` (dizi, en çok 500) | evet | sayfalama yok; tamlık `unknown` |
| LLM `ModelInfo` | `id`, `task` (1–64 karakter, denetim karakteri yok), `created` zorunlu; `modalities`, `context_length`, `default_max_output_tokens`, `precision`, `pricing` | `id`, `task`, `created` | `task` açık dize; kimlik ve görev ham tutulur |
| LLM `pricing` | `prompt_token_price`, `completion_token_price` (zorunlu, 0 veya üstü); `currency`, `free_until` | zorunlu iki fiyat | `free_until` yalnız bilgidir, maliyet kapısı değildir |
| Platform `GET /models` | `items`, `total` | evet | sayfa kuralı aşağıda |
| Platform `Model` (liste/detay) | `id`, `slug`, `name`, `modality`, `stage`, `visibility`, `versions_count`, `created_at`, `updated_at` zorunlu; `owner_username`, `description`, `license`, `architecture` | yukarıdakiler | `owner_username` null olabilir |
| Platform sürüm öğesi | `id`, `version_tag`, `created_at` zorunlu; `framework`, `file_size_bytes`; `weights_url`, `onnx_url`, `tflite_url` yalnız varlık bayrağı | yukarıdakiler | URL değeri tipte taşınmaz. Null veya boş/boşluk dizesi “konum yok” (bayrak `false`); boş olmayan dize “konum var” (bayrak `true`); dize olmayan her değer (ör. `false`, sayı, liste) `invalid_response` |
| Platform veri seti öğesi | `id`, `name`, `slug`, `modality`, `item_count`, `visibility`, `updated_at` zorunlu; `owner_username` | yukarıdakiler | kapsam etiketi K4 teyidine kadar `unknown` |

Zorunlu alan yoksa, tip yanlışsa (`true` bir sayı yerine geçemez; `1.0` bir tam sayı yerine geçemez), sayı eksi veya 2^53−1’i aşıyorsa, boş veya duplicate anahtarlı JSON ya da sınırı aşan yanıt `invalid_response` döner.

Tanımlayıcılar (`id`, `slug`, `owner_username`, `version_id`, `version_tag`, veri seti `id`/`slug`, LLM `id` ve `task`) en çok 256 karakterdir ve denetim, biçim veya satır ayracı karakteri içeremez; böyle bir değer temizlenmez, `invalid_response` olur (temizlenmiş bir kimlik başka bir modele ya da bir sırrın parçasına dönüşebilir).

Zaman damgaları RFC 3339 tarih-saat biçimindedir: saat dilimi (`Z` veya `±HH:MM`) zorunludur, saniye kesirinde en çok altı rakam vardır, takvim tarihi gerçek olmalıdır (ör. 30 Şubat yoktur). Başka her biçim `invalid_response`.

## Görüntü metni ve kimlik

Sağlayıcı metinleri güvenilmez metindir. Ad, açıklama, lisans, mimari, modalite, aşama, görünürlük, biçim, para birimi, fiyat tarihi, LLM `precision` ve `modalities` çözümlenirken temizlenir: kontrol ve çift yönlü geçersiz kılma karakterleri düşer, satır sonu ve sekme boşluk olur, uzunluk sınırı aşılırsa sonda `…` bulunur. Sınırlar: ad ve biçim alanları 128, açıklama 512 gösterim karakteri.

Kimlikler (`id`, `slug`, `owner_username`, `version_tag`, LLM `id`) temizlenmez; temizlenmiş bir kimlik başka bir modele dönüşebilir. Satır sonu benzeri Unicode ayraçlar (U+2028, U+2029) boşluğa çevrilir. Kimlik ham tutulur, yalnız görüntülenirken temizlenir ve görüntüden alınan değer hiçbir zaman argüman olarak kullanılmaz.

## Adres alfabesi

`owner`, `slug`, `model_id` ve `version_id` argümanları `[A-Za-z0-9._-]{1,128}` ile sınırlıdır; `.` ve `..` yasaktır (URL’de gezinme anlamına gelirler). `...` gibi noktalardan oluşan diğer adlar bu alfabede olağan adlardır. Dışarıdaki her değer ağ isteğinden önce `invalid_request` ile reddedilir.

API’den gelen ve bu alfabeye uymayan kimlikler listede temizlenmiş metin olarak gösterilir; onlarla `show` veya `download` yapılamaz. Bu bilinçli bir sınırdır. Sağlayıcının `id`’si 128 karakterden uzunsa veya bu alfabenin dışındaysa, detay ve liste yine gösterilir; ama bu kimlikle sürüm listesi (`--versions`) ve sürüm çözümü yolu kurulamadığı için `invalid_response` verir ve tek bir sürüm çözülmez.

`version_tag` URL’ye girmez; yalnız istemci tarafında tam eşleşmede kullanılır. Kurallar: 1–128 karakter ve kontrol karakteri yok.

## Sayfa kuralları

Platform modelleri: istek `1 ≤ page ≤ 2^53−1` ve `1 ≤ page_size ≤ 100` ile gönderilir; aralık dışı değer ağ isteğinden önce `invalid_request` olur (varsayılan 20; üst sınır K4 ile teyit edilecek). Yanıtta `total` negatif olmayan tam sayı olmalıdır. Döndürülen kayıt sayısı `n`, şu değere eşit olmalıdır:

`n = max(0, min(page_size, total - (page - 1) * page_size))`

Eşit değilse `invalid_response` (sunucu sayfa boyutunu sessizce düşürmüş olabilir). `has_next = page * page_size < total`.

Tamlık etiketleri:

| Etiket | Ne demek |
|---|---|
| `complete` | tüm liste bu tek sayfada (`page = 1`, sonraki sayfa yok) |
| `partial` | sonraki sayfa var; komut sonraki sayfayı verir |
| `last_page` | `page > 1` ve sonraki sayfa yok; önceki sayfalar gösterilmedi |
| `unknown` | kanıtlanamıyor |

Veri setleri sayfa bilgisini başlıkta taşır. Sonraki sayfanın varlığı bildirilmişse (`X-Has-Next: 1`) sayfadaki satır sayısı istenen sayfa boyutuna eşit olmalıdır; kısa bir sayfa devam bildiriyorsa satırlar sonraki istekte atlanır ve yanıt `invalid_response` olur. `X-Has-Next` tam olarak bir kez ve `0` veya `1` olarak bulunmalıdır (canlı gözlem: tamsayı biçimi); başka her durum `unknown`. `X-Total-Count` bulunursa düz bir ondalık sayı olmalıdır: tekrarlanmış, eksi, biçimi bozuk veya okunamayan bir değer sayfayı `unknown` yapar (tamlık iddiası kurulmaz). Okunabilen bir `X-Total-Count` satır sayısıyla ve `X-Has-Next` ile çelişirse `invalid_response`. Veri seti isteğinde `limit`, `offset` ve `sort` kullanılmaz.

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

## Uç noktalar ve taşıma (P02-4d)

Her komut, tek seçilmiş profilin (`--config`/`--profile` veya aktif profil) hizmet kimliğiyle bir kez çözülür; anahtar yalnız tek salt okuma GET’inin kendi başlığında gider. Platform uçları `X-API-Key`, LLM uçları `Authorization: Bearer` ile çağrılır; hiçbiri diğer hizmete gönderilmez. Yönlendirme izlenmez. Komut başına istek sayısı sabittir.

| Komut ailesi | İstekler | Not |
|---|---|---|
| Platform modelleri listesi | `GET models?page&page_size` | tek sayfa; `total` ve satır sayısı kuralı |
| Model detayı | `GET models/{owner}/{slug}` (+ `GET models/{id}/versions`) | `--versions` ile iki istek; detay sahibi ve slug’ı istenenle eşleşmelidir |
| Sürüm listesi (kimlikle) | `GET models/{id}/versions` | tamlık `unknown` (detay yok) |
| Sürüm çözümü | detay + `GET models/{id}/versions` | `versions_count` eşitliği zorunlu; tam bir sürüm |
| Veri seti listesi | `GET datasets?page&page_size&scope=owned` | başlık tabanlı tamlık; `scope` etiketi K4’e kadar `unknown` |
| LLM listesi | `GET models` | tek yanıt; tamlık `unknown` |
| LLM modeli | `GET models/{model_id}` | görev kontrolü isteğe bağlı |

Yeniden deneme yalnız salt okuma GET’inde en çok iki denemedir ve yalnız 408, 429, 502, 503, 504 ile geçici bağlantı hatalarında yapılır. Her katalog GET’inde 422 `invalid_request` olur; model kapsamlı uçta 404 `model_not_visible` olur (liste uçlarında 404 uzak hata sayılır); diğer durum kodları kapalı kataloğun kodlarıdır (401/403 `remote_access_denied`, 429 `remote_rate_limited`, diğerleri `remote_failed`). Hata metni sır, ham gövde ya da adres içermez.

Komut, yazılacak hiçbir durum dosyası açmaz ve çalışma dizinine dosya yazmaz.

## Gözlem penceresi

`observed_from`: komutun ilk ağ isteğinin başladığı an (oturum ve kimlik kurulumu bu sürenin dışındadır). `observed_until`: son yanıt gövdesinin tamamen okunduğu an. Aynı komutta birden fazla istek varsa tek pencere bunları kapsar.

## Komut yüzeyi (P02-4e)

- `models list --service evren-llm --task T` süzmesi istemci tarafındadır ve isteği değiştirmez. Metin başlığı `görev süzmesi: T` yazar. JSON'da `data.task_filter` aynı değeri taşır; sağlayıcı listesi boşsa süzme kaydedilmez ve `task_filter` `null` olur. Tamlık etiketi süzmeyle değişmez (`unknown` kalır).
- Öneri satırları (`Sonraki sayfa`, sahip adı olmayan modeller için kimlik yolu, sürüm indirme ipucu, katalog hata ipuçları), çağıranın verdiği `--config` ve `--profile` seçeneklerini aynen tekrarlar; öneri aynı hesabı okur.
- Geçersiz argümanlar hiçbir istek gönderilmeden çıkış 2 ve `invalid_request` ile döner: `page_size` 1–100, `page` 1 ile 2^53−1 arası; `--page`/`--page-size` yalnız Platform listesinde; `--task` yalnız LLM'de (listede süzme, gösterimde beklenen görev); görev 1–64 karakter, denetim ya da biçim karakteri içermez ve baştan veya sondan boşluk taşımaz. `show`: `--model` yalnız Platform'da ve `OWNER/SLUG` biçiminde; `--model-id` Platform'da yalnız `--versions` ile, LLM'de tek başına; `--model` ile `--model-id` birlikte verilmez; `--versions` yalnız Platform'da.

## Canlı teyit (K4)

2026-11-19 salt okuma kaydı ([kanıt](../research/p02-4-catalog-live-read-20261119.md)): `page_size=100` kabul edildi; veri seti başlığı `X-Has-Next` `0`/`1` olarak geliyor; veri seti `scope=owned` filtresinin etkisi bu hesapta gözlenemedi (etiket `unknown` kalır); LLM kimlikleri alfabeye uygun; LLM görevleri `decision` ve `guard` değerlerini de içeriyor. Hâlâ teyit bekleyenler: platform sayfasında 100'ün üstü, `model_id` ile sürüm listesi (hesapta model yok), sürüm çözümü ve büyük `model_card` alanının 1 MiB sınırına etkisi.
