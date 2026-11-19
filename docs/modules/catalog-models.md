# Katalog ve modeller modülü

**Durum:** P02-4 [PR #18](https://github.com/HodeTech/Yorunge/pull/18) ile development’a teslim edildi ([plan](../roadmap/p02-4-delivery-plan.md); [ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) Accepted, 2026-11-19). K4 canlı salt okuma kabul; K5 canlı indirme yapılmadı. **Kapsam:** C05. **Faz:** P02/P03.

Model/veri araması, sahip/slug/UUID çözümleme, model görevi ve sürüm metadata'sı bu modüldedir. Modelin hesapta görünmesi ile belirli iş/parametreyi desteklemesi farklı sonuçlardır.

**Girdi:** Arama filtreleri veya açık kaynak kimliği. **Çıktı:** Tipli, sayfalı katalog sonucu ve varsa sabit sürüm referansı. Her komutta bütün modellerin tüm detaylarını okumak yerine özet/detail ayrımı kullanılır; P02-4’te kalıcı önbellek yoktur, her komut okur ve gözlem zamanını gösterir ([ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) §4).

Görev seçimi için metin üretimi, embedding, rerank, görsel veya karar modeli türü korunur. “En iyi model” sabit bir sıralama olarak verilmez; görev, erişim ve ölçülmüş ihtiyaca göre seçenek sunulur. İndirme talebi artefakt modülünün dosya/güvenlik kurallarıyla yürür.

**Kabul:** Belirsiz sürüm etiketi, eksik yetki, tamlık belirsizliği, model sürümü değişimi ve bilinmeyen görev türü ele alınır. Katalog sorgusu eğitim paketi yüklemez. Kesin model sürümü kimliğiyle ağırlık indirme (`models download`) P02-3n’de uygulandı ve PR #15 ile development’a teslim edildi ([ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) Accepted; [başvuru](../reference/download-engine.md); canlı kabul yok); katalog çözümlü seçim P02-4b’dedir. Kullanıcıya modelin listede olmasının sağlık/servis garantisi olmadığı doğru bağlamda anlatılır.
