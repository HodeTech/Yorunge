# ADR-0035: Model ve veri kataloğu — salt okuma kaynakları, sabit referans ve seçim sınırı

**Durum:** Proposed — kullanıcı onayı bekleniyor ([P02-4 teslim planı](../roadmap/p02-4-delivery-plan.md), K1–K11; onay açık verilmelidir, sessizlik onay sayılmaz). **Tarih:** 2026-11-19 (ilk taslak 2026-11-18; iki fresh review turu işlendi). **İş:** P02-4a (okuma ve çözüm), P02-4b (seçilmiş sürüm indirmesi).

## Bağlam

[Faz satırı](../roadmap/phase-02-data-and-inference.md) P02-4’ü sayfalı veri/model kataloğu, göreve uygun sabit referans çözümü ve seçilmiş ağırlığın indirmeye bağlanması olarak tanımlar. Bugün katalog okuma yüzeyi yoktur; `models download` yalnız açık `--version-id` alır ([başvuru](../reference/download-engine.md#model-ağırlığı-yüzeyi-p02-3n)).

Kaynaklar ve bilinen sınırlar (yerel keşif OpenAPI özeti ve repodaki kanıtlar; canlı doğrulanmadı):

- **Platform** (`X-API-Key`):
  - `GET /api/v1/models`: `page`, `page_size` parametreleri (tip şemada `string`); yanıt `items` ve `total`.
  - `GET /api/v1/models/{owner}/{slug}`: tek model detayı.
  - `GET /api/v1/models/{model_id}/versions`: sürüm dizisi; sayfalama gözlenmedi.
  - `GET /api/v1/models/versions/{version_id}/download`: P02-3n akışı.
  - `GET /api/v1/datasets`: dizi döner; sayfa bilgisi gövdede değil `X-Total-Count` ve `X-Has-Next` başlıklarındadır; başlık değerlerinin anlamı canlı teyit bekler.
  - `GET /api/v1/datasets/options`: bu kararda kullanılmaz; tamlık kanıtı taşımaz.
  - Model `id` UUID’dir; sürüm `version_id` ile indirilir; `version_tag` istemcinin göreceği addır.
  - `owner_username` şemada null olabilir; bu durumda model `owner/slug` ile adreslenemez.
  - Yerel upload kodu veri setlerini `scope=owned` ile listeler ([dataset-upload-http](../reference/dataset-upload-http.md)); keşif şemasında `scope` alanı yoktur.
  - Bilinmeyen sorgu parametreleri sessizce yok sayılır.
  - Platform modellerinin hangi kapsamda görüneceği gözlenmedi; “anahtarın eriştiği” dışında kapsam iddiası kanıtlanana kadar kullanılmaz.
- **LLM geçidi** (`Authorization: Bearer`): `GET /v1/models` tek yanıt `data: ModelInfo[]` döner, sayfalama yoktur; `GET /v1/models/{model_id}`. `ModelInfo` zorunlu alanları `created`, `id`, `task`; `task` açık dizedir. `pricing` null olabilir; `free_until` yalnız bilgidir. Liste anahtara göre süzülür; görünmeyen model 404 verir, bu yüzden bulunamamak “yok” değil “bu anahtara görünmüyor” demektir ([LLM şema yeniden okuması](../research/p02-llm-gateway-schema-review.md#resmî-şemada-doğrulananlar-o)).
- Resmî şemada immutable revizyon, deprecation/sunset alanı ve sabit model tablosu yoktur. Platform’un `api-keys/selectable-models` ve llm-portal görünümleri ayrı Platform gözlemleridir; inference kimliği olarak doğrulanmamıştır.
- Repo yanıt codec’i `decode_response` kapalı modelleri zorunlu kılar ve `_closed_codec` `extra=forbid` olmayan modeli reddeder ([kod](../../src/yorunge/application/response_json.py)). Tek bir keşif gözleminden Platform modelinin tam şekli (boş kalmış iç nesneler, `null` tipli alanlar, serbest nesneler) çıkarılamaz; repo “serbest nesne” ve “genel dict” DTO’larını da kabul etmez.
- [Performans standardı](../standards/performance.md): model/yetenek önbelleği hesap, hizmet, sürüm ve son doğrulama zamanını taşır; maliyet ve yetki kararı eski önbellekle kesinleşmez.
- Kalıcı önbellek yeni bir state tüketicisidir; DDL, migration, yedek ve sıfırlama kapsamı ister ([ADR-0015](0015-checksummed-data-migrations.md)).

## Karar

1. **Kaynak sınırı.** Katalog yalnız GET ile okunur. LLM model kimliği yalnız LLM geçidinin `/v1/models` ve `/v1/models/{model_id}` yanıtından gelir; Platform `selectable-models` ve llm-portal görünümleri P02-4 kaynağı değildir. Platform uçları kayıtlı Platform hedefine `api/v1` altında gider. Yönlendirme (3xx) izlenmez ve hata sayılır. Okuma en çok **iki** denemedir; yalnız açıkça salt okuma GET’lerinde geçerlidir ([ADR-0017](0017-bounded-http-transport.md)). 401, 403, 404 ve 408/429 dışındaki 4xx yeniden denenmez; 408, 429 ve geçici bağlantı hataları retry adayıdır ([taşıma referansı](../reference/http-transport.md#retry-ve-hata)).
2. **Sınırlar ve sayfa semantiği.** Her komut **istenen tek sayfayı** okur; komut içinde otomatik sayfa döngüsü yoktur. Platform sayfa boyutu varsayılanı 20’dir (`datasets upload` kodunun kullandığı değer); üst sınır başlangıçta 100 kabul edilir ve K4 canlı okumasıyla teyit edilir. Tek yanıt en çok 1 MiB’dır; LLM listesi en çok 500 kayıt kabul eder. Aşım sessiz kırpma değil `invalid_response`dur. Komut toplamı 30 s ile sınırlıdır. Komut başına istek sayısı: liste 1, detay 1, `--versions` ile detay 2, veri seti listesi 1.
3. **Tamlık durumu.** Her liste sonucu üç değerden birini taşır: `complete` (kanıtlanmış tam liste), `partial` (kanıtlanmış eksik; sonraki sayfa komutu verilir), `unknown` (kanıtlanamıyor).
   - Platform modelleri: sayfa `p`, sayfa boyutu `s`, döndürülen kayıt sayısı `n`, toplam `t` ise `(p-1)*s + n >= t` ise `complete`, değilse `partial`. Bu, repodaki `has_next ⇔ page*page_size < total` kuralıyla tutarlıdır.
   - Veri setleri: `X-Has-Next` başlığı yoksa veya değeri ayrıştırılamazsa `unknown`. Başlık `false` ise `complete`, `true` ise `partial`; başlık değerlerinin biçimi K4 ile teyit edilir.
   - LLM tek yanıtı için kapsam kanıtı yoksa `unknown`dur.
4. **Önbellek yok (P02-4).** Kalıcı katalog önbelleği, yerel katalog tablosu ve “son bilinen liste” çıktısı yoktur. Her komut okur ve çıktıda gözlem aralığını (`observed_from`, `observed_until`) verir. Önbellek gerekirse ayrı bir ADR ile hesap, hizmet, hedef ve sürüm anahtarı, `validated_at`, TTL, tek transaksiyon ve V2 migration birlikte kabul edilir.
5. **Sabit referans semantiği ve adresleme.**
   - Platform: `model_id` (UUID), `owner_username` ve `slug` adresi, `version_id` (UUID), `version_tag`. İndirme kimliği `version_id`’dir. Sağlayıcı sürüm kimliğinin değişmezliğini garanti etmez; çıktı “gözlemlenen kimlik” der, “sabitlenmiş” demez.
   - `owner_username` null ise model `owner/slug` ile adreslenemez; `model_not_addressable` ile reddedilir. Bu durumda çıkış yolu `models show --service evren-platform --model-id UUID --versions` (sürüm listesi) ve ardından mevcut `models download --version-id` yoludur. `model_id` ile model detayı için GET keşifte yoktur; yalnız sürüm listesi kullanılır.
   - Adres segmentleri (`owner`, `slug`, `model_id`, `version_id`) `[A-Za-z0-9._-]{1,128}` ile sınırlıdır ve `.` ya da `..` olamaz (yol enjeksiyonu kapanır). Dışarıdaki her karakter (`/` fazlası, `%`, `?`, `#`, boşluk, kontrol) I/O öncesi `invalid_request` olur.
   - Çözüm `owner/slug` için tek detay isteğidir; sahip ve slug tam eşleşir (büyük/küçük harf duyarlı); bulanık arama ve sayfa taraması yoktur.
   - Sürüm çözümü `version_tag` için sürüm dizisinde tam eşleşme arar: sıfır sonuç `model_not_visible` (“bu yanıtta yok veya bu anahtara görünmüyor”, kesin yokluk değil), birden fazla sonuç `model_ambiguous` (en çok beş aday: kimlik, etiket, tarih) ile reddedilir. “En son” veya “varsayılan” sürüm seçilmez.
   - LLM: `model_id` dizesi ve `task`. Revizyon yoktur; referans “bu anahtarla bu zamanda görünen model kimliği”dir. Beklenen görev gözlemlenen görevle eşleşmezse `model_task_mismatch`; bilinmeyen görev dizesi listelemede reddedilmez, “bilinmeyen görev” olarak gösterilir. LLM kimlikleri `/` içerebilir mi sorusu K4’e bağlıdır; içermeyen alfabe dışı kimlikler listede gösterilir ama `show` ile çözülmez.
6. **Seçim bağı (P02-4b).** `models download --version-id` yolu değişmez. Yeni `--model OWNER/SLUG --version-tag TAG` yolunda sıra şöyledir:
   1. Argüman yargısı (adres alfabesi dahil); ağsız.
   2. Ağsız yerel ön kontroller, sürüm kimliği gerekmeden karar verilenler: hedef var, meşgul, doğrulanamayan iz. Bu kararlardan biri verilirse katalog çözümü yapılmaz.
   3. Katalog çözümü (en çok iki GET); çözülen `version_id` çıktıya yazılır.
   4. Stage kimlik kararı (devam, temiz başlangıç, tam stage yayımı) çözülen `version_id` ile yapılır; gerekiyorsa tek JSON ağırlık çağrısı ve motor.
   Motordaki `open_sink` bugün yerel kararı tek adımda verir; bu sırayı uygulamak için P02-4f’de kanıtlanmış davranışı koruyan bir ayrıştırma gerekir ve regresyon testleriyle kapatılır. Stage adı hedef adından türediği için çözülen sürüm farklıysa önceki kısmi içerik kurala göre atılır ve yeni indirme başlar; bu bir üzerine yazma değildir. Çözüm hiçbir durumda saklanmaz. Belirsiz, bulunamayan veya görev uyumsuz çözümde ağırlık çağrısı yapılmaz.
   Bu yolda tam stage’in ağsız yayımı garanti edilmez: kimlik doğrulaması için katalog okuması gerekir. Bu ödünleşme referansa yazılır; `--version-id` yolundaki ağsız tam-stage yayımı değişmez.
7. **Güven sınırı.** Katalog metinleri (ad, açıklama, sahip görünen adı, etiket, görev, modalite, lisans) güvenilmez metindir: terminal kontrol ve çift yönlü geçersiz kılma karakterleri temizlenir, uzunluk sınırlanır, yol, URL veya komut olarak kullanılmaz. Depolama adresleri (`weights_url`, `onnx_url`, `tflite_url`, `download_url`, önizleme, metrik ve matris bağlantıları) çıktıya girmez ve takip edilmez; sürüm listesinde yalnız biçim mevcudiyeti bayrağı gösterilir. Ağırlık adresi yalnız P02-3n JSON akışından gelir. Lisans ve şart bilgisi gösterilir; hiçbir şart otomatik kabul edilmez.
8. **Codec ve gizli tarama (K9).** Katalog yanıtı, repo kapalı-codec kuralından ayrı bir **dar tüketici** ile çözülür. Önerilen kural, [ADR-0022](0022-observed-platform-consumer-contract.md)’nin Platform gözlem sözleşmesindeki desenidir: tüketilen alanlar (P02-4c’de listelenir) tip ve zorunluluk açısından sıkı doğrulanır; tüketilmeyen alanlar yok sayılır ve hiçbir çıktıya girmez; ham yanıtın tüm ağacında seçili anahtar için literal-secret taraması çalışır (`scan_for_secret`); dış DTO’lar yine kapalıdır (`extra=forbid`). Bu, `decode_response` kuralını değiştirmez; yeni bir tüketici olduğu için kendi kararı gerekir. Alternatif (K9-B) kapalı tam şekil codec’tir: sağlayıcı yeni bir alan eklerse liste fail-closed durur; ancak tam şekil bugün tek gözlemle bilinmediği için K4 öncesi kesin sayılmaz.
9. **Hata kodları (K11).** Dört yeni kararlı kod eklenir: `model_not_visible`, `model_ambiguous`, `model_task_mismatch`, `model_not_addressable`. Öneri: `model_ambiguous`, `model_task_mismatch` ve `model_not_addressable` çıkış 2 (kullanıcının seçimi çözülemedi); `model_not_visible` çıkış 1 (uzak sonuç: kaynak bu anahtara görünmüyor). Kodlar P02-4e’de [CLI hata kataloğuna](../reference/cli-contract.md#p01-5-hata-kataloğu) işlenir; mevcut kodlar değişmez.
10. **Yüzey ve hesap.** Katalog komutları `models` ailesinde yaşar ve `models download` ile aynı kuralı izler: profil seçenekleri (`--config`, `--profile`, `--project`) yoktur; hesap aktif profilden gelir (`yorunge context use-profile` ile değişir). `--project` katalog komutlarında reddedilir. Planlanan örnek olan `yorunge llm models` (cli-contract örnekleri, taslak) bu kararla `models list --service evren-llm` olarak yerine geçer ve örnek P02-4e’de güncellenir.
11. **Maliyet ve görünürlük.** `pricing.free_until` ve kota alanları bilgi olarak okunur; maliyet kapısını gevşetmez. Katalogda görünen model, GPU erişimi, servis sağlığı veya kullanım yetkisi kanıtı değildir.

## Alternatifler

- **Kalıcı SQLite önbelleği (TTL):** P02-4’te reddedildi. Gerekçe: V2 migration ve yedek kapsamı, bayat veri riski, performans standardının hesap anahtarı zorunluluğu. Ölçülmüş gecikme ihtiyacı çıkarsa ayrı ADR.
- **Platform `selectable-models` listesini LLM kaynağı yapmak:** reddedildi; inference hedefi gateway’dir.
- **Otomatik sayfa döngüsü:** reddedildi. Hangi komutun kaç sayfa okuduğu gizli olur; istek sayısı ve süre belirsizleşir.
- **Kapalı tam şekil codec (K9-B):** önerilmiyor; tek gözlemle tam şekil bilinmiyor, repo serbest nesne kabul etmiyor, ve yeni alan tüm listeyi durdurur.
- **“En son sürüm” varsayılanı:** reddedildi; hareketli hedef.
- **Statik model tablosu veya “önerilen model”:** reddedildi; şemada deprecation alanı yoktur ve tablo bayatlar.
- **Bulanık ad arama:** reddedildi; yanlış hedef riski.

## Sonuçlar

- Katalog çevrimdışı çalışmaz; her komut ağ ister ve çıktı bunu söyler.
- “Sabit” terimi “gözlemlenen kimlik” olarak sınırlanır. İndirmenin kanıtı ADR-0032’nin doğrulama seviyeleriyle sınırlıdır (`transfer_complete` / `sha256_matched`).
- Dört yeni kararlı hata kodu eklenir (K11 ile çıkış eşlemesi).
- Motor sırasının ayrıştırılması P02-4f’de ayrı regresyon kanıtı gerektirir.
- Dataset baytı indirme ve upload’ın uzak byte sınırı değişmez ([P02-R5](../roadmap/tasks/p02-r5-dataset-item-byte-access.md)).
- Kabul: ADR Accepted olduktan sonra P02-4c `ready` yapılabilir (bağımlılıkları verified). Bu ADR tek başına hiçbir kodu yetkilendirmez; kapsamın kabulü kartlarda ölçülür.
