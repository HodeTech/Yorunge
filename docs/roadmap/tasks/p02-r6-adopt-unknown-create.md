---
id: P02-R6
phase: P02
status: draft
size: M
depends_on: [P02-3h]
capabilities: [C03, C12]
---
# P02-R6 — Bilinmeyen create sonucunun açık dataset sahiplenmesi

**Tarih:** 2026-11-06. **Sahip:** P02 / datasets modülü. [ADR-0031](../../decisions/0031-upload-continuation.md) create sonucu bilinmeyen kaynağı bloke eder; bu kart özgün ihtiyacın açık sahibidir, kendisi uygulama veya ready yetkisi değildir.

## Kullanıcı sonucu ve mevcut eksik

Create isteği gönderildi ama cevap/makbuz kayboldu; sağlayıcıda private bir dataset kalmış olabilir ve Yörünge kimliğini bilmiyor. Bugün ada göre arama yapılmaz ve aynı ad/proje niyeti kalıcı tekildir; kullanıcı devam edemez, Platform’da kalan kaynağı yalnız elle bulabilir.

## Giren ve girmeyen kapsam

Kullanıcının dataset kimliğini **açıkça** vermesi; salt okuma ile sahip/proje/private/ad/modality/katılım eşliği, boş veya yalnız Manifest dosyalarını içeren envanter ve oluşturma zamanı penceresi kontrolü; kullanıcı onaylı kalıcı sahiplenme kaydı ve sonra continuation girer. Ada göre otomatik eşleme, kimlik tahmini, birden çok aday arasında seçim yapma, yeniden create ve silme girmez.

## Bağımlılıklar ve kararlar

P02-3h’nin continuation temeline ve ayrı bir Proposed ADR’ye bağlıdır (insan onaylı sahiplenme kaydı ADR-0027 baseline’ının yerini tutamayacağı için yeni makbuz/baseline türü gerekebilir). Karar onaylanmadan ready değildir.

## Sözleşme ve uygulama sınırı

Sahiplenme, mevcut değişmez CreateReceiptV2 baseline’ını sahte üretmez; ayrı, insan onaylı ve açıkça “bildirilen” baseline türü olarak tanımlanır. Authority/pricing/remote-byte iddiası yükseltilmez.

## Kabul

1. Doğru, boş private dataset kimliği kullanıcı onayıyla sahiplenilir ve continuation ile tamamlanır; yanlış sahip/proje/görünürlük/ad/modality veya beklenmeyen item reddedilir.
2. Hiçbir koşulda ikinci create veya ada göre otomatik eşleşme yoktur.
3. İki fresh review turu ve önceden sınırlanmış canlı kabul olmadan verified olmaz.

## Doğrulama

Önce ADR; sonra anlamlı TLS/süreç testleri. Her deneyde hedef kaynak ve temizlik sahibi önceden yazılır.

## Teslim kaydı

Draft; uygulama, ADR veya canlı kabul yoktur.
