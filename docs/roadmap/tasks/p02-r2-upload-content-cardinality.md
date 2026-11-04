---
id: P02-R2
phase: P02
status: draft
size: M
depends_on: [P02-2b]
capabilities: [C03, C12, C13]
---
# P02-R2 — Aynı içerikli dosya adlarının uzak çokluğu

**Tarih:** 2026-11-04. **Sahip:** P02 / datasets modülü. [ADR-0028](../../decisions/0028-platform-upload-content-cardinality.md) Proposed; bu kart ihtiyacı görünür tutar, kabul daraltması veya uygulama yetkisi değildir.

## Kullanıcı sonucu ve mevcut eksik

Manifestte farklı adlarla kayıtlı aynı içerikli dosyalar uzak dataset’te de ayrı ad/item olarak bulunur. [Gerçek r4](../../research/p02-2-implementation-validation.md#4-kasım--r4-aynı-içerik-kardinalitesi-engeli), skip_dedup=true rağmen üçüncü confirm’de created=0/batch_duplicates=1 döndürdü. Bu, bugünkü pozitif kabulü kapatmaz; bütün sağlayıcı varyantları hakkında genel iddia değildir.

## Giren ve girmeyen kapsam

Desteklenen sağlayıcı wire/sürüm/semantik araştırması, ad/hash/cardinality eşliği, strict consumer ve ayrıca yetkili küçük canlı kabul girer. Sessiz skip/rename, yanlış hash, ZIP/import fallback, eski unknown isteği yeniden gönderme veya sağlayıcıya izinsiz mesaj gönderme girmez.

## Bağımlılıklar ve kararlar

P02-2b bounded temel yolu ve gerçek sağlayıcı çözümü gerekir. Resmî düzeltme/sözleşme veya aynı anlamı kapatan izinli deney olmadan ready değildir. ADR-0028 reddedilirse özgün P02-2c olumlu kabulü bu ihtiyaca bağlı kalır. Onaylanırsa ilk teslimden ayrılan takip işidir; ihtiyacın tamamlandığı anlamına gelmez.

## Sözleşme ve uygulama sınırı

Manifest v1 dosya kimliği değişmez. Olası çözüm mevcut durable stage/receipt/tek-deneme/ad-hash eşliğiyle karşılaştırılır; farklı batch/receipt modeli gerekiyorsa koddan önce kullanıcı kararı alınır. Yetki/fiyat/metadata ayrımı korunur.

## Kabul

1. Aynı hash/farklı adlar desteklenen açık wire ile ayrı item’lara dönüşür; tüm ad/size/SHA ve ayrı item-ID’leri eşleşir.
2. Yanlış duplicate/created sayacı, eksik item veya response kaybı başarı sayılmaz; yeni effect/replay yoktur.
3. Uygunluğun yeniden açılması eski terminal/digest/DDL/golden’ları bozmaz; global capability/auth kanıtı üretilmez.
4. İki fresh review turu, anlamlı TLS/süreç testleri ve önceden sınırlanmış gerçek olumlu kabul olmadan erken-ret kuralı kaldırılmaz.

## Doğrulama

Önce kaynak/gerçek gözlem ayrımı; sonra dar kod/test ve provider oracle’ı. Her deneyde hedef/proje, request/byte/süre/maliyet/stop koşulları önce yazılır. Eski deneme başlatılmaz; sır/hesap JSON’u yayımlanmaz.

## Teslim kaydı

Draft; çözüm veya pozitif canlı kabul yoktur. P02-2’nin ret/unknown gözlemi bu ihtiyacı kapatmaz.
