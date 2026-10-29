# Mevcut durum ve sıradaki iş

**Güncellendi:** 2026-10-29.

## Tamamlanan ilk çekirdek

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

## Tamamlanan P01-3

**P01-3 tamamlandı/verified; takip uygulaması da development'a alındı.** Kullanıcı [PR #8](https://github.com/HodeTech/Yorunge/pull/8)'i [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa), ardından [PR #9](https://github.com/HodeTech/Yorunge/pull/9)'u **2026-10-28 16:04:25 Europe/Istanbul** tarihinde [merge a9f1f2e](https://github.com/HodeTech/Yorunge/commit/a9f1f2e12b49279d139b3c39bca2999e561b0b8d) ile birleştirdi. P01-3a/b ve dört uygulama adımı, ikişer bağımsız review turu ve PR düzeltmeleri tamamlandı. [PR #8 paket kapanışı](../research/p01-3-implementation-validation.md#development-merge-kapanışı) ve [PR #9 merge/CI kapanışı](../research/p01-3-implementation-validation.md#pr-9-development-merge-kapanışı) kanoniktir.

Teslim edilenler: tam ScopeV2/kanıt, kalıcı capability cache/TTL/kota/clock generation; ayrı immutable execution v2, descriptor üzerinden sınırlı input hash/root bağı, güncel validation, digest onayı/revoke/forget ve cache/plan/onay tüketicilerinin reset/restore/recover uyumu. Stateless offline v1 biçimi/digest'i korundu. ADR-0013/0014/0015 Accepted.

PR #9 ile store şeması **5**'e çıktı; bu P01-3'ün teslim sınırıdır. Global expiry indeksi başka cache/proof/conflict ve plan/onay sürelerinin gözlendikten sonra saat geri dönüşüyle yeniden etkinleşmesini önler. Migration 1–4'ün V1 kimlikleri korundu; yeni adımlar V2'dir. Tek dosyalı handler'ın hash'i doğrulanan aynı baytları import/pyc/modül önbelleği kullanılmadan çalışır. İki V2 uygulama adımı ikişer fresh review turuyla tamamlandı; [yoğun bütçe kabulünde](../research/p01-3-implementation-validation.md#v2-uygulaması--adım-2) 30/30 yeni store mevcut 5 s bütçesinde tamamlandı, en yavaş yol 3,473 s idi.

**PR #9 sonrası CI takibi kapandı:** a9f1f2e merge koşusunun 218,223 ms cache p95 reddi ve ikinci denemenin 200,926 ms sonucu tarihsel kanıttır; kayıtlar korunur. [Ölçüm güvenilirliği/CLI bakımı](../research/startup-ci-reliability.md) PR #10 ile development'a alındı. [805f8bd merge CI](https://github.com/HodeTech/Yorunge/actions/runs/40838856922), aynı-host AB/BA ve özgün 500/200 ms kapılarıyla geçti. Bu, bütün GitHub host'larında sabit süre garantisi değildir; önceki başarısız koşular başarıya çevrilmedi.

## Tamamlanan P01-4

**P01-4 tamamlandı ve development'a alındı.** Kullanıcı [PR #10](https://github.com/HodeTech/Yorunge/pull/10)'u **2026-10-29 10:58:15 Europe/Istanbul** tarihinde [merge 805f8bd](https://github.com/HodeTech/Yorunge/commit/805f8bd418847da6463408404a85675bdcb4173e) ile birleştirdi. P01-4a önceki PR #6'da tamamlanmıştı; [P01-4b](tasks/p01-4b-operation-coordination.md) ve [P01-4c](tasks/p01-4c-local-jobs.md) bu paketle verified ve teslim edildi. Dört adımın ikişer fresh review turu, sonraki PR/performans/kanıt düzeltmeleri ve merge kanıtı [kapanış kaydındadır](../research/p01-4-implementation-validation.md#development-merge-kapanışı). ADR-0016 Accepted; güncel development store şeması **6**'dır.

Teslim edilenler: kalıcı operation/attempt/terminal sonuç; admission/arm'da güncel credential/onay denetimi; lease/fencing ve ikinci gönderimi önleyen kalıcı dispatch latch; trusted unknown uzlaştırma; tarihçeyi koruyan reset preview v3; ortak CLI/Python yerel jobs list/show. Aynı geçerli gözlem geçmiş kotasını tüketmez; yeni kanıt/recovery ve son yetki/süre kapıları korunur. Public producer draft/blocked kalır; gerçek run, uzak watch/stop/reconcile ve EVREN/ForgeLM adaptörü bu teslim değildir.

Son PR head'i **36ae2a4** için offline-core/branch-policy/SonarCloud ve CodeRabbit başarılıdır. Merge sonrası [development CI](https://github.com/HodeTech/Yorunge/actions/runs/40838856922) **1.816 test / 204,52 s**, statik/belge/ajan, iki temiz kurulum ve başlangıç kapılarını geçti. Merge cache p95 aday/taban **191,569/193,882 ms**; CPU AMD EPYC 7763, disk unknown. Yerel ürün kabulünde **27/27 operation + 24/24 migration**, kurulu normal/yoğun jobs için 30-process p95 kapıları geçti. Yoğun reset referans marjı **148,292 ms** ile dardır; farklı host/I/O için kesin duvar saati garantisi değildir.

Ham ölçümler [manifest/indeks](../research/evidence.md) ve CI hash/özet denetimiyle kayıpsız arşivlenir; CodeRabbit yalnız raw dizinini dışlar, ajanlar hedefli kanıt incelemesi yapar. Başarısız ara ölçümler ve merge kaydı korunur. Arşivler sdist'e girmez; test vektörleri ve ölçüm kodu normal incelemede kalır. Development teslimi paket yayını değildir; Master/release aktarımı kullanıcıdadır.

## Aktif paket: kalan P01 kapanışı

**Dal:** `feat/p01-5-transport`, development `805f8bd` tabanında; P01-4 kapanış commit'i d686c8f korunur. Kullanıcının 2026-10-29 talebiyle **P01-5a + P01-5b + P01-6b tek nihai development PR'ında**, [altı adımlı planla](p01-remaining-delivery-plan.md) ele alınır. [Ön inceleme](../research/p01-remaining-readiness-review.md) ve üç kart hazırlandı; ADR-0017/0018, 2026-10-29 kullanıcı review'ü doğrulanıp düzeltildikten sonra verdiği açık yetkiyle Accepted. P01-5a verified: iki adım/ikişer fresh review ve ec2d202 runtime kaynağında iki artifact kurulumu kapandı. [Kabul kaydı](../research/p01-remaining-implementation-validation.md). P01-5b de adım3–4, ikişer fresh review, gerçek TLS/ayrı süreç ve 0bf70a4 runtime iki artifact NDJSON kabulüyle verified. P01-6b ready; adım5 bütünleşik faz kabulüne geçilir. Her adım commit ve iki farklı fresh review turuyla ilerler. Ayrı belge PR'ı/merge yapılmaz.

1. **P01-5a — HTTP/SDK seçimi ve ortak taşıma portu:** B01 ve SDK sınırı B03 ön incelemesi; TLS/hedef/redirect/sır koruması, tek retry/total deadline bütçesi ve gerçek loopback kabulü. Async HTTPX ve SDK'yı core'a almama kararı ADR-0017'de Accepted; Taşıma kartı verified; stream/CLI ve faz kapanışı tamamlanmadığı için paket/P01 bütünü verified değildir. Ücretli/canlı EVREN isteği bu yerel kabul değildir.
2. **P01-5b — Ortak sonuç/akış/iptal hattı:** Mevcut JSON zarfı üzerine JSON/NDJSON akışı, kesilme ve iptal ayrımı; gerçek loopback/süreç sınırında CLI/Python eşliği. Yerel izlemeyi bırakmak uzak işi durdurma sayılmaz.
3. **Ardından P01-6b — Faz kapanışı:** Bütün kabul kanıtları, kurulum/restart/hata/performans akışı ve gerçekten doğrulanmış ortam matrisi. P01-6a CI temeli tamamlandı; **P01 bütünü henüz tamamlanmadı**.

[Kesin sıra](phase-01-core.md), [ajan rehberi](../../.agents/README.md). Gerçek hesap keşfi/veri/çıkarım P02; ForgeLM/muadil araç adaptörleri ve uzak yürütme P03 kapsamındadır. Plan seçimi adaptör desteği değildir. Canlı EVREN, gerçek Windows veya fiziksel güç kesintisi kabulü iddia edilmez.

## Çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulumu, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar ilgili özelliklerin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).
