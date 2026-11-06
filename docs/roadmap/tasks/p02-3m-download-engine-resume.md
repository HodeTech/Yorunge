---
id: P02-3m
phase: P02
status: draft
size: M
depends_on: [P02-3k, P02-3l]
capabilities: [C03]
---
# P02-3m — İndirme motoru, resume kararı ve uçtan uca uyumluluk

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 10. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md); taşıma ve yazıcıyı birleştiren uygulama katmanı.

## Kullanıcı sonucu ve mevcut eksik

Taşıma ve yerel yazıcı hazır olsa bile hangi durumda devam edileceği, ne zaman baştan başlanacağı, seviyenin nasıl hesaplanacağı ve hata/iptal önceliği tek bir yerde sınanmış olmalıdır.

## Giren ve girmeyen kapsam

Uygulama katmanı `run_download`: ön kontrol, istek, yanıt sınıflandırması, yazma, resume kararı (kimlik/ETag/boyut/ön ek), beklenti karşılaştırması ve yayın; bounded ilerleme sayacı; iptal/deadline önceliği girer. Model tüketicisi, CLI ve ölçüm araçları girmez.

## Bağımlılıklar ve kararlar

P02-3k ve P02-3l verified olmalıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md)#4 resume koşulları ve ETag/Range kuralları değişmez. Karar gerekmez.

## Sözleşme ve uygulama sınırı

Motor tek akışlı, tek denemelidir; devam yalnız çağrı yeniden başlatıldığında ve koşullar sağlanıyorsa olur. Seviye ve kaynak P02-3j kurallarıyla hesaplanır; uyuşmazlık yayın öncesi 7. Hata sırası: iptal/uncertain önce, sonra yerel yazma, sonra beklenti, sonra uzak. İlerleme yalnız bayt sayısı/toplam taşır; URL, yol, ETag içermez.

## Kabul

Gerçek loopback TLS sunucusunda (Range/ETag/206/416 betiklenebilir) şu matris, her satır için hedefin son durumu ve istek sayısıyla birlikte: tam indirme; kesik → aynı komutla 206 devam; ETag değişti → baştan; 200 yanıtı Range’e → baştan; 416 → baştan; güçlü ETag yok → yarım dosya tutulmaz; yanlış/tutarsız `Content-Range`; toplam değişti; erken kapanış ve kesik chunked; Content-Length uyuşmazlığı; beklenen boyut/SHA uyuşmazlığı → hedef yok; hedef var; `--no-resume` benzeri politika; farklı süreçte kill sonrası devam. Her başarıda bağımsız hashlib oracle’ı eşleşir, devam başarısında ön ek yeniden hash’lenir, bellek sınırlı ve ilerleme birleştirilir.

## Doğrulama

Gerçek TLS + süreç integration testleri, Ruff, strict mypy. Native bellek/süre ölçümü P02-3o’dadır; canlı Platform kabulü P02-3n/3b’dedir.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
