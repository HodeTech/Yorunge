---
id: P02-3k
phase: P02
status: draft
size: M
depends_on: [P02-3j, P02-2f]
capabilities: [C03]
---
# P02-3k — İmzalı URL için kimliksiz, akışlı GET taşıması

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 10. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) §2; ADR-0025’in kısmi değişikliği.

## Kullanıcı sonucu ve mevcut eksik

Mevcut storage portu yalnız PUT yapar ve 64 KiB yanıtla sınırlıdır; hizmet HTTP yolu imzalı query’yi yeniden kodlar ve DNS/public-IP korumasından geçmez. İmzalı bir model URL’sini kimlik göndermeden, güvenle ve akışlı okumanın tipli yolu yoktur.

## Giren ve girmeyen kapsam

Private `DownloadTarget` ve kapalı başlıklı `StorageGetRequest`; ortak `TransferSession` üzerinde `open_download`; durum yorumu (200/206/416 için P02-3j’deki tipli `DownloadResponse`; hizmet görünümünün yalnız-2xx kapısı yeniden kullanılmaz; diğerleri kontrollü hata); Content-Length/chunked şartı ve tavan ön kontrolü; koşan sayaç taşımasının **yalnız gövde fazında** `download_limit_exceeded`a eşlenmesi (başlık fazı `invalid_response` kalır); gövde fazı kopmasının `download_incomplete`a eşlenmesi (zaman aşımı önceliği korunur); PUT penceresinden **bağımsız** GET penceresi (kullanıcı toplamı, 120 s PUT sınırı değişmez); kimlik/cookie/redirect yokluğu; guard uygulaması; literal-secret taraması girer. Dosya yazımı, engine, tüketici JSON çağrısı ve CLI girmez.

## Bağımlılıklar ve kararlar

P02-3j tiplerine ve P02-2f storage portuna bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)’nin Accepted olması gerekir (bugün Proposed); ADR-0025’in PUT kuralları (expiry zorunluluğu, header/yanıt sınırı, 120 s) değişmez, yalnız GET hedefi için `expires_at` aranmaz.

## Sözleşme ve uygulama sınırı

`DownloadTarget` ADR-0025 direct hedef kurallarını yeniden kullanır (HTTPS/443, ham query korunur, ≤16 KiB, userinfo/fragment/dot-segment/çift kodlama reddi, tek önceden bilinen origin, tüketici yol öneki — yanıt genişletemez). İstek başlıkları kapalıdır: yalnız `Range: bytes=N-` ve güçlü ETag’li `If-Range`; `Accept-Encoding: identity` taşıma tarafından eklenir. Tek deneme; retry, proxy veya kimlikli fallback yok (protokol dönüşü motor katmanındadır). Servis ve indirme aynı iki slotluk havuzu paylaşır.

## Kabul

1. Gerçek loopback TLS: kimlikli JSON çağrısından sonra aynı origin/aynı bağlantıda indirme isteği `X-API-Key`, Authorization, Cookie taşımaz; Platform ve LLM kimliği hiçbir koşulda eklenmez.
2. Kapalı başlık kümesi dışındaki her başlık, zayıf ETag ve çoklu aralık ağdan önce reddedilir; hazırlanan wire hedefi/headers descriptor’la eşit olmalıdır.
3. İstek sayımı: imzalı URL’ye en çok iki GET; bağlantı JSON çağrısı ayrı sayılır (ADR-0017). 3xx takip edilmez; Content-Encoding ≠ identity gövde okunmadan reddedilir; Content-Length ve chunked yokken kapanışla sınırlanan gövde reddedilir; tutarsız Content-Length/aşım hem ön kontrolle hem koşan sayaçla yakalanır ve `download_limit_exceeded` olur; 416 tipli sonuç olarak döner.
4. Yavaş/duran gövde faz ve toplam deadline ile durur (GET penceresi 120 s PUT sınırına takılmaz); iptal cleanup sonrası yayılır; private/karışık DNS ve peer uyuşmazlığı HTTP baytından önce reddedilir.
5. URL ham baytları korunur: **query’de** `%2F`/`%2B`/`%3D` geçerli, **path’te** `%2F` ve `%2e%2e` ret; 16 KiB aşımı ve literal-secret içeren URL parçaları reddedilir; URL/query hata, log ve repr’e girmez.
6. Mevcut PUT taşıma testleri ve ADR-0025 kabulü değiştirilmeden geçer.

## Doğrulama

Gerçek TLS/guard integration testleri, mevcut storage testleri, Ruff ve strict mypy. Yazıcı ve engine davranışı P02-3l/3m’dedir.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
