---
id: P02-3c
phase: P02
status: draft
size: M
depends_on: [P02-3q]
capabilities: [C04, C13]
---
# P02-3c — Veri sürümü referansı bütünleşik kabulü

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md). Üst kart: p–q alt kartlarının bütünleşik kabulü ve teslim kaydı. **Boyut notu:** özgün L tahmini alt kartlara bölündüğünden doğrulama aracı büyük kartın verified olmasını reddeder, üst kart yalnız kabul/teslim kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı Platform’da dondurulmuş bir veri sürümünü ve bölme sayımlarını görür, değişmez referansa bağlar ve sapmayı sonradan denetler; P03-1 bu referansı tüketebilir.

## Giren ve girmeyen kapsam

p–q alt kartlarının verified olması; ADR-0033 acceptance listesi; kurulu yolculuk; belgeler; kalıcı kanıt saklama; ayrı yetkili salt okuma canlı kabulü girer. Sürüm oluşturma/freeze (P02-R4), üyelik iddiası, eğitim bağı ve sağlayıcı değişmezlik garantisi girmez.

## Bağımlılıklar ve kararlar

Alt kartlar p–q; [ADR-0033](../../decisions/0033-dataset-version-references.md) Accepted. Canlı salt okuma kabulü için kullanıcının dondurulmuş sürümlü bir dataset kimliği ve sınırlı GET yetkisi gerekir; yoksa canlı kabul yapılmış gibi yazılmaz ve karar kayda geçer.

## Sözleşme ve uygulama sınırı

Kanonik sözleşme [sürüm referansı sözleşmesi](../../reference/dataset-versions.md); gerçek durum `current.md` ve yetenek matrisidir.

## Kabul

1. Alt kartlar verified ve ikişer fresh turla kapanmış.
2. Üç ortam CI ve kurulu smoke geçer.
3. Yetkili canlı salt okuma kabulü (sınırlı GET sayısı, receipt): `list`/`show`/`bind`/`check` gerçek hesapta tutarlı; yapılmadıysa kısıt kayıtlı.
4. Belgeler, yetenek matrisi (C04) ve P03-1 bağımlılığı doğru durumu gösterir.

## Doğrulama

Hedefli ve tam test paketi, belge/rehber/kanıt kontrolleri, canlı kabul raporu (yetki varsa).

## Teslim kaydı

Draft; uygulama ve kabul kaydı yoktur.
