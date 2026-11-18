---
id: P02-4d
phase: P02
status: draft
size: M
depends_on: [P02-4c, P01-5a, P02-0c, P02-0d]
capabilities: [C01, C05, C13]
---
# P02-4d — Katalog okuma taşıması ve Python API

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 2; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) §1–§5, §7.

## Kullanıcı sonucu ve mevcut eksik

Uygulama geliştiricisi `yorunge.api` üzerinden Platform modellerini/sürümlerini/veri setlerini ve LLM model listesini, ağ hatalarında kontrollü sonuçla ve sınırları aşmadan okuyabilir. Bugün katalog için ağ adaptörü ve public API yoktur.

## Giren ve girmeyen kapsam

**Girer:**

- Platform GET’leri (`X-API-Key`): `api/v1/models` (tek sayfa), `api/v1/models/{owner}/{slug}`, `api/v1/models/{model_id}/versions`, `api/v1/datasets` (tek sayfa; K2).
- LLM GET’leri (`Authorization: Bearer`): `v1/models`, `v1/models/{model_id}`.
- Kayıtlı hedef: P01/P02-0 bağlamındaki origin ve API kökü; yönlendirme izlenmez.
- Tek sayfa okuma, P02-4c tamlık ve çözüm kuralları, yanıt sınırı 1 MiB, süre bütçesi 30 s.
- Yerel anahtar: aktif profil ve ortam değişkeni üzerinden tek anlık okuma (`models download` ile aynı kural); state yazılmaz, veri tabanı açılmaz, kimlik doğrulama iddiası kurulmaz.
- `api.py` fonksiyonları: model listesi (Platform/LLM), model detayı, sürüm listesi (`owner/slug` veya `model_id` ile), veri seti listesi. Dönüşler tipli `Result` zarfında; sır taşımaz. Çözüm yardımcısı (`owner/slug` + `version_tag`) P02-4f için bu kartta yazılır.
- Kapsam: `--project` katalog API’sinde yoktur; profil `project` tercihi katalog kapsamına uygulanmaz ve sonuçta kapsam `unknown` gösterilir.

**Girmez:** CLI biçimlendirme (P02-4e), canlı çağrı kaydı (P02-4e), kalıcı önbellek, yazma uçları, indirme.

**Dosya önerisi** (uygulanmış sınıf iddiası değildir): `src/yorunge/adapters/catalog_http.py`, `src/yorunge/api.py` katalog fonksiyonları.

## Bağımlılıklar ve kararlar

[P02-4c](p02-4c-catalog-contract.md) sözleşmesi ve dar codec’leri; P01-5a ortak taşıma; P02-0c/0d yerel anahtar ve hedef normalizasyonu. Kararlar [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) ile sınırlıdır. Sır ve ağ sınırı için [güvenlik standardı](../../standards/security.md) bağlayıcıdır.

## Sözleşme ve uygulama sınırı

- Her istek tek `HttpRequest` ile kayıtlı hedefe gider; `read_only=true`; bayt sınırı ve toplam süre bütçesi istekten önce belirlenir.
- Okuma en çok **iki deneme** yapar (ADR-0017; yalnız salt okuma GET). 401, 403, 404 ve 408/429 dışındaki 4xx yeniden denenmez; 408, 429 ve geçici bağlantı hataları retry adayıdır ([taşıma referansı](../../reference/http-transport.md#retry-ve-hata)). Yanıt gövdesinin verisi tüketiciye verildikten sonra yeniden deneme yapılmaz.
- Sayfa isteği `page` ve `page_size` değerlerini tam sayı olarak gönderir; `page_size` 1–100 aralığındadır ve üst sınır K4 ile teyit edilir.
- Yönlendirme (3xx) hata olarak döner; ikinci istek yapılmaz.
- 401/403 `remote_access_denied` (çıkış 3), 404 çözümde `model_not_visible` (çıkış 1), 429 `remote_rate_limited`, 5xx ve zaman aşımı ayrı kodlarla döner; hata metninde sır, ham gövde veya adres yoktur.
- Her komut için istek sayısı sabittir: liste 1, detay 1, `model_id` ile sürüm listesi 1, `--versions` ile detay 2, veri seti listesi 1; liste satırlarından detay üretilmez (N+1 yok).

## Kabul

1. Loopback TLS sahte Platform ve LLM sunucuları: doğru başlık (`X-API-Key` yalnız Platform, `Authorization` yalnız LLM); yanlış hedefe sıfır istek; yönlendirmede ikinci istek yok.
2. İstek sayımı: her komut için tam sayı kanıtı; tamlık formülü ve başlık tutarsızlığı `invalid_response` veya `unknown` sonucu; tek sayfa dışında istek yok.
3. Yanıt 1 MiB ve LLM 500 kayıt sınırında kırpma yok; aşımda kontrollü `invalid_response`.
4. Zaman aşımı, bağlantı kopması, TLS hatası ve 429 yeniden deneme sayısı ADR-0017 ile tutarlı; 401/403/404 ve diğer 4xx (408/429 hariç) yeniden denenmez; iki denemeden fazlası yok.
5. Sızıntı sentinel: anahtar değeri istek dışı hiçbir çıktı, hata ayrıntısı veya günlükte yoktur; ham yanıtın tüm ağacında literal-secret taraması çalışır.
6. Adres kuralları: `.` ve `..` segmenti, `%`, `/` fazlası ve boşluk I/O öncesi `invalid_request`; hiçbir istek üretilmez.
7. `api.py` dönüşleri aynı typed Result zarfında; kapsam `unknown` ve tamlık alanları doğru.
8. Açık state veya veri tabanı yolu oluşmaz; kök dizinde yeni dosya yoktur.

## Doğrulama

Runtime satırı: integration testleri (loopback TLS), contract/unit testleri, Ruff, strict mypy, `check-docs.py`. Canlı çağrı yoktur. Import grafiği değişirse startup kapısı P02-4e’de ölçülür.

## Teslim kaydı

Hazırlık; uygulama ve kabul kaydı yoktur.
