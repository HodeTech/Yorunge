# Mevcut durum ve sıradaki iş

**Güncellendi:** 2026-10-27.

## Bugün

- Devirdeki Git durumu doğrulandı: `Master`, temiz çalışma ağacı ve `6ec4b16` belge temeli commit'i mevcuttu. İlk uygulama `feat/offline-core` dalında `bb67b3a` ile kaydedildi.
- Kullanıcı onayıyla `development`, Master belge temelinden oluşturuldu ve varsayılan dal yapıldı. [PR #1](https://github.com/HodeTech/Yorunge/pull/1) merge commit ile development'a alındı. Koruma ve CI doğrulaması [canlı kayıtta](../research/branch-workflow-validation.md); [kanonik politika](../standards/git-release.md). `Master` birleştirmesi kullanıcıda kalır.
- P00 tamamlandı. İlk çalışan dilim: Python paketi/konsol girişi, yerel TOML context, dar YAML reçetesi, dört durumlu capability görünümü, araç seçimi ve digest'li çevrimdışı plan. CLI/Python API ortak kullanım senaryolarına bağlı.
- Plan yalnız şema/seçim düzeyinde doğrulanır; `draft`, `executable=false`, `inputs_verified=false`. Adaptör, uzak yetki, veri/model içeriği ve yürütme desteği iddia edilmez. Sahte eğitim başarısı üretilmez.
- P01-1 paket/CLI/şema/build kısmı tamamlandı; HTTP seçimi kapsam gereği P01-5'e bırakıldı. P01-2/P01-3'ün dar yerel alt kümeleri ve P01-6 kontrol altyapısı eklendi. P01 bütünü tamamlanmadı.
- Yerel test, tip/lint/format, dağıtım/temiz kurulum ve başlangıç kanıtı [kabul kaydında](../research/p01-core-validation.md). İlk PR'da 100 test ve bütün CI kontrolleri Ubuntu/Python 3.11'de geçti. Metadata kontrolü PR #2'de doğrulandı; iki dalda `offline-core` ve `branch-policy` zorunlu. Yayımlanmış paket yok.
- Genel belge ve paket girdileri izin listeleriyle sınırlandırıldı; yerel analiz arşivi üretim girdisi değildir. Site/doküman yayın sistemi henüz yoktur.
- Aktif ürün kodlaması öncesi roadmap ve ajan hazırlığı gözden geçirildi; [bulgu ve karar kaydı](../research/roadmap-readiness-review.md). P01 bağımlılık sırası ve uzak fazların paket sınırı netleştirildi. Bu hazırlık yeni ürün capability'si uygulamaz.
- P01-1 kapanış düzeltmeleri ve bağımsız review turları tamamlandı; [P01-1a teslim kaydı](tasks/p01-1a-core-acceptance-hardening.md). Kullanıcı [PR #4](https://github.com/HodeTech/Yorunge/pull/4)'ü `3d3c86b` merge commit'iyle development'a aldı; [merge sonrası CI](https://github.com/HodeTech/Yorunge/actions/runs/40489316036) başarılı. Kapanış belgeleri [PR #5](https://github.com/HodeTech/Yorunge/pull/5) ile `83bcd83` tabanına alındı. P01-1 kapsamında açık iş kalmadı; P01 bütünü devam ediyor.

## Tamamlanan P01-2 ve sıradaki somut iş

**P01-2 tamamlandı ve [PR #6](https://github.com/HodeTech/Yorunge/pull/6) kullanıcı tarafından 2026-10-27 tarihinde development'a alındı:** [merge c042383](https://github.com/HodeTech/Yorunge/commit/c042383178c051fa2ea9e895d5179e681f8450f1). P01-2a, P01-4a, P01-2b ve P01-2c verified; bu pakette açık uygulama/kabul işi kalmadı. Beş uygulama adımı, ikişer bağımsız review turu ve sonraki PR bulgularının kapanış kanıtı [uygulama kaydındadır](../research/p01-2-implementation-validation.md#development-merge-kapanışı).

Teslim edilenler: hizmete bağlı tek env çözümleme/hedef kapısı; güvenli SQLite store, migration ve backup; kalıcı credential kimliği/nesli ve açık reset/restore/recover; config init/profil/proje yönetimi ve yerel doctor. Son ürün head'i ca9502c'de 837 test, lint/type, iki temiz kurulum ve başlangıç bütçeleri geçti. Bu yerel kabuller uzak auth/hesap keşfi, HTTP, capability cache, execution geçerliliği veya operation/lease teslimi sayılmaz. Eski offline Plan biçimi/yürütülemezliği korunur.

**Sıradaki ürün paketi P01-3:** P01-3a kapsam/kanıt/tazelik bağlı capability cache ve P01-3b execution planı/onay bağı. Doğrudan önkoşullar P01-2b/P01-4a development'ta tamamlandı. İki alt iş hâlâ draft; önce kapsam/kabul ve karar boşlukları iş kartlarıyla netleştirilecek, ardından tek development PR'ında uygulanacak. Bu kapanış işi P01-3 planlama veya implementasyonunu başlatmaz.

Ardından P01-4'te operation/attempt, lease/fencing, unknown uzlaştırma ve jobs; P01-5'te HTTP/SDK, akış ve iptal; P01-6'da bütün P01 kabulü/destek matrisi kalır. P01-4a ve P01-6a yeniden yapılacak işler değildir. [Kesin sıra](phase-01-core.md), [ajan rehberi](../../.agents/README.md). Master/release aktarımı kullanıcıda kalır; henüz paket yayını yoktur.

Paralel ürün araştırması P02 veri/çıkarım görevlerinin güncel EVREN sözleşmesini doğrular. Gerçek ForgeLM/muadil adaptörleri P03'tedir; plan seçim desteği adaptör desteği değildir.

## Çözülmemiş dış sorular

EVREN workspace genel kullanıcı erişimi, haricî paket/araç kurulumu, kalıcı artefakt, managed LLM eğitim API'si ve kullanıcı LLM serving sözleşmesi. Bunlar ilgili özelliklerin durumunu sınırlar. [Araştırma soruları](../research/validation-questions.md), [backlog](backlog.md).
