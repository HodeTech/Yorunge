---
id: P02-3a
phase: P02
status: draft
size: M
depends_on: [P02-3i]
capabilities: [C03, C12, C13]
---
# P02-3a — Etkili resume bütünleşik kabulü

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md). Üst kart: d–i ve r alt kartlarının bütünleşik kabulü ve teslim kaydı; tek kod adımı değildir. **Boyut notu:** özgün L tahmini alt kartlara bölündüğünden doğrulama aracı büyük (L) kartı ready/in_progress/in_review/verified yapmaz; bu üst kart yalnız bütünleşik kabul/teslim kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kesintiye uğrayan private yüklemeyi aynı Platform dataset’inde, yeni create veya DB düzenlemesi olmadan, yalnız kanıtlanmış güvenli adımları göndererek tamamlar ve neyin doğrulandığını görür.

## Giren ve girmeyen kapsam

d–i ve r alt kartlarının verified olması; kurulu paket yolculuğu; ADR-0031 acceptance listesinin tamamı; belge/matris/current/README/changelog gerçek duruma göre; kalıcı kanıt saklama; ayrı yetkili küçük canlı kabul girer. Create ID kaybı sahiplenmesi (P02-R6), kesin retlerin kalıcı makbuzu (P02-R7), aynı SHA farklı ad (P02-R2), dosya ekleme/güncelleme, uzak silme ve yetki/fiyat doğrulaması girmez.

## Bağımlılıklar ve kararlar

Alt kartlar d–i ve r; [ADR-0031](../../decisions/0031-upload-continuation.md)’in Accepted olması gerekir (bugün Proposed). Canlı kabul için kullanıcı yetkisi (hedef owner/proje, azami istek/byte, **kalan private veri setinin sahibi — silme yolu yoktur**) gerekir; yetki verilmezse canlı kabul yapılmış gibi yazılmaz ve karar kayda geçer.

## Sözleşme ve uygulama sınırı

Kanonik sözleşme [continuation sözleşmesi](../../reference/dataset-upload-continuation.md); kullanım rehberi `upload-workflows.md`; gerçek durum `current.md` ve yetenek matrisidir. Bu kart ikinci sözleşme tanımlamaz.

## Kabul

1. Alt kartlar verified; her biri ikişer fresh review turuyla kapanmış.
2. Kurulu wheel/sdist ve altı temiz kurulumda `resume`/`approve` yardımı ve ağsız/yerel kapıları çalışır; upload native ölçümü continuation yolunu aynı kod yolu olarak kapsar (ek ölçüm gereksinimi gerekçeyle belgelenir).
3. Yetkili küçük canlı kabul: gerçek kesintiden sonra aynı dataset’te devam, N-dosya metadata proof, iki distinct SHA-256; ikinci create yok; authority/pricing/remote-bytes iddiası yok. Yapılmazsa kullanıcı kararı ve kısıt kayıtlıdır.
4. Belge kontrolü, rehber kontrolü ve kanıt arşivi doğrulaması temiz; v1/v2 geçmişi ve golden’ları değişmemiş.

## Doğrulama

Hedefli ve tam test paketi, kurulum/dağıtım denetimi, belge/rehber/kanıt kontrolleri, canlı kabul raporu (yetki varsa). Çalıştırılmayan kontrol başarılı gösterilmez.

## Teslim kaydı

Draft; uygulama ve kabul kaydı yoktur.
