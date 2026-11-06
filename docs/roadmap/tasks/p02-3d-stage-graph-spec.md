---
id: P02-3d
phase: P02
status: draft
size: M
depends_on: [P02-2c]
capabilities: [C03, C12]
---
# P02-3d — Transfer aşama grafiği tek belirtimi (davranış korunur)

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 1. Salt refaktör: v1/v2 davranışı, byte/digest ve golden’lar değişmez.

## Kullanıcı sonucu ve mevcut eksik

Transfer grafiğinin “create, project_link, ardından her dosya için presign/PUT/confirm” kuralı bugün çok sayıda yerde ayrı ayrı hesaplanır: gerekli aşamalar ve kabul edilmiş aşama kümesi, öncül zinciri, arm girdisi, istek özeti (dataset kaynağı), rezervasyon/kapasite formülü, istek bütçesi, kanıt toplamı ve koordinatör döngüleri. Continuation ([ADR-0031](../../decisions/0031-upload-continuation.md)) ikinci bir grafik türü ekleyecek; bu dağınıklık güvenli eklemeyi imkânsız kılar. Bu kart yeni bir kullanıcı sonucu üretmez, sonraki dilimlerin güvenle eklenebilmesi için tek belirtim kaynağını kurar.

## Giren ve girmeyen kapsam

Aşama kümesi, öncül kuralı, rezervasyon ve istek-bütçesi sayımlarını tek kapalı belirtimden (`StageGraphSpec`) türeten refaktör girer; mevcut çağrı noktaları bu belirtimi kullanır. Plan türü yalnız mevcut v1/v2’yi bilir. v3 davranışı, yeni tip, DDL/migration, wire/çıktı değişikliği, performans iddiası ve public yüzey girmez.

## Bağımlılıklar ve kararlar

P02-2c verified ve development’tadır. Karar gerekmez; ancak [ADR-0031](../../decisions/0031-upload-continuation.md) onayı olmadan sonraki dilimler başlamaz. Refaktör ayrı dilimdir, çünkü regresyon ağı bunu davranışsız kanıtlayabilir.

## Sözleşme ve uygulama sınırı

Belirtim, plan sürümünden (şimdilik 1/2) ve dosya sayısından gerekli aşamaları, her aşamanın öncülünü, rezerv boyutunu ve istek sayacı tavanlarını verir. Mevcut `required_stages`, `acknowledged_stages`, `predecessor`, `operation_reservation` ve istek-limit bağlantıları bu belirtimden okur; hiçbir public sembol, hata kodu, mesaj veya persisted byte değişmez. Alan adlarını/tip sınıflarını uygulama kartı seçer.

## Kabul

1. Eski formüllerin test içine donmuş kopyaları ile yeni belirtim N=1..128 ve her plan sürümü için aynı aşama kümesini, öncülleri, rezervi ve sayaç tavanlarını verir (özellik testi, bağımsız oracle).
2. Mevcut bütün upload contract/integration testleri, gerçek süreç-kill testleri ve golden/byte fixture’ları **değiştirilmeden** geçer; hiçbir golden güncellenmez.
3. Strict mypy ve Ruff geçer; yeni public API/CLI/hata yok; kapasite, frontier, reset ve backup davranışı aynı.
4. Belirtim v1/v2 dışındaki sürümü sessizce kabul etmez (bilinmeyen sürüm kontrollü reddedilir).

## Doğrulama

Değişikliğe uygun hedefli upload contract/integration paketleri, kill testleri, tam `pytest` (çekirdeğe dokunulduğu için bir kez), Ruff format/lint, strict mypy ve `git diff --check`. Performans beklenmez; ölçülmemiş iddia yazılmaz.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
