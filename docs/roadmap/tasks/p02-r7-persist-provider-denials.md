---
id: P02-R7
phase: P02
status: draft
size: M
depends_on: [P02-2c]
capabilities: [C03, C12]
---
# P02-R7 — Kesin sağlayıcı retlerinin kalıcı `rejected` makbuzu

**Tarih:** 2026-11-06. **Sahip:** P02 / datasets modülü. [ADR-0031](../../decisions/0031-upload-continuation.md) incelemesinde bulunan bir belge–kod boşluğunun açık sahibidir; kendisi uygulama veya ready yetkisi değildir.

## Kullanıcı sonucu ve mevcut eksik

Sağlayıcı bir yazma isteğini kesin reddettiğinde (örn. 401/403 veya doğrulama hatası) kullanıcı bunun “hiçbir etki olmadı” anlamına gelen kalıcı bir sonuç olduğunu görmeli ve aynı isteğin yetki değişimi olmadan yeniden denenmediğini bilmelidir. [v2 sözleşmesi](../../reference/dataset-upload-v2.md#tüketici-profili-http-ve-my-role) “gerçek write 401/403 durable receipt/namespace’te kalır; yeni plan/flag/revision replay vermez” der ve ADR-0024 kesin ret için `rejected` makbuz ve `failed/provider_rejected` terminali tanımlar. Üretim yolu bugün bunu uygulamaz: `HttpStatusFailure` ve benzeri istek hataları `request_uncertain` olarak `unknown` bırakılır; `rejected` makbuzlar yalnız testlerde üretilir. Sonuç: kesin ret ile belirsiz cevap kullanıcı için ayırt edilemez ve continuation bu retleri bilinen olumsuz sayamaz.

## Giren ve girmeyen kapsam

Her etkili aşama (create, link, presign, PUT, confirm) için hangi HTTP/mantıksal sonucun “kesin ret” sayıldığının kapalı tablosu, bunun `rejected` StageReceipt’e ve `failed/provider_rejected` terminaline bağlanması, v2 belge hükmüyle uyum ve mevcut kill/state matrisinin yeni durumlarla genişletilmesi girer. 429, 5xx, zaman aşımı, bağlantı kopması ve çözülemeyen 2xx gövde kesin ret **sayılmaz**; ikinci denemeyi etkinleştirmek, sağlayıcıya izinsiz istek veya geçmiş kayıtları yeniden yazmak girmez.

## Bağımlılıklar ve kararlar

Kabul edilmiş v2 hata yolunu ve ADR-0024/0026 hükümlerinin uygulanışını değiştirdiğinden koddan önce kısa bir Proposed ADR (veya kısmi değişiklik notu) ve kullanıcı onayı gerekir. P02-3a continuation bu işi beklemez; dürüst sınırı ADR-0031 §2’dedir. Bu iş tamamlanınca continuation’ın savunmacı `rejected` kapısı gerçek veriye bağlanır.

## Sözleşme ve uygulama sınırı

Kesin ret tablosu sağlayıcı oracle’ına dayanır: yalnız “isteğin işlenmediği” sağlayıcı sözleşmesiyle açık olan sonuçlar girer; belirsiz her durum unknown kalır. Receipt şeması ve wire değişmez (mevcut `rejected` türü kullanılır).

## Kabul

1. Kesin ret sınıfı her aşamada kalıcı `rejected` makbuza ve (tüm intent’ler kesinleşince) `failed/provider_rejected` terminaline dönüşür; kullanıcı ret ile belirsizliği ayrı mesajlarla görür.
2. Belirsiz sonuçlar (zaman aşımı, kopma, çözülemeyen cevap) hâlâ `unknown` olur; yanlış `failed` yoktur.
3. Eski geçmiş, golden’lar ve mevcut kill matrisi korunur; iki fresh review turu olmadan verified olmaz.

## Doğrulama

Önce ADR; sonra gerçek TLS/SQLite/süreç testleri ve mevcut upload regresyon ağı.

## Teslim kaydı

Draft; uygulama, ADR veya kabul kaydı yoktur.
