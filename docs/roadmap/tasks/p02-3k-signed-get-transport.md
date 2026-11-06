---
id: P02-3k
phase: P02
status: draft
size: M
depends_on: [P02-3j]
capabilities: [C03]
---
# P02-3k — İmzalı URL için kimliksiz, akışlı GET taşıması

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 8. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)#2; ADR-0025’in kısmi değişikliği.

## Kullanıcı sonucu ve mevcut eksik

Mevcut storage portu yalnız PUT yapar ve 64 KiB yanıtla sınırlıdır; hizmet HTTP yolu imzalı query’yi yeniden kodlar ve DNS/public-IP korumasından geçmez. İmzalı bir model URL’sini kimlik göndermeden, güvenle ve akışlı okumanın tipli yolu yoktur.

## Giren ve girmeyen kapsam

Private `DownloadTarget` ve kapalı başlıklı `StorageGetRequest`; ortak `TransferSession` üzerinde `open_download`; durum yorumu (200/206/416 tipli sonuç, diğerleri kontrollü hata); Content-Length/tavan ön kontrolü; yapılandırılabilir toplam süre; kimlik/cookie/redirect yokluğu; guard uygulaması; literal-secret taraması girer. Dosya yazımı, engine, tüketici JSON çağrısı ve CLI girmez.

## Bağımlılıklar ve kararlar

P02-3j tiplerine bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) onayı gerekir; ADR-0025’in PUT kuralları (expiry zorunluluğu, header/yanıt sınırı) değişmez, yalnız GET hedefi için `expires_at` aranmaz.

## Sözleşme ve uygulama sınırı

`DownloadTarget` ADR-0025 direct hedef kurallarını yeniden kullanır (HTTPS/443, ham query korunur, ≤16 KiB, userinfo/fragment/dot-segment/çift kodlama reddi, tek önceden bilinen origin, tüketici yol öneki). İstek başlıkları kapalıdır: yalnız `Range: bytes=N-` ve güçlü ETag’li `If-Range`; `Accept-Encoding: identity` taşıma tarafından eklenir. Tek deneme; retry, proxy veya kimlikli fallback yok. Servis ve indirme aynı iki slotluk havuzu paylaşır.

## Kabul

1. Gerçek loopback TLS: kimlikli JSON çağrısından sonra aynı origin/aynı bağlantıda indirme isteği `X-API-Key`, Authorization, Cookie taşımaz; Platform ve LLM kimliği hiçbir koşulda eklenmez.
2. Kapalı başlık kümesi dışındaki her başlık, zayıf ETag ve çoklu aralık ağdan önce reddedilir; hazırlanan wire hedefi/headers descriptor’la eşit olmalıdır.
3. 3xx takip edilmez; Content-Encoding ≠ identity gövde okunmadan reddedilir; tutarsız Content-Length/aşım hem ön kontrolle hem koşan sayaçla yakalanır; 416 tipli sonuç olarak döner.
4. Yavaş/duran gövde faz ve toplam deadline ile durur; iptal cleanup sonrası yayılır; private/karışık DNS ve peer uyuşmazlığı HTTP baytından önce reddedilir.
5. URL ham baytları korunur (`%2F` geçerli, `%2e%2e` path’te ret), 16 KiB aşımı ve literal-secret içeren URL parçaları reddedilir; URL/query hata, log ve repr’e girmez.
6. Mevcut PUT taşıma testleri ve ADR-0025 kabulü değiştirilmeden geçer.

## Doğrulama

Gerçek TLS/guard integration testleri, mevcut storage testleri, Ruff ve strict mypy. Yazıcı ve engine davranışı P02-3l/3m’dedir.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
