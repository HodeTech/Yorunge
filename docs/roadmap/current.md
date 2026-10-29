# Mevcut durum ve sıradaki iş

**Güncellendi:** 2026-10-28.

## Bugün

- Devirdeki Git durumu doğrulandı: `Master`, temiz çalışma ağacı ve `6ec4b16` belge temeli commit'i mevcuttu. İlk uygulama `feat/offline-core` dalında `bb67b3a` ile kaydedildi.
- Kullanıcı onayıyla `development`, Master belge temelinden oluşturuldu ve varsayılan dal yapıldı. [PR #1](https://github.com/HodeTech/Yorunge/pull/1) merge commit ile development'a alındı. Koruma ve CI doğrulaması [canlı kayıtta](../research/branch-workflow-validation.md); [kanonik politika](../standards/git-release.md). `Master` birleştirmesi kullanıcıda kalır.
- P00 tamamlandı. İlk çalışan dilim: Python paketi/konsol girişi, yerel TOML context, dar YAML reçetesi, dört durumlu capability görünümü, araç seçimi ve digest'li çevrimdışı plan. CLI/Python API ortak kullanım senaryolarına bağlı.
- Offline v1 plan yalnız şema/seçim düzeyinde doğrulanır; `draft`, `executable=false`, `inputs_verified=false`. Adaptör, uzak yetki, veri/model içeriği ve yürütme desteği iddia edilmez. Sahte eğitim başarısı üretilmez.
- P01-1 paket/CLI/şema/build kısmı tamamlandı; HTTP seçimi kapsam gereği P01-5'e bırakıldı. P01-2/P01-3'ün dar yerel alt kümeleri ve P01-6 kontrol altyapısı eklendi. P01 bütünü tamamlanmadı.
- Yerel test, tip/lint/format, dağıtım/temiz kurulum ve başlangıç kanıtı [kabul kaydında](../research/p01-core-validation.md). İlk PR'da 100 test ve bütün CI kontrolleri Ubuntu/Python 3.11'de geçti. Metadata kontrolü PR #2'de doğrulandı; iki dalda `offline-core` ve `branch-policy` zorunlu. Yayımlanmış paket yok.
- Genel belge ve paket girdileri izin listeleriyle sınırlandırıldı; yerel analiz arşivi üretim girdisi değildir. Site/doküman yayın sistemi henüz yoktur.
- Aktif ürün kodlaması öncesi roadmap ve ajan hazırlığı gözden geçirildi; [bulgu ve karar kaydı](../research/roadmap-readiness-review.md). P01 bağımlılık sırası ve uzak fazların paket sınırı netleştirildi. Bu hazırlık yeni ürün capability'si uygulamaz.
- P01-1 kapanış düzeltmeleri ve bağımsız review turları tamamlandı; [P01-1a teslim kaydı](tasks/p01-1a-core-acceptance-hardening.md). Kullanıcı [PR #4](https://github.com/HodeTech/Yorunge/pull/4)'ü `3d3c86b` merge commit'iyle development'a aldı; [merge sonrası CI](https://github.com/HodeTech/Yorunge/actions/runs/40489316036) başarılı. Kapanış belgeleri [PR #5](https://github.com/HodeTech/Yorunge/pull/5) ile `83bcd83` tabanına alındı. P01-1 kapsamında açık iş kalmadı; P01 bütünü devam ediyor.

## Tamamlanan P01-2

**P01-2 tamamlandı ve [PR #6](https://github.com/HodeTech/Yorunge/pull/6) kullanıcı tarafından 2026-10-27 tarihinde development'a alındı:** [merge c042383](https://github.com/HodeTech/Yorunge/commit/c042383178c051fa2ea9e895d5179e681f8450f1). P01-2a, P01-4a, P01-2b ve P01-2c verified; bu pakette açık uygulama/kabul işi kalmadı. Beş uygulama adımı, ikişer bağımsız review turu ve sonraki PR bulgularının kapanış kanıtı [uygulama kaydındadır](../research/p01-2-implementation-validation.md#development-merge-kapanışı).

Teslim edilenler: hizmete bağlı tek env çözümleme/hedef kapısı; güvenli SQLite store, migration ve backup; kalıcı credential kimliği/nesli ve açık reset/restore/recover; config init/profil/proje yönetimi ve yerel doctor. Son ürün head'i ca9502c'de 837 test, lint/type, iki temiz kurulum ve başlangıç bütçeleri geçti. Bu yerel kabuller uzak auth/hesap keşfi, HTTP, capability cache, execution geçerliliği veya operation/lease teslimi sayılmaz. Eski offline Plan biçimi/yürütülemezliği korunur.

## Tamamlanan P01-3 ve sıradaki paket

**P01-3 tamamlandı/verified; takip uygulaması da development'a alındı.** Kullanıcı [PR #8](https://github.com/HodeTech/Yorunge/pull/8)'i [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa), ardından [PR #9](https://github.com/HodeTech/Yorunge/pull/9)'u **2026-10-28 16:04:25 Europe/Istanbul** tarihinde [merge a9f1f2e](https://github.com/HodeTech/Yorunge/commit/a9f1f2e12b49279d139b3c39bca2999e561b0b8d) ile birleştirdi. P01-3a/b ve dört uygulama adımı, ikişer bağımsız review turu ve PR düzeltmeleri tamamlandı. [PR #8 paket kapanışı](../research/p01-3-implementation-validation.md#development-merge-kapanışı) ve [PR #9 merge/CI kapanışı](../research/p01-3-implementation-validation.md#pr-9-development-merge-kapanışı) kanoniktir.

Teslim edilenler: tam ScopeV2/kanıt, kalıcı capability cache/TTL/kota/clock generation; ayrı immutable execution v2, descriptor üzerinden sınırlı input hash/root bağı, güncel validation, digest onayı/revoke/forget ve cache/plan/onay tüketicilerinin reset/restore/recover uyumu. Stateless offline v1 biçimi/digest'i korundu. ADR-0013/0014/0015 Accepted.

PR #9 ile development'ın güncel store şeması **5** oldu. Global expiry indeksi başka cache/proof/conflict ve plan/onay sürelerinin gözlendikten sonra saat geri dönüşüyle yeniden etkinleşmesini önler. Migration 1–4'ün V1 kimlikleri korundu; yeni adımlar V2'dir. Tek dosyalı handler'ın hash'i doğrulanan aynı baytları import/pyc/modül önbelleği kullanılmadan çalışır. İki V2 uygulama adımı ikişer fresh review turuyla tamamlandı; [yoğun bütçe kabulünde](../research/p01-3-implementation-validation.md#v2-uygulaması--adım-2) 30/30 yeni store mevcut 5 s bütçesinde tamamlandı, en yavaş yol 3,473 s idi.

**Açık teknik takip:** Son PR head'i cf852a1'de offline-core, branch-policy ve SonarCloud başarılıydı; cache p95 192,217 ms idi. Ancak [merge sonrası development CI](https://github.com/HodeTech/Yorunge/actions/runs/40693146816), **1.304 test**, lint/type/belge/ajan ve iki temiz kurulumu geçip cache p95 **218,223 ms** ile 200 ms kapısında başarısız oldu (AMD EPYC 7763/disk unknown). [İlk denemenin ham ölçümü](../research/p01-3-followup-merged-startup.json) korunur; incelenen ikinci GitHub denemesi de 200,926 ms ile başarısızdır. Bu bakımda yeni uzak koşu başlatılmadı ve eşik değiştirilmedi. Merge/ürün teslimi tamamlandı. Kullanıcının sonraki talebiyle [ölçüm güvenilirliği ve hedefli CLI bakımı](../research/startup-ci-reliability.md) bu dalda uygulanıp yerelde doğrulandı: aynı host'ta izole runtime wheel/venv ve AB/BA karşılaştırması, 1.325 test ve gerçek A/B + A/A ölçümleri tamamlandı. Dış CI performans takibi açık kalır; yeni Linux workflow çıktıları kullanıcı tercihiyle P01-4 bitimindeki PR/merge'de incelenecek, bu bakım için ayrı PR/merge beklenmez. Geçmiş başarılı head veya yerel sonuç merge CI'ı yerine kullanılmaz.

Güncel development tabanındaki `feat/p01-4-operations` dalı, PR #9 belge kapanışını ve başlangıç ölçümü/CLI bakımını taşır. Kullanıcının talebiyle ayrı PR açılmaz; bu commit'ler sonraki P01-4 PR'ında incelenir. Kullanıcı şimdi P01-4 uygulamasını istedi; [ön inceleme](../research/p01-4-readiness-review.md), [dört adımlı plan](p01-4-delivery-plan.md), iki iş kartı ve [Accepted ADR-0016](../decisions/0016-operation-admission-and-ownership.md) hazırlandı. 29 Ekim kullanıcı review düzeltmeleri ve iki fresh revizyon turu tamamlandı; ADR-0016 Accepted, P01-4b bu dalda verified; P01-4c adım 4 in_progress.

Public producer eksik araç/uzak auth/tam girdi kapanışı nedeniyle draft/blocked kalır; plan hazırlığı ve onay altyapısı gerçek run/dispatch yetkisi değildir. Canlı EVREN, gerçek Windows veya fiziksel güç kesintisi doğrulaması iddia edilmez. Development teslimi paket yayını değildir; Master/release aktarımı kullanıcıda kalır.

**Aktif hazırlık P01-4:** önce [P01-4b](tasks/p01-4b-operation-coordination.md) operation/attempt, lease/fencing ve unknown uzlaştırma; sonra [P01-4c](tasks/p01-4c-local-jobs.md) yerel jobs list/show ve kalıcı sonuç okuma. P01-4a store/migration temeli önceki PR #6'da tamamlandı; yeniden uygulanmaz. P01-3b önkoşulu development'tadır. ADR-0016 ve bağlı exact wire 29 Ekim yetkisiyle kabul edildi. Adım 1–3 ikişer fresh review turuyla kapandı; 1.594 full test, son kaynakta 27/27 operation ve 24/24 migration kabulü geçti. P01-4b bu dalda verified; adım 4 public jobs uygulandı; 1.686 full test, iki temiz kurulum, normal/yoğun 30-process 200 ms ve eşli startup kapıları geçti. İki fresh review turu ve son kaynak/paket PR kabulü otomatik ilerler.

P01-4 sonrası P01-5a HTTP/SDK ve ortak taşıma, P01-5b JSON/NDJSON/iptal kullanım senaryosu hattı; ardından P01-6b bütün faz kabulü ve desteklenen ortam kaydı kalır. P01-6a CI temeli tamamlandı; P01 bütünü henüz tamamlanmadı. [Kesin sıra](phase-01-core.md), [ajan rehberi](../../.agents/README.md). [P01-3 hazırlık incelemesi](../research/p01-3-readiness-review.md) tarihsel karar kanıtıdır.

Paralel ürün araştırması P02 veri/çıkarım görevlerinin güncel EVREN sözleşmesini doğrular. Gerçek ForgeLM/muadil adaptörleri P03'tedir; plan seçim desteği adaptör desteği değildir.

## Çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulumu, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar ilgili özelliklerin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).
