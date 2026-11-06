---
id: P02-R4
phase: P02
status: draft
size: L
depends_on: [P02-3q]
capabilities: [C04, C12]
---
# P02-R4 — Veri sürümü oluşturma (freeze) etkisi

**Tarih:** 2026-11-06. **Sahip:** P02 / datasets modülü. [ADR-0033](../../decisions/0033-dataset-version-references.md) sürüm oluşturmayı bilinçli olarak P02-3c dışında bıraktı; bu kart özgün ihtiyacın açık sahibidir, kendisi uygulama veya ready yetkisi değildir.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı, doğrulanmış yüklemeden sonra Yörünge’den çıkmadan dataset’in dondurulmuş bir sürümünü oluşturmak ister. Bugün sürüm yalnız Platform arayüzünde oluşturulur; Yörünge onu okuyup bağlayabilir ([P02-3c](../phase-02-data-and-inference.md#uygulama-birimleri-ve-sıra)) ama üretemez. Sağlayıcıda `POST datasets/{id}/versions` etiketi istemci seçer; aynı etiket çakışmasında sunucu 500 gözlendi, idempotency, geri alma (silme/rollback) ve maliyet sözleşmesi bilinmiyor.

## Giren ve girmeyen kapsam

Plan/onay/tek gönderim/kayıp cevap uzlaştırması olan açık bir sürüm oluşturma etkisi, sağlayıcı çakışma ve hata semantiği araştırması ve ayrıca yetkili küçük canlı kabul girer. Otomatik etiket seçimi, sürüm silme/rollback/export, öğe bölme ataması ve upload sonrası örtük freeze girmez.

## Bağımlılıklar ve kararlar

P02-3q’nun sürüm okuma ve değişmez referans temeline bağlıdır. Koddan önce ayrı bir Proposed ADR (etki sözleşmesi, etiket politikası, çakışma/500 sınıflandırması, unknown uzlaştırma) kullanıcı onayına sunulur; sağlayıcı sözleşmesi çözülmeden ready değildir.

## Sözleşme ve uygulama sınırı

Mevcut `DatasetVersionBinding v1` ve `check` değişmez. Etki, upload gibi kalıcı niyet ve tek deneme modeline mi, daha hafif bir yola mı oturacağı ADR’de seçilir; yeni durum ailesi gerekiyorsa koddan önce kullanıcı kararı alınır.

## Kabul

1. Açık onayla tek bir sürüm oluşur; yanıt kaybında ikinci oluşturma yoktur ve durum salt okunur liste/detail ile uzlaştırılır.
2. Etiket çakışması ve sağlayıcı 500’ü başarı veya otomatik yeniden deneme sayılmaz.
3. Oluşan sürüm `bind` ile değişmez referansa dönüşür ve `check` unchanged verir.
4. İki fresh review turu ve önceden sınırlanmış canlı kabul olmadan verified olmaz.

## Doğrulama

Önce araştırma/ADR; sonra anlamlı TLS/süreç testleri ve kısıtlı canlı kabul. Her deneyde hedef, istek sayısı ve temizlik sahibi önceden yazılır.

## Teslim kaydı

Draft; uygulama, sağlayıcı sözleşmesi veya canlı kabul yoktur.
