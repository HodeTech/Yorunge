---
id: P02-3b
phase: P02
status: draft
size: M
depends_on: [P02-3o]
capabilities: [C03, C05, C13]
---
# P02-3b — Ortak indirme bütünleşik kabulü

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md). Üst kart: j–o alt kartlarının bütünleşik kabulü ve teslim kaydı. **Boyut notu:** özgün L tahmini alt kartlara bölündüğünden doğrulama aracı büyük kartın verified olmasını reddeder, üst kart yalnız kabul/teslim kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kesin model sürümü ağırlığını güvenli ve doğrulama seviyesi görünür biçimde indirir; yarım indirme aynı komutla, koşullar sağlanıyorsa devam eder. Dataset öğesi baytları API anahtarıyla sunulmadığı için upload’ın uzak byte doğrulaması bu kartla kapanmaz; açıkça [P02-R5](p02-r5-dataset-item-byte-access.md)’tedir.

## Giren ve girmeyen kapsam

j–o alt kartlarının verified olması; ADR-0032 acceptance listesi; kurulu yolculuk; belge/matris/current/README/changelog gerçek duruma göre; kalıcı kanıt saklama; ayrı yetkili model indirme kabulü girer. Dataset öğesi indirme, ZIP export, 1 GiB üzeri dosya, oturum JWT’si ve ücret/lisans garantisi girmez.

## Bağımlılıklar ve kararlar

Alt kartlar j–o; [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) Accepted. Canlı kabul için kullanıcının erişebildiği model sürümü kimliği ve kapsamlı yetki gerekir; verilmezse canlı kabul yapılmış gibi yazılmaz ve karar kayda geçer.

## Sözleşme ve uygulama sınırı

Kanonik sözleşme [indirme motoru sözleşmesi](../../reference/download-engine.md); gerçek durum `current.md` ve yetenek matrisidir. Bu kart ikinci sözleşme tanımlamaz.

## Kabul

1. Alt kartlar verified ve her biri ikişer fresh turla kapanmış.
2. Üç ortam CI’da indirme testleri ve kurulu smoke geçer; native referans kayıtlı ve doğrulanmıştır.
3. Yetkili model indirme kabulü: kimlikli JSON çağrısı + kimliksiz imzalı GET, hedef yayını, seviye çıktısı; yapılmadıysa kısıt kayıtlı.
4. Upload’ın `remote_bytes_verified=false` sınırı ve P02-R5 görünür kalır; P02-7 faz kabulü bu boşluğu `partial` olarak taşır.

## Doğrulama

Hedefli ve tam test paketi, kurulum/dağıtım denetimi, belge/rehber/kanıt kontrolleri, canlı kabul raporu (yetki varsa).

## Teslim kaydı

Draft; uygulama ve kabul kaydı yoktur.
