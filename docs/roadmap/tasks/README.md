# Yakın iş kartları

**Güncellendi:** 2026-10-29. Kartlar yalnız yaklaşan veya gerçekten başlanmış işler için oluşturulur. Planlama sözleşmesi [roadmap indeksindedir](../README.md#hazır-iş-paketi).

| Kart | Sonuç |
|---|---|
| [P01-1a](p01-1a-core-acceptance-hardening.md) | Mevcut çekirdeğin parser/şema hata sınırı ve dağıtım kabulünü sağlamlaştırma |
| [P01-2a](p01-2a-secret-resolution.md) | Açık istekle hizmete bağlı env secret çözümleme |
| [P01-4a](p01-4a-state-foundation.md) | P01-2 PR'ında store/migration ve kimlik kayıt temeli |
| [P01-2b](p01-2b-credential-identity.md) | Opak credential kimliği/nesli ve hedef bağları |
| [P01-2c](p01-2c-local-context-management.md) | Yerel init, context yönetimi ve doctor |
| [P01-3a](p01-3a-scoped-capability-cache.md) | Tam kapsamlı capability cache, kanıt ve tazelik |
| [P01-3b](p01-3b-execution-plan-validity.md) | Ayrı execution hazırlığı, güncel geçerlilik ve onay bağı |
| [P01-4b](p01-4b-operation-coordination.md) | Kalıcı operation kabulü, tek gönderim, lease/fencing ve unknown |
| [P01-4c](p01-4c-local-jobs.md) | Gerçek yerel iş geçmişinden CLI/Python list/show |
| [P01-5a](p01-5a-http-transport.md) | Ortak HTTP/TLS/deadline/retry, SDK sınırı ve operation composition |
| [P01-5b](p01-5b-stream-results.md) | Tipli stream/NDJSON, terminal/EOF ve yerel iptal/çıktı |
| [P01-6b](p01-6b-phase-acceptance.md) | Bütünleşik faz kabulü, kurulum/performans ve gerçek ortam matrisi |

[Kalan P01 paketi](../p01-remaining-delivery-plan.md) bu üç kartı son kullanıcı talebiyle tek nihai PR’da toplar; ADR-0017/0018 Accepted. P01-5a/b iki adım/ikişer fresh review ve gerçek kurulumla verified; P01-6b bütünleşik kabul ve gerçek CI/performans kapanışıyla çalışma dalında verified; tek development PR bekleniyor. Güncel durum kart metadata'sındadır.

Durum kart metadata'sında ve onunla denetlenen faz satırındadır; indeks durumu tekrar etmez. Uzak fazlar için boş kart yığını üretilmez. Tamamlanan kart kanıtıyla korunur; current yalnız aktif/sonraki kartı işaret eder.

P01-2'nin dört alt işi [teslim planıyla](../p01-2-delivery-plan.md) tek [PR #6](https://github.com/HodeTech/Yorunge/pull/6) içinde tamamlanıp development'a alındı. P01-3a/b [tek PR planı](../p01-3-delivery-plan.md) ve [PR #8](https://github.com/HodeTech/Yorunge/pull/8) ile development'a alındı; [merge/CI kapanışı](../../research/p01-3-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. Takip PR #9 ile şema 5 de development’a alındı; [merge ve o tarihteki açık CI performans takibi](../../research/p01-3-implementation-validation.md#pr-9-development-merge-kapanışı) tarihsel kayıttır. Bu takip [ölçüm güvenilirliği/CLI bakımı](../../research/startup-ci-reliability.md) ve PR #10 ile kapandı. P01-4b/4c için [tek PR planı](../p01-4-delivery-plan.md), [koordinasyon](p01-4b-operation-coordination.md) ve [yerel jobs](p01-4c-local-jobs.md) kartları ADR-0016 Accepted kararına bağlıdır; PR #10 ile development'a alındı; [merge/CI kapanışı](../../research/p01-4-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. Güncel durum kart metadata’sındadır; bu indeks uygulama/kabul kanıtı saymaz.
