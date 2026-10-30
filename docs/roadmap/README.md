# Yol haritası

**Güncellendi:** 2026-10-31. Fazlar kapsam ve kabul kapılarıdır; takvim veya yayın taahhüdü değildir. Bugünkü uygulama [current](current.md) ve [matriste](../capability-matrix.md), geliştirmeye hazır iş ise iş kartında gösterilir.

| Faz | Kullanıcı sonucu | Bugünkü durum | Fazın sınırı |
|---|---|---|---|
| [P00](phase-00-foundation.md) | Ürün ve belge temeli | Tamamlandı; tarihsel kanıt | Ürün çalışıyor iddiası yok |
| [P01](phase-01-core.md) | Güvenilir yerel çekirdek ve taşıma/durum sözleşmesi | Tamamlandı; PR #11 ile development’a teslim edildi | Gerçek EVREN veya eğitim adaptörü değil |
| [P02](phase-02-data-and-inference.md) | Veri aktarımı, katalog ve native çıkarım | P02-0a araştırması ve P02-0c LLM yerel verified; P02-0 partial, Platform raw sözleşmesi ve bütünleşik PR/CI kabulü açık | Canlı endpoint/hesap ve yeni kararlar ilgili tüketicide kapılı |
| [P03](phase-03-training-and-tools.md) | Yönetilen eğitim ve ForgeLM + bir muadil | Planlandı; iki bağımsız hat | Runtime erişimi varsayılmaz |
| [P04](phase-04-automation-and-hardening.md) | Seçilmiş ileri işler ve yayın kabulü | Planlandı; koşullu hatlar | Bütün opsiyonel işler ilk yayın önkoşulu değil |

## Hazır iş paketi

Faz tablosundaki iş satırı bir epik veya alt teslimdir; bütün faz tek uygulama birimi değildir. Anlamlı yeni uygulama için tek gözden geçirilebilir kullanıcı sonucunu [iş kartı şablonuyla](task-template.md) daralt. Aktif/yakın kartlar [tasks indeksinde](tasks/README.md) tutulur. Rutin yazım/bağlantı düzeltmesi yeni kart veya ADR gerektirmez. Henüz ayrıntılandırılmamış gelecek işler için boş dosyalar oluşturulmaz.

| İş durumu | Anlamı |
|---|---|
| `draft` | Sınır, karar veya kabul henüz tamam değil; kod işine hazır sayılmaz |
| `ready` | Kapsam/kabul net, doğrudan bağımlılıklar kanıtlı; başlayabilir |
| `in_progress` | Yetkili iş fiilen başladı; current kartı işaret eder |
| `in_review` | Teslim ve kontroller hazır, inceleme/PR sonucu bekleniyor |
| `verified` | Kartın bütün kabulü kanıtlı; yayınlandığı anlamına gelmez |
| `blocked` | Adlandırılmış dış koşul/karar yüzünden ilerleyemiyor; açılma ölçütü kayıtlı |
| `deferred` | Bilinçli ertelendi; ilk teslimin gizli önkoşulu değil |
| `partial` | Yalnız epik/üst işte: bazı alt işler tamam, bütünü değil |

Bu durumlar ürün matrisindeki teslim durumlarından ve runtime capability enum'larından ayrıdır. `ready` için: kullanıcı sonucu + giren/girmeyen kapsam + tamamlanmış bağımlılık kanıtı + olumlu/negatif kabul + uygun test/ölçüm + gerekli dış yetki/karar bulunmalı. Bu koşullar `in_progress`, `in_review` ve `verified` durumlarında da korunur. Kritik karar eksikse uygulama değil, ayrı karar/araştırma paketi hazırlanır. Araştırma kartının `ready` olması, çıktısı olacak kararı önceden onaylanmış veya pilotu yetkili yapmaz; yalnız kendi kanıt toplama kapsamı başlayabilir. Hazırlık mevcut kullanıcı yetkisini iptal eden genel bir onay kapısı değildir.

