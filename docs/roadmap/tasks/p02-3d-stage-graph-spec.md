---
id: P02-3d
phase: P02
status: draft
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

P02-2c verified ve development’tadır. [ADR-0031](../../decisions/0031-upload-continuation.md)’in Accepted olması gerekir (bugün Proposed); bu dilim davranışı değiştirmese de resume hattının ilk adımıdır ve K1 onayını bekler. Refaktör ayrı dilimdir, çünkü genişletilmiş regresyon ağı bunu davranışsız kanıtlayabilir.

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

Draft; uygulama, commit veya review kanıtı yoktur.
