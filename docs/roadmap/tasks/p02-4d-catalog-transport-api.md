---
id: P02-4d
phase: P02
status: verified
size: M
depends_on: [P02-4c, P01-5a, P02-0c, P02-0d]
capabilities: [C01, C05, C13]
---
# P02-4d — Katalog okuma taşıması ve Python API

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md) adım 2; [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted (Karar 1–2, 5–7, 10).

## Kullanıcı sonucu ve mevcut eksik

Uygulama geliştiricisi `yorunge.api` üzerinden Platform modellerini/sürümlerini/veri setlerini ve LLM model listesini, ağ hatalarında kontrollü sonuçla ve sınırları aşmadan okuyabilir. Planlama anında katalog için ağ adaptörü ve public API yoktur.

## Giren ve girmeyen kapsam

**Girer:**

- Platform GET’leri (`X-API-Key`): `api/v1/models` (tek sayfa), `api/v1/models/{owner}/{slug}`, `api/v1/models/{model_id}/versions`, `api/v1/datasets` (tek sayfa; `scope=owned` isteği gönderilir, etiket K4 teyidine kadar `unknown`).
- LLM GET’leri (`Authorization: Bearer`): `v1/models`, `v1/models/{model_id}`.
- Kayıtlı hedef: P01/P02-0 bağlamındaki origin ve API kökü; yönlendirme izlenmez.
- P02-4c’nin okuma, tamlık ve çözüm kuralları; yanıt sınırı 1 MiB; katalog süre bütçesi 30 s.
- Yerel anahtar: `--config`/`--profile` ile seçilen veya aktif profilden tek anlık okuma (`models download` ile aynı kaynak); state yazılmaz, veri tabanı açılmaz, kimlik doğrulama iddiası kurulmaz.
- `api.py` fonksiyonları: model listesi (Platform/LLM), model detayı, sürüm listesi (`owner/slug` veya `model_id` ile), veri seti listesi, çözüm yardımcısı (`owner/slug` + `version_tag`; P02-4f kullanır). Dönüşler tipli `Result` zarfında; sır taşımaz.
- Kapsam: `--project` katalog API’sinde yoktur; profil `project` tercihi katalog kapsamına uygulanmaz.

**Girmez:** CLI biçimlendirme (P02-4e), canlı çağrı kaydı (P02-4e), kalıcı önbellek, yazma uçları, indirme.

**Dosya önerisi** (uygulanmış sınıf iddiası değildir): `src/yorunge/adapters/catalog_http.py`, `src/yorunge/api.py` katalog fonksiyonları.

## Bağımlılıklar ve kararlar

[P02-4c](p02-4c-catalog-contract.md) sözleşmesi ve dar codec’leri; P01-5a ortak taşıma; P02-0c/0d yerel anahtar ve hedef normalizasyonu. Sır ve ağ sınırı için [güvenlik standardı](../../standards/security.md) bağlayıcıdır.

## Sözleşme ve uygulama sınırı

- Her istek tek `HttpRequest` ile kayıtlı hedefe gider; `read_only=true`; bayt sınırı ve süre bütçesi istekten önce belirlenir.
- Yeniden deneme ([ADR-0017](../../decisions/0017-bounded-http-transport.md) ve [taşıma referansı](../../reference/http-transport.md#retry-ve-hata)): yalnız salt okuma GET’i en çok iki deneme alır. 408, 429, 502, 503, 504 ve geçici bağlantı hataları retry adayıdır; diğer 4xx ve 5xx yeniden denenmez. Yanıt verisi tüketiciye verildikten sonra yeniden deneme yapılmaz.
- Hata eşlemesi: 401/403 `remote_access_denied` (çıkış 3); 404 çözümde `model_not_visible` (çıkış 1); 422 `invalid_request` (çıkış 2); 429 `remote_rate_limited` (çıkış 1); diğer kabul edilmeyen durum kodları `remote_failed` (çıkış 1); zaman aşımı `transport_timeout`. Hata metninde sır, ham gövde veya adres yoktur.
- Yönlendirme (3xx) hata olarak döner; ikinci istek yapılmaz.
- Sayfa isteği `page` ve `page_size` değerlerini tam sayı olarak gönderir; `page_size` 1–100 aralığındadır; yanıt P02-4c’deki sayfa kuralıyla doğrulanır.
- Her komut için istek sayısı sabittir: liste 1, detay 1, `model_id` ile sürüm listesi 1, `--versions` ile detay 2, veri seti listesi 1; liste satırlarından detay üretilmez (N+1 yok).

## Kabul

1. Loopback TLS sahte Platform ve LLM sunucuları: doğru başlık (`X-API-Key` yalnız Platform, `Authorization` yalnız LLM); yanlış hedefe sıfır istek; yönlendirmede ikinci istek yok.
2. İstek sayımı: her komut için tam sayı kanıtı; sayfa kuralı ihlali (sunucu sayfa boyutunu düşürdüğünde dahil) `invalid_response`; tek sayfa dışında istek yok.
3. Yanıt 1 MiB ve LLM 500 kayıt sınırında kırpma yok; aşımda kontrollü `invalid_response`.
4. Yeniden deneme: 408, 429, 502, 503, 504 ve geçici bağlantı hatası en çok bir kez yeniden denenir (toplam iki deneme); 401/403/404 ve diğer 4xx/5xx yeniden denenmez; iki denemeden fazlası yok.
5. Hata eşlemesi tablodaki sınıflarla birebir; 422 `invalid_request` ve yanıt gövdesi yansıtılmaz.
6. Sızıntı sentinel: anahtar değeri istek dışı hiçbir çıktı, hata ayrıntısı veya günlükte yoktur; ham yanıtın tüm ağacında literal-secret taraması çalışır.
7. Adres kuralları: alfabe dışı veya `.`/`..` argüman `invalid_request` ve sıfır ağ isteği; `version_tag` URL’ye girmez.
8. `api.py` dönüşleri aynı typed Result zarfında; kapsam `unknown` ve tamlık alanları doğru; açık `--project` API’de yoktur.
9. Açık state veya veri tabanı yolu oluşmaz; kök dizinde yeni dosya yoktur.

## Doğrulama

Runtime satırı: integration testleri (loopback TLS), contract/unit testleri, Ruff, strict mypy, `check-docs.py`. Canlı çağrı yoktur. Import grafiği değişirse startup kapısı P02-4e’de ölçülür.

## Teslim kaydı

- PR/commit: [PR #18](https://github.com/HodeTech/Yorunge/pull/18) (`feat/p02-4-catalog-and-selection`, `development` hedefi).
- Sonuç: salt okuma GET taşıması, sınırlar, 422/404 eşlemesi, 30 sn pencere ve Python API (`list_*`, `show_*`, `resolve_*`) uygulandı; loopback TLS ve istek sayımı testleri geçti; bulgular iki turda düzeltildi (2201df9, 99f2020).
- Kalan sınır: model kapsamlı uçların (404 `model_not_visible`) canlı davranışı hesapta model olmadığı için gözlenmedi.
