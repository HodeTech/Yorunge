# Yetenek çözümleme modülü

**Durum:** Uygulanıyor — offline v1 ile açık yerel cache/clock v2 testli; P01-3a yerel kabulü tamamlandı, uzak keşif planlandı. **Kapsam:** C02. **Faz:** P01 ve tüm adaptörler.

Görev, model, hesap, hizmet, araç ve execution birleşiminde destek bilgisini bir araya getirir. Şema/kılavuz/istemci gözlemi/canlı test kanıtlarını birbirine eşitlemez. Aynı hizmette farklı hesapların veya aynı hesaptaki farklı yetki kimliği/nesli/kapsamının kayıtları cache'te paylaşılmaz.

**Girdi:** Context, görev ve sağlayıcı manifestleri. **Çıktı:** `supported`, `unsupported`, `unknown` veya `requires_access`, gerekçe ve kanıt zamanı. Kaynaklar çelişirse yüksek güvenle destek ilan etmek yerine çelişki görünür tutulur.

Hız için kapsamlı cache kullanılır; düşük riskli listeleme eski veri etiketini gösterebilir. İş başlatma/yetki/maliyet kararında yenileme politikası uygulanır. Bir 401/403 yanlış config veya erişim olabilir; global unsupported sayılmaz. Bütün endpointleri her komutta taramak tanılama değildir.

**Kabul:** Stale kayıt, kapsam çakışması, bilinmeyen enum ve eksik alanlarla çözümleme sınanır. Haricî araç kurulu olsa da doğrulanmış sürüm/görev desteği ayrı gösterilir. [Kayıt sözleşmesi](../reference/capability-record.md).
