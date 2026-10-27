# Vizyon ve konumlandırma

**Güncellendi:** 2026-10-27. **Durum:** Benimsenmiş ürün yönü; uygulama planlanıyor.

Yörünge, EVREN platformunda çalışan kişilerin veriyi hazırlama, doğru hizmet/modeli seçme, işi yürütme ve sonucunu kullanma süresini kısaltır. Platformun farklı yüzeyleri arasında anlaşılır bir yardımcı katman kurar.

## Değer önerisi

Kullanıcı “hangi API, anahtar, klasör, sürüm ve durum?” sorularını tekrar tekrar çözmek yerine amacını ve girdisini belirtir. Yörünge gereken bağlamı doğrular, uygun seçenekleri sunar, işi izler ve sonucu açık bir yerde toplar. İleri kullanıcı aynı davranışı doğrudan komut veya Python API ile otomasyona bağlar.

Birincil hedefler: EVREN veri seti/model kullanıcıları, çıkarım ve LLM uygulaması geliştirenler, eğitim yapan ML mühendisleri ve bu işleri otomatikleştiren ekipler. LLM fine-tuning bu kapsamın önemli bir alanıdır; bütün ürünün tek giriş koşulu değildir.

## Araç ilişkisi

Yörünge görevleri ve EVREN ilişkisini yönetir. ForgeLM, yeteneklerinin örtüştüğü LLM eğitim/veri/değerlendirme görevlerinde varsayılan araçtır. Kullanıcı desteklenen muadil sağlayıcıyı seçebilir. Varsayılan olmak; zorunlu kurulum, diğer araçların seçeneklerini gizleme veya başarısızlıkta sessiz araç değiştirme anlamına gelmez. [ADR-0002](decisions/0002-forgelm-default-open-tools.md).

## Başarıyı nasıl anlayacağız?

| Öncelik | Gözlenebilir sonuç |
|---|---|
| Kullanım kolaylığı | Yeni kullanıcı ilk veri/çıkarım görevini yardım aramadan tamamlar; hata sonraki adımı açıklar. |
| Fayda ve işlevsellik | İş, geçici ekran çıktısından kullanılabilir sonuç ve kayıtlı kimliğe ulaşır. |
| Performans | Hafif komut hızlı açılır; büyük dosya RAM'e alınmaz; istek sayısı ve bekleme ölçülür. |
| Optimizasyon | Eşzamanlılık, disk, ağ, kota ve tekrar bütçesi sınırlıdır; kalite/durum doğruluğu korunur. |
| Seçim özgürlüğü | Aynı desteklenen görev farklı araçla yürütülebilir; farklar plan öncesinde görünür. |

Sayısal hedefler [performans standardında](standards/performance.md); kullanıcı görevleri [yolculuklarda](user-journeys.md) tanımlıdır. Bu hedefler henüz ölçülmüş sonuç değildir.

## Ürün sınırı

İlk ürün yerel araç ve API istemcisi olarak tasarlanır. EVREN hesap oluşturma, kaynak altyapısı sağlama veya platformun etiketleme arayüzünü yeniden üretme hedefi yoktur. Notebook, özel eğitim veya kullanıcı modeli serving gibi dış yetenekler erişim kanıtıyla açılır. İleride farklı bir arayüz eklenirse aynı çekirdek ve sözleşmeler korunur. [Kapsam](product-scope.md).
