---
id: P02-3e
phase: P02
status: draft
size: M
depends_on: [P02-3d]
capabilities: [C03, C12]
---
# P02-3e — Resume kanıt sınıflandırıcısı ve uzak envanter indirgeyicisi

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 2. [ADR-0031](../../decisions/0031-upload-continuation.md) kanıt sınıfları; yerel kalıcılık, plan ve yazma yok.

## Kullanıcı sonucu ve mevcut eksik

Kesintiden sonra kullanıcı, hangi dosyanın gerçekten uzakta olduğunu, hangisinin gönderilmesinin güvenli olduğunu ve hangisinin kanıtsız belirsiz kaldığını söyleyecek tek, deterministik bir sınıflandırmaya sahip değildir. Mevcut salt okuma yolu envanteri toplam eşleşmezse hata verir ve dosya bazlı present/missing/conflict kümesi döndürmez.

## Giren ve girmeyen kapsam

Kaynak journal’ının dosya başına özetini (intent/accepted makbuz var mı; makbuz içeriği dışarı çıkmaz) ve tam, sayfalı, kapalı sınırlı uzak envanteri alıp kapalı sınıflara (`confirmed`, `observed`, `pending_clean`, `pending_uncertain`, `drift_missing`, `conflict`) ve plan düzeyi engellere indirgeyen saf mantık, canonical `classification_digest` ve `inventory_digest` girer. Mevcut items okuyucusunun yanında non-raising bir indirgeyici ve repository’de salt okuma journal özeti girer. Plan/onay tipi, kalıcı yazı, HTTP bileşimi, CLI/API ve continuation yürütmesi girmez.

## Bağımlılıklar ve kararlar

P02-3d belirtimine bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) sınıf tablosu ve güvenlik gerekçesi onaylanmadan başlamaz. Fazla item sınırı (örn. üst sınır aşılırsa engel) kartta sabitlenir ve sessizce kesilmez.

## Sözleşme ve uygulama sınırı

Sınıflandırma, [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) içindeki kapalı karar tablosunun birebir uygulamasıdır. Giriş: manifest sırası, dosya başına journal durumu, uzak item kümesi (ad, boyut, nullable sha256, tekil kimlik). Çıkış: dosya→sınıf vektörü, sayaçlar, plan düzeyi engeller (`drift_missing`, `conflict`, `extra_remote`, `inventory_unreliable`, `inventory_too_large`), iki canonical özet. Özetler item kimliği ve sağlayıcı zamanını içermez.

## Kabul

1. Tablonun bütün (journal × uzak) hücreleri ayrı beklenen sonuçla sınanır; sınıf, sayaç ve özetler bağımsız elle hesaplanmış vektörlerle eşleşir (üreticinin kendi çıktısı tek oracle değildir).
2. Saldırgan envanterler: kopya kimlik, aynı ad farklı boyut/SHA, aynı SHA başka ad, fazladan item, `total` uyuşmazlığı, cursor döngüsü, null/yanlış tipli sha256, boyut aşımı; hiçbiri `confirmed`/`observed`/`pending_clean` üretmez ve veri kesilmez.
3. Sıralama ve özet deterministiktir; item kimliği/sıra/zaman değişimi özeti değiştirmez, ad/boyut/SHA değişimi değiştirir.
4. Journal özeti makbuz içeriğini, anahtarı, URL’yi veya `created_dataset` alanlarını dışarı vermez; salt okuma hiçbir yazı/lease/permit üretmez.

## Doğrulama

Unit/contract/integration (gerçek SQLite journal fixture’ları + loopback TLS items sunucusu), Ruff ve strict mypy. HTTP bileşimi sonraki dilimdedir; burada ağ bütçesi iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
