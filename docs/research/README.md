# Araştırma ve kanıtlar

**Güncellendi:** 2026-10-27. Bu bölüm dış kaynak, gözlem ve açık soruları taşır; uygulanmış ürün sözleşmesi değildir.

- [Kanıt ve referans kaydı](evidence-register.md): resmî EVREN kaynakları, ForgeLM, muadil araç belgeleri ve referans repo yapıları.
- [Doğrulama soruları](validation-questions.md): kullanıcı görevleri, API erişimi, muadil araç ve runtime geçiş kapıları.
- [P01 ilk dilim ve kapanış kabulü](p01-core-validation.md): yerel test/build/temiz kurulum ve performans kanıtı; [ilk ham başlangıç ölçümü](p01-startup.json), [P01-1a ham ölçümü](p01-1a-startup.json).
- [Dal/PR/koruma kabulü](branch-workflow-validation.md): development kurulumu, gerçek GitHub CI ve koruma geri okuma kanıtı.
- [Roadmap ve ajan hazırlığı review'si](roadmap-readiness-review.md): bulgular, yapılan düzeltmeler, referans örüntüleri ve kalan kararlar.
- [P01-2 B02/B13 karar araştırması](p01-2-state-identity-decision-review.md): seçenekler, resmî kaynaklar ve kullanıcı onayıyla benimsenen ADR'ler; [tekrarlanabilir yerel probe](p01-2-state-identity-probe.py), [ham araştırma sonucu](p01-2-state-identity-probe.json). Ürün kabulü değildir.
- [P01-2 onay öncesi review kanıtı](p01-2-state-identity-decision-review.md#onay-öncesi-review-bulgularının-doğrulanması): bulgu doğrulaması/düzeltme kaydı; [ek probe](p01-2-review-probe.py) ve [ham sonuç/binding byte vektörleri](p01-2-review-probe.json). Ürün migration/restore kabulü değildir.
- [P01-2 uygulama ve kabul kaydı](p01-2-implementation-validation.md): adım/commit, iki yeni review turu, doğrulanmış bulgu ve gerçek ürün kanıtı; P01-2 teslim/kabulü tamamlandı; PR #6 development’a merge edildi, [merge/CI kapanışı](p01-2-implementation-validation.md#development-merge-kapanışı) kayıtlıdır.
- [P01-3 hazırlık incelemesi](p01-3-readiness-review.md): mevcut belge/kod audit'i, resmî teknik kaynaklar, onay öncesi Proposed ADR geçmişi ve uygulama öncesi karar sınırı; ADR'ler daha sonra kullanıcı onayıyla Accepted; ürün kabulü değildir.
- [P01-3 uygulama/kabul kaydı](p01-3-implementation-validation.md): kullanıcı ADR onayı, gerçek cache/plan/onay/state/CLI testleri ve dört adım ve review kabulü tamamlandı; [PR #8](https://github.com/HodeTech/Yorunge/pull/8) kullanıcı incelemesine açık, development merge bekleniyor. [İlk cache başlangıç ölçümü](p01-3-step-1-startup.json), [son 1.024 kayıt ölçümü](p01-3-final-startup.json), [büyük input hash/bellek ölçümü](p01-3-input-memory.json), [ilk Linux cache bütçe reddi](p01-3-linux-startup-initial.json), [lazy YAML sonrası yerel ölçüm](p01-3-import-startup.json).
- [P01-2 adım 1 başlangıç ham ölçümü](p01-2-step-1-startup.json): ikinci review turunun son ürün head'inde ayrı süreçlerle ölçüm; ortam/yöntem ve kapsam uygulama kabul kaydındadır.
- [P01-2 adım 2 başlangıç ham ölçümü](p01-2-step-2-startup.json): store/migration adımının son ürün head'inde ayrı süreçlerle ölçüm; kapsam uygulama kabul kaydındadır.

26 Ekim'deki öncül araştırma LLM/ForgeLM akışını öne almıştı. 27 Ekim kullanıcı talimatı Yörünge'yi EVREN kapsamlı yardımcı araç olarak konumlandırdı ve ForgeLM'i ilgili görevlerin seçilebilir varsayılanı yaptı. Güncel ürün yönü [ADR-0001](../decisions/0001-platform-companion.md) ve [ADR-0002](../decisions/0002-forgelm-default-open-tools.md) ile kayıtlıdır.

Ham özel veriler, API anahtarları ve başka checkout'a bağlı kişisel dosya yolları bu depoya alınmaz. Kayıtların amacı kanıtın türünü, tarihini ve neyi doğrulamadığını görünür tutmaktır.

- [P01-3 ikinci Linux başlangıç ölçümü](p01-3-linux-startup-second.json): farklı runner CPU ortamı; 200 ms cache bütçesi başarısız, ilk kayıt korunur.

- [P01-3 Linux doğrulanmış başlangıç ölçümü](p01-3-linux-startup-verified.json): 83f70a8 CI koşusu, 1.024 fresh kayıt ve 30 süreçte bütün bütçeler geçti; runner farkı kayıtlıdır.

- [P01-3 review sonrası input hash/bellek ölçümü](p01-3-reviewed-input-memory.json): hasher yardımcı ayrımı sonrası üç boyutta bağımsız tam içerik doğrulaması ve sınırlı bellek.
