# ADR-0035: Model ve veri kataloğu — salt okuma kaynakları, sabit referans ve seçim sınırı

**Durum:** Accepted — kullanıcı 2026-11-19 talimatıyla, iki fresh review turu ve ardından gelen belge incelemesinin bulguları işlendikten sonra onayladı. Kapsam: bu ADR’nin Karar bölümündeki kurallar (K1, K6, K9 ve K11 sonuçları). Plan’daki diğer kararlar (K2–K5, K7, K8, K10) önerileriyle uygulanır ([P02-4 teslim planı](../roadmap/p02-4-delivery-plan.md)). **Tarih:** 2026-11-19 (ilk taslak 2026-11-18). **İş:** P02-4a (okuma ve çözüm), P02-4b (seçilmiş sürüm indirmesi).

## Bağlam

[Faz satırı](../roadmap/phase-02-data-and-inference.md) P02-4’ü sayfalı veri/model kataloğu, göreve uygun sabit referans çözümü ve seçilmiş ağırlığın indirmeye bağlanması olarak tanımlar. Bugün katalog okuma yüzeyi yoktur; `models download` yalnız açık `--version-id` alır ([başvuru](../reference/download-engine.md#model-ağırlığı-yüzeyi-p02-3n)).

Kaynaklar ve bilinen sınırlar (yerel keşif OpenAPI özeti ve repodaki kanıtlar; canlı doğrulanmadı):

- **Platform** (`X-API-Key`):
  - `GET /api/v1/models`: `page`, `page_size` (şemada tip `string`); yanıt `items` ve `total`. Sunucunun istenen boyutu sessizce düşürüp düşürmediği gözlenmedi.
  - `GET /api/v1/models/{owner}/{slug}`: tek model detayı; `versions_count` alanını taşır.
  - `GET /api/v1/models/{model_id}/versions`: düz sürüm dizisi; sayfalama alanı yoktur.
  - `GET /api/v1/models/versions/{version_id}/download`: P02-3n akışı.
  - `GET /api/v1/datasets`: dizi döner; sayfa bilgisi `X-Total-Count` ve `X-Has-Next` başlıklarındadır. Başlık değerlerinin biçimi canlı teyit bekler. Repodaki upload kodu bu uçta `page`, `page_size` ve `scope=owned` kullanır ([platform_upload_reader](../../src/yorunge/adapters/platform_upload_reader.py)); katalog yolunda `scope` filtresinin sunucuda uygulandığı kanıtlanmamıştır.
  - `GET /api/v1/datasets/options`: kullanılmaz; tamlık kanıtı taşımaz.
  - Model `id` UUID’dir; sürüm `version_id` ile indirilir; `version_tag` istemcinin göreceği addır.
  - `owner_username` şemada null olabilir; bu durumda model `owner/slug` ile adreslenemez.
  - Model `license` ve `description` alanları null|string olarak şemadadır.
  - Bilinmeyen sorgu parametreleri sessizce yok sayılır.
  - Platform modellerinin hangi kapsamda görüneceği gözlenmedi; “anahtarın eriştiği” dışında kapsam iddiası kanıtlanana kadar kullanılmaz.
- **LLM geçidi** (`Authorization: Bearer`): `GET /v1/models` tek yanıt `data: ModelInfo[]` döner, sayfalama yoktur; `GET /v1/models/{model_id}`. `ModelInfo` zorunlu alanları `created`, `id`, `task`; `task` açık dizedir. `pricing` null olabilir; `free_until` yalnız bilgidir. Liste anahtara göre süzülür; görünmeyen model 404 verir, bu yüzden bulunamamak “yok” değil “bu anahtara görünmüyor” demektir ([LLM şema yeniden okuması](../research/p02-llm-gateway-schema-review.md#resmî-şemada-doğrulananlar-o)).
- Resmî şemada immutable revizyon, deprecation/sunset alanı ve sabit model tablosu yoktur. Platform’un `api-keys/selectable-models` ve llm-portal görünümleri ayrı Platform gözlemleridir; inference kimliği olarak doğrulanmamıştır.
- Repo yanıt codec’i `decode_response` kapalı modelleri zorunlu kılar; `_closed_codec` `extra=forbid` olmayan modeli reddeder ([kod](../../src/yorunge/application/response_json.py)). Tek bir keşif gözleminden Platform modelinin tam şekli (boş kalmış iç nesneler, `null` tipli alanlar, serbest nesneler) çıkarılamaz.
- [Performans standardı](../standards/performance.md): model/yetenek önbelleği hesap, hizmet, sürüm ve son doğrulama zamanını taşır; maliyet ve yetki kararı eski önbellekle kesinleşmez.
- Kalıcı önbellek yeni bir state tüketicisidir; DDL, migration, yedek ve sıfırlama kapsamı ister ([ADR-0015](0015-checksummed-data-migrations.md)).

## Karar

1. **Kaynak ve istek kuralları.** Katalog yalnız GET ile okunur. LLM model kimliği yalnız LLM geçidinin `/v1/models` ve `/v1/models/{model_id}` yanıtından gelir; Platform `selectable-models` ve llm-portal görünümleri P02-4 kaynağı değildir. Platform uçları kayıtlı Platform hedefine `api/v1` altında gider. Yönlendirme (3xx) izlenmez ve hata sayılır.
   - Yeniden deneme ve hata sınıfı [ADR-0017](0017-bounded-http-transport.md) ve [taşıma referansıyla](../reference/http-transport.md#retry-ve-hata) aynıdır: yalnız salt okuma GET’i en çok iki deneme alır; 408, 429, 502, 503, 504 ve geçici bağlantı hataları retry adayıdır. Diğer 4xx ve 5xx yeniden denenmez.
   - Hata eşlemesi: 401/403 `remote_access_denied` (çıkış 3); 429 `remote_rate_limited` (çıkış 1); diğer kabul edilmeyen durum kodları `remote_failed` (çıkış 1), gövde yansıtılmaz; 422 `invalid_request` (çıkış 2); 404 çözümde `model_not_visible`.
2. **Sayfa semantiği ve doğrulama.** Her komut **istenen tek sayfayı** okur; otomatik sayfa döngüsü yoktur. Platform sayfa boyutu istemci varsayılanı 20’dir (upload kodunun değeri); üst sınır başlangıçta 100 kabul edilir ve K4 canlı okumasıyla teyit edilir. Sayfa boyutu `page_size` olarak açıkça gönderilir. Veri setlerinde `limit`, `offset` ve `sort` parametreleri kullanılmaz: katalog tek bir sayfalama biçimi (`page`/`page_size`) kullanır ve diğer biçimler tamlık kanıtı üretmez.
   - Platform doğrulaması: `t` (toplam) negatif olmayan tam sayı olmalıdır. `n` döndürülen kayıt sayısıdır ve `n = max(0, min(s, t - (p-1)*s))` ile eşleşmelidir; eşleşmezse `invalid_response`. Bu kural sunucunun sayfa boyutunu sessizce düşürmesini de yakalar. `has_next = p*s < t`.
   - Tek yanıt en çok 1 MiB’dır; aşım `invalid_response`dur. LLM listesi en çok 500 kayıt kabul eder.
   - Komut toplamı için ayrı katalog bütçesi 30 s’dir.
   - Komut başına istek sayısı: liste 1; `owner/slug` detayı 1; `--versions` ile detay 2; `model_id` ile sürüm listesi 1; veri seti listesi 1.
3. **Tamlık durumu ve gözlem penceresi.**
   - Platform modelleri: `has_next` yokken ve `p=1` ise `complete` (tüm liste); `has_next` varsa `partial` (sonraki sayfa komutu verilir); `p>1` ve `has_next` yoksa `last_page` (önceki sayfalar gösterilmedi). Boş `t=0`, `p=1` tam listedir (`complete`).
   - Veri setleri: `X-Has-Next` tam olarak bir kez ve `true` veya `false` olarak bulunmalıdır; başka her durum `unknown`. `X-Total-Count` bulunursa düz ondalık sayı olmalıdır; okunamayan, tekrarlanmış veya eksi değer sayfayı `unknown` yapar. Okunabilen toplam satır sayısı ve `X-Has-Next` ile çelişirse `invalid_response`. Başlık biçimi K4 ile teyit edilir.
   - Sürüm listesi: detay yanıtındaki `versions_count` ile dizi uzunluğu eşitse `complete`; değilse `unknown`. `model_id` yolunda detay olmadığı için bu yolda `unknown`dur.
   - LLM tek yanıtı için kapsam kanıtı yoksa `unknown`dur.
   - `observed_from`, bir komutun ilk ağ isteği başladığı an; `observed_until`, son yanıtın tamamlandığı andır. Aynı komutta birden fazla istek varsa tek pencere bunları kapsar.
4. **Önbellek yok (P02-4).** Kalıcı katalog önbelleği, yerel katalog tablosu ve “son bilinen liste” çıktısı yoktur. Her komut okur ve çıktıda gözlem penceresini verir. Önbellek gerekirse ayrı bir ADR ile hesap, hizmet, hedef ve sürüm anahtarı, `validated_at`, TTL, tek transaksiyon ve V2 migration birlikte kabul edilir.
5. **Sabit referans ve adresleme.**
   - Platform: `model_id` (UUID), `owner_username` ve `slug` adresi, `version_id` (UUID), `version_tag`. İndirme kimliği `version_id`’dir. Sağlayıcı sürüm kimliğinin değişmezliğini garanti etmez; çıktı “gözlemlenen kimlik” der, “sabitlenmiş” demez.
   - `owner_username` null ise `owner/slug` yolu `model_not_addressable` ile reddedilir. Çıkış yolu `models show --service evren-platform --model-id UUID --versions` (yalnız sürüm listesi; tamlık `unknown`; etiketle çözüm yok) ve mevcut `models download --version-id` yoludur. `model_id` ile model detayı GET’i keşifte yoktur.
   - Adres alfabesi: `owner`, `slug`, `model_id` (Platform ve LLM) ve `version_id` için `[A-Za-z0-9._-]{1,128}`; `.` ve `..` yasak. `show` ve `download` argümanları bu alfabeye uymazsa I/O öncesi `invalid_request` (çıkış 2) döner. API’den gelen ve alfabeye uymayan kimlikler listede temizlenmiş metin olarak gösterilir; onlarla `show`/`download` yapılamaz. Bu bilinçli bir sınırdır; alfabe dışı LLM kimliklerinin varlığı K4 ile gözlenir.
   - `version_tag` URL’de kullanılmaz; yalnız istemci tarafında tam eşleşmede kullanılır. Kurallar: 1–128 karakter, kontrol karakteri yok.
   - Çözüm `owner/slug` için tek detay isteğidir; sahip ve slug tam eşleşir (büyük/küçük harf duyarlı); bulanık arama ve sayfa taraması yoktur. Detay `versions_count` ile sürüm dizisi uyuşmazsa çözüm `invalid_response` ile durur (fail-closed).
   - Sürüm çözümü `version_tag` için dizide tam eşleşme arar. Sıfır sonuç `model_not_visible` (metin: “bu anahtara görünmüyor (kesin yokluk değil)”), birden fazla sonuç `model_ambiguous` (en çok beş aday: kimlik, etiket, tarih) ile reddedilir. “En son” veya “varsayılan” sürüm seçilmez.
   - LLM: `model_id` dizesi ve `task`. Revizyon yoktur; referans “bu anahtarla bu zamanda görünen model kimliği”dir. Beklenen görev gözlemlenen görevle eşleşmezse `model_task_mismatch`; bilinmeyen görev dizesi listelemede reddedilmez, “bilinmeyen görev” olarak gösterilir.
6. **Seçim bağı (P02-4b).** `models download --version-id` yolu değişmez. Yeni `--model OWNER/SLUG --version-tag TAG` yolunda sıra şudur ve tamamı motorun kilidi altında yürür:
   1. Argüman yargısı (adres alfabesi dahil); ağsız.
   2. Yerel ön kontroller, sürüm kimliği gerekmeden karar verilenler: hedef var (`download_output_exists`), meşgul (`download_busy`), doğrulanamayan iz (`download_partial_unverified`). Biri verilirse katalog çözümü yapılmaz ve ağ isteği yoktur.
   3. Katalog çözümü (en çok iki GET); çözülen `version_id` çıktıda gösterilir.
   4. Stage kimlik kararı (devam, temiz başlangıç, tam stage yayımı) çözülen `version_id` ile verilir; gerekiyorsa tek JSON ağırlık çağrısı ve motor.
   - Kilit, çözüm çağrısı boyunca tutulur (bugünkü `open_sink` davranışı). Böylece ön kontrol ile kimlik kararı arasında yarış ve kilitsiz “atma” kararı oluşmaz.
   - Bütçe: çözüm kendi 30 s katalog bütçesine sahiptir; motorun JSON çağrısı gibi indirme deadline’ından düşülmez. İndirme deadline’ı `--timeout` ile yerel durum ve GET’i kapsar.
   - Stage adı hedef adından türediği için çözülen sürüm farklıysa önceki kısmi içerik kurala göre atılır ve yeni indirme başlar; bu bir üzerine yazma değildir. Çözüm hiçbir durumda saklanmaz.
   - Bu yolda tam stage’in ağsız yayımı garanti edilmez: kimlik doğrulaması için katalog okuması gerekir. Bu ödünleşme referansa yazılır; `--version-id` yolundaki ağsız tam-stage yayımı değişmez.
7. **Güven sınırı.** Katalog metinleri (ad, açıklama, sahip görünen adı, etiket, görev, modalite, lisans) güvenilmez metindir: terminal kontrol ve çift yönlü geçersiz kılma karakterleri temizlenir, uzunluk sınırlanır, yol, URL veya komut olarak kullanılmaz. Depolama adresleri (`weights_url`, `onnx_url`, `tflite_url`, `download_url`, önizleme, metrik ve matris bağlantıları) çıktıya girmez ve takip edilmez; sürüm listesinde yalnız biçim mevcudiyeti bayrağı gösterilir. Ağırlık adresi yalnız P02-3n JSON akışından gelir.
   - `license` ve `description` tüketilen alanlardır ve gösterilir (açıklama 512 gösterim karakteriyle sınırlı). Lisans ve şart bilgisi yalnız gösterilir; hiçbir şart otomatik kabul edilmez.
8. **Codec ve gizli tarama (K9 — dar tüketici).** Katalog yanıtı, `decode_response` kuralını değiştirmeden **dar bir tüketici** ile çözülür. Desen [ADR-0022](0022-observed-platform-consumer-contract.md)’nin Platform gözlem sözleşmesinden alınır:
   - Tüketilen alanlar (P02-4c’de listelenir) tip ve zorunluluk açısından sıkı doğrulanır; `null` yalnız şemanın nullable dediği yerde kabul edilir.
   - Tüketilmeyen alanlar yok sayılır ve hiçbir çıktıya girmez.
   - Ham yanıtın tüm ağacında seçili anahtar için literal-secret taraması yapılır (`scan_for_secret`); tüketilen dizeler ayrıca `check_response_secrets` ile denetlenir.
   - Dış DTO’lar kapalıdır (`extra=forbid`).
   - ADR-0022’nin “aynı istisna verilmez” hükmü yetki ve yazma tüketicilerini kapsar; katalog salt okumadır, yetki veya yazma kararı üretmez. Gizli tarama ve dış DTO kapalılığı korunduğu için istisna genişlemesi değildir.
   - Alternatif K9-B (kapalı tam şekil) reddedildi: tek gözlemle tam şekil bilinmiyor, serbest nesne alanları repo kuralıyla çelişiyor ve yeni alan tüm listeyi durdurur.
9. **Hata kodları ve çıkış (K11).** Dört yeni kararlı kod eklenir: `model_not_visible` (çıkış 1; uzak sonuç: kaynak bu anahtara görünmüyor), `model_ambiguous`, `model_task_mismatch`, `model_not_addressable` (çıkış 2; kullanıcının seçimi çözülemedi). Kodlar P02-4e’de [CLI hata kataloğuna](../reference/cli-contract.md#p01-5-hata-kataloğu) işlenir; mevcut kodlar değişmez.
10. **Yüzey ve hesap (O1 düzeltmesi).** Katalog okuma komutları `models download` ile aynı `--config` ve `--profile` seçeneklerini alır; hesap bu seçeneklerden veya aktif profilden gelir. Katalog komutlarında `--project` yoktur (katalog kapsamı proje değil; `--project` `invalid_request` ile reddedilir, parser testi bunu kilitler). Katalog okuma `--state-dir` almaz (state yazılmaz). `models download` mevcut `--config`, `--profile`, `--state-dir` seçeneklerini korur. Planlanan örnek `yorunge llm models` (cli-contract, taslak) `models list --service evren-llm` ile yerine geçer ve örnek P02-4e’de güncellenir.
11. **Maliyet ve görünürlük.** `pricing.free_until` ve kota alanları bilgi olarak okunur; maliyet kapısını gevşetmez. Katalogda görünen model, GPU erişimi, servis sağlığı veya kullanım yetkisi kanıtı değildir.

## Alternatifler

- **Kalıcı SQLite önbelleği (TTL):** P02-4’te reddedildi. Gerekçe: V2 migration ve yedek kapsamı, bayat veri riski, performans standardının hesap anahtarı zorunluluğu.
- **Platform `selectable-models` listesini LLM kaynağı yapmak:** reddedildi; inference hedefi gateway’dir.
- **Otomatik sayfa döngüsü:** reddedildi; istek sayısı ve süre belirsizleşir, hangi komutun kaç sayfa okuduğu gizli olur.
- **Kapalı tam şekil codec (K9-B):** reddedildi (Karar 8).
- **Sürüm listesinde sessiz eşleşme:** reddedildi; eşitlik kontrolü olmadan kısmi liste ikinci eşleşmeyi gizleyebilir.
- **“En son sürüm” varsayılanı:** reddedildi; hareketli hedef.
- **Statik model tablosu veya “önerilen model”:** reddedildi; şemada deprecation alanı yoktur ve tablo bayatlar.
- **Bulanık ad arama:** reddedildi; yanlış hedef riski.

## Sonuçlar

- Katalog çevrimdışı çalışmaz; her komut ağ ister ve çıktı bunu söyler.
- “Sabit” terimi “gözlemlenen kimlik” olarak sınırlanır. İndirmenin kanıtı ADR-0032’nin doğrulama seviyeleriyle sınırlıdır (`transfer_complete` / `sha256_matched`).
- Dört yeni kararlı hata kodu eklenir (Karar 9).
- Motor sırasının ayrıştırılması ve kilit kapsamının korunması P02-4f’de ayrı regresyon kanıtı gerektirir.
- Dataset baytı indirme ve upload’ın uzak byte sınırı değişmez ([P02-R5](../roadmap/tasks/p02-r5-dataset-item-byte-access.md)).
- Canlı K4 okumasında teyit edilecek maddeler: sayfa üst sınırı, sunucunun sayfa boyutunu düşürme davranışı, `X-Has-Next`/`X-Total-Count` biçimi, `scope` filtresinin etkisi, LLM kimlik alfabesi, en büyük gerçek sayfanın boyutu (1 MiB sınırı).
