# Açık karar ve araştırma kayıtları

**Güncellendi:** 2026-10-27. Bu liste uygulanmış özellik değildir. Yeni iş kaydı oluştuğunda ilgili satırdan bağlantı verilir; henüz GitHub issue açılmadı.

| Kimlik | Konu | Önkoşul / sonraki adım | Sahip faz |
|---|---|---|---|
| B01 | CLI/şema/YAML seçildi; HTTP açık | [ADR-0008](../decisions/0008-offline-core-stack.md); taşıma/deadline deneyi kaldı | P01-5 |
| B02 | Ortak state DDL/migration/lease | Önce P01-4a store/migration kararı, sonra P01-4b sahiplik; çökme ve çok süreç deneyi | P01-4a/P01-4b |
| B03 | SDK'yı kullanma sınırı | Güncel kod/endpoint/retry sözleşme denetimi | P02 |
| B04 | Aktarım limitleri ve native eğitim durumları | Güncel resmî sözleşme + yetkili küçük pilot | P02/P03 |
| B05 | İlk muadil araç ve sürüm aralığı | Aynı SFT task/result deneyi; Axolotl ilk aday | P03-4 |
| B06 | Workspace genel kullanıcı erişimi | Sağlayıcı sözleşmesi ve erişim sonucu | P03-6/P04-3 |
| B07 | Kullanıcı LLM/adapter serving | EVREN kayıt/deploy API kanıtı; export sonucu serving kanıtı değildir | P04-R1 / C17 |
| B08 | Rehberli terminal ve çıktı dili | Görev gözlemi, ekran okuyucu/dar terminal | P01–P04 |
| B09 | Ekip kullanımı/uzak koordinasyon ihtiyacı | Yerel ilk pilot sonuçları; server ancak gerekçeyle | Sonraki kapsam |
| B10 | Puan/katkı ve organizasyon gelişmiş işleri | Gerçek kullanıcı talebi ve etki alanı | Sonraki kapsam |
| B11 | Dal politikası seçildi; ilk release numarası açık | [ADR-0009](../decisions/0009-development-and-release-branches.md); geliştirme sürümü release değildir | P01/P04 |
| B12 | Özel güvenlik bildirimi ve yedek kanal | Ana kanalı etkinleştirip kullanılabilirliğini, bakım ekibi erişimini ve özel yedek adresi doğrulamak; güncel kayıt [SECURITY.md](../../SECURITY.md) | İlk yayın öncesi / P04-6 |
| B13 | Credential kimliği/nesli için kalıcılık ve değişim kanıtı | Ham secret/hash saklamadan hedef/kimlik ayrımı, yerel koruma ve rotation tasarımı; P01-4a/P01-2b kartından önce karar | P01-4a/P01-2b |

Her yeni kapsam maddesi kullanıcı sonucuna, modülüne ve kabul kanıtına bağlanır. Bu kayıt tarih verilmiş bir teslim taahhüdü değildir. Kullanıcı önceliği değişirse [kapsam](../product-scope.md) ve [matris](../capability-matrix.md) birlikte güncellenir.
