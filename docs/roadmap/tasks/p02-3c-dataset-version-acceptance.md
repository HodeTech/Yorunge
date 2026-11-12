---
id: P02-3c
phase: P02
status: in_review
size: M
depends_on: [P02-3q]
capabilities: [C04, C13]
---
# P02-3c — Veri sürümü referansı bütünleşik kabulü

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md). Üst kart: p–q alt kartlarının bütünleşik kabulü ve teslim kaydı. **Boyut notu:** özgün L tahmini alt kartlara bölündüğünden doğrulama aracı büyük (L) kartı ready/in_progress/in_review/verified yapmaz; bu üst kart yalnız bütünleşik kabul/teslim kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı Platform’da dondurulmuş bir veri sürümünü ve bölme sayımlarını görür, değişmez referansa bağlar ve sapmayı sonradan denetler; P03-1 bu referansı tüketebilir.

## Giren ve girmeyen kapsam

p–q alt kartlarının verified olması; ADR-0033 acceptance listesi; kurulu yolculuk; belgeler; kalıcı kanıt saklama; ayrı yetkili salt okuma canlı kabulü girer. Sürüm oluşturma/freeze (P02-R4), üyelik iddiası, eğitim bağı ve sağlayıcı değişmezlik garantisi girmez.

## Bağımlılıklar ve kararlar

Alt kartlar p–q; [ADR-0033](../../decisions/0033-dataset-version-references.md) Accepted’dir (2026-11-06). Canlı salt okuma kabulü için kullanıcının dondurulmuş sürümlü bir dataset kimliği ve sınırlı GET yetkisi gerekir; yoksa canlı kabul yapılmış gibi yazılmaz ve karar kayda geçer.

## Sözleşme ve uygulama sınırı

Kanonik sözleşme [sürüm referansı sözleşmesi](../../reference/dataset-versions.md); gerçek durum `current.md` ve yetenek matrisidir.

## Kabul

1. Alt kartlar verified ve ikişer fresh turla kapanmış.
2. Üç ortam CI ve kurulu smoke geçer.
3. Yetkili canlı salt okuma kabulü (sınırlı GET sayısı, receipt): `list`/`show`/`bind`/`check` gerçek hesapta tutarlı; yapılmadıysa kısıt kayıtlı. **Canlı yoklama listesi** (offline fixture yeşili bunların hiçbirini kanıtlamaz; her madde gözlenip kaydedilir ya da “yapılmadı” kalır): (1) sağlayıcı zamanları bölge taşıyor mu (`Z`/`±SS:DD`) ve `T` ayırıcısı kullanıyor mu — değilse bütün yanıtlar `invalid_response` olur (ilk madde); (2) sınıfsız bir sürümde `class_labels_snapshot` `[]` mı `null` mu — `null` ise `show`/`bind`/`check` hepsi başarısız olur; (3) `meta.{page, page_size, total, has_next}` anlamı: varsayılan sayfa boyutu ≤ 100 mü, `page` parametresi uygulanıyor mu, son sayfanın ötesi 200 ve boş mu (404 `remote_failed` olur), tam dolu son sayfada `has_next`; (4) sürüm detayının 404’ü ne demek — silinmiş sürüm, başka veri seti ya da yetkinin gizlediği veri seti; yetkisiz anahtarda 404 mü 403 mü (404 ise başka projenin anahtarıyla `check` bir bütünlük hatası, `dataset_version_missing`/7, olur); (5) `is_frozen` ve `is_partial` anlamları ve 100 satırlık sayfanın (uzun açıklamalarla) 1 MiB altında kalması; (6) etiket `id` türleri (tamsayı/dize) ve bir sürümün sınıf sayısı (4096 sınırı).
4. Belgeler, yetenek matrisi (C04) ve P03-1 bağımlılığı doğru durumu gösterir.

## Doğrulama

Hedefli ve tam test paketi, belge/rehber/kanıt kontrolleri, canlı kabul raporu (yetki varsa).

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: alt kartların commit’leri ilgili kartlarında; bu kartın kendi değişiklikleri belge güncellemeleridir.
- Sonuç: Alt kartlar (P02-3p, q) `verified` ve her biri iki fresh yorumcu turuyla kapandı; `datasets versions list|show|bind|check` salt okuma sürüm/bölme referansını ve bağ artifact’ını verir; kurulu `versions_smoke` (wheel ve sdist) yerelde geçti. Tam paket: 12.721 geçti, 1 atlandı, 0 düştü (`1b2cc1f`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Üç ortam CI PR aşamasında görülür; **yetkili canlı salt okuma kabulü yapılmadı** (K6c: kullanıcının dataset kimliği ve yetkisi sağlanmadı) — sağlayıcı zamanının bölge taşıması, `class_labels_snapshot` null/[] ayrımı, sayfa davranışı ve 404’ün anlamı canlı doğrulanmadı; sürüm oluşturma/freeze P02-R4’te kalır.
