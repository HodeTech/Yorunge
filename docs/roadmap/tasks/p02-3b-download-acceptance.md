---
id: P02-3b
phase: P02
status: in_review
size: M
depends_on: [P02-3o, P02-3z]
capabilities: [C03, C05, C13]
---
# P02-3b — Ortak indirme bütünleşik kabulü

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md). Üst kart: j–o ve z alt kartlarının bütünleşik kabulü ve teslim kaydı. **Boyut notu:** özgün L tahmini alt kartlara bölündüğünden doğrulama aracı büyük (L) kartı ready/in_progress/in_review/verified yapmaz; bu üst kart yalnız bütünleşik kabul/teslim kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kesin model sürümü ağırlığını güvenli ve doğrulama seviyesi görünür biçimde indirir; sağlayıcı güçlü ETag ve Range sunarsa yarım indirme aynı komutla devam eder. Dataset öğesi baytları API anahtarıyla sunulmadığı için upload’ın uzak byte doğrulaması bu kartla kapanmaz; açıkça [P02-R5](p02-r5-dataset-item-byte-access.md)’tedir.

## Giren ve girmeyen kapsam

j–o alt kartlarının verified olması; ADR-0032 acceptance listesi; kurulu yolculuk; belge/matris/current/README/changelog gerçek duruma göre; kalıcı kanıt saklama; ayrı yetkili model indirme kabulü girer. Dataset öğesi indirme, ZIP export, 1 GiB üzeri dosya, oturum JWT’si ve ücret/lisans garantisi girmez.

## Bağımlılıklar ve kararlar

Alt kartlar j–o; [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) Accepted’dir (2026-11-06). Canlı kabul için kullanıcının erişebildiği model sürümü kimliği ve kapsamlı yetki gerekir; verilmezse canlı kabul yapılmış gibi yazılmaz ve karar kayda geçer.

## Sözleşme ve uygulama sınırı

Kanonik sözleşme [indirme motoru sözleşmesi](../../reference/download-engine.md); gerçek durum `current.md` ve yetenek matrisidir. Bu kart ikinci sözleşme tanımlamaz.

## Kabul

1. Alt kartlar verified ve her biri ikişer fresh turla kapanmış.
2. Üç ortam CI’da indirme testleri ve kurulu smoke geçer; native referans kayıtlı ve doğrulanmıştır.
3. Yetkili model indirme kabulü: kimlikli JSON çağrısı + kimliksiz imzalı GET, hedef yayını, seviye çıktısı; yapılmadıysa kısıt kayıtlı. Model yoklaması olumsuzsa (oturum gerekli) bu madde “oturum gerekli” kaydıyla kapanır, yüzeysiz iç tüketici ve kütüphane ölçümü teslim edilir.
4. Upload’ın `remote_bytes_verified=false` sınırı ve P02-R5 görünür kalır; P02-7 faz kabulü bu boşluğu `partial` olarak taşır.

## Doğrulama

Hedefli ve tam test paketi, kurulum/dağıtım denetimi, belge/rehber/kanıt kontrolleri, canlı kabul raporu (yetki varsa).

## Teslim kaydı

- PR/commit: tek development PR’ı ([PR #15](https://github.com/HodeTech/Yorunge/pull/15)) bu daldan açıldı ve incelemededir; adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: alt kartların commit’leri ilgili kartlarında; bu kartın kendi değişiklikleri belge güncellemeleridir.
- Sonuç: Alt kartlar (P02-3j, k, l, m, n, o, z, s) `verified` ve her biri iki fresh yorumcu turuyla kapandı; `models download` kesin model sürümü ağırlığını no-clobber yayınlar, doğrulama seviyesi görünür; kurulu `models download` smoke’u (gerçek CLI indirmesi, wheel ve sdist) yerelde geçti. Tam paket: 12.721 geçti, 1 atlandı, 0 düştü (`1b2cc1f`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Üç ortam CI ve altı kurulum PR aşamasında görülür; **yetkili canlı model indirme kabulü yapılmadı** (K6a: kullanıcının erişebildiği model sürümü kimliği ve yetki sağlanmadı) — JSON şekli ve `/files/evren-models/` öneki çevrimdışı keşiften gelir, doğrulanmadı; dataset öğesi baytları API anahtarıyla indirilemediğinden upload’ın `remote_bytes_verified=false` sınırı ve P02-R5 görünür kalır; native referans: `p02-3-reference-{startup,jobs,datasets,raw,upload,download}-5` kod `1b2cc1f`’de dondurulduktan sonra kişisiz kökte bir kez alındı, altısı da ilk denemede geçti ve beş kaynak bağlı doğrulayıcıdan geçti (indirme: 12 süreç `accepted`, en uzun 3,35 s, U ≤ 2.179.072 bayt, G ≤ 1.146.880 bayt); ayrıntı araştırma kaydındadır.
