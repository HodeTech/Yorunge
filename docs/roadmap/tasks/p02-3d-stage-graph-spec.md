---
id: P02-3d
phase: P02
status: verified
size: M
depends_on: [P02-2c]
capabilities: [C03, C12]
---
# P02-3d — Transfer aşama grafiği tek belirtimi ve v2 kill karakterizasyonu

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 1. Önce mevcut v2 yolunun eksik gerçek-kill sınırları karakterizasyon testi olarak eklenir, sonra salt refaktör yapılır; v1/v2 davranışı, byte/digest ve golden’lar değişmez.

## Kullanıcı sonucu ve mevcut eksik

Transfer grafiğinin “create, project_link, ardından her dosya için presign/PUT/confirm” kuralı bugün ayrı ayrı hesaplanır (gerekli aşamalar ve kabul edilmiş aşama kümesi, öncül zinciri, arm girdisi, istek özetinin dataset kaynağı, rezervasyon formülü, istek bütçesi, kanıt toplamı, koordinatör döngüleri). Continuation ([ADR-0031](../../decisions/0031-upload-continuation.md)) ikinci bir grafik türü ekleyecek; bu dağınıklık güvenli eklemeyi imkânsız kılar. Ayrıca mevcut gerçek SIGKILL matrisi sekiz sınırdır ve `project_link` ile iki-worker PUT sınırı yoktur; bu boşluk hem refaktörün hem sonraki dilimlerin regresyon ağında eksiktir.

## Giren ve girmeyen kapsam

Girer: (a) `project_link` ve iki-worker PUT için gerçek SIGKILL karakterizasyon testleri (mevcut davranışı kaydeder: aynı-ID unknown/latch, ikinci etki yok); (b) aşama kümesi, öncül kuralı, rezervasyon ve istek-bütçesi sayımlarını tek kapalı belirtimden (`StageGraphSpec`) türeten refaktör; mevcut çağrı noktaları bu belirtimi kullanır. Plan türü yalnız mevcut v1/v2’yi bilir. Girmez: v3 davranışı, yeni tip, DDL/migration, wire/çıktı değişikliği, performans iddiası, public yüzey.

## Bağımlılıklar ve kararlar

P02-2c verified ve development’tadır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06); bu dilim davranışı değiştirmese de resume hattının ilk adımıdır ve K1 onayını bekler. Refaktör ayrı dilimdir, çünkü genişletilmiş regresyon ağı bunu davranışsız kanıtlayabilir.

## Sözleşme ve uygulama sınırı

Belirtim, plan sürümünden (şimdilik 1/2) ve dosya sayısından gerekli aşamaları, her aşamanın öncülünü, rezerv boyutunu ve istek sayacı tavanlarını verir. `required_stages`, `acknowledged_stages`, `predecessor`, `operation_reservation` ve istek-limit bağlantıları bu belirtimden okur; hiçbir public sembol, hata kodu, mesaj veya persisted byte değişmez. Alan adlarını/tip sınıflarını uygulama kartı seçer.

## Kabul

1. Karakterizasyon: link ve iki-worker PUT sınırlarında gerçek SIGKILL sonrası kayıt aynı-ID unknown/latch’tir, create/link/presign/PUT/confirm ikinci etkisi sıfırdır; bu testler **refaktörden önce** yeşildir ve refaktör sonrası değişmeden geçer.
2. Eski formüllerin test içine donmuş kopyaları ile yeni belirtim N=1..128 ve her plan sürümü için aynı aşama kümesini, öncülleri, rezervi ve sayaç tavanlarını verir (özellik testi, bağımsız oracle).
3. Mevcut bütün upload contract/integration testleri, gerçek süreç-kill testleri ve golden/byte fixture’ları **değiştirilmeden** geçer; hiçbir golden güncellenmez.
4. Strict mypy ve Ruff geçer; yeni public API/CLI/hata yok; kapasite, frontier, reset ve backup davranışı aynı.
5. Belirtim v1/v2 dışındaki sürümü sessizce kabul etmez (bilinmeyen sürüm kontrollü reddedilir).

## Doğrulama

Değişikliğe uygun hedefli upload contract/integration paketleri, yeni kill testleri, tam `pytest` (çekirdeğe dokunulduğu için bir kez), Ruff format/lint, strict mypy ve `git diff --check`. Performans beklenmez; ölçülmemiş iddia yazılmaz.

## Teslim kaydı

- PR/commit: tek development PR’ı ([PR #15](https://github.com/HodeTech/Yorunge/pull/15)) bu daldan açıldı ve 2026-11-12’de [69efc8d](https://github.com/HodeTech/Yorunge/commit/69efc8d465078257257d6494e15fda0e360b01e2) merge commit’iyle development’a alındı; adım commit’leri artık development tarihçesindedir: karakterizasyon `a881aca`, refaktör `8308ae9`, R1 düzeltmeleri `67c7191`, R2 düzeltmeleri [0c02464](https://github.com/HodeTech/Yorunge/commit/0c024649d7440a5cb2e9a4b0aeaec01102ee1253); kontrol çıktıları ve review kaydı [uygulama kaydındadır](../../research/p02-3-implementation-validation.md#adım-1--p02-3d-aşama-grafiği-tek-belirtimi).
- Sonuç: v2 yolunun gerçek SIGKILL matrisi 19 duruma çıktı (`link`, `presign`, `put`, `confirm`, iki-worker PUT ve üç dosyalı ikinci batch sınırları dahil) ve hem refaktör öncesi hem sonrası ürün koduyla geçti; aşama kümesi, öncül kuralı, rezervasyon, istek tavanları ve PUT batch’leri tek kapalı `StageGraphSpec` belirtiminden okunur, eski formüllerin donmuş kopyalarıyla N=1..128 × plan sürümü 1/2 için farksızdır ve çağrı noktaları eşdeğerlik ile mutasyon testleriyle kilitlidir. Hiçbir golden/fixture değişmedi; tam paket 6799 passed, 1 skipped; Ruff, strict mypy, check-docs ve check-agent-guides temiz; R1 ve R2 (tasarım ve mutasyon eksenleri) doğrulanmış bulguları işlendi.
- Kalan sınır: v3 davranışı, yeni tip ve DDL kapsam dışıdır; plan sürümü taşımayan dört çağrı noktası (`ORIGINAL_PLAN_VERSION`) ve `StageGraphSpec`in continuation grafiği P02-3g/3h kartlarında devir notlarıyla gözden geçirilir. `operation_reservation` sarmalayıcısı 0 ve 128 üstü sayıda artık `ValueError` verir (yalnız testler çağırır, saklı plan 1..128 dosyadır). Bu adım ürün yüzeyini, kalıcı byte/digest’i veya canlı davranışı değiştirmez.
