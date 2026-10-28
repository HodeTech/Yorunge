# Yakın iş kartları

**Güncellendi:** 2026-10-28. Kartlar yalnız yaklaşan veya gerçekten başlanmış işler için oluşturulur. Planlama sözleşmesi [roadmap indeksindedir](../README.md#hazır-iş-paketi).

| Kart | Sonuç |
|---|---|
| [P01-1a](p01-1a-core-acceptance-hardening.md) | Mevcut çekirdeğin parser/şema hata sınırı ve dağıtım kabulünü sağlamlaştırma |
| [P01-2a](p01-2a-secret-resolution.md) | Açık istekle hizmete bağlı env secret çözümleme |
| [P01-4a](p01-4a-state-foundation.md) | P01-2 PR'ında store/migration ve kimlik kayıt temeli |
| [P01-2b](p01-2b-credential-identity.md) | Opak credential kimliği/nesli ve hedef bağları |
| [P01-2c](p01-2c-local-context-management.md) | Yerel init, context yönetimi ve doctor |
| [P01-3a](p01-3a-scoped-capability-cache.md) | Tam kapsamlı capability cache, kanıt ve tazelik |
| [P01-3b](p01-3b-execution-plan-validity.md) | Ayrı execution hazırlığı, güncel geçerlilik ve onay bağı |

Durum kart metadata'sında ve onunla denetlenen faz satırındadır; indeks durumu tekrar etmez. Uzak fazlar için boş kart yığını üretilmez. Tamamlanan kart kanıtıyla korunur; current yalnız aktif/sonraki kartı işaret eder.

P01-2'nin dört alt işi [teslim planıyla](../p01-2-delivery-plan.md) tek [PR #6](https://github.com/HodeTech/Yorunge/pull/6) içinde tamamlanıp development'a alındı. P01-3a/b [tek PR planı](../p01-3-delivery-plan.md) ve [PR #8](https://github.com/HodeTech/Yorunge/pull/8) ile development'a alındı; [merge/CI kapanışı](../../research/p01-3-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. Sıradaki P01-4b/4c hâlâ fazdaki draft kapsam satırlarıdır; ayrıntılı plan/kart ve karar incelemesi gereklidir. Bu indeks hazırlığı uygulama/kabul kanıtı saymaz.