## Ne kadar iş alınır?

Büyüklük takvim tahmini değil, inceleme birimi sınırıdır: **S** tek sözleşme/tek dar sonuç, **M** birkaç bağlı sınır, **L** birden çok bağımsız sonuç veya dış sözleşme belirsizliği. L iş koddan önce S/M alt işlere bölünür; alt iş ile PR sınırı aynı olmak zorunda değildir. Ağır test veya yeni bilinmez ortaya çıkarsa kabulü sessizce küçültmek yerine bölünme/karar kaydedilir. Saat/gün ve canlı pilot maliyeti, ilgili paket somutlaşmadan uydurulmaz.

Mevcut ID'ler korunur; bölünme `P01-2a` gibi alt ID üretir. Faz özeti işi ve bağımlılığı, kart ayrıntılı kabulü, current aktif iş/sonraki adımı taşır. Aynı kabul listesi üç dosyada tutulmaz. `verified` geçişinde PR/commit ve gerçek kanıt bağlanır; eski tarihsel ölçümler silinmez.

## Epik başına PR

Kullanıcının 2026-10-27 tercihiyle P01-2 → P01-3 → P01-4 → P01-5 → P01-6 epik başına tek development PR'ında ilerler. Alt kartlar kabul/test/commit/review birimleridir; her biri için ayrı PR açılmaz. Paket koordinasyon planı kapsamı, iç sırayı ve bütünleşik kapanışı taşır; ayrıntılı alt kabul kartlarda kalır. [P01-2 teslim edildi](p01-2-delivery-plan.md); [P01-3 teslim edildi](p01-3-delivery-plan.md); [P01-4 plan/kartları](p01-4-delivery-plan.md) ADR-0016 Accepted sonrası uygulandı; dört adımın kabulü verified ve [PR #10 merge/CI kapanışı](../research/p01-4-implementation-validation.md#development-merge-kapanışı) ile development'a teslim edildi.

**2026-10-29 kapanış istisnası:** Kullanıcının kalan bütün P01 işleri talebiyle P01-5a/5b ve P01-6b [tek son pakette](p01-remaining-delivery-plan.md), mevcut feat/p01-5-transport dalından tek development PR'ında tamamlandı; PR #11 kullanıcı tarafından development’a birleştirildi. Ayrı kart/step/commit ve iki fresh review döngüleri korunur; önceki epiklerin geçmiş PR sınırları değişmez.

Aynı PR'daki sonraki alt iş, öncekinin gerçek kod/test/review kanıtı oluşunca başlayabilir; bağımlılığın ayrı PR'da merge edilmesi gerekmez. Yerel `verified` alt iş kaydı gerçek commit'e dayanır ve paket/PR durumunu olduğundan ileride göstermez. Epik, bütün alt işler ve bütünleşik kabul tamamlanmadan kapanmaz. Karar bekleyen alt iş taslak kalır; paket büyüklüğü hazır olma kontrolünü veya kullanıcı ADR onayını kaldırmaz.

Gerekli ortak temel, ihtiyaç duyan ilk epik PR'ında teslim edilir ve özgün ID'sinde işaretlenir: P01-4a P01-2 PR'ına dahildir; operation/lease/jobs P01-4'te kalır. Yerel doctor P01-2, HTTP tanılaması P01-5, gerçek hesap/proje keşfi P02-0b kapsamıdır. Epik numarası bütün altyapının ilk kez o PR'da yazılacağı anlamına gelmez.

## P02 paket akışı

P02-0a sözleşme/SDK/pilot **planı** ilk araştırma teslimidir; P02-0b gerçek hesap/context keşfi ayrı uygulama ve hesap kabulüdür. P02-0 üst satırı ikisini toplar; araştırma onayı canlı pilot yetkisi yerine geçmez. Kullanıcının 31 Ekim 2026 talebiyle P02-0a ve P02-0b, [P02-0 teslim planında](p02-0-delivery-plan.md) mevcut `feat/p02-0a-sdk-pilot` dalından **tek nihai development PR** içinde ele alınır. P01 kapanış belgeleri ve P02 hazırlığı da bu PR’a dahildir; yalnız belge kapanışı için ayrı PR açılmaz. Adım başına commit ve iki fresh review turu korunur.

