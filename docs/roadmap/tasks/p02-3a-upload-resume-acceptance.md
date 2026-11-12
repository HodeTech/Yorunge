---
id: P02-3a
phase: P02
status: in_review
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

Alt kartlar d–i ve r; [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06). Canlı kabul için kullanıcı yetkisi (hedef owner/proje, azami istek/byte, **kalan private veri setinin sahibi — silme yolu yoktur**) gerekir; yetki verilmezse canlı kabul yapılmış gibi yazılmaz ve karar kayda geçer.

## Sözleşme ve uygulama sınırı

Kanonik sözleşme [continuation sözleşmesi](../../reference/dataset-upload-continuation.md); kullanım rehberi `upload-workflows.md`; gerçek durum `current.md` ve yetenek matrisidir. Bu kart ikinci sözleşme tanımlamaz.

## Kabul

1. Alt kartlar verified; her biri ikişer fresh review turuyla kapanmış.
2. Kurulu wheel/sdist ve altı temiz kurulumda `resume`/`approve` yardımı ve ağsız/yerel kapıları çalışır. Karar: continuation için **ek native ölçüm yapılmaz**; PUT akışı aynı koddur ve ek yükler (tam kök hash’i, ≤1.024 item envanter okuması) mevcut dataset hash ölçümü ve items okuma bütçeleriyle kapsanır, gerekçe kabul kaydına yazılır. Son kaynak M5 referans serisi ve üç ortam CI epik kapanışına aittir (plan adım 17, onaylanan hatlar için); bu kartın kabulü ona bağlı değildir, böylece kısmi onayda bu kart başka bir hattın ölçümünü beklemez.
3. Yetkili küçük canlı kabul: gerçek kesintiden sonra aynı dataset’te devam, N-dosya metadata proof, iki distinct SHA-256; ikinci create yok; authority/pricing/remote-bytes iddiası yok. Kabul, dolu veri setindeki confirm `actual_count` anlamını (kümülatif `taban+k+1` mi, yalnız-işlem `k+1` mi) kanıt kaydına yazar; ikisine de uymayan bir değer görülürse ADR-0031 §5 oracle kararı yeniden açılır. Yapılmazsa kullanıcı kararı ve kısıt kayıtlıdır; bu durumda oracle anlamı “doğrulanmadı” olarak kalır.
4. Belge kontrolü, rehber kontrolü ve kanıt arşivi doğrulaması temiz; v1/v2 geçmişi ve golden’ları değişmemiş.

## Doğrulama

Hedefli ve tam test paketi, kurulum/dağıtım denetimi, belge/rehber/kanıt kontrolleri, canlı kabul raporu (yetki varsa). Çalıştırılmayan kontrol başarılı gösterilmez.

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: alt kartların commit’leri ilgili kartlarında; bu kartın kendi değişiklikleri belge güncellemeleridir.
- Sonuç: Alt kartlar (P02-3d, e, f, t, g, u, v, r, h, w, y, x, i) `verified` ve her biri iki fresh yorumcu turuyla kapandı; `resume`/`approve` yardımı ve ağsız/yerel kapıları kurulu wheel ve sdist’te çalışır (`resume_smoke`; P02-3z, `installation_v4`); v1/v2 geçmişi ve golden’lar değişmedi; continuation için ek native ölçüm yapılmaz (karar kartta). Kullanıcı belgeleri, referans, yetenek matrisi ve rehber gerçek duruma göre güncel. Tam paket: 12.716 geçti, 1 atlandı, 0 düştü (`9ab9d6a`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Altı temiz kurulum (wheel ve sdist × üç CI hücresi) ve üç ortam CI yalnız PR aşamasında görülebilir; **yetkili canlı kabul yapılmadı** (K6b: gerçek kesintiden sonra aynı dataset’te devam, `actual_count` anlamı) — oracle anlamı “doğrulanmadı” kalır; son kaynak M5 referans serisi: `p02-3-reference-{startup,jobs,datasets,raw,upload,download}-4` kod `9ab9d6a`’de dondurulduktan sonra kişisiz kökte bir kez alındı, altısı da ilk denemede geçti ve beş kaynak bağlı doğrulayıcıdan geçti (indirme: 12 süreç `accepted`, en uzun 3,07 s, U ≤ 2.473.984 bayt, G ≤ 1.015.808 bayt); ayrıntı araştırma kaydındadır.
