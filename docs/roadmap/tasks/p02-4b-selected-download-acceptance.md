---
id: P02-4b
phase: P02
status: verified
size: M
depends_on: [P02-4a, P02-4f, P02-3b, P02-3n]
capabilities: [C03, C05, C13]
---
# P02-4b — Katalog çözümlü seçimin model ağırlığı indirmesine bağlanması: üst kabul

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md). Üst kart: P02-4f adımının ve bütünleşik seçim kabulünün kaydı. **Boyut notu:** iş tek alt karta (P02-4f) bağlıdır; bu üst kart yalnız kabul kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı bir modeli `owner/slug` ve sürüm etiketiyle seçip ağırlığını doğrulama seviyesiyle indirir; indirmeden önce hangi sürümün çözüldüğünü görür. Belirsiz seçimde hiçbir ağırlık isteği yapılmaz. Bugün bu yol yoktur ([P02-3n](p02-3n-model-weights-consumer.md) yalnız sürüm kimliği alır).

## Giren ve girmeyen kapsam

Girer: `--model OWNER/SLUG --version-tag TAG` yolu; çözüm sırası; çözülen kimlik çıktısı; download-engine ve katalog referanslarının seçim bölümleri; K5 kapsamında ayrı onayla canlı indirme kabulü (erişilebilir sürüm kimliği ve ek yetki verilirse).

Girmez: “en son sürüm”, seçim saklama, lisans kabulü, ZIP ve dataset öğesi indirme (P02-R5), sürüm oluşturma (P02-R4), ağırlık uygunluğu kararı.

## Bağımlılıklar ve kararlar

[P02-4f](p02-4f-selected-download-binding.md) ve üst kart [P02-4a](p02-4a-catalog-acceptance.md); [P02-3b](p02-3b-download-acceptance.md) ve [P02-3n](p02-3n-model-weights-consumer.md) (verified; canlı kabulleri yapılmamış). Karar kaynağı [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) §5–§6, K6 (sözdizimi) ve K5 (canlı indirme).

## Sözleşme ve uygulama sınırı

Kanonik sınırlar: [indirme motoru sözleşmesi](../../reference/download-engine.md) (model ağırlığı yüzeyi) ve katalog referansı (`docs/reference/catalog.md`, P02-4c ile yazılır). Bu kart ikinci sözleşme tanımlamaz.

## Kabul

1. P02-4f `verified` ve iki fresh review turuyla kapanmış.
2. Çözüm başarısız, belirsiz veya görev uyumsuzsa 0 ağırlık isteği; istek sayımı kanıtı.
3. `--version-id` yolu regresyonsuz; P02-3n testleri geçer.
4. Canlı (K5): ayrı onayla kimlikli JSON çağrısı ve kimliksiz imzalı GET ile tek model indirme kaydı; onay yoksa “yapılmadı” ve nedeni (onay, erişilebilir sürüm veya ek yetki yok) açıkça yazılır.
5. Belge ve sürüm: [C05](../../capability-matrix.md) ve [C03](../../capability-matrix.md) satırları, [CLI sözleşmesi](../../reference/cli-contract.md) ve [download-engine](../../reference/download-engine.md) gerçek durumla eşleşir.

## Doğrulama

P02-4f doğrulamaları ve belge denetimi; tam paket ve kurulu wheel smoke’u ([CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi)). Canlı indirme yapılırsa indirilen bayt sayısı, süre ve doğrulama seviyesi kayıtlı olur; dosya yalnız kabul için ayrılmış geçici bir hedefe yazılır ve kabul sonunda silinir.

## Teslim kaydı

- PR/commit: [PR #18](https://github.com/HodeTech/Yorunge/pull/18) (`feat/p02-4-catalog-and-selection`, `development` hedefi).
- Sonuç: `models download --model OWNER/SLUG --version-tag TAG` uygulandı; çözüm sırası ADR-0035 Karar 6'ya göre kilit altında; çözülen kimlik çıktıda; download-engine ve katalog referanslarının seçim bölümleri yazıldı. Her adım iki fresh review turundan geçti (62300f7, 2d26af0, bb1df34); mutasyon kanıtları alındı.
- Kalan sınır: K5 canlı indirme **yapılmadı** (kabul maddesi 4 gereği): pilot hesapta Platform modeli yok (toplam 0), sürüm kimliği ve ek yetki verilmedi. Etiketle seçimde tam stage'in ağsız yayımı yoktur (Karar 6 ödünleşmesi).