Sonrasında varsayılan PR birimi P02-1, P02-2, P02-3, P02-4, P02-5, P02-6 ve P02-7 epikleridir. Alt kartlar aynı dalda adım/commit/kabul/review birimleridir; büyük epik tek kod adımı yapılmaz. Araştırma/ADR onayı veya ölçülen review büyüklüğü bölünmeyi gerektirirse PR sınırı paket planında **iş başlamadan** ilan edilir; kapsam küçültülmez. Önceki P01 PR sınırları tarihsel kalır. Kullanıcının uygulama talebindeki commit ve review döngüsü ilgili paket planına bağlanır; bu belge kendiliğinden ajan veya pilot başlatma yetkisi vermez.

Tek PR tercihi ayrı bir sonucu hazır olmadığı halde implementasyona alma gerekçesi değildir. Kullanılan ortak temel ilk gerçek tüketicinin PR’ında özgün ID/kabulüyle teslim edilebilir. [P02 alt bağımlılıkları](phase-02-data-and-inference.md#uygulama-birimleri-ve-sıra) belirleyicidir; bütün P02’nin bitmesi P03’ün bağımsız yerel araç hattının önkoşulu olmaz.

## Bağımlılık ve dış kapılar

P01 içindeki kesin sıra kendi belgesindedir. P02 sözleşme araştırması P01 ile ilerleyebilir; uzak yürütüm sağlam kimlik/taşıma/durum kapıları olmadan başlamaz. P03 native eğitim ve yerel araç hatları birbirini gereksiz yere bekletmez. EVREN workspace erişimi kapanırsa yerel araç, veri ve çıkarım işleri durmaz; workspace `unknown` kalır.

Dış hizmet işi bir güncel resmî sözleşme kaydı ve gerekiyorsa kapsamı/maliyeti yetkili pilot ister. CI fixture'ı canlı hesap kanıtı değildir. Eksik erişim için ilk adım yeni implementasyon veya başka ortama gizli geçiş değildir. Araştırma sonuçları [B kayıtlarına](backlog.md), feature durumu matrise bağlanır.

## Faz kapısı ve yayın kapısı

Bir faz kapanırken kullanıcı akışı, kontrollü hata/toparlanma, kaynak bütçesi ve belge uyumu birlikte değerlendirilir. Başlangıç, aktarım ve ağ bütçelerinin tek kaynağı [performans standardıdır](../standards/performance.md); UX kabulü ilgili iş kartında gözlenebilir göreve bağlanır. İlk pilot ölçümünde görev süresi, yardım/yanlış seçim ve çıktı bulunabilirliği kaydedilir; hedef belirlenmediyse kullanıcı kolaylığı geçmiş sayılmaz.

P01 offline kabulü, P02/P03 entegrasyon kabulü ve paket yayını ayrı kararlardır. [Ürün kapsamındaki ilk kullanılabilir hedefler](../product-scope.md#ilk-kullanılabilir-sürüm) korunur. Release adayı hangi görev/sürüm/ortamın gerçekten teslim edildiğini listeler; kapalı bir hedef kapsamdan sessizce çıkarılmaz, kullanıcıyla sürüm kapsamı kararı kaydedilir. P04'ün yayın hattı bu kararı, güvenlik/kurulum/recovery ve belge kapılarını toplar. Master aktarımı ve yayın kullanıcıdadır.

[Mevcut durum](current.md), [açık kararlar](backlog.md), [P02 hazırlık review’si](../research/p02-readiness-review.md), [ilk roadmap review’si](../research/roadmap-readiness-review.md), [ajan çalışma rehberi](../../.agents/README.md).
