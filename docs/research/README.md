# Araştırma ve kanıtlar

**Güncellendi:** 2026-10-27. Bu bölüm dış kaynak, gözlem ve açık soruları taşır; uygulanmış ürün sözleşmesi değildir.

- [Kanıt ve referans kaydı](evidence-register.md): resmî EVREN kaynakları, ForgeLM, muadil araç belgeleri ve referans repo yapıları.
- [Doğrulama soruları](validation-questions.md): kullanıcı görevleri, API erişimi, muadil araç ve runtime geçiş kapıları.
- [P01 ilk dilim kabulü](p01-core-validation.md): yerel test/build/temiz kurulum ve performans kanıtı; [ham başlangıç ölçümü](p01-startup.json).
- [Dal/PR/koruma kabulü](branch-workflow-validation.md): development kurulumu, gerçek GitHub CI ve koruma geri okuma kanıtı.

26 Ekim'deki öncül araştırma LLM/ForgeLM akışını öne almıştı. 27 Ekim kullanıcı talimatı Yörünge'yi EVREN kapsamlı yardımcı araç olarak konumlandırdı ve ForgeLM'i ilgili görevlerin seçilebilir varsayılanı yaptı. Güncel ürün yönü [ADR-0001](../decisions/0001-platform-companion.md) ve [ADR-0002](../decisions/0002-forgelm-default-open-tools.md) ile kayıtlıdır.

Ham özel veriler, API anahtarları ve başka checkout'a bağlı kişisel dosya yolları bu depoya alınmaz. Kayıtların amacı kanıtın türünü, tarihini ve neyi doğrulamadığını görünür tutmaktır.
