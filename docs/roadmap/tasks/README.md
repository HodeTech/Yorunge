# Yakın iş kartları

**Güncellendi:** 2026-11-02. Kartlar yalnız yaklaşan veya gerçekten başlanmış işler için oluşturulur. Planlama sözleşmesi [roadmap indeksindedir](../README.md#hazır-iş-paketi).

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
| [P02-0a](p02-0a-contract-sdk-pilot.md) | Güncel resmî sözleşme, endpoint SDK değerlendirmesi ve yetkili pilot planı; ürün/pilot icrası değil |
| [P02-0b](p02-0b-context-discovery.md) | Hizmete bağlı dar context gözlemi üst teslimi; ADR-0022 tüketici sınırı |
| [P02-0c](p02-0c-llm-context-discovery.md) | Platform’dan bağımsız LLM terms/context ve dürüst kimlik/auth sınırı |
| [P02-0d](p02-0d-platform-context-discovery.md) | ADR-0022 ile nihai unverified consumer; üç uç/seçili proje gözlemi |
| [P02-1a](p02-1a-evidence-capacity.md) | B15 aynı evidence v1 biçiminde bounded katalog kapasitesi ve yazı öncesi ret |
| [P02-1b](p02-1b-manifest-contract.md) | ADR-0023’e bağlı strict Manifest v1 ve bağımsız byte/digest oracle’ı |
| [P02-1c](p02-1c-descriptor-dataset-scan.md) | Bounded descriptor klasör envanteri ve yeniden hash’leyerek verify |
| [P02-1d](p02-1d-dataset-inspection-cli.md) | Root dışı atomik artifact, ortak CLI/Python ve bütünleşik paket kabulü |
| [P02-R1](p02-r1-verified-context-binding.md) | Doğrulanmış kimlik/bağ ve gerekli tüketici otoritesi için kanonik P02 takip işi; mevcut P02-0 paketinin yeni önkoşulu değil |

[Kalan P01 paketi](../p01-remaining-delivery-plan.md), P01-5a/b ve P01-6b’yi tek epik PR’ına bağlar; [kabul kaydı](../../research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı) test/review/kurulum/performans kanıtının kaynağıdır.

[P02-0 paketi](../p02-0-delivery-plan.md), araştırma P02-0a ile üst keşif teslimi P02-0b’yi, bağımsız [LLM P02-0c](p02-0c-llm-context-discovery.md) ve [Platform P02-0d](p02-0d-platform-context-discovery.md) kabulleriyle ilişkilendirir. [Kabul/merge kaydı](../../research/p02-0-implementation-validation.md#development-merge-kapanışı) ve [hazırlık review’si](../../research/p02-readiness-review.md) ayrı amaç taşır.

[P02-1 teslim planı](../p02-1-delivery-plan.md), B15 kapasite bakımı, manifest/parser, descriptor tarama ve public yayın/yüzey kartlarını beş commit/review adımında tek nihai development PR’ına bağlar. [Kabul kaydı](../../research/p02-1-implementation-validation.md) özgün test/ölçüm/inceleme kanıtını taşır.

Durum kart metadata’sında ve onunla denetlenen faz satırındadır; indeks durumu tekrar etmez. Aktif/sonraki iş için [current](../current.md#sıradaki-iş-ve-kalan-kapsam) kanoniktir. Diğer P02 kartları karar/endpoint kanıtları geldikçe hazırlanır; uzak fazlar için boş kart yığını üretilmez. Kart, kanıtıyla birlikte korunur.

Önceki P01 epiklerinin alt kart/PR eşlemesi [P01-2](../p01-2-delivery-plan.md), [P01-3](../p01-3-delivery-plan.md) ve [P01-4](../p01-4-delivery-plan.md) planlarındadır. Store şeması/merge/CI geçmişi ilgili kabul kayıtlarından izlenir; bu indeks ikinci durum veya kanıt kaynağı değildir.
