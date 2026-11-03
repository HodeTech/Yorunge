# Referans sözleşmeler

**Durum:** CLI/config/capability yerel alt kümeleri uygulandı; tam yürütme/araç portları tasarım. **Tarih:** 2026-11-03.

| Belge | Kanonik tanım |
|---|---|
| [Yerel kullanım rehberi](local-workflows.md) | Çalışan CLI/Python örnekleri, profil, keşif, plan ve jobs akışları |
| [CLI](cli-contract.md) | Komut aileleri, çıktı ve çıkış kodları |
| [Yapılandırma](configuration.md) | Profil/reçete, öncelik ve doğrulama |
| [Context keşfi](context-discovery.md) | Accepted ADR-0020/0021/0022: uygulanmış dar LLM terms/Platform ID-liste-seçim gözlemi, kapalı wire/target/snapshot ve state sınırı; unknown/unverified/no-authority, PR/CI ayrı |
| [Yerel veri manifesti](dataset-manifest.md) | Accepted ADR-0023’e bağlı inspect/verify, Manifest v1, bounded dosya ve no-clobber çıktı; PR #13 ile development’a teslim edildi, kabul durumu bağlı sözleşmede |
| [Private dataset aktarımı](dataset-transfer.md) | Accepted ADR-0024/0025: ayrı transfer/aşama/target taslağı; ürün kodu veya kapanmış endpoint wire değildir |
| [Araç sağlayıcısı](tool-provider-contract.md) | Görev, plan, execution ve sonuç sınırı |
| [Yetenek kaydı](capability-record.md) | Destek, kapsam, kanıt ve güncellik |
| [CapabilityScopeV2](capability-scope-v2.md) | Uygulandı — ADR-0013'e bağlı kapalı wire, nullability, sıralama ve kanonik anahtar; P01-3 kabulü tamamlandı |
| [Credential binding v1](credential-binding-v1.md) | Uygulandı — ortak hedef/UNIQUE/HMAC, kalıcı gözlem ve byte vektörleri; Accepted ADR-0012 |
| [Execution planı v2](execution-plan.md) | Uygulandı — ayrı kalıcı prepare/list/show/validate, descriptor input, güncel validity ve açık digest onayı/yönetim; P01-3 kabulü tamamlandı |
| [Yerel state](local-state.md) | Store/migration/backup, açık reset/restore/recover ve koruma sınırı |
| [Operation/jobs](operations.md) | ADR-0016 çekirdeği ve yerel list/show verified; PR #10 ile development'a teslim edildi; [merge/CI kanıtı](../research/p01-4-implementation-validation.md#development-merge-kapanışı) |
| [HTTP taşıma](http-transport.md) | Çalışma dalında verified — ADR-0017; hedef/sır/deadline/retry ve owned async session; gerçek TLS/kurulu artifact kabulü |
| [Akış sonucu](stream-results.md) | Çalışma dalında verified — ADR-0018; kapalı event, terminal/EOF, NDJSON ve yerel iptal; CLI/Python ve gerçek süreç kabulü |
| [Upload v2](dataset-upload-v2.md) | ADR-0026 Accepted: exact-work maliyet, policy reducer ve v2 gate/uyumluluk; yerel g–k kabulü ilgili kartta, public/live ayrı |
| [Platform upload tüketicisi](platform-upload-consumer.md) | Gerçek context/create/link codec'inin dar oracle'ı; grant/fiyat üretmez, upload wire ve bütünleşik kabul ayrı |
| [Upload input/current hazırlığı](dataset-upload-preparation.md) | O kartının tam hash/metadata ve gerçek provider hazırlık sınırı; uygulama durumu ilgili dilimde |
| [Upload HTTP effect portu](dataset-upload-port.md) | P02-2q yerel verified effect/metadata, intent/quota/receipt ve cleanup sınırı |
| [Upload original koordinatörü](dataset-upload-workflow.md) | P02-2r yerel verified original composition, current memo, worker, proof ve hata sınırı |
| [Upload salt okuma uzlaştırması](dataset-upload-reconciliation.md) | P02-2s yerel verified preflight/current/read lease/proof ve source hata sınırı |
| [Upload CLI/Python](dataset-upload-public.md) | P02-2t uygulama öncesi dar public summary, requested-intent review ve ortak kullanım senaryoları |
| [Upload HTTP bütçeleri](dataset-upload-http.md) | V2 work limitlerinin gerçek HTTP çağrı/deneme/gövde yoluna bağlanması ve kayıtlı service URI; uygulama/kabul ilgili kartta |

Her belgenin başlangıcı uygulanmış alt kümeyi belirtir; kalan tasarımlar mevcut destek değildir. Çalışan başlangıç [README](../../README.md), tarihsel [ilk P01 kabulü](../research/p01-core-validation.md) ve [bf652f6 tarihsel kaynak kabulü](../research/p01-remaining-implementation-validation.md#kullanıcı-review-kapanışı) ile [ADR-0019/Sonar son kaynak kapanışı](../research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı) ayrı kayıtlardır.
