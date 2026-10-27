---
name: yorunge-implement-task
description: Yörünge'de yetkilendirilmiş özellik, hata düzeltmesi veya refaktörü ortak CLI/Python çekirdeği üzerinde kod, anlamlı test ve belgeyle tamamla. Salt yol haritası/skill hazırlığı veya yalnız review talebinde ürün geliştirmesi başlatma.
---
# Yörünge işini uygula

[AGENTS.md](../../../AGENTS.md), ilgili iş kartı ve [mimari sınırlar](../../../docs/architecture/overview.md) ile başla. Güncel development tabanını ve kullanıcı değişikliklerini denetle; çalışma dalını [Git standardına](../../../docs/standards/git-release.md) göre hazırla.

- Mevcut davranışı ve en yakın anlamlı testi oku. `ready` kartı varsa kapsamı yeniden keşfetme; eksikse yalnız gerekli kadar daralt. Kullanıcı uygulama istemişse sadece plan verip durma.
- Domain/application kuralını CLI içine kopyalama. CLI ve Python aynı kullanım senaryosunu çağırmalı; somut dosya/ağ/DB/araç işleri dış katmanda kalmalı. Henüz olmayan portu/komutu varmış gibi kullanma veya boş modül iskeleti üretme.
- Sözleşme değişiyorsa [yorunge-contract-change](../yorunge-contract-change/SKILL.md) akışını uygula. ForgeLM seçiminin adaptör desteği olmadığını koru; native işi eğitim bağımlılığına bağlama.
- Başarı ve kontrollü hata yolunu birlikte tamamla. Yan etki belirsizliğini otomatik yeni yürütmeye dönüştürme. Test double'ı yalnız test/fixture alanında tut; ürün kodunda sahte eğitim/teslim başarısı oluşturma.
- [Doğrulama matrisine](../../../CONTRIBUTING.md#doğrulama-seçimi) göre kontrolleri çalıştır ve başarısızlıkları gider. Geçerli bir neden olmadan aynı kontrolleri tekrar tekrar koşma.
- Aynı değişiklikte kanonik referansı ve ilgili kullanıcı belgesini güncelle. İş kartı/current/matris durumu yalnız gerçek teslim kanıtını taşımalı; kapsamın geri kalanı planlandı kalmalı.

Çıktı: çalışan kullanıcı sonucu, değişen sözleşmeler, test/build/ölçüm kanıtı ve kalan sınır. Yetkili PR işi için [yorunge-pr](../yorunge-pr/SKILL.md) kullan; bu skill tek başına yayın veya Master birleştirmesi izni vermez.
