# Açık karar ve araştırma kayıtları

**Güncellendi:** 2026-10-31. Bu liste uygulanmış özellik değildir. Yeni iş kaydı oluştuğunda ilgili satırdan bağlantı verilir; henüz GitHub issue açılmadı.

| Kimlik | Konu | Önkoşul / sonraki adım | Sahip faz |
|---|---|---|---|
| B01 | CLI/şema/YAML ve HTTP taşıma seçimi | [ADR-0017](../decisions/0017-bounded-http-transport.md) Accepted; ortak taşıma ve gerçek TLS loopback kabulü P01-5a verified ve PR #11 ile development’a teslim edildi. Gerçek endpoint adaptörü P02 kapsamındadır | P01-5a / P02 |
| B02 | Ortak state DDL/migration/lease | [Araştırma](../research/p01-2-state-identity-decision-review.md), [ADR-0011](../decisions/0011-state-foundation-and-migrations.md) Accepted; store/migration karar kapısı kapandı. P01-4a PR #6 ile, operation/lease/jobs ve ADR-0016 [PR #10](https://github.com/HodeTech/Yorunge/pull/10) ile tamamlanıp development'a alındı; B02 karar/uygulama kapısı kapandı | P01-4a/P01-4b |
| B03 | SDK'yı kullanma sınırı | [0.11.0 ön incelemesi](../research/p01-remaining-readiness-review.md), ADR-0017 Accepted. [P02-0a kaynak araştırması](../research/p02-contract-sdk-pilot.md#sabit-sdk-değerlendirmesi--b03) sabit wheel/Git eşliğini ve endpoint farklarını kaydetti; ortak HTTP + bağımsız normalizasyon önerisi Accepted ADR-0020 kapsamında bu tüketicide benimsendi; diğer endpoint tüketici kararları ayrı. Tüketici kabulü ayrı, core bağımlılığı yasağı sürer | P01-5a karar / P02 adaptör |
| B04 | Veri/çıkarım limitleri ve native eğitim durumları | P02 auth/limit/replay/signed URL/SSE kaynak ve unknown/açılma koşulları [araştırmada](../research/p02-contract-sdk-pilot.md#b04-ve-sonraki-kararların-açılma-koşulu) kaydedildi; sayısal provider garanti ve canlı kabul değil. Signed URL çelişkisi/çok aşamalı transfer/SSE kararları ilk tüketicide açık; pilot planı ile icra ayrı. Yönetilen eğitim durum/parametreleri P03-1’de araştırılır; P02’yi bekleten gizli önkoşul değildir | P02/P03 |
| B05 | İlk muadil araç ve sürüm aralığı | Aynı SFT task/result deneyi; Axolotl ilk aday | P03-4 |
| B06 | Workspace genel kullanıcı erişimi | Sağlayıcı sözleşmesi ve erişim sonucu | P03-6/P04-3 |
| B07 | Kullanıcı LLM/adapter serving | EVREN kayıt/deploy API kanıtı; export sonucu serving kanıtı değildir | P04-R1 / C17 |
| B08 | Rehberli terminal ve çıktı dili | Görev gözlemi, ekran okuyucu/dar terminal | P01–P04 |
| B09 | Ekip kullanımı/uzak koordinasyon ihtiyacı | Yerel ilk pilot sonuçları; server ancak gerekçeyle | Sonraki kapsam |
| B10 | Puan/katkı ve organizasyon gelişmiş işleri | Gerçek kullanıcı talebi ve etki alanı | Sonraki kapsam |
| B11 | Dal politikası seçildi; ilk release numarası açık | [ADR-0009](../decisions/0009-development-and-release-branches.md); geliştirme sürümü release değildir | P01/P04 |
| B12 | Özel güvenlik bildirimi ve yedek kanal | Ana kanalı etkinleştirip kullanılabilirliğini, bakım ekibi erişimini ve özel yedek adresi doğrulamak; güncel kayıt [SECURITY.md](../../SECURITY.md) | İlk yayın öncesi / P04-6 |
| B13 | Credential kimliği/nesli için kalıcılık ve değişim kanıtı | [Araştırma](../research/p01-2-state-identity-decision-review.md), [ADR-0012](../decisions/0012-credential-identity-and-change-detection.md) Accepted; özel HMAC + ayrı K dosyası/tehdit/kurtarma ve binding v1 kararı kapandı. Uygulama/kabul P01-4a/P01-2b'de tamamlandı | P01-4a/P01-2b |

Her yeni kapsam maddesi kullanıcı sonucuna, modülüne ve kabul kanıtına bağlanır. Bu kayıt tarih verilmiş bir teslim taahhüdü değildir. Kullanıcı önceliği değişirse [kapsam](../product-scope.md) ve [matris](../capability-matrix.md) birlikte güncellenir.
