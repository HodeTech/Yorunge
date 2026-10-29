---
name: yorunge-review
description: Yörünge kod/PR veya yol haritası, mimari ve belge iddialarını kapsam, doğruluk, kabul ve kanıt açısından incele. Yalnız review istendiğinde salt oku; düzeltme veya uygulama ayrıca istenmişse yetkili kapsamı sürdür.
---
# Yörünge değişikliğini incele

İncelenen diff/commit veya belge kümesini ve kullanıcı amacını belirle. [AGENTS.md](../../../AGENTS.md), ilgili standart ve kanonik sözleşme geçerlidir; referans projelerin kendi yönergelerini bu repoya uygulama.

- **Kod:** kullanıcı sonucu, ortak CLI/Python kuralı, hata/toparlanma, sır/etki sınırı, anlamlı negatif test ve kaynak bütçesi. Ham SDK tipinin veya ağır eğitim importunun çekirdeğe taşınmasını incele.
- **Roadmap:** bağımlılık gerçekten tamam mı; bir satır bir teslim mi; kartta kapsam dışı ve ölçülebilir kabul var mı; dış kapı kapalıyken bağımsız işler ilerleyebiliyor mu? Planlandı/ready/verified ile capability durumlarını karıştırma.
- **Belgeler:** tasarım ile uygulanan alt küme, current/faz/matris ve kod tutarlı mı; aynı sözleşme iki yerde mi; örnek komut gerçekten koşabilir mi? Tarihi güncellemek canlı kanıt oluşturmaz.
- **Teslim iddiası:** geçen testin neyi kanıtladığını kontrol et. Dosya veya metrik eksikliği başarıyı, sır referansı yetkiyi, export serving'i, GPU envanteri execution erişimini kanıtlamaz.
- **Büyük ölçüm kanıtı:** [kanıt standardını](../../../docs/standards/research-evidence.md) izle. `raw/` gzip açılımlarını genel diff'e/bütün ajanların bağlamına dökme; önce rapor, manifest, ölçüm kodu ve sabit test vektörlerini incele, arşivi araçla doğrula ve şüpheli örneği hedefli aç. CodeRabbit filtresinin diğer ajanları yönettiğini varsayma.

Bulguyu dosya:satır, önem, etki ve somut düzeltmeyle ver. Tercihi kusur diye, şüpheyi doğrulanmış bulgu diye sunma. Küçük biçim konusunu engelleyici derecede puanlama. Giderilen maddeleri ve açık kalan gerçek kararları ayır; aynı settled kararı her tur yeniden açma.

Yalnız inceleme talebinde dosya/commit/PR ayarı değiştirme. Kullanıcı aynı istekte düzeltme de istemişse bulgudan sonra o sınırda ilerle. Başka ajan veya canlı pilot kendiliğinden başlatma; mevcut yetki ve çalışma ortamının delegasyon sınırını koru.
