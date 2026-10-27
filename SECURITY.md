# Güvenlik bildirimi

**Durum:** Yayımlanmış Yörünge sürümü yoktur; henüz desteklenen çalışma zamanı sürümü listelenmez.

Ana özel bildirim adresi [GitHub güvenlik bildirim formudur](https://github.com/HodeTech/Yorunge/security/advisories/new). **27 Ekim 2026 kontrolü:** [GitHub API durum sorgusu](https://api.github.com/repos/HodeTech/Yorunge/private-vulnerability-reporting) `enabled: false` döndürdü; form henüz kullanılabilir kanal olarak doğrulanmış değildir. Depo yöneticisinin özel güvenlik bildirimini etkinleştirip yetkili oturumla formun açıldığını doğrulaması gerekir. Bu belge değişikliği depo ayarını etkinleştirmez.

Etkinleştirme yolu: Settings → Advanced Security → Private vulnerability reporting → Enable. [GitHub'ın resmî yönergesi](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository) bu ayarı ve bildirim erişimini açıklar. Form erişimi ile bakım ekibinin bildirimleri alması ayrı kontrol edilmelidir; deneme raporu göndermek bu belge çalışmasının kapsamında değildir.

**Yayın öncesi açık koşul:** Ana kanalın kullanılabilirliği ve bakım ekibinin izlediği doğrudan özel bir yedek kanal doğrulanmalı; doğrulama tarihi ve yedek adres burada yayımlanmalıdır. Henüz doğrulanmış yedek kanal yoktur. Bu koşul tamamlanana kadar sır veya istismar ayrıntısını herkese açık issue/yorumda paylaşmayın. Henüz yanıt/düzeltme süresi taahhüdü yoktur.

Bildirimde etkilenen commit/sürümü, önkoşulları, etkiyi ve sahte veriyle yeniden üretim adımlarını paylaşın. API anahtarı, kişisel veri, özel veri seti veya model ağırlığı göndermeyin.

## Tasarlanan sınırlar

- Platform ve LLM sırları farklı hizmet bağlamlarında kullanılır; hedef ve yönlendirme denetimi uygulanır.
- Dosya yolları, sembolik bağlar, arşiv boyutları ve uzak indirmeler sınırlandırılır.
- Haricî araçlar açık seçim ve doğrulanmış manifestle çalışır; keyfî shell komutu araç sağlayıcısı sayılmaz.
- Belirsiz yan etkili çağrı körlemesine tekrarlanmaz; işlem kaydı ve uzlaştırma gerekir.

Bunlar tasarım gerekleridir; bugün uygulanan koruma iddiası değildir. Ayrıntılar: [güvenlik standardı](docs/standards/security.md), [entegrasyon sınırları](docs/architecture/integration-boundaries.md).
