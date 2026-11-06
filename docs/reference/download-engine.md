# Akışlı indirme motoru ve model ağırlığı indirme

**Durum:** Taslak sözleşme — [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, DTO ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek, sağlayıcı garantisi, ücret/lisans bilgisi veya dataset bayt erişimi değildir. Bu belge indirme hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

## Planlanan yüzey

```text
yorunge models download --version-id UUID --format onnx|pt|tflite [--fold N] --weights-out FILE
    [--sha256 HEX64] [--timeout SECONDS] [--no-resume]
    [--config FILE] [--profile NAME] [--state-dir PATH]
```

Python karşılığı aynı kullanım senaryosuna bağlı tek API’dir. `--version-id` kesin model sürümü kimliğidir; kullanıcı onu Platform arayüzündeki model sürümü sayfasından alır (katalog çözümü P02-4’tedir), ilk sürüm otomatik seçilmez, ad/slug çözülmez. `--format` zorunludur (sağlayıcı varsayılanı tahmin edilmez). `--fold` yalnız k-fold sürümlerinde sağlayıcı istemcisinin gönderdiği isteğe bağlı parametredir; 0–1024 kesin tamsayıdır (`+`/boşluk/ondalık yok), verilirse iletilir ve kimlik anahtarına girer. `--timeout` 30–3600 tamsayı saniyedir (varsayılan 900). `--weights-out` açık, mevcut parent içinde yeni bir dosya adıdır (genel `--output text|json|ndjson` yalnız çıktı biçimini seçer; hedef dosya için kullanılmaz). `--sha256` kullanıcının bağımsız beklenen özetidir (64 küçük harf hex). Anahtar argüman değildir; yalnız JSON bağlantı çağrısında Platform kimliği kullanılır.

## Motor sınırı

| Sınır | Kural |
|---|---|
| Boyut | En çok 1 GiB (ortak ham HTTP sınırı); Content-Length bilinen ve aşan gövde bayt yazılmadan reddedilir; gövde sırasında koşan sayaç da tavanı uygular (ortak taşımanın gövde fazındaki `invalid_response`i indirme görünümünde `download_limit_exceeded`a eşlenir; başlık fazı ihlalleri `invalid_response` kalır) |
| Çerçeve | Yanıt `Content-Length` veya chunked terminasyonu taşımalıdır; kapanışla sınırlanan gövde (ikisi de yok) `invalid_response`. Chunked ise toplam bilinmez: resume sunulmaz, ilerleme toplamsızdır |
| Yazma | Tek akış, en çok 1 MiB blok, async görevde `os.write`; executor/thread, bütün dosya buffer’ı ve ikinci kuyruk yok |
| Süre | JSON çağrısı ayrı 30 s kontrol bütçesi; ardından tek mutlak indirme deadline’ı: varsayılan 900 s, kullanıcı 30–3600 s; connect/write/read 5 s, pool 1 s. GET penceresi PUT penceresinin 120 s sınırından bağımsızdır; yarım dosya ön ek hash’i bu deadline içindedir |
| Deneme | Hata sonrası otomatik tekrar, kimlikli fallback ve proxy yok; devam yalnız kullanıcı komutu yeniden çalıştırınca. İmzalı URL’ye en çok iki GET: ilk istek + (resume uygulanmazsa) bir Range’siz protokol dönüşü. Bağlantı JSON çağrısı ayrıdır ve ADR-0017 salt okuma politikasıyla en çok iki deneme alır |
| İstek başlıkları | Kapalı: `Range: bytes=N-` ve güçlü ETag’li `If-Range`. Başka başlık, `W/` ETag, `Last-Modified`, `If-Match` yok |
| Hedef | HTTPS/443, imzalı query ham baytlarıyla korunur, ≤16 KiB; kimlik/cookie/redirect/proxy yok; DNS/public-IP/peer koruması; origin tek ve önceden bilinir; yol öneki tüketici sabitidir (model: `{api_base_path}/files/evren-models/`; canlı yoklamada gözlenen tam önekten türetilir) ve yanıt onu genişletemez; query’de `%2F`/`%2B`/`%3D` geçerli, path’te `%2F` ve `%2e%2e` ret |
| Taşıma çıktısı | GET taşıması tipli bir yanıt döndürür (durum ∈ {200,206,416}, ayrıştırılmış `Content-Range`, güçlü ETag veya yok, çerçeve türü); motor ham header’a dokunmaz. Hizmet görünümünün yalnız-2xx kapısı yeniden kullanılmaz |
| Sidecar | ≤4 KiB, 0600; imzalı URL/sır/yol içermez |

## Yanıt işleme (kapalı tablo)

| Durum | Sonuç |
|---|---|
| Sidecar+stage tamam (`committed_bytes == total_size`) ve ön ek özeti eşleşiyor | **GET yapılmaz**; beklenti karşılaştırması ve yayın doğrudan (`resumed=true`, `resumed_from_bytes=T`). Sağlayıcıda nesnenin hâlâ aynı olduğunu iddia etmez |
| `200`, Range’siz istek | Tam gövde; `Content-Length` (veya chunked terminasyonu) zorunlu |
| `200`, Range’li istek | Sağlayıcı aralığı uygulamadı: stage ve sidecar sıfırlanır, aynı yanıttan baştan yazılır (ek istek yok) |
| `206` + tam `Content-Range: bytes N-(T-1)/T`, N = fsync edilmiş ön ek, T = kayıtlı toplam, aynı güçlü ETag, `Content-Length = T-N` | Devam |
| `206` ETag/`Content-Range`/`Content-Length` uyumsuz veya eksik, `416` | Stage ve sidecar **önce atılır**; sonra bir Range’siz istek |
| `206`, Range göndermeyen isteğe | `invalid_response`, hedef yok |
| Diğer 2xx, 3xx, Content-Encoding ≠ identity | Kontrollü ret, hedef yok |
| 401/403 | `remote_access_denied`/3; kimlikle yeniden denemek yok |
| 429/5xx/timeout/taşıma (gövde öncesi) | Mevcut `remote_rate_limited`/`remote_failed`/`transport_*`; yarım dosya koşullara göre korunur |
| Gövde fazında kopma, EOF ile yazılan < Content-Length veya eksik chunked terminasyonu | `download_incomplete`/1 (`transport_timeout` önceliğini korur) |

## Doğrulama seviyeleri

`transfer_complete` < `sha256_matched`. Her sonuç yazılan bayt, hesaplanan SHA-256, seviye ve `expectation_source` taşır; bugün yalnız `none` ve `user_supplied` üretilir (`size_matched` seviyesi ve `provider_metadata`/`local_manifest` kaynakları, onları üretecek bir tüketici gelince eklenir). Beklenen özet uyuşmazlığı yayın öncesi `download_integrity_mismatch`/7’dir. Seviye yazılan baytın beklentiyle bağını anlatır; sağlayıcıda saklanan nesnenin özgünlüğü, lisansı veya model uygunluğu değildir. ETag özet sayılmaz; `transfer_complete`, çerçevenin tam olduğunu söyler.

## Stage ve sidecar protokolü

Stage `.yorunge-download-<hedef adının hash’i>.part`, sidecar aynı önekle `.json` (tmp: `.json.tmp`)dir; hepsi hedefle aynı dizindedir ve bütün işlemler `dir_fd`’ye göredir. Mevcut dosya açılmadan önce `lstat` (`follow_symlinks=False`) ile normal dosya, uid’i mevcut kullanıcı, kipi 0600 ve `nlink==1` denetlenir; açılış `O_NONBLOCK|O_NOFOLLOW` ile yapılır ve fstat kimliği `lstat` ile eşleşmelidir. İlk koşuda stage `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600 açılır, ardından sidecar yazılır (tmp `O_EXCL|O_NOFOLLOW` 0600, fsync, `os.replace`, dizin fsync); devam koşusunda stage `O_RDWR|O_NOFOLLOW|O_NONBLOCK` (`O_CREAT` yok) açılır, ön ek aynı fd’den okunur, `ftruncate` aynı fd’de yapılır. Stage fd’sinde indirme boyunca `flock(LOCK_EX|LOCK_NB)` tutulur (`os.replace` kilidi bozmaz). Stage sahipliği; normal dosya, uid, 0600, `nlink==1` ve device/inode’un sidecar’la eşleşmesiyle kanıtlanır. Sidecar checkpoint’i her 8 MiB’da ve temiz durmada, stage `os.fsync`’inden sonra yapılır; kalıcı yayın `full_sync` kullanır (macOS’ta süreç öldürme dayanıklılığı, güç kesintisi değil). Artımlı SHA-256 checkpoint’te `copy()` ile alınır; `prefix_sha256` tam olarak fsync edilen baytların özetidir.

| Başlangıç durumu | Karar |
|---|---|
| Stage yok, sidecar yok | Temiz başla |
| Stage yok, sidecar var (sahiplik ✓) | Sidecar atılır, temiz başla |
| Sahiplik ✓ kalıntı sidecar tmp | İlk checkpoint öncesi silinir |
| Stage boş + sahiplik ✓, sidecar yok | Yeniden kullan (ilk açılış–ilk sidecar penceresi) |
| Stage dolu, sidecar yok/bozuk | `download_partial_unverified` (hiçbir şey silinmez; dosya adı gösterilir) |
| Stage/sidecar/tmp sahiplik denetimini geçmiyor veya FIFO/aygıt/symlink | `download_partial_unverified` |
| Stage kilitli (başka süreç) | `download_write_failed` (“başka indirme sürüyor”) |
| Stage+sidecar ✓, resume koşulları sağlanıyor | Devam (ön ek yeniden hash’lenir ve `prefix_sha256` ile karşılaştırılır) veya tam-stage satırı |
| Stage+sidecar ✓, koşullar sağlanmıyor (ETag yok/farklı, boyut farkı, ön ek özeti uyuşmuyor) | Yarım içerik atılır, temiz başla |
| Yayında kesin EEXIST (`link`) | Sahipliği kanıtlı stage ve sidecar silinir; `download_output_exists` |

`--no-resume`, yarım içeriği yalnız sahipliği kanıtlanmış stage/sidecar/tmp için siler; aksi durumda `download_partial_unverified` kalır. **Yarım dosya yalnız güçlü ETag ve toplam boyut ikisi de bilinirse tutulur**; aksi halde (sidecar `etag=null` veya `total_size=null`) hata/iptalde silinir.

`DownloadPartial v1` alanları: `schema_version=1`, `kind=download_partial`, `identity_key` (tüketici tanımlı kararlı anahtar: model sürümü + biçim + isteğe bağlı `fold`), `target_hash`, `etag` (güçlü veya null), `total_size` (veya null), `committed_bytes` (fsync edilmiş), `prefix_sha256` (o bayt sayısına kadar ön ekin SHA-256’sı), `stage_device`, `stage_inode`, `created_at`, `updated_at`.

## Sonuç ve hatalar

Başarı DTO’su (taslak): `schema_version=1`, `kind=download_summary`, `output_path`, `bytes`, `sha256`, `verification_level`, `expectation_source`, `resumed`, `resumed_from_bytes`, kaynak (`model_version`, kimlik, biçim, `fold`). Metin/JSON/NDJSON Result v1 zarfını korur; ilerleme yalnız TTY stderr’dedir.

| Kod | Exit | Tetik |
|---|---:|---|
| `download_target_invalid` | 2 | Parent yok/no-follow değil/kontrol-bidi karakter/uzunluk, boş ad |
| `download_output_exists` | 2 | Hedef var veya yayın yarışında oluştu; hedefe dokunulmaz |
| `download_partial_unverified` | 2 | Yarım indirme izi doğrulanamadı; hiçbir dosyaya dokunulmadı, dosya adı gösterilir |
| `download_limit_exceeded` | 2 | Content-Length veya gövde 1 GiB’ı aştı |
| `download_integrity_mismatch` | 7 | Beklenen özet eşleşmedi; hedef yok |
| `download_incomplete` | 1 | Gövde fazında çerçeve/Content-Length tamamlanmadan kesildi; yarım dosya koşula göre korunur |
| `download_write_failed` | 2 | Stage/yazma/sync/disk hatası veya başka indirme sürüyor (yayın öncesi) |
| `download_write_uncertain` | 5 | Link çağrısı başladıktan sonra sonuç/kalıcılık kesinleşmedi; hedefi inceleyin, otomatik tekrar yok |

Erişim, lisans veya şart engeli `remote_access_denied`/3’tür ve kullanıcı adına kabul edilmez.
