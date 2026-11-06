---
id: P02-R8
phase: P02
status: draft
size: M
depends_on: [P02-2c]
capabilities: [C03, C12]
---
# P02-R8 — Operation’sız upload planlarını unutma

**Tarih:** 2026-11-06. **Sahip:** P02 / datasets modülü. [ADR-0031](../../decisions/0031-upload-continuation.md) incelemesinde bulunan kota etkisinin açık sahibidir; kendisi uygulama veya ready yetkisi değildir.

## Kullanıcı sonucu ve mevcut eksik

Başlatılmamış, süresi dolmuş veya iptal edilmiş upload planları plan/dosya/payload kotasına dahildir ve bugün hiçbir yolla silinmez ([upload kullanım rehberi](../../reference/upload-workflows.md)); kalıcı geçmiş otomatik silinmez ve dolu store yeni upload açamaz. Continuation her denemede N dosyayı yeniden saydığından (128 dosyalık bir iş için kök dahil yaklaşık 32 plan) bu sınır pratikte daha erken görülür. Kullanıcının tek çaresi yeni bir state dizinidir; bu belirsiz işleri de terk etmek anlamına gelebilir.

## Giren ve girmeyen kapsam

Hiç operation’ı olmayan upload planlarını (ve onaylarını) açık, tek kayıt hedefli bir komutla unutma, kota yeniden hesabı, reset önizleme parmak izi ve expiry frontier uyumu ile kullanıcı belgesi girer. Operation’lı planların, geçmişin, makbuzların veya namespace niyetlerinin silinmesi; toplu/otomatik temizlik; remote kaynakların silinmesi girmez.

## Bağımlılıklar ve kararlar

Saklama politikası kararıdır: koddan önce kısa bir Proposed ADR (veya ADR-0024 kısmi değişiklik notu) ve kullanıcı onayı gerekir. Mevcut “geçmiş otomatik silinmez” ilkesi operation’lı kayıtlar için aynen korunur; yalnız operation’sız planlar için açık kullanıcı eylemi eklenir. P02-3 bu işi beklemez; sınır ADR-0031 §6’da görünür.

**Açılma ölçütü ve hedef:** operation’sız planlar için saklama politikası (açık kullanıcı eylemiyle unutma) kullanıcı onaylı kısa Proposed ADR’si. Hedef: P02-7 faz kabulünden önce; gerçek kullanımda continuation kotayı beklenenden erken doldurursa öne alınır; K4’te kullanıcı isterse P02-3i öncesine çekilir.

## Sözleşme ve uygulama sınırı

Plan yaşam döngüsü kuralları (`plan_in_use` benzeri bir ret operation’lı planı korur), kapasite hesabı ve namespace satırı davranışı kartta kapatılır; namespace’in create intent’i hiç oluşmamış satırlarının serbest bırakılması gerekip gerekmediği karar konusudur.

## Kabul

1. Operation’sız plan açık komutla unutulur; kota sayaçları düşer, `list/show` buna göre davranır.
2. Operation’lı plan, makbuzu olan geçmiş veya namespace niyeti silinemez; kontrollü ret ve ID korunur.
3. Reset önizleme/uygulama, expiry frontier ve full/hot doğrulama unutma sonrasında tutarlıdır; v1/v2/v3 geçmişi ve golden’lar değişmez.
4. İki fresh review turu olmadan verified olmaz.

## Doğrulama

Önce ADR/karar; sonra gerçek SQLite/süreç testleri ve mevcut kota/maintenance regresyon ağı.

## Teslim kaydı

Draft; uygulama, ADR veya kabul kaydı yoktur.
