# Akışlı indirme motoru ve model ağırlığı indirme

**Durum:** Taslak sözleşme — [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, DTO ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek, sağlayıcı garantisi, ücret/lisans bilgisi veya dataset bayt erişimi değildir. Bu belge indirme hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

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
| Sidecar+stage tamam (`committed_bytes == total_size`) ve ön ek özeti eşleşiyor | **Hiçbir ağ isteği yapılmaz (JSON çağrısı dahil)**; beklenti karşılaştırması ve yayın doğrudan (`resumed=true`, `resumed_from_bytes=T`). Sağlayıcıda nesnenin hâlâ aynı olduğunu iddia etmez |
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

Stage `.yorunge-download-<hedef adının hash’i>.part`, sidecar aynı önekle `.json` (tmp: `.json.tmp`)dir; hepsi hedefle aynı dizindedir ve bütün işlemler `dir_fd`’ye göredir. Stage sahipliği; normal dosya, uid, 0600, `nlink==1` ve device/inode’un sidecar’la eşleşmesiyle kanıtlanır. Denetimi geçmeyen dosya örtük silinmez veya değiştirilmez.

**Kapalı sıra** (P02-3l kabulünün oracle’ıdır; her adımdaki kesinti bir sonraki koşuda elle silme gerektirmeden çözülür):

1. Hedef denetimi: parent mevcut ve no-follow; hedef varsa `download_output_exists` (hedefle aynı device/inode’lu, `nlink==2`, sahipliği kanıtlı stage — link sonrası/unlink öncesi kesinti izi — varsa önce stage, sonra sidecar silinir).
2. Stage `lstat` (`follow_symlinks=False`): yoksa `O_CREAT|O_EXCL|O_NOFOLLOW|O_RDWR` 0600 + `fchmod(0600)` (umask’tan bağımsız; `EEXIST` yarışı bu adımı “mevcut stage” koluyla yeniden çalıştırır); varsa normal dosya/uid/0600/`nlink==1` denetlenir, `O_RDWR|O_NOFOLLOW|O_NONBLOCK` (`O_CREAT` yok) açılır ve fstat aynı denetimden ve `lstat` eşleşmesinden geçer.
3. `flock(LOCK_EX|LOCK_NB)`; meşgulse `download_busy`, hiçbir şey silinmez.
4. **Kilit alındıktan sonra:** kalıntı sidecar tmp silinir, sidecar yüklenip denetlenir, başlangıç tablosu karar verir (kesme/atma bu adımdadır; `ENOENT` tolere edilir).
5. Tam-stage ise 9. adıma geçilir (ağ yok); değilse JSON çağrısı ve imzalı GET.
6. Kabul edilen `200`/`206` başlıkları: sıfırlama gerekiyorsa `ftruncate(0)`; **başlık checkpoint’i** (ETag, toplam, `committed_bytes`) ilk gövde baytından önce yazılır.
7. Gövde: ≤1 MiB blok; her 8 MiB’da stage `os.fsync`, sonra hash `copy()` ile checkpoint (tmp `O_EXCL|O_NOFOLLOW` 0600 → fsync → `os.replace` → dizin fsync).
8. Gövde bitince bayt eşliği, stage `os.fsync` ve **tamamlanma checkpoint’i** (`committed_bytes == total_size`); bundan sonraki I/O veya zaman aşımı hatası stage’i atmaz.
9. Beklenti karşılaştırması: uyuşmazlıkta stage ve sidecar silinir (`download_integrity_mismatch`).
10. `full_sync`, parent/stage kimliği son denetimi, exclusive `link()`; kesin `EEXIST` → stage ve sidecar silinir, `download_output_exists`; stage/parent kimliği değişmişse `download_write_failed`, link başladıktan sonraki belirsizlik `download_write_uncertain`.
11. Stage `unlink` → sidecar `unlink` → varsa tmp → dizin `fsync` → hedef kimliği denetimi.

Atma/silme sırası her yerde stage → sidecar → tmp → dizin `fsync`’tir; en kötü kesinti “stage yok, sidecar var” izi bırakır ve o iz bir sonraki koşuda atılır (kalıcı takılma yok). Yayın adımları (8–11) yerel I/O’dur ve indirme deadline’ından muaftır; iptal ve link sonrası belirsizlik kuralları manifest yayıncısıyla aynıdır. macOS’ta kalıcılık süreç öldürme dayanıklılığıdır, güç kesintisi değil. `prefix_sha256` tam olarak fsync edilen baytların özetidir (checkpoint anında hash `copy()`’si).

| Başlangıç durumu | Karar |
|---|---|
| Hedef var | `download_output_exists`; yalnız hedefle aynı device/inode’lu (`nlink==2`) sahipliği kanıtlı stage varsa (link sonrası/unlink öncesi kesinti izi) stage ve sidecar önce silinir |
| Stage yok, sidecar yok | Temiz başla (stage `O_EXCL` yaratılır; `EEXIST` yarışı “mevcut stage” koluna döner) |
| Stage yok, sidecar var (sahiplik ✓) | Stage yaratılıp kilitlendikten sonra sidecar atılır, temiz başla |
| Kalıntı sidecar tmp (sahiplik ✓) | Kilit alındıktan sonra silinir |
| Stage boş + sahiplik ✓, sidecar yok | Yeniden kullan (stage açılışı–ilk sidecar penceresi) |
| Stage dolu, sidecar yok/bozuk | `download_partial_unverified`; `--no-resume` yalnız sahiplik ✓ ve kilit alınabiliyorsa stage’i (ve varsa sidecar/tmp) siler |
| Stage/sidecar/tmp sahiplik denetimini geçmiyor veya FIFO/aygıt/symlink | `download_partial_unverified` (hiçbir şey silinmez, `--no-resume` dahil) |
| Stage kilitli (başka süreç) | `download_busy` (hiçbir şey silinmez) |
| Stage+sidecar ✓, resume koşulları sağlanıyor | Devam (ön ek yeniden hash’lenir ve `prefix_sha256` ile karşılaştırılır) veya tam-stage satırı |
| Stage+sidecar ✓, koşullar sağlanmıyor (ETag yok/farklı, boyut farkı, ön ek özeti uyuşmuyor) | Yarım içerik atılır (stage, sonra sidecar), temiz başla |
| Yayında kesin EEXIST (`link`) | Sahipliği kanıtlı stage ve sidecar silinir (stage önce); `download_output_exists` |

**Yarım dosya yalnız güçlü ETag ve toplam boyut ikisi de bilinirse tutulur**; aksi halde (sidecar `etag=null` veya `total_size=null`) hata/iptalde silinir. Beklenen özet uyuşmazlığında stage tutulmaz.

`DownloadPartial v1` alanları: `schema_version=1`, `kind=download_partial`, `identity_key` (tüketici tanımlı kararlı anahtar: model sürümü + biçim + isteğe bağlı `fold`), `target_hash`, `etag` (güçlü veya null), `total_size` (veya null), `committed_bytes` (fsync edilmiş), `prefix_sha256` (o bayt sayısına kadar ön ekin SHA-256’sı), `stage_device`, `stage_inode`, `created_at`, `updated_at`.

## Sonuç ve hatalar

Başarı DTO’su (taslak): `schema_version=1`, `kind=download_summary`, `output_path`, `bytes`, `sha256`, `verification_level`, `expectation_source`, `resumed`, `resumed_from_bytes`, kaynak (`model_version`, kimlik, biçim, `fold`). Metin/JSON/NDJSON Result v1 zarfını korur; ilerleme yalnız TTY stderr’dedir.

| Kod | Exit | Tetik |
|---|---:|---|
| `download_target_invalid` | 2 | Parent yok/no-follow değil/kontrol-bidi karakter/uzunluk, boş ad |
| `download_output_exists` | 2 | Hedef var veya yayın yarışında oluştu; hedefe dokunulmaz (yalnız kendi yayınımızın artığı olan stage/sidecar temizlenir) |
| `download_partial_unverified` | 2 | Yarım indirme izi doğrulanamadı; hiçbir dosyaya dokunulmadı. Mesaj sabittir: dosya adı taşımaz, hedef dizindeki `.yorunge-download-` dosyalarını incelemeyi veya başka hedef seçmeyi önerir |
| `download_busy` | 2 | Aynı hedef için başka bir indirme sürüyor (stage kilidi alınamadı); hiçbir dosyaya dokunulmadı (`config_busy` emsali) |
| `download_limit_exceeded` | 2 | Content-Length veya gövde 1 GiB’ı aştı |
| `download_integrity_mismatch` | 7 | Beklenen özet eşleşmedi; hedef yok, stage ve sidecar silinir (yeniden çalıştırma baştan indirir). Kapalı ayrıntı: `computed_sha256`, `bytes` (`ManifestMismatch` emsali; düz kod `details={}` korur) |
| `download_incomplete` | 1 | Gövde fazında çerçeve/Content-Length tamamlanmadan kesildi; yarım dosya koşula göre korunur |
| `download_write_failed` | 2 | Stage/yazma/sync/disk hatası veya stage/parent kimliğinin yayın öncesi değişmesi |
| `download_write_uncertain` | 5 | Link çağrısı başladıktan sonra sonuç/kalıcılık kesinleşmedi; hedefi inceleyin, otomatik tekrar yok |

Mesajlar sabittir ve `details={}` korunur (tek istisna `download_integrity_mismatch`): dosya adı, yol, URL, ETag veya sağlayıcı gövdesi hiçbir hatada yer almaz. Erişim, lisans veya şart engeli `remote_access_denied`/3’tür ve kullanıcı adına kabul edilmez.
