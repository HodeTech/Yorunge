---
id: P02-4a
phase: P02
status: verified
size: M
depends_on: [P02-4c, P02-4d, P02-4e]
capabilities: [C03, C05, C13]
---
# P02-4a — Sayfalı veri/model kataloğu: üst kabul

**Tarih:** 2026-11-19. [P02-4 teslim planı](../p02-4-delivery-plan.md). Üst kart: P02-4c, 4d ve 4e adımlarının bütünleşik kabulü ve teslim kaydı. **Boyut notu:** özgün iş alt kartlara bölündüğü için bu üst kart yalnız kabul kaydı olarak M izlenir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı Platform’da anahtarının eriştiği model ve veri setlerini (kapsam K2/K4 ile teyit edilir), LLM geçidinin bu anahtara görünen modellerini ve sürüm etiketlerini sayfa sayfa görür; hangi bilginin kesin, hangisinin gözlemsel olduğunu bilir. Bugün katalog okuma yüzeyi yoktur.

## Giren ve girmeyen kapsam

Girer: P02-4c (sözleşme), P02-4d (taşıma ve API), P02-4e (CLI ve canlı salt okuma kabulü); [ADR-0035](../../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted; kullanıcı belgesi ve kanonik referans; K4 kapsamında canlı kayıt. Girmez: indirme seçim bağı ([P02-4b](p02-4b-selected-download-acceptance.md)), önbellek, öneri, GPU/kota, LLM çıkarım.

## Bağımlılıklar ve kararlar

Alt kartlar P02-4c, P02-4d, P02-4e; ADR-0035 (K1), K2 (veri seti ucu ve kapsamı), K3 (LLM kaynağı), K4 (canlı salt okuma), K8 (UX hedefleri), K9 (kapalı codec). Bağımlılıklar development’ta verified veya teslim edilmiştir: [P02-0a](p02-0a-contract-sdk-pilot.md), [P02-0c](p02-0c-llm-context-discovery.md), [P02-0d](p02-0d-platform-context-discovery.md).

## Sözleşme ve uygulama sınırı

Kanonik katalog sınırı `docs/reference/catalog.md` dosyasıdır (P02-4c ile yazılır); CLI yüzeyi [CLI sözleşmesinde](../../reference/cli-contract.md) tutulur. Üst kart yalnız kabul kaydıdır; ikinci sözleşme tanımlamaz.

## Kabul

1. Alt kartlar P02-4c, 4d, 4e `verified` ve her biri iki fresh review turuyla kapanmış.
2. Çevrimdışı kabul: sahte sunucularla sayfalama, çözüm, sınırlar, sızıntı ve sanitizasyon negatifleri geçer; kurulu wheel smoke’u (çevrimdışı ret ve yardım) geçer; kurulu pakette başarılı katalog okuması bu turda kapsanmadı (sınır).
3. Canlı kabul (K4): Platform modelleri, veri setleri ve LLM listesi/detayı için salt okuma GET kaydı; alan kümesi, sayfa üst sınırı ve başlıklar teyit edilir. Yapılmadıysa “yapılmadı” kaydı ve doğrulanmayan uçlar açıkça yazılır.
4. LLM alt kabulü: P02-5’in model/görev doğrulaması için gereken `ModelInfo` alanları kanıtlı; P02-5 bu alt kabulü ön koşul olarak okur. Canlı kabul yoksa alt kabul “canlı doğrulanmadı” ile işaretlenir.
5. Belge: [C05](../../capability-matrix.md) satırı, [katalog modülü](../../modules/catalog-models.md), [CLI sözleşmesi](../../reference/cli-contract.md), [current](../current.md) ve [faz satırı](../phase-02-data-and-inference.md) gerçek durumla eşleşir.

## Doğrulama

Alt kartların doğrulamaları birleşir; bu kartta ek olarak belge/matris denetimi ve tam paket çalıştırılır ([CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi)). Canlı kanıt ayrı kayıtta tutulur.

## Teslim kaydı

- PR/commit: [PR #18](https://github.com/HodeTech/Yorunge/pull/18) (`feat/p02-4-catalog-and-selection`, `development` hedefi).
- Sonuç: alt kartlar P02-4c, P02-4d ve P02-4e teslim edildi; K4 canlı salt okuma kaydı yapıldı ([kanıt](../../research/p02-4-catalog-live-read-20261119.md)): LLM listesi (15 model) ve detayı canlı okundu, kimlikler alfabeye uygun, veri seti başlığı `0`/`1` olarak düzeltildi.
- Kalan sınır: Platform model okuması ve sürüm çözümü pilot hesapta model olmadığı için canlı kanıtsız; 100 üstü sayfa ve `scope=owned` etkisi gözlenmedi. P02-5 LLM girdilerini bu kayda göre "canlı doğrulanmadı" sınırıyla okuyabilir.
