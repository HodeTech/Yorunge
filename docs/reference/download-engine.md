# Akışlı indirme motoru ve model ağırlığı indirme

**Durum:** Taslak sözleşme — [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) Accepted (2026-11-06); saf kısım (değerler, seviyeler, sidecar, adlar, yanıt tablosu, başlangıç tablosu, hata kodları) P02-3j’de uygulandı ([aşağıda](#saf-sözleşme-p02-3j)); ağ, yerel yazıcı, motor ve komut ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, DTO ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek, sağlayıcı garantisi, ücret/lisans bilgisi veya dataset bayt erişimi değildir. Bu belge indirme hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

## Planlanan yüzey

```text
yorunge models download --version-id UUID --format onnx|pt|tflite [--fold N] --weights-out FILE
    [--sha256 HEX64] [--timeout SECONDS] [--no-resume]
    [--config FILE] [--profile NAME] [--state-dir PATH]
```

Python karşılığı aynı kullanım senaryosuna bağlı tek API’dir. `--version-id` kesin model sürümü kimliğidir; kullanıcı onu Platform arayüzündeki model sürümü sayfasından alır (katalog çözümü P02-4’tedir), ilk sürüm otomatik seçilmez, ad/slug çözülmez. `--format` zorunludur (sağlayıcı varsayılanı tahmin edilmez). `--fold` yalnız k-fold sürümlerinde sağlayıcı istemcisinin gönderdiği isteğe bağlı parametredir; 0–1024 kesin tamsayıdır (`+`/boşluk/ondalık yok), verilirse iletilir ve kimlik anahtarına girer. `--timeout` 30–3600 tamsayı saniyedir (varsayılan 900). `--weights-out` açık, mevcut parent içinde yeni bir dosya adıdır (genel `--output text|json|ndjson` yalnız çıktı biçimini seçer; hedef dosya için kullanılmaz). `--sha256` kullanıcının bağımsız beklenen özetidir (64 küçük harf hex). `--no-resume`, kilit alınabilen ve sahipliği kanıtlanabilen (normal dosya, uid, 0600, `nlink==1`) yarım indirme dosyalarını siler ve baştan indirir; kanıtlanamayan hiçbir dosyaya dokunmaz. Anahtar argüman değildir; yalnız JSON bağlantı çağrısında Platform kimliği kullanılır.

## Motor sınırı

| Sınır | Kural |
|---|---|
| Boyut | En çok 1 GiB (ortak ham HTTP sınırı); Content-Length bilinen ve aşan gövde bayt yazılmadan reddedilir; gövde sırasında koşan sayaç da tavanı uygular (ortak taşımanın gövde fazındaki `invalid_response`i indirme görünümünde `download_limit_exceeded`a eşlenir; başlık fazı ihlalleri `invalid_response` kalır) |
| Çerçeve | Yanıt `Content-Length` veya chunked terminasyonu taşımalıdır; kapanışla sınırlanan gövde (ikisi de yok) `invalid_response`. Chunked ise toplam bilinmez: resume sunulmaz, ilerleme toplamsızdır |
| Yazma | Tek akış, en çok 1 MiB blok, async görevde `os.write`; executor/thread, bütün dosya buffer’ı ve ikinci kuyruk yok |
| Süre | JSON çağrısı ayrı 30 s kontrol bütçesi; ardından tek mutlak indirme deadline’ı: varsayılan 900 s, kullanıcı 30–3600 s; connect/write/read 5 s, pool 1 s. GET penceresi PUT penceresinin 120 s sınırından bağımsızdır; yarım dosya ön ek hash’i bu deadline içindedir; yayın adımları (tamamlanma checkpoint’i, `full_sync`, `link`, `unlink`, dizin fsync) yerel I/O’dur ve deadline’dan muaftır |
| Deneme | Hata sonrası otomatik tekrar, kimlikli fallback ve proxy yok; devam yalnız kullanıcı komutu yeniden çalıştırınca. İmzalı URL’ye en çok iki GET: ilk istek + (resume uygulanmazsa) bir Range’siz protokol dönüşü. Bağlantı JSON çağrısı ayrıdır ve ADR-0017 salt okuma politikasıyla en çok iki deneme alır |
| İstek başlıkları | Kapalı: `Range: bytes=N-` ve güçlü ETag’li `If-Range`. Başka başlık, `W/` ETag, `Last-Modified`, `If-Match` yok |
| Hedef | HTTPS/443, imzalı query ham baytlarıyla korunur, ≤16 KiB; kimlik/cookie/redirect/proxy yok; DNS/public-IP/peer koruması; origin tek ve önceden bilinir; yol öneki tüketici sabitidir (model: `{api_base_path}/files/evren-models/`; canlı yoklamada gözlenen tam önekten türetilir) ve yanıt onu genişletemez; query’de `%2F`/`%2B`/`%3D` geçerli, path’te `%2F` ve `%2e%2e` ret |
| Taşıma çıktısı | GET taşıması tipli bir yanıt döndürür (durum ∈ {200,206,416}, ayrıştırılmış `Content-Range`, güçlü ETag veya yok, çerçeve türü); motor ham header’a dokunmaz. Hizmet görünümünün yalnız-2xx kapısı yeniden kullanılmaz |
| Sidecar | ≤4 KiB, 0600; imzalı URL/sır/yol içermez |

## Yanıt işleme (kapalı tablo)

Yerel durum (aşağıdaki başlangıç tablosu) **her ağ isteğinden önce, JSON çağrısı dahil**, değerlendirilir. Her tel olayı tek satıra ve tek koda düşer; tablo dışı yanıt yoktur.

| Durum | Sonuç |
|---|---|
| Sidecar+stage tamam (`committed_bytes == total_size`), kimlik anahtarı (hizmet hedefi dahil) ve ön ek özeti eşleşiyor | **Hiçbir ağ isteği yapılmaz (JSON çağrısı dahil)**; beklenti karşılaştırması ve yayın doğrudan (`resumed=true`, `resumed_from_bytes=T`). Sağlayıcıda nesnenin hâlâ aynı olduğunu iddia etmez |
| `200`, Range’siz istek | Tam gövde; `Content-Length` (veya chunked terminasyonu) zorunlu; ikisi de yoksa `invalid_response` |
| `200`, Range’li istek | Sağlayıcı aralığı uygulamadı: `ftruncate(0)`, başlık checkpoint’i, aynı yanıttan baştan yazılır (ek istek yok) |
| `206` + tam `Content-Range: bytes N-(T-1)/T`, N = fsync edilmiş ön ek, T = kayıtlı toplam, aynı güçlü ETag, `Content-Length = T-N` | Devam |
| `206` ETag/`Content-Range`/`Content-Length` uyumsuz veya eksik, `416` | Stage ve sidecar Range’siz istekten **önce** atılır (stage, sonra sidecar); sonra bir Range’siz istek |
| `206`, Range göndermeyen isteğe | `invalid_response`/1, hedef yok |
| Diğer 2xx (`201`, `204`, …), `Content-Encoding ≠ identity` | `invalid_response`/1; gövde okunmaz, hedef yok |
| 3xx | `remote_failed`/1 (redirect takip edilmez); hedef yok |
| 401/403 | `remote_access_denied`/3; kimlikle yeniden denemek yok |
| 429 | `remote_rate_limited`/1 |
| 404 ve diğer 4xx (401/403/416/429 hariç) | `remote_failed`/1; URL aynı koşuda yeniden çözülmez (kullanıcı komutu yeniden çalıştırır) |
| 5xx, gövde öncesi timeout/taşıma | `remote_failed`/1 veya `transport_*`/1; yarım dosya koşullara göre korunur |
| Gövde fazında kopma, EOF ile yazılan < Content-Length veya eksik chunked terminasyonu | `download_incomplete`/1 (`transport_timeout` önceliğini korur) |

## Doğrulama seviyeleri

`transfer_complete` < `sha256_matched`. Her sonuç yazılan bayt, hesaplanan SHA-256, seviye ve `expectation_source` taşır; bugün yalnız `none` ve `user_supplied` üretilir (`size_matched` seviyesi ve `provider_metadata`/`local_manifest` kaynakları, onları üretecek bir tüketici gelince eklenir). Beklenen özet uyuşmazlığı yayın öncesi `download_integrity_mismatch`/7’dir. Seviye yazılan baytın beklentiyle bağını anlatır; sağlayıcıda saklanan nesnenin özgünlüğü, lisansı veya model uygunluğu değildir. ETag özet sayılmaz; `transfer_complete`, çerçevenin tam olduğunu söyler.

## Stage ve sidecar protokolü

Hedefle aynı dizinde, hedef adının hash’inden (`<h>`) türeyen sabit uzunluklu dört ad kullanılır: kilit nesnesi `.yorunge-download-<h>.lock`, stage `.yorunge-download-<h>.part`, sidecar `.yorunge-download-<h>.json` ve sidecar tmp `.yorunge-download-<h>.json.tmp`; bütün işlemler `dir_fd`’ye göredir. **Tek yazıcıyı kilit nesnesi sağlar, stage değil:** stage silinip yeniden yaratılsa da (atma ve sıfırlama yolları) kilit sahibi değişmez. Sahiplik denetimi (her mevcut dosya için): `lstat` (`follow_symlinks=False`) ile normal dosya, uid’i mevcut kullanıcı, kip 0600, `nlink==1`; açılış `O_NOFOLLOW|O_NONBLOCK`; açılış sonrası fstat aynı denetimden ve `lstat` ile device/inode eşleşmesinden geçer. Sidecar ek olarak ≤4 KiB ve şema çözümü ister; stage varsa sidecar’ın `stage_device/stage_inode` değeri stage’le eşleşmelidir. Denetimi geçmeyen dosya örtük silinmez veya değiştirilmez.

**Kapalı sıra** (P02-3l kabulünün oracle’ıdır; her adımdaki kesinti bir sonraki koşuda elle silme gerektirmeden çözülür):

1. Hedef parent’ı mevcut ve no-follow olmalı (aksi `download_target_invalid`).
2. Kilit nesnesi `lstat`: yoksa `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600 + `fchmod(0600)` (`EEXIST` yarışı bu adımı “mevcut” koluyla yeniden çalıştırır); varsa sahiplik denetimi + `O_RDWR|O_NOFOLLOW|O_NONBLOCK` açılışı.
3. `flock(LOCK_EX|LOCK_NB)`: meşgulse `download_busy`, hiçbir şey silinmez. Kilit alınınca fstat–lstat kimlik eşleşmesi doğrulanır; eşleşmezse (bitirmekte olan süreç nesneyi silmiş) kilit bırakılır ve 2. adım en çok üç kez yeniden denenir, sonra `download_busy`.
4. **Kilit altında:** hedef varsa `download_output_exists`; ondan önce hedefle aynı device/inode’lu (`nlink==2`) sahipliği kanıtlı stage — link sonrası/unlink öncesi kesinti izi — varsa stage, sidecar ve tmp sırasıyla silinir.
5. Stage `lstat`: yoksa `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600 + `fchmod(0600)` (kilit altında `EEXIST` yabancı dosya demektir → mevcut-stage koluna döner); varsa sahiplik denetimi + `O_RDWR|O_NOFOLLOW|O_NONBLOCK` açılışı + fstat yeniden denetimi.
6. Kalıntı sidecar tmp silinir (sahiplik ✓), sidecar yüklenip sahiplik denetimine sokulur ve başlangıç tablosu karar verir (kesme/atma bu adımdadır; `ENOENT` tolere edilir).
7. Tam-stage ise 11. adıma geçilir (ağ yok); değilse JSON çağrısı ve imzalı GET.
8. Kabul edilen `200`/`206` başlıkları: sıfırlama gerekiyorsa `ftruncate(0)`; **başlık checkpoint’i** (ETag, toplam, `committed_bytes`) ilk gövde baytından önce yazılır.
9. Gövde: ≤1 MiB blok; her 8 MiB’da stage `os.fsync`, sonra hash `copy()` ile checkpoint (tmp `O_EXCL|O_NOFOLLOW` 0600 → fsync → `os.replace` → dizin fsync). **Temiz durma** (SIGINT, Task iptali, taşıma veya zaman aşımı hatası) ve güçlü ETag + toplam biliniyorsa: stage `os.fsync` → checkpoint → çıkış (stage tutulur); bilinmiyorsa stage atılır. SIGKILL’de son checkpoint’ten sonraki baytlar (ilk 8 MiB’ta tüm ilerleme) yeniden indirilir.
10. Gövde bitince bayt eşliği, stage `os.fsync` ve **tamamlanma checkpoint’i** (`committed_bytes == total_size`; chunked gövdede `total_size` burada kesinleşen bayt sayısına sabitlenir); bundan sonraki I/O veya zaman aşımı hatası stage’i atmaz.
11. Beklenti karşılaştırması: uyuşmazlıkta stage, sidecar ve tmp silinir (`download_integrity_mismatch`).
12. `full_sync`, parent/stage kimliği son denetimi, exclusive `link()`; kesin `EEXIST` → stage ve sidecar silinir, `download_output_exists`; kimlik değişmişse `download_write_failed`; link başladıktan sonraki belirsizlik `download_write_uncertain`.
13. Stage `unlink` → sidecar `unlink` → varsa tmp → dizin `fsync` → hedef kimliği denetimi → **kilit nesnesi `unlink`** (en son dosya sistemi değişikliği) → kilit fd’si kapanır.

Atma yolları (206 uyumsuz, 416, ETag/kimlik farkı) kilit altında stage → sidecar → tmp sırasıyla siler ve 5. adımdan temiz başlar; kilit nesnesi değişmez. Her çıkış yolu (başarı, hata, iptal) 13. adımın kilit nesnesi silmesini uygular (kalan yarım içerik yalnız stage/sidecar’dır); SIGKILL kilit nesnesini bırakabilir ve sonraki koşu onu yeniden kullanır. Yayın adımları (10–13) yerel I/O’dur ve indirme deadline’ından muaftır; iptal ve link sonrası belirsizlik kuralları manifest yayıncısıyla aynıdır. macOS’ta kalıcılık süreç öldürme dayanıklılığıdır, güç kesintisi değil. `prefix_sha256` tam olarak fsync edilen baytların özetidir (checkpoint anında hash `copy()`’si).

| Başlangıç durumu | Karar |
|---|---|
| Kilit alınamadı | `download_busy` (hiçbir şey silinmez) |
| Hedef var | `download_output_exists`; yalnız hedefle aynı device/inode’lu (`nlink==2`) sahipliği kanıtlı stage varsa stage ve sidecar önce silinir |
| Stage yok, sidecar yok | Temiz başla (stage `O_EXCL` yaratılır) |
| Stage yok, sidecar var — sidecar sahipliği ✓ (normal dosya, uid, 0600, `nlink==1`, ≤4 KiB, şema ✓) | Sidecar atılır, temiz başla |
| Stage yok, sidecar var — sahiplik ✗ | `download_partial_unverified` (dokunulmaz) |
| Kalıntı sidecar tmp (sahiplik ✓) | Silinir |
| Stage boş + sahiplik ✓, sidecar yok | Yeniden kullan (stage açılışı–ilk sidecar penceresi) |
| Stage dolu, sidecar yok/bozuk | `download_partial_unverified`; `--no-resume` yalnız sahiplik ✓ ise stage’i (ve varsa sidecar/tmp) siler |
| Stage/sidecar/tmp/kilit nesnesi sahiplik denetimini geçmiyor veya FIFO/aygıt/symlink | `download_partial_unverified` (hiçbir şey silinmez, `--no-resume` dahil) |
| Stage+sidecar ✓, resume koşulları sağlanıyor | Devam (ön ek yeniden hash’lenir ve `prefix_sha256` ile karşılaştırılır) veya tam-stage satırı |
| Stage+sidecar ✓, koşullar sağlanmıyor (kimlik anahtarı, ETag, boyut, ön ek özeti) | Yarım içerik atılır (stage, sonra sidecar), temiz başla |
| Yayında kesin EEXIST (`link`) | Sahipliği kanıtlı stage ve sidecar silinir (stage önce); `download_output_exists` |

**Yarım dosya yalnız güçlü ETag ve toplam boyut ikisi de bilinirse tutulur**; aksi halde (sidecar `etag=null` veya `total_size=null`) hata/iptalde silinir. **Tamamlanmış** stage (`committed_bytes == total_size`) ETag’siz ve chunked kaynaklı da olsa tutulur. Beklenen özet uyuşmazlığında stage tutulmaz.

`DownloadPartial v1` alanları: `schema_version=1`, `kind=download_partial`, `identity_key` (tüketici tanımlı kararlı anahtar: normalize edilmiş Platform origin’i + `api_base_path` + model sürümü kimliği + biçim + isteğe bağlı `fold`), `target_hash`, `etag` (güçlü veya null), `total_size` (null olabilir; chunked gövdede yalnız başarılı terminasyondan sonraki tamamlanma checkpoint’inde kesinleşen bayt sayısı), `committed_bytes` (fsync edilmiş), `prefix_sha256` (o bayt sayısına kadar ön ekin SHA-256’sı), `stage_device`, `stage_inode`, `created_at`, `updated_at`.

## Sonuç ve hatalar

Başarı DTO’su (taslak): `schema_version=1`, `kind=download_summary`, `output_path`, `bytes`, `sha256`, `verification_level`, `expectation_source`, `resumed`, `resumed_from_bytes`, kaynak (`model_version`, kimlik, biçim, `fold`). Metin/JSON/NDJSON Result v1 zarfını korur; ilerleme yalnız TTY stderr’dedir.

| Kod | Exit | Tetik |
|---|---:|---|
| `download_target_invalid` | 2 | Parent yok/no-follow değil/kontrol-bidi karakter/uzunluk, boş ad |
| `download_output_exists` | 2 | Hedef var veya yayın yarışında oluştu; hedefe dokunulmaz (yalnız kendi yayınımızın artığı olan stage/sidecar temizlenir) |
| `download_partial_unverified` | 2 | Yarım indirme izi (stage, sidecar, tmp veya kilit nesnesi) doğrulanamadı; hiçbir dosyaya dokunulmadı. Mesaj sabittir: dosya adı taşımaz, hedef dizindeki `.yorunge-download-` dosyalarını incelemeyi veya başka hedef seçmeyi önerir |
| `download_busy` | 2 | Aynı hedef için başka bir indirme sürüyor (kilit nesnesinin kilidi alınamadı); hiçbir dosyaya dokunulmadı (`config_busy` emsali) |
| `download_limit_exceeded` | 2 | Content-Length veya gövde 1 GiB’ı aştı |
| `download_integrity_mismatch` | 7 | Beklenen özet eşleşmedi; hedef yok, stage ve sidecar silinir (yeniden çalıştırma baştan indirir). Kapalı ayrıntı: `computed_sha256`, `bytes` (`ManifestMismatch` emsali; düz kod `details={}` korur) |
| `download_incomplete` | 1 | Gövde fazında çerçeve/Content-Length tamamlanmadan kesildi; yarım dosya koşula göre korunur |
| `download_write_failed` | 2 | Stage/yazma/sync/disk hatası veya stage/parent kimliğinin yayın öncesi değişmesi |
| `download_write_uncertain` | 5 | Link çağrısı başladıktan sonra sonuç/kalıcılık kesinleşmedi; hedefi inceleyin, otomatik tekrar yok |

Mesajlar sabittir ve `details={}` korunur (tek istisna `download_integrity_mismatch`): dosya adı, yol, URL, ETag veya sağlayıcı gövdesi hiçbir hatada yer almaz. Erişim, lisans veya şart engeli `remote_access_denied`/3’tür ve kullanıcı adına kabul edilmez.

## Saf sözleşme (P02-3j)

Bu belgedeki seviye, değer, kayıt, ad ve tablo kuralları `domain/download.py`, `domain/download_response.py` ve `domain/download_state.py` içinde saf (G/Ç, saat ve rastgelelik olmadan) uygulanmıştır; ağ (P02-3k), yerel yazıcı (P02-3l), motor (P02-3m) ve komut (P02-3n) sonraki kartlardadır.

- **Değerler.** `--fold` 0–1024, `--timeout` 30–3600 ve `--sha256` 64 küçük harf hex tam biçimde ayrıştırılır (işaret, boşluk, ondalık, öndeki sıfır, ASCII dışı rakam, bool ve büyük harf reddedilir) ve `invalid_request` verir.
- **Seviyeler.** `verify_expectation(hesaplanan, bayt, beklenen)`: beklenti yoksa `transfer_complete`/`none`, eşitse `sha256_matched`/`user_supplied`, farklıysa `DownloadIntegrityMismatch` (yalnız `computed_sha256` ve `bytes`; beklenen özet yankılanmaz). `DownloadSummary` aynı tutarlılığı doğrular (seviye kendi beklenti türüyle; `resumed` sayaçları).
- **Sidecar.** `DownloadPartial v1`: canonical bayt (sıralı anahtar, boşluksuz, ASCII), ≤4 KiB; `decode` yalnız tam canonical baytları kabul eder (ek/eksik alan, bool/int karışımı, kopya anahtar, boşluk ve anahtar sırası farkı reddedilir). `committed_bytes ≤ total_size`; hiç bayt işlenmediyse `prefix_sha256` boş özettir; ETag yalnız güçlü ve boş olmayan etikettir (1–126 yazdırılabilir ASCII, boşluk dışında). `identity_key` hizmet hedefini (origin ve API kökü), kaynağı, biçimi ve `fold`u kapsar (`identity_key(...)`, sha256).
- **Adlar.** `<h>` = `sha256("yorunge-download-target-v1\0" + ad)` özetinin ilk 32 hex’idir; dört ad `.lock`, `.part`, `.json` için 55 ve `.json.tmp` için 59 karakterdir. Hedef adı bayt bayt hashlenir: büyük/küçük harf ve normalize farkları katlanmaz (bu tür dosya sistemlerinde aynı dosyanın iki yazımı iki ayrı ad kümesi üretir; hedefin exclusive `link`i birini kazanan yapar). `.yorunge-download-` ile başlayan, kontrol ya da biçim (bidi) karakteri içeren, 255 bayttan uzun ya da `.`, `..`, `/`, NUL içeren ad `download_target_invalid`dir.
- **Yanıt.** `parse_response(durum, başlıklar)` 200/206/416 için tipli `DownloadResponse` verir; tablo dışı her yanıt kapalı kodunu verir. `Content-Range` yalnız tek, toplamı bilinen `bytes a-b/T` biçimidir (birim büyük/küçük harfe duyarsız, tek boşluk; işaret, öndeki sıfır, çoklu aralık ve bilinmeyen toplam (`*`) kullanılamaz: aralık yok sayılır); ETag yalnız tek, tırnaklı güçlü etikettir (zayıf, boş, çoklu alan → etiket yok); çerçeve tek `Content-Length` ya da yalnız `chunked`dir (ikisi ya da hiçbiri, tekrarlı alan → `invalid_response`); 1 GiB’ı aşan uzunluk bayt yazılmadan `download_limit_exceeded`. `disposition(yanıt, ask)` → `full | restart | continue | discard_and_retry`; Range’siz isteğe `206`/`416` `invalid_response`. `request_headers(ask)` yalnız `Range` ve `If-Range`i verir. Gövde fazı: `check_written`, `check_body_end` ve `body_failure` (kopma `download_incomplete`, ortak taşımanın gövde fazındaki `invalid_response`i `download_limit_exceeded`, zaman aşımı kendi kodunu korur).
- **Başlangıç tablosu.** `decide_start(...)` bu belgenin tablosunun tek fonksiyonudur: girdi kilit durumu (`held`, `busy`, `unowned`), hedef, stage, sidecar (dosya ve çözülmüş kayıt), sidecar tmp, kimlik anahtarı, hedef hash’i ve `--no-resume`; çıktı eylem (`busy`, `output_exists`, `unverified`, `start_clean`, `reuse_empty_stage`, `resume`, `publish_complete`), kilit altında silinecekler (her zaman stage, sidecar, tmp sırasıyla ve yalnız var olan ve sahipliği kanıtlı olanlar), kesilecek uzunluk ve devam isteği. Kilit alınmadıkça hiçbir silme kararı çıkmaz; sahipliği kanıtlanamayan hiçbir iz silinmez (`--no-resume` dahil); `--no-resume` hiçbir zaman devam ya da yayın kararı vermez. `resume` ve `publish_complete` kararı, çağıranın stage’in kayıtlı ön ekini yeniden hashleyip `confirm_prefix`ten geçirmesiyle kesinleşir; uyuşmayan ön ek stage ve sidecar silinerek temiz başlatılır. Sidecar’ı stage’in device/inode’una uymayan bir iz doğrulanmamıştır (`--no-resume` sahipliği kanıtlı ikisini de siler). Hiç bayt işlenmemiş sidecar devam ettirilmez; tamamlanmış sıfır baytlık stage ağsız yayımlanır.

## İmzalı GET taşıması (P02-3k)

`application/download_transport.py` ile `TransferHttpxTransport.open_download` ve `TransferSession.download`: `DownloadTarget` ADR-0025’in direct hedef kurallarını yeniden kullanır (HTTPS/443, ham query baytları korunur, ≤16 KiB, userinfo/fragment/nokta parçası/çift kodlama reddi, tek önceden bilinen origin ve tüketici yol öneki; son kullanma zamanı aranmaz) ve kapalı `DownloadRequest` yalnız `Range: bytes=N-` ile güçlü ETag’li `If-Range`i taşır (taşıma `Host` ve `Accept-Encoding: identity` ekler; kimlik, cookie, redirect, proxy yok; hazırlanan tel isteği tarif edilenle bire bir eşit olmalıdır). Taşıma tek fiziksel GET yapar (yeniden deneme yok), yanıtı P02-3j’nin `parse_response` ve `disposition` işlevleriyle tipler ve tablo dışı her yanıtı gövdesini okumadan kapalı koduna çevirir. Gövde `chunks()` ile gelir; bitişte `check_body_end` uygulanır (kısa gövde, kopma ve eksik chunked terminasyonu `download_incomplete`; gövde fazında boyut aşımı `download_limit_exceeded`; zaman aşımı `transport_timeout`); 416’nın okunacak gövdesi yoktur. GET penceresi çağıranın tek mutlak deadline’ıdır (PUT’un 120 s sınırı yoktur); servis, PUT ve indirme aynı iki slotluk havuzu ve aynı DNS/public-IP/peer korumasını paylaşır. Adres, anahtar ve sağlayıcı gövdesi hata, log ve repr’e girmez. Bu bölüm taşımayı anlatır: yerel yazıcı P02-3l’de, motor P02-3m’dedir.
