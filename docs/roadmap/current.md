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

**P01-3 tamamlandı/verified.** Kullanıcı [PR #8](https://github.com/HodeTech/Yorunge/pull/8)'i 2026-10-28 tarihinde development'a [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa) ile aldı. P01-3a/b ve dört uygulama adımı, her adımın ikişer bağımsız review turu ve sonraki PR düzeltmeleri tamamlandı. [Paket planı](p01-3-delivery-plan.md) ile [merge/kabul kaydı](../research/p01-3-implementation-validation.md#development-merge-kapanışı) kanoniktir. Bu pakette açık uygulama/kabul işi kalmadı.

Teslim edilenler: tam ScopeV2/kanıt, kalıcı capability cache/TTL/kota/clock generation; ayrı immutable execution v2; erken CWD/root/inode ve sınırlı descriptor hash bağı; güncel validation, digest onayı/revoke/forget; cache/plan/onay tüketicilerinin reset/restore/recover uyumu ve eski intent→schema 4 kurtarması. Kullanıcı review'inin beş davranış/kanıt bulgusu giderildi. ADR-0013/0014 ve ScopeV2 Accepted; eski stateless offline v1 biçimi/digest'i korundu.

Son PR head'i ef1d39a için offline-core, branch-policy ve SonarCloud başarılıdır. S8707 somut analiz akışı için issue düzeyinde False positive olarak kapatıldı; kural/kalite eşiği değiştirilmedi. [Merge sonrası development CI](https://github.com/HodeTech/Yorunge/actions/runs/40633876330) da başarılı: 1.159 test, format/lint/strict mypy/belge/ajan, wheel/sdist iki temiz kurulum ve dört başlangıç bütçesi geçti. 1.024 kayıtta cache p95 195,928 ms (AMD EPYC 9V74, disk unknown); önceki farklı donanımlardaki başarılı/başarısız ölçümler kayıtta korunur. 16 MiB/256 MiB/1 GiB tam hash kabulünde Python allocation peak yaklaşık 2 MiB'dir. İlk a086bb3 belge kapanışında ürün testleri yerelde tekrar çalıştırılmadı; doğrulanmış ürün/merge CI kanıtı kullanıldı. İzleyen CI düzeltmesi aşağıda ayrı kaydedilir.

Kapanış [PR #9](https://github.com/HodeTech/Yorunge/pull/9)'da aynı runtime'ın Linux cache p95'i 246,461 ms ile başarısız oldu. Kullanıcı talebiyle normal cache okumasındaki yinelenen kalıcı saat yazması, son clock/expiry/bağ kapıları korunarak azaltıldı; bu yolda kullanılmayan şemaların kurulumu ilk kullanıma ertelendi. Eşik, doğrulama veya dayanıklılık ayarı değiştirilmedi. İki düzeltmenin ikişer fresh review turu tamamlandı; 63194ed Linux CI'ında 1.164 test/iki temiz kurulum ve dört bütçe geçti (cache p95 192,426 ms, Intel Xeon 8573C/disk unknown). [Düzeltme ve ayrı doğrulama kaydı](../research/p01-3-implementation-validation.md#merge-sonrası-ci-düzeltmesi) kanoniktir; son belge head'i kendi PR kontrollerinden geçirilir. PR #8 ile tamamlanan P01-3 durumu korunur.

PR #9 dış review'inde, eski merge tabanında da bulunan kayıtlar arası clock boşluğu doğrulandı. Mevcut ADR garantisini tamamlayan şema 5/global expiry indeksi uygulandı: cache/proof/conflict ile plan/onay süreleri aynı terminal snapshot'ta korunur; bilinmeyen tüketici kapısı, TTL ve dayanıklılık değişmedi. Tam yerel takım 1.177 test ve iki normal/yoğun başlangıç koşusu başarılıdır; yeni kaynağın iki fresh review turu ve son head CI kapanışı [aynı kanonik kayıttan](../research/p01-3-implementation-validation.md#dış-review-kayıtlar-arası-clock-boşluğu-ve-global-fence) izlenir. Bu takip tamamlanırken PR #9 taslaktır; P01-3'ün PR #8 teslim durumu verified kalır.

Public producer eksik araç/uzak auth/tam girdi kapanışı nedeniyle draft/blocked kalır; plan hazırlığı ve onay altyapısı gerçek run/dispatch yetkisi değildir. Canlı EVREN, gerçek Windows veya fiziksel güç kesintisi doğrulaması iddia edilmez. Development teslimi paket yayını değildir; Master/release aktarımı kullanıcıda kalır.

**Sıradaki ürün paketi P01-4:** önce P01-4b operation/attempt, lease/fencing ve unknown uzlaştırma; sonra P01-4c yerel jobs list/show ve kalıcı sonuç okuma. P01-4a store/migration temeli önceki PR #6'da tamamlandı; yeniden uygulanmaz. P01-3b önkoşulu artık development'tadır. P01-4b/4c hâlâ draft kapsam satırlarıdır; sonraki adım bunları tek PR paket planı ve ölçülebilir iş kartlarına daraltmak, mevcut state/execution/restore kararlarını incelemek ve gereken yeni kararları koddan önce sunmaktır.

P01-4 sonrası P01-5a HTTP/SDK ve ortak taşıma, P01-5b JSON/NDJSON/iptal kullanım senaryosu hattı; ardından P01-6b bütün faz kabulü ve desteklenen ortam kaydı kalır. P01-6a CI temeli tamamlandı; P01 bütünü henüz tamamlanmadı. [Kesin sıra](phase-01-core.md), [ajan rehberi](../../.agents/README.md). [P01-3 hazırlık incelemesi](../research/p01-3-readiness-review.md) tarihsel karar kanıtıdır.

Paralel ürün araştırması P02 veri/çıkarım görevlerinin güncel EVREN sözleşmesini doğrular. Gerçek ForgeLM/muadil adaptörleri P03'tedir; plan seçim desteği adaptör desteği değildir.

## Çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulumu, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar ilgili özelliklerin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).
