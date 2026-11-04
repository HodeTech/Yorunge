# Yakın iş kartları

**Güncellendi:** 2026-11-04. Kartlar yalnız yaklaşan veya gerçekten başlanmış işler için oluşturulur. Planlama sözleşmesi [roadmap indeksindedir](../README.md#hazır-iş-paketi).

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
| [P02-2a](p02-2a-private-create.md) | Private create/proje bağı, ayrı upload planı ve kalıcı aşama temeli; karar/otorite kapılı |
| [P02-2b](p02-2b-verified-upload.md) | Ayrı hedef politikasıyla bounded presign/PUT/confirm |
| [P02-2c](p02-2c-upload-recovery-acceptance.md) | Aynı-ID read recovery, kesinti ve bütünleşik paket kabulü |
| [P02-2d](p02-2d-upload-plan-contract.md) | Uzak otoriteyi beklemeyen yerel upload plan/manifest/onay sözleşmesi |
| [P02-2e](p02-2e-durable-transfer-journal.md) | Ortak state içinde kalıcı transfer stage/CAS/recovery temeli |
| [P02-2f](p02-2f-bounded-storage-port.md) | Ayrı hedef/auth ve sınırlı streaming storage temeli |
| [P02-2g](p02-2g-work-cost-v2.md) | Exact işe/döneme bağlı maliyet v2; ADR-0026 uyumu |
| [P02-2h](p02-2h-plan-policy-v2.md) | Policy-aware v2 plan/onay/current sözleşmesi; ADR-0026 uyumu |
| [P02-2i](p02-2i-versioned-journal.md) | V1/V2 journal union ve tam graph okuması; ADR-0026 uyumu |
| [P02-2j](p02-2j-write-gates-v2.md) | V2 admission/arm ve v1 weak-cost write kapanışı; ADR-0026 uyumu |
| [P02-2k](p02-2k-read-recovery-v2.md) | V2 explicit read/metadata/reset uyumu; ADR-0026 uyumu |
| [P02-2l](p02-2l-platform-control-codecs.md) | Platform context/create/link strict codec ve literal sınırları |
| [P02-2m](p02-2m-platform-upload-codecs.md) | Proxy descriptor, tek dosya presign/confirm ve bounded item codec'leri |
| [P02-2n](p02-2n-upload-http-budgets.md) | Kayıtlı service URI literal kuralı ve gerçek HTTP quota/counter bağlantısı |
| [P02-2o](p02-2o-current-upload-preparation.md) | Güncel input/current provider ve prepare/approve kompozisyonu |
| [P02-2p](p02-2p-created-dataset-context.md) | Atomik create baseline, versioned receipt ve legacy mutation gate |
| [P02-2q](p02-2q-platform-effect-port.md) | Bütçeli gerçek effect/metadata HTTP portu |
| [P02-2r](p02-2r-original-upload-workflow.md) | Original invocation, create/link ve tam upload koordinatörü |
| [P02-2s](p02-2s-readonly-upload-reconciliation.md) | Aynı upload kaydında salt okuma uzlaştırması |
| [P02-2t](p02-2t-public-upload-workflows.md) | Ortak sekiz API/CLI, dar public niyet/sonuç ve bounded TTY ilerleme |
| [P02-2u](p02-2u-offline-upload-acceptance.md) | Public süreç/azami envanter ve çevrimdışı test kabulü |
| [P02-2v](p02-2v-installed-upload-measurement.md) | Kurulu gerçek upload için native ölçüm araçları ve bağımsız kanıt |
| [P02-2w](p02-2w-upload-maintainability.md) | Son kaynak öncesi upload doğrulama/transaction bakım sınırları |
| [P02-R1](p02-r1-verified-context-binding.md) | Doğrulanmış kimlik/bağ ve gerekli tüketici otoritesi için kanonik P02 takip işi; mevcut P02-0 paketinin yeni önkoşulu değil |
| [P02-R2](p02-r2-upload-content-cardinality.md) | Aynı hash/farklı adın ayrı uzak item olarak korunması; Accepted ADR-0028 ile ilk teslimden ayrılan özgün ihtiyacın açık takip sahibi |

[Kalan P01 paketi](../p01-remaining-delivery-plan.md), P01-5a/b ve P01-6b’yi tek epik PR’ına bağlar; [kabul kaydı](../../research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı) test/review/kurulum/performans kanıtının kaynağıdır.

[P02-0 paketi](../p02-0-delivery-plan.md), araştırma P02-0a ile üst keşif teslimi P02-0b’yi, bağımsız [LLM P02-0c](p02-0c-llm-context-discovery.md) ve [Platform P02-0d](p02-0d-platform-context-discovery.md) kabulleriyle ilişkilendirir. [Kabul/merge kaydı](../../research/p02-0-implementation-validation.md#development-merge-kapanışı) ve [hazırlık review’si](../../research/p02-readiness-review.md) ayrı amaç taşır.

[P02-1 teslim planı](../p02-1-delivery-plan.md) B15, manifest/parser, descriptor tarama ve public yayın/yüzey kartlarını beş adımda topladı; bütün kartlar [PR #13](https://github.com/HodeTech/Yorunge/pull/13) / [50d68b1](https://github.com/HodeTech/Yorunge/commit/50d68b1deab80d6fe14749d556efde1f103b5759) ile development’a teslim edildi. [Kabul ve merge kaydı](../../research/p02-1-implementation-validation.md#development-merge-kapanışı) kanoniktir. Sıradaki P02-2a–c kartları [P02-2 planında](../p02-2-delivery-plan.md) hazırlandı; ADR-0024/0025 Accepted; bağımsız yerel dilimler yetkili, ilgili provider/otorite kabulü açıkken remote kartlar draft kalır. [Current](../current.md#sıradaki-iş-ve-kalan-kapsam) sonraki adımı gösterir.

[P02-2t](p02-2t-public-upload-workflows.md), s salt okuma kabulünden sonra ortak CLI/Python ve dar public sonuç/niyet görünümünü iki fresh turla tamamladı; [kanonik yüzey](../../reference/dataset-upload-public.md) uygulanmıştır.

Durum kart metadata’sında ve onunla denetlenen faz satırındadır; indeks durumu tekrar etmez. Aktif/sonraki iş için [current](../current.md#sıradaki-iş-ve-kalan-kapsam) kanoniktir. Diğer P02 kartları karar/endpoint kanıtları geldikçe hazırlanır; uzak fazlar için boş kart yığını üretilmez. Kart, kanıtıyla birlikte korunur.

Önceki P01 epiklerinin alt kart/PR eşlemesi [P01-2](../p01-2-delivery-plan.md), [P01-3](../p01-3-delivery-plan.md) ve [P01-4](../p01-4-delivery-plan.md) planlarındadır. Store şeması/merge/CI geçmişi ilgili kabul kayıtlarından izlenir; bu indeks ikinci durum veya kanıt kaynağı değildir.
