# Araştırma ve kanıtlar

**Güncellendi:** 2026-10-29. Bu bölüm dış kaynak, gözlem ve açık soruları taşır; uygulanmış ürün sözleşmesi değildir.

[Ham ölçüm indeksi](evidence.md) ve [manifest](evidence-manifest.json), kayıpsız arşivlerin review girişidir. Python ölçüm betikleri, bu raporlar ve testlerin okuduğu sabit JSON vektörleri normal incelemede kalır; `raw/` gzip dosyaları ayrı araçla doğrulanır. [Saklama/review/paket standardı](../standards/research-evidence.md). Önceki fazların kökteki ham kayıtları bu bakımda taşınmadı.

- [Kalan P01 uygulama ve faz kabulü](p01-remaining-implementation-validation.md#kullanıcı-review-kapanışı): altı adım/ikişer fresh review ve CI takibi tamamlandı; üç gerçek ortam/iki kurulum/son kaynak bütçeleriyle çalışma dalında verified. Development PR review/merge ve yayın ayrıdır; önceki başarısız ölçümler korunur.
- [Kalan P01 hazırlık incelemesi](p01-remaining-readiness-review.md): HTTP/SDK kaynak karşılaştırması, stream/iptal ve faz kabulü; ADR-0017/0018 kullanıcı review düzeltmeleri sonrası Accepted; ürün kabulü ayrı.
- [Kanıt ve referans kaydı](evidence-register.md): resmî EVREN kaynakları, ForgeLM, muadil araç belgeleri ve referans repo yapıları.
- [Doğrulama soruları](validation-questions.md): kullanıcı görevleri, API erişimi, muadil araç ve runtime geçiş kapıları.
- [P01 ilk dilim ve kapanış kabulü](p01-core-validation.md): yerel test/build/temiz kurulum ve performans kanıtı; [ilk ham başlangıç ölçümü](p01-startup.json), [P01-1a ham ölçümü](p01-1a-startup.json).
- [Dal/PR/koruma kabulü](branch-workflow-validation.md): development kurulumu, gerçek GitHub CI ve koruma geri okuma kanıtı.
- [Roadmap ve ajan hazırlığı review'si](roadmap-readiness-review.md): bulgular, yapılan düzeltmeler, referans örüntüleri ve kalan kararlar.
- [P01-2 B02/B13 karar araştırması](p01-2-state-identity-decision-review.md): seçenekler, resmî kaynaklar ve kullanıcı onayıyla benimsenen ADR'ler; [tekrarlanabilir yerel probe](p01-2-state-identity-probe.py), [ham araştırma sonucu](p01-2-state-identity-probe.json). Ürün kabulü değildir.
- [P01-2 onay öncesi review kanıtı](p01-2-state-identity-decision-review.md#onay-öncesi-review-bulgularının-doğrulanması): bulgu doğrulaması/düzeltme kaydı; [ek probe](p01-2-review-probe.py) ve [ham sonuç/binding byte vektörleri](p01-2-review-probe.json). Ürün migration/restore kabulü değildir.
- [P01-2 uygulama ve kabul kaydı](p01-2-implementation-validation.md): adım/commit, iki yeni review turu, doğrulanmış bulgu ve gerçek ürün kanıtı; P01-2 teslim/kabulü tamamlandı; PR #6 development’a merge edildi, [merge/CI kapanışı](p01-2-implementation-validation.md#development-merge-kapanışı) kayıtlıdır.
- [P01-3 hazırlık incelemesi](p01-3-readiness-review.md): mevcut belge/kod audit'i, resmî teknik kaynaklar, onay öncesi Proposed ADR geçmişi ve uygulama öncesi karar sınırı; ADR'ler daha sonra kullanıcı onayıyla Accepted; ürün kabulü değildir.
- [P01-3 uygulama/kabul kaydı](p01-3-implementation-validation.md): kullanıcı ADR onayı, gerçek cache/plan/onay/state/CLI testleri ve dört adım ve review kabulü tamamlandı; [PR #8](https://github.com/HodeTech/Yorunge/pull/8) development'a alındı; [merge/CI kapanışı](p01-3-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. [İlk cache başlangıç ölçümü](p01-3-step-1-startup.json), [son 1.024 kayıt ölçümü](p01-3-final-startup.json), [büyük input hash/bellek ölçümü](p01-3-input-memory.json), [ilk Linux cache bütçe reddi](p01-3-linux-startup-initial.json), [lazy YAML sonrası yerel ölçüm](p01-3-import-startup.json).
- [P01-2 adım 1 başlangıç ham ölçümü](p01-2-step-1-startup.json): ikinci review turunun son ürün head'inde ayrı süreçlerle ölçüm; ortam/yöntem ve kapsam uygulama kabul kaydındadır.
- [P01-3 merge sonrası CI düzeltmesi](p01-3-implementation-validation.md#merge-sonrası-ci-düzeltmesi): başarısız Linux cache ölçümü ve kalıcı clock checkpoint'i için aynı ortamda önce/sonra yerel kanıt; P01-3 tamamlanma durumu korunur.
- [Tarihsel ADR-0015 onay öncesi kullanıcı review'i](p01-3-implementation-validation.md#adr-0015-kullanıcı-reviewi--onay-öncesi-revizyon): revize Proposed karar, bağımsız expiry vektörleri ve kaynak/bytecode karşı örneği; V2 uygulama kabulü değildir.
- [V2 yoğun migration kabulü](p01-3-implementation-validation.md#v2-uygulaması--adım-2): 30 gerçek dosya/store koşusu, eski stage/live kurtarması, faz/VM/CPU kayıtları ve normal/yoğun başlangıç; [tekrarlanabilir probe](p01-3-migration-budget-probe.py). PR #9 development’a alındı; [merge sonrası CI bütçe reddi ve tarihsel takip](p01-3-implementation-validation.md#pr-9-development-merge-kapanışı) ayrı kayıtlıdır.
- [PR #9 development merge kapanışı](p01-3-implementation-validation.md#pr-9-development-merge-kapanışı): kullanıcı merge’i, şema 5/V2 teslimi ve 1.304 test/iki temiz kurulum; [merge head ham başlangıç ölçümü](evidence.md#p01-3-followup-merged-startup) cache p95 218,223 ms ile başarısızdır. Bu tarihsel reddin takibi [PR #10 merge/CI kapanışında](p01-4-implementation-validation.md#development-merge-kapanışı) kapandı.
- [Başlangıç CI güvenilirliği ve CLI bakım kabulü](startup-ci-reliability.md): izole frozen wheel ortamları, aynı-host AB/BA ölçümü, gerçek A/B ve A/A kontrolü; PR #10 ile development'a teslim edildi; Linux PR ve merge CI sonuçları [kapanışta](p01-4-implementation-validation.md#development-merge-kapanışı).
- [P01-4 uygulama öncesi inceleme](p01-4-readiness-review.md): üç bağımsız preflight, mevcut kod/Accepted sınırlar, operation/ownership ve jobs karar boşlukları; Proposed ADR-0016 ve ölçülebilir kart/plan hazırlığı, ürün kabulü değildir.
- [P01-4 uygulama/kabul kaydı](p01-4-implementation-validation.md): Accepted ADR-0016, dört adım/ikişer fresh review ve PR düzeltmeleri tamamlandı; P01-4b/4c verified; PR #10 development'a merge edildi. [Merge/CI kapanışı](p01-4-implementation-validation.md#development-merge-kapanışı) kanoniktir. [182f695 ürün kaynağı kapanışı](p01-4-implementation-validation.md#pr-10-son-kaynak-kapanışı): 1.779 test, iki temiz kurulum, 27/27 operation + 24/24 migration ve normal/yoğun 30-process jobs/paired startup geçti. Development PR/merge dış CI sonuçları ayrı izlenir.
- [P01-4 operation bütçe probe'u](p01-4-operation-budget-probe.py): yeni sentetik normal/azami terminal/karma store'larda fresh süreç, özgün 5 s deadline/callback, wall/RSS ve örneklenmiş VM callback quanta kaydı; [ilk ham 27 işlem](evidence.md#p01-4-step-3-operation-budget), [iki review sonrası 27 işlem](evidence.md#p01-4-step-3-reviewed-operation-budget) ve [son kaynak 24 migration](evidence.md#p01-4-step-3-reviewed-migration-budget); ürün/review kabulü uygulama kaydındadır.
- [P01-2 adım 2 başlangıç ham ölçümü](p01-2-step-2-startup.json): store/migration adımının son ürün head'inde ayrı süreçlerle ölçüm; kapsam uygulama kabul kaydındadır.

26 Ekim'deki öncül araştırma LLM/ForgeLM akışını öne almıştı. 27 Ekim kullanıcı talimatı Yörünge'yi EVREN kapsamlı yardımcı araç olarak konumlandırdı ve ForgeLM'i ilgili görevlerin seçilebilir varsayılanı yaptı. Güncel ürün yönü [ADR-0001](../decisions/0001-platform-companion.md) ve [ADR-0002](../decisions/0002-forgelm-default-open-tools.md) ile kayıtlıdır.

Ham özel veriler, API anahtarları ve başka checkout'a bağlı kişisel dosya yolları bu depoya alınmaz. Kayıtların amacı kanıtın türünü, tarihini ve neyi doğrulamadığını görünür tutmaktır.

- [P01-3 ikinci Linux başlangıç ölçümü](p01-3-linux-startup-second.json): farklı runner CPU ortamı; 200 ms cache bütçesi başarısız, ilk kayıt korunur.

- [P01-3 Linux doğrulanmış başlangıç ölçümü](p01-3-linux-startup-verified.json): 83f70a8 CI koşusu, 1.024 fresh kayıt ve 30 süreçte bütün bütçeler geçti; runner farkı kayıtlıdır.

- [P01-3 review sonrası input hash/bellek ölçümü](p01-3-reviewed-input-memory.json): hasher yardımcı ayrımı sonrası üç boyutta bağımsız tam içerik doğrulaması ve sınırlı bellek.

- [P01-3 kullanıcı review sonrası yerel başlangıç ölçümü](p01-3-review-startup.json): zorunlu cache fixture ile kanonik .local seed, 1.024 kayıt ve 30 süreçte dört bütçe geçti.
- [P01-3 kullanıcı review sonrası hash/bellek ölçümü](p01-3-review-memory.json): ilk fstat boyutuna bağlı strict read sınırıyla 16/256/1.024 MiB tam hash ve bellek doğrulaması.
- [P01-3 kullanıcı review sonrası Linux bütçe reddi](p01-3-review-linux-startup-failed.json): d9d1117, AMD EPYC 7763; test/build geçti, cache p95 218,042 ms başarısız. Profil tanısı CI logunda korunur.

- [P01-3 Sonar issue disposition ve gate makbuzu](p01-3-sonar-disposition.json): S8707 issue-bazlı False positive; kalite kapısı OK, kural/izin/eşik değişikliği yok.
- [P01-3 kullanıcı review sonrası başarılı Linux ölçümü](p01-3-review-linux-startup-passed.json): 27f6f27/AMD EPYC 9V45, dört bütçe geçti; önceki farklı-CPU başarısızlığı korunur.

- [P01-3 merge head başlangıç ölçümü](p01-3-merged-startup.json): e32cb42 development push CI'ı, 1.024 kayıt/30 süreç; ortam ve kabul sınırı merge kapanışındadır.

- [P01-4 kurulu jobs bütçe probe'u](p01-4-jobs-budget-probe.py): [ilk ham normal/yoğun ölçüm](evidence.md#p01-4-step-4-initial-jobs-budget), [iki temiz kurulum](evidence.md#p01-4-step-4-initial-installations), [eşli startup](evidence.md#p01-4-step-4-initial-startup) ve [30 yardım çıktısı eşliği](evidence.md#p01-4-initial-help-parity). İlk kaynak kabulü tarihsel; son kaynak yerel kabulü uygulama kaydındadır.

- [P01-4 ilk paket kabulü — tarihsel 17de965](p01-4-implementation-validation.md#son-kaynakla-bütünleşik-yerel-kabul): [operation 27 işlem](evidence.md#p01-4-final-operation-budget), [migration 24 işlem](evidence.md#p01-4-final-migration-budget), [kurulu jobs](evidence.md#p01-4-final-jobs-budget), [eşli startup](evidence.md#p01-4-final-startup), [iki ürün temiz kurulumu](evidence.md#p01-4-final-installations). Güncel ürün kaynağı kabulünün yerine geçmez.
- [PR #10 son kaynak kapanışı — ürün 182f695](p01-4-implementation-validation.md#pr-10-son-kaynak-kapanışı): [27 operation](evidence.md#p01-4-noop-operation-budget), [24 migration](evidence.md#p01-4-noop-migration-budget), [kurulu jobs](evidence.md#p01-4-noop-jobs-budget), [eşli startup](evidence.md#p01-4-noop-startup), [iki temiz kurulum](evidence.md#p01-4-noop-installations). Önceki başarısız kaynak ölçümleri kabul kaydında korunur; canlı EVREN, merge veya release kanıtı değildir.
