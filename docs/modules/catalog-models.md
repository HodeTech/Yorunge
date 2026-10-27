# Katalog ve modeller modülü

**Durum:** Planlandı. **Kapsam:** C05. **Faz:** P02/P03.

Model/veri araması, sahip/slug/UUID çözümleme, model görevi ve sürüm metadata'sı bu modüldedir. Modelin hesapta görünmesi ile belirli iş/parametreyi desteklemesi farklı sonuçlardır.

**Girdi:** Arama filtreleri veya açık kaynak kimliği. **Çıktı:** Tipli, sayfalı katalog sonucu ve varsa sabit sürüm referansı. Her komutta bütün modellerin tüm detaylarını okumak yerine özet/detail ayrımı ve cache kullanılır.

Görev seçimi için metin üretimi, embedding, rerank, görsel veya karar modeli türü korunur. “En iyi model” sabit bir sıralama olarak verilmez; görev, erişim ve ölçülmüş ihtiyaca göre seçenek sunulur. İndirme talebi artefakt modülünün dosya/güvenlik kurallarıyla yürür.

**Kabul:** Belirsiz slug, eksik yetki, stale katalog, model sürümü değişimi ve bilinmeyen görev türü ele alınır. Katalog sorgusu eğitim paketi yüklemez. Kullanıcıya modelin listede olmasının sağlık/servis garantisi olmadığı doğru bağlamda anlatılır.
