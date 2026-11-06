# Akışlı indirme motoru ve model ağırlığı indirme

**Durum:** Taslak sözleşme — [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Komut, DTO ve hata adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek, sağlayıcı garantisi, ücret/lisans bilgisi veya dataset bayt erişimi değildir.

## Planlanan yüzey

```text
yorunge models download --version-id UUID --format onnx|pt|tflite --output FILE
    [--sha256 HEX64] [--timeout SECONDS] [--no-resume]
    [--config FILE] [--profile NAME] [--state-dir PATH]
```

Python karşılığı aynı kullanım senaryosuna bağlı tek API’dir. `--version-id` kesin model sürümü kimliğidir; ilk sürüm otomatik seçilmez, ad/slug çözülmez. `--format` zorunludur (sağlayıcı varsayılanı tahmin edilmez). `--output` açık, mevcut parent içinde yeni bir dosya adıdır. `--sha256` kullanıcının bağımsız beklenen özetidir. Anahtar argüman değildir; yalnız JSON bağlantı çağrısında Platform kimliği kullanılır.

## Motor sınırı

| Sınır | Kural |
|---|---|
| Boyut | En çok 1 GiB (ortak ham HTTP sınırı); Content-Length bilinen ve aşan gövde bayt yazılmadan reddedilir; gövde sırasında koşan sayaç da tavanı uygular |
| Yazma | Tek akış, en çok 1 MiB blok, async görevde `os.write`; executor/thread, bütün dosya buffer’ı ve ikinci kuyruk yok |
| Süre | Toplam varsayılan 900 s, kullanıcı 30–3600 s; connect/write/read 5 s, pool 1 s, tek mutlak deadline; ilk bağlantı çağrısı ayrı 30 s kontrol bütçesidir |
| Deneme | İndirme GET’i tek denemedir; otomatik tekrar, kimlikli fallback ve proxy yok. Devam yalnız kullanıcı komutu yeniden çalıştırınca |
| İstek başlıkları | Kapalı: `Range: bytes=N-` ve güçlü ETag’li `If-Range`. Başka başlık, `W/` ETag, `Last-Modified`, `If-Match` yok |
| Hedef | HTTPS/443, imzalı query ham baytlarıyla korunur, ≤16 KiB; kimlik/cookie/redirect/proxy yok; DNS/public-IP/peer koruması; origin tek ve önceden bilinir; yol öneki `{api_base_path}/files/evren-models/` |
| Sidecar | ≤4 KiB, 0600; imzalı URL/sır/yol içermez |

## Yanıt işleme

| Durum | Sonuç |
|---|---|
| `200` ilk istek veya yarım dosyayı yok sayan yanıt | Tam gövde; varsa stage sıfırlanır ve baştan yazılır |
| `206` + tam `Content-Range: bytes N-(T-1)/T`, N = fsync edilmiş ön ek, T = kayıtlı toplam, aynı güçlü ETag, `Content-Length = T-N` | Devam |
| `416` | Yarım içerik atılır ve istek Range’siz yeniden kurulur (aynı kullanıcı komutu içinde tek ek istek) |
| Diğer 2xx, 3xx, tutarsız Content-Length/Content-Range, Content-Encoding ≠ identity | Kontrollü ret, hedef yok |
| 401/403 | `remote_access_denied`/3; kimlikle yeniden denemek yok |
| 429/5xx/timeout/taşıma | Mevcut `remote_rate_limited`/`remote_failed`/`transport_*`; yarım dosya koşullara göre korunur |

## Doğrulama seviyeleri

`transfer_complete` < `size_matched` < `sha256_matched`. Her sonuç yazılan bayt, hesaplanan SHA-256, seviye ve `expectation_source` (`none|provider_metadata|local_manifest|user_supplied`) taşır. Beklenen boyut/özet uyuşmazlığı yayın öncesi `download_integrity_mismatch`/7’dir. Seviye yazılan baytın beklentiyle bağını anlatır; sağlayıcıda saklanan nesnenin özgünlüğü, lisansı veya model uygunluğu değildir. ETag özet sayılmaz.

## Yarım indirme (DownloadPartial v1)

Stage `.yorunge-download-<hedef-adı-hash’i>.part`, sidecar aynı önekle `.json`dur. Sidecar alanları: `schema_version=1`, `kind=download_partial`, `identity_key` (tüketici tanımlı kararlı anahtar, ör. model sürümü + biçim), `target_hash`, `etag` (güçlü), `total_size`, `committed_bytes`, `stage_device`, `stage_inode`, `created_at`, `updated_at`. Sidecar 8 MiB’da bir ve temiz durmada, stage `fsync`’inden sonra `os.replace` ile yazılır. Resume koşulları ADR-0032 §4’tedir; ETag görülmediyse yarım dosya tutulmaz.

## Sonuç ve hatalar

Başarı DTO’su (taslak): `schema_version=1`, `kind=download_summary`, `output_path`, `bytes`, `sha256`, `verification_level`, `expectation_source`, `resumed`, `resumed_from_bytes`, kaynak (`model_version`, kimlik, biçim). Metin/JSON/NDJSON Result v1 zarfını korur; ilerleme yalnız TTY stderr’dedir.

| Kod | Exit | Tetik |
|---|---:|---|
| `download_target_invalid` | 2 | Parent yok/no-follow değil/kontrol-bidi karakter/uzunluk, boş ad |
| `download_target_exists` | 2 | Hedef var veya yayın yarışında oluştu; dokunulmaz |
| `download_limit_exceeded` | 2 | Content-Length veya gövde 1 GiB’ı aştı |
| `download_integrity_mismatch` | 7 | Beklenen boyut/özet eşleşmedi; hedef yok |
| `download_incomplete` | 1 | Çerçeve/Content-Length tamamlanmadan kesildi; yarım dosya koşula göre korunur |
| `download_write_failed` | 2 | Stage/yazma/sync/disk hatası (yayın öncesi) |
| `download_write_uncertain` | 5 | Link çağrısı başladıktan sonra sonuç/kalıcılık kesinleşmedi; hedefi inceleyin, otomatik tekrar yok |

Erişim, lisans veya şart engeli `remote_access_denied`/3’tür ve kullanıcı adına kabul edilmez. Kanonik hata kataloğu [CLI sözleşmesindedir](cli-contract.md#p01-5-hata-kataloğu); burada ikinci katalog tutulmaz.
