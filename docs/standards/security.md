# Güvenlik ve veri sınırları standardı

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

Güvenlik kontrolleri kullanıcı işini doğru hedefe ve beklenen içerikle tamamlamayı destekler. Hayalî risklere dayalı her adımda onay istemek yerine, somut veri aktarımı/maliyet/yayınlama etkisi planla görünür kılınır.

## Ağ ve sırlar

Platform ve LLM sırları ayrı hizmet kimliğiyle taşınır. Kimlik doğrulama sırrı, hizmet sözleşmesinin belirlediği yetkilendirme başlığında yalnız doğrulanmış HTTPS hedefine gönderilir. Hedef origin doğrulanır; yönlendirmede kontrol her adımda uygulanır veya redirect reddedilir. İmzalı depolama URL'sine Platform anahtarı otomatik eklenmez.

Yetkilendirme başlığının ağ isteğinde sır taşıması gerekir; bu değer plan, log, hata, artefakt manifesti veya kullanıcı çıktısına yansıtılmaz. Başlık dökümleri ve debug çıktısı da bu yasağa dahildir. Kimlik doğrulama sırrı URL'ye yazılmaz; hizmetten gelen imzalı URL'nin yetki taşıyan query değerleri de sır olarak korunur. Bilinen sır redaksiyonu bütün çıktı sınırlarını kapsar; bu, her türlü kişisel verinin otomatik bulunacağı iddiası değildir.

Kimlik ve yetki hatası retry döngüsünde tüketilmez. Capability cache anahtarı hizmet hedefini, hesap/projeyi ve etkin yetki kimliği/nesli/kapsamını ayırır; kesin kapsam [yetenek kaydı sözleşmesindedir](../reference/capability-record.md). Yapılandırılabilir endpoint erişimi ayrıca hedef politikası gerektirir; HTTPS tek başına doğru host kanıtı değildir.

## Dosya ve içerik

Gerçek yolun çalışma kökü içinde kalması denetlenir; symlink politikası açıktır. Kontrol/açma arasında değişim hesaba katılır. Arşivde üye sayısı, açılmış boyut ve oran sınırı; indirmede toplam bayt, güvenli ad ve no-clobber yazma gerekir. Sadece dosya uzantısı içerik doğrulaması değildir.

Uzak `success`, confirm veya `ready` cevabı endpoint şemasıyla doğrulanır. Yerel güncel hash ve uzak metadata doğrulaması farklı kanıtlardır. Yalnız metadata kontrol edildiyse içerik baytları indirilip karşılaştırılmış gibi anlatılmaz.

## Araç ve yan etki

Haricî araç ayrı süreç/ortamda, shell interpolation olmadan sabit argüman listesiyle çalıştırılır. Araç keşfi kod çalıştırma veya otomatik kurulum nedeni değildir. Kullanıcı seçimi, executable yolu, sürüm ve görevin yetkileri planla bağlanır. Şema doğrulaması keyfî Python plugin'ini güvenilir yapmaz.

Plan onayı, plan digest'i ve geçerlilik koşuluna bağlıdır; modelin `approved=true` demesi insan onayı kanıtı değildir. Kullanıcı şartları otomatik kabul edilmez. Yayınlama/silme ayrı etkili işlemdir. Sır veya özel veri olmadan sentetik test tercih edilir. [Çalıştırma modeli](../architecture/execution-model.md).
