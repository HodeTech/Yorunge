---
id: P02-R3
phase: P02
status: draft
size: M
depends_on: [P02-2v]
capabilities: [C02, C03, C12, C13]
---
# P02-R3 — İzole son kaynak performans kabulü

**Tarih:** 2026-11-05. **Sahip:** teslim eden maintainer/ajan; performance ve research-evidence. [ADR-0030](../../decisions/0030-development-performance-acceptance.md) Proposed; bu kart mevcut zorunlu CI kapısını henüz değiştirmez.

## Kullanıcı sonucu ve mevcut eksik

Başlangıç/yerel jobs hedefleri ve dataset/upload native bütçeleri son ürün kaynağı için güvenilir, izole ortamda kabul edilir. [09](../../research/p02-2-implementation-validation.md#5-kasım--09-ac-serisi-ve-açık-performans-kabulü) süre retlerini korur; kullanıcı başka testin sürekli çalıştığını bildirdi. Sakin spot pencere sürekli izolasyon sayılmaz. Sonuca bakarak örnek seçilmez.

## Giren ve girmeyen kapsam

Son kaynak/wheel/controller/fixture eşliği, önceden sabit dört reference adı, kaynak kapıları ve bütün ilk örneklerle startup/jobs/dataset/upload kabulü; raw native uyumu ve strict CI kapılarının geri bağlanması girer. Eşik değişimi, varsayımsal ürün optimizasyonu, başka host’u M5 etiketleme, yeni canlı EVREN deneyi veya otomatik seri tekrarı girmez.

## Bağımlılıklar ve kararlar

Araç temeli verified P02-2v’dir; P02-2c/P02-3 kapanışı bu işin başlaması için önkoşul değildir. ADR-0030 onayı ve izole referans makine dış kapıdır. Onaylanırsa bağımsız geliştirme ilerleyebilir; **P02-7 faz kapanışı ve ilk Master/release önerisi bu iş kapanmadan yapılamaz**. Yeni yönetilen ortam ancak ayrı kabul kararıyla kullanılabilir.

## Sözleşme ve uygulama sınırı

Kanonik bütçe/yöntem [performans standardında](../../standards/performance.md), kayıpsız saklama [kanıt standardında](../../standards/research-evidence.md). Onay sonrası deferred geliştirme durumu gerçek performans başarısı değildir. Strict reference verifier’ları kaldırılmaz; bu işin kapanışında zorunlu CI yoluna yeniden bağlanır.

## Kabul

1. Son source/test/script/workflow/runtime haritası sabittir; dosya adları ölçümden önce seçilir, kaynak değişimi veya yetersiz ortam ret üretir.
2. Eşzamanlı ağır test/build/profiler işi olmayan gerçek M5/SSD ortamında bütün ilk örnekler saklanır; startup dört 500/200 ms ve jobs dört 200 ms kapısı, dataset/upload 64/8 MiB ve mevcut deadline’lar geçer. Bir ret yeni yeşil arama yetkisi değildir.
3. Katı dört reference kapısı yeniden mandatory olur; deferred yolu kaldırılır. Mevcut son kaynakla üç ortam CI, altı kurulum, native Linux ve kanıt/gizlilik/saklama kontrolleri geçer.
4. İki farklı fresh review turu ve kanonik current/phase/matris güncellemesi; faz/ilk yayın kapısında açık kalan performans kaydı yoktur. Tarihsel retler değişmez.

## Doğrulama

Yalnız uygun ortam hazırken son kaynakta bir önceden planlı seri; önceki geçen geniş testleri gereksiz tekrarlama. Araç/politika değişirse anlamlı dar test ve review; sonra bütün kaynak sabitken gerçek ölçüm ve final CI. Henüz yeni ölçüm planlanmadı.

## Teslim kaydı

Draft; ADR-0030 kullanıcı kararı ve uygun izole ortam bekleniyor. Mevcut ölçüm değerleri bu kartı verified yapmaz.
