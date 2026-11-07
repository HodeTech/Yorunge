# P02 — Veri, katalog ve çıkarım

**Güncellendi:** 2026-11-06. **Durum:** [P02-0 paketi](p02-0-delivery-plan.md) ve bütün alt kartları verified; [PR #12](https://github.com/HodeTech/Yorunge/pull/12) kullanıcı tarafından [9f30fd2](https://github.com/HodeTech/Yorunge/commit/9f30fd2bad7c3495120b127fefd588b4458d0f07) ile development’a birleştirildi. [Merge/CI kapanışı](../research/p02-0-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. ADR-0022 onaylı nihai dar gözlem, ayrı gerçek LLM/Platform consumer kabulleri, iki fresh review döngüleri, kaynak bağlı M5 ve üç ortam CI tamamlandı. Public kimlik/yetki unknown/unverified; özgün doğrulanmış kimlik/bağ P02-R1’de açık kalır. P01 PR #11/bc9532c ile development’a teslim edildi; P02-1 ve bütün alt kartları verified; [PR #13](https://github.com/HodeTech/Yorunge/pull/13), 2 Kasım’da [50d68b1](https://github.com/HodeTech/Yorunge/commit/50d68b1deab80d6fe14749d556efde1f103b5759) ile development’a teslim edildi. [Merge/CI ve kanıt kapanışı](../research/p02-1-implementation-validation.md#development-merge-kapanışı) kayıtlıdır. P02-2 ve P02-2a/b/c verified; [PR #14](https://github.com/HodeTech/Yorunge/pull/14), 6 Kasım’da [94aaaf0](https://github.com/HodeTech/Yorunge/commit/94aaaf03e380381e95c9432de340378e23007e95) ile development’a teslim edildi. [Merge/CI ve kanıt kapanışı](../research/p02-2-implementation-validation.md#development-merge-kapanışı) kayıtlıdır; yetki, fiyat ve uzaktan byte doğrulaması P02-2 sonucunda kanıtlanmış sayılmaz. Etkin epik P02-3’tür: [teslim planı](p02-3-delivery-plan.md) ve ADR-0031/0032/0033 (Accepted, 2026-11-06) hazırdır; ürün kodu adım adım ilerler. P02-4–7 planlandı. **Yetenekler:** C01/C02 uzak gözlem alt kümesi, C03–C07, C11 okuma, C12/C13 entegrasyon.

## Kullanıcı sonucu ve kapsam

Veri sorumlusu doğru hesap/projede küçük klasörü private veri setine aktarır; kesintiden sonra aynı işi uzlaştırır, indirir ve doğrulama seviyesini görür. Uygulama geliştirici uygun model/görevle metin, stream, embedding/rerank veya görsel çıkarım sonucu ve bilinen kullanım bilgisini alır. Bu akışlar ForgeLM, Torch veya eğitim kurulumu gerektirmez.

Public görünürlük, silme, rezervasyon yazma, model warmup/benchmark gibi ek ücretli etkiler, görsel eğitim, OCR/ses, tool calling sonucu araç yürütme, notebook execution ve kullanıcı modeli serving bu fazın gizli kapsamı değildir. ZIP import/otomatik arşiv açma ilk normal-dosya yoluna eklenmez; gerekiyorsa ayrı kapsam/limit/kabul kararı gerekir. Mevcut CLI komutları bu hedeflerin uygulanmış yüzeyi sayılmaz; yeni komut/API adları ilgili kart ve referansta kesinleşir.

## Epikler ve bağımlılıklar

| ID | Teslim sınırı | Önkoşul | Kabulün sahibi | Durum |
|---|---|---|---|---|
| P02-0 | Sözleşme ve gerçek hesap bağlamı giriş hattı | P02-0a, P02-0b | Araştırma, iki hizmet/live, review, kurulum/M5 ve üç ortam CI kabulü; PR #12 ile development’a teslim edildi | `verified` |
| P02-0a | Güncel Platform/LLM sözleşmesi, endpoint SDK değerlendirmesi ve pilot planı | P01-2b, P01-3a, P01-5a, P01-5b | [Hazır araştırma kartı](tasks/p02-0a-contract-sdk-pilot.md); B03/B04 çözümü bu araştırmanın çıktısıdır | `verified` |
| P02-0b | Hizmete bağlı salt okunur context gözlemi üst teslimi | P02-0c, P02-0d | [Üst kart](tasks/p02-0b-context-discovery.md); iki hizmet kabulü ve son source CI tamam; PR #12 ile development’a teslim edildi | `verified` |
| P02-0c | Bağımsız LLM terms/context gözlemi | P02-0a; P01-2b/P01-3a/P01-5a/P01-5b | [LLM kartı](tasks/p02-0c-llm-context-discovery.md); kod/review/live ve kaynak bağlı referans, PR #12 source CI tamam; development’a teslim edildi | `verified` |
| P02-0d | Platform reported ID/organizasyon/proje gözlemi | P02-0a; P01-2b/P01-3a/P01-5a/P01-5b | [Platform kartı](tasks/p02-0d-platform-context-discovery.md); ADR-0022 nihai consumer/live/review/kurulum/M5 ve üç ortam CI tamam; PR #12 ile development’a teslim edildi | `verified` |
| P02-R1 | Doğrulanmış hizmet kimliği ve seçili context bağı için açık takip | P02-0a, P02-0d; yetkili auth/principal/ilişki kaynağı | [Takip kartı](tasks/p02-r1-verified-context-binding.md); identity-context sahibi, ready öncesi alt işlere bölünür; mevcut P02-0 paketinin yeni önkoşulu değildir | `draft` |
| P02-R2 | Aynı hash/farklı dosya adının uzak item çokluğu | P02-2m/q; sağlayıcı çözümü ve ayrı canlı kabul | [Takip kartı](tasks/p02-r2-upload-content-cardinality.md); Accepted ADR-0028 ile özgün ihtiyaç ayrı takip edilir | `draft` |
| P02-R3 | Son kaynakta izole yerel performans kabulü | P02-2v ve uygun referans ortam | [Takip kartı](tasks/p02-r3-isolated-performance-acceptance.md); ADR-0030 Proposed, mevcut reference/CI kapıları henüz değişmedi | `draft` |
| P02-R4 | Veri sürümü oluşturma (freeze) etkisi | P02-3q; ayrı Proposed ADR | [Takip kartı](tasks/p02-r4-dataset-version-creation.md); ADR-0033 ile P02-3c dışında bırakıldı | `draft` |
| P02-R5 | Dataset öğesi baytlarına programatik erişim | P02-3m; sağlayıcıda API-key erişimli yol | [Takip kartı](tasks/p02-r5-dataset-item-byte-access.md); API anahtarıyla `file_url` 401, açılma ölçütü dış koşul | `blocked` |
| P02-R6 | Bilinmeyen create sonucunun açık dataset sahiplenmesi | P02-3h; ayrı Proposed ADR | [Takip kartı](tasks/p02-r6-adopt-unknown-create.md); ADR-0031 ile P02-3a dışında bırakıldı | `draft` |
| P02-R7 | Kesin sağlayıcı retlerinin kalıcı `rejected` makbuzu | P02-2c; ayrı Proposed ADR | [Takip kartı](tasks/p02-r7-persist-provider-denials.md); ADR-0031 incelemesinde bulunan belge–kod boşluğu | `draft` |
| P02-R8 | Operation’sız upload planlarını unutma (kota yeniden kazanımı) | P02-2c; ayrı karar | [Takip kartı](tasks/p02-r8-forget-unused-upload-plans.md); ADR-0031 incelemesinde bulunan kota etkisi | `draft` |
| P02-1 | Yerel normal dosya denetimi ve sürümlü manifest | P01-1a, P01-3b; alt kartlar | [Paket planı](p02-1-delivery-plan.md); P02-1a/b/c/d, kurulum/native, iki review turu ve üç ortam source/metadata CI/kanıt kabulü tamam; PR #13 / 50d68b1 ile development’a teslim edildi | `verified` |
| P02-2 | Private oluşturma ve tek doğrulanmış upload yolu | P02-0a, ilgili P02-0b kabulü, P02-1; P01-4b/P01-5b | [P02-2 planı](p02-2-delivery-plan.md); P02-2a–c ve d–w verified, Accepted ADR-0024–0029; ayrı project link dahil create/upload ve ilk kesinti güvenliği PR #14 / 94aaaf0 ile development’a teslim edildi | `verified` |
| P02-3 | Resume/reconcile, indirme/verify ve veri sürüm bağları | P02-2c (resume), P02-2f ve P02-0d (indirme/sürüm) | [Paket planı](p02-3-delivery-plan.md); üst kartlar P02-3a–c, adım kartları P02-3d–v (on dokuz kart); ADR-0031/0032/0033 Accepted (2026-11-06); indirme ve sürüm hatları resume’dan bağımsız hazırlanabilir | `draft` |
| P02-4 | Veri/model kataloğu, sabit referans çözümü ve seçilmiş ağırlık indirme | P02-0a, ilgili P02-0b kabulü; P01-3a/P01-5a | P02-4a/b; indirme ayrıca P02-3b | `draft` |
| P02-5 | Native LLM ve temel çıkarım | P02-4a’nın ilgili hizmet/model kabulü; P01-5b | P02-5a–e; her görev ayrı typed girdi/çıktı ve maliyet sınırı | `draft` |
| P02-6 | GPU/kuyruk/rezervasyon bilgisi ve kota okuma | P02-0a; hesap verisi için ilgili P02-0b kabulü | P02-6a/b; yalnız okuma, tahsis/fatura garantisi yok | `draft` |
| P02-7 | Bütünleşik kullanıcı akışı ve faz kapanışı | Kapanışa alınan bütün P02 alt işleri | [Faz kabulü](#faz-kabulü); eksik hedef açıkça kalır | `draft` |

`P02-0b ilgili kabulü`, artık somut LLM P02-0c veya Platform P02-0d kabulünü gösterir. Downstream kart depends_on alanında yalnız ihtiyaç duyduğu tamamlanmış hizmet ID’sini kullanır; üst işin bütününü gereksiz yere beklemez. Hesap/org/proje alanı sunulmuyorsa uydurulmaz; LLM selected=null ve profile_preference scope ayrımı [referansa](../reference/context-discovery.md) bağlıdır. Ortak profil tercihi provider/service kimliği kanıtı değildir.

B03’ün P01’de kapanan kısmı SDK’nın core bağımlılığı olmaması ve ortak taşıma politikasını atlamamasıdır; endpoint seçimi açık kalır. B04’ün P02 kısmı veri/çıkarım limitleridir; yönetilen eğitim durumları P03’te kalır. P02-0a bu kayıtları araştırır; kayıtların önceden çözülmesini bekleyen bir döngü yoktur.

## Uygulama birimleri ve sıra

Aşağıdaki alt ID’ler kapsam/bağımlılık sınırıdır; henüz hazır uygulama kartı değildir. Yakın iş ayrıntılandırılırken S/M karta dönüştürülür; L iş alt adımlara bölünür. Kesin format, sayısal sınır, deadline, schema/migration ve olumlu/negatif oracle o kartta tek yerde tutulur. Epik bir PR içinde teslim edilebilir; alt ID ayrı PR zorunluluğu değildir. [Paket akışı](README.md#p02-paket-akışı) geçerlidir.

| ID | Tek gözden geçirilebilir sonuç | Doğrudan P02 bağımlılığı | Durum |
|---|---|---|---|
| P02-1a | B15 bounded araştırma kanıtı kapasitesi ve preflight | P02-0; [kart](tasks/p02-1a-evidence-capacity.md) | `verified` |
| P02-1b | Strict yerel Manifest v1 ve sabit byte/digest oracle’ı | P01-1a; ADR-0023 Accepted; [kart](tasks/p02-1b-manifest-contract.md) | `verified` |
| P02-1c | Descriptor recursive scan ve güncel byte kümesi verify | P01-3b, P02-1b; [kart](tasks/p02-1c-descriptor-dataset-scan.md) | `verified` |
| P02-1d | Atomik artifact, API/CLI ve kurulu/final kaynak kabulü | P02-1a, P02-1c; [kart](tasks/p02-1d-dataset-inspection-cli.md) | `verified` |
| P02-2a | Private oluşturma planı, güncel onay ve kalıcı create/korelasyon kaydı | P02-0a, P02-0d, P02-1; [kart](tasks/p02-2a-private-create.md) | `verified` |
| P02-2b | Yetkili depolama hedefinde bounded byte upload ve doğrulanmış confirm | P02-2a; [kart](tasks/p02-2b-verified-upload.md)/aşağıdaki aktarım kararları | `verified` |
| P02-2c | İlk upload’ın kill/restart/kayıp cevap ve teslim kapanışı | P02-2b; [kart](tasks/p02-2c-upload-recovery-acceptance.md); belirsizlikte yeni create/PUT yok | `verified` |
| P02-2d | Ayrı upload plan/manifest/onay kapalı sözleşmesi | P02-1; [yerel kart](tasks/p02-2d-upload-plan-contract.md) | `verified` |
| P02-2e | Kalıcı transfer stage/intent ve ortak state kapıları | P02-2d; [yerel kart](tasks/p02-2e-durable-transfer-journal.md) | `verified` |
| P02-2f | İzole storage hedefi ve bounded stream portu | P02-2d; [yerel kart](tasks/p02-2f-bounded-storage-port.md) | `verified` |
| P02-2g | Exact işe/döneme bağlı maliyet v2 | P02-2d; [kart](tasks/p02-2g-work-cost-v2.md) | `verified` |
| P02-2h | Policy-aware v2 plan/onay/current sözleşmesi | P02-2g; [kart](tasks/p02-2h-plan-policy-v2.md) | `verified` |
| P02-2i | V1/V2 journal union ve tam graph okuması | P02-2h, P02-2e; [kart](tasks/p02-2i-versioned-journal.md) | `verified` |
| P02-2j | V2 admission/arm ve v1 weak-cost write kapanışı | P02-2i, P02-2f; [kart](tasks/p02-2j-write-gates-v2.md) | `verified` |
| P02-2k | V2 explicit read/metadata/reset uyumu | P02-2j; [kart](tasks/p02-2k-read-recovery-v2.md) | `verified` |
| P02-2l | Platform context/create/link strict codec'leri | P02-2k; [kart](tasks/p02-2l-platform-control-codecs.md) | `verified` |
| P02-2m | Platform proxy upload/confirm/items codec'leri | P02-2l, P02-2f; [kart](tasks/p02-2m-platform-upload-codecs.md) | `verified` |
| P02-2n | Kayıtlı service URI ve gerçek HTTP quota bağlantısı | P02-2g, P02-2f, P02-2k, P02-2l; [kart](tasks/p02-2n-upload-http-budgets.md) | `verified` |
| P02-2o | Güncel input/current provider ve prepare/approve kompozisyonu | P02-2n, P02-2m, P02-2k; [kart](tasks/p02-2o-current-upload-preparation.md) | `verified` |
| P02-2p | Kalıcı create baseline, receipt union ve legacy gate | P02-2o; [kart](tasks/p02-2p-created-dataset-context.md), ADR-0027 Accepted | `verified` |
| P02-2q | Gerçek bütçeli Platform effect/metadata portu | P02-2p, P02-2n, P02-2o; [kart](tasks/p02-2q-platform-effect-port.md) | `verified` |
| P02-2r | Original upload koordinatörü | P02-2q; [kart](tasks/p02-2r-original-upload-workflow.md) | `verified` |
| P02-2s | Salt okuma upload uzlaştırması | P02-2r; [kart](tasks/p02-2s-readonly-upload-reconciliation.md) | `verified` |
| P02-2t | Ortak upload CLI/Python ve dar sonuç/niyet incelemesi | P02-2s; [kart](tasks/p02-2t-public-upload-workflows.md) | `verified` |
| P02-2u | Çevrimdışı upload süreç/azami envanter kabulü | P02-2t; [kart](tasks/p02-2u-offline-upload-acceptance.md) | `verified` |
| P02-2v | Kurulu upload native ölçüm araçları | P02-2w; [kart](tasks/p02-2v-installed-upload-measurement.md); üç dilim/ikişer fresh tur ve saklama tamam | `verified` |
| P02-2w | Upload kaynak bakım/refaktör sınırları | P02-2u; [kart](tasks/p02-2w-upload-maintainability.md) | `verified` |
| P02-3a | Kesintiye uğramış aktarımın kanıtlı, yeni onaylı devamı — continuation (üst kabul) | P02-3i; [üst kart](tasks/p02-3a-upload-resume-acceptance.md), [ADR-0031](../decisions/0031-upload-continuation.md) Accepted | `draft` |
| P02-3b | Ortak akışlı indirme, no-clobber yayın ve açık verify seviyesi (üst kabul) | P02-3o; [üst kart](tasks/p02-3b-download-acceptance.md), [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) Accepted | `draft` |
| P02-3c | Veri sürümü/bölme metadata’sı ve değişmez referans; eğitim planı bağı P03-1’dedir (üst kabul) | P02-3q; [üst kart](tasks/p02-3c-dataset-version-acceptance.md), [ADR-0033](../decisions/0033-dataset-version-references.md) Accepted; teknik olarak P02-3a/b’ye bağlı değil, plan sırası sonradır; freeze P02-R4’te | `draft` |
| P02-3d | Transfer aşama grafiği tek belirtimi ve v2 kill karakterizasyonu | P02-2c; [kart](tasks/p02-3d-stage-graph-spec.md) | `verified` |
| P02-3e | Resume kanıt sınıflandırıcısı ve uzak envanter indirgeyicisi | P02-3d; [kart](tasks/p02-3e-resume-evidence-classifier.md) | `verified` |
| P02-3f | Continuation v3 plan tarafı: bağlama, plan, onay, limit/maliyet işi ve politika | P02-3e; [kart](tasks/p02-3f-continuation-domain-v3.md) | `verified` |
| P02-3t | Continuation v3 kayıt, kontrol, doğrulama ve kullanıcı DTO tipleri (P02-3f’den ayrıştırıldı) | P02-3f; [kart](tasks/p02-3t-continuation-records-and-dtos.md) | `verified` |
| P02-3g | Continuation sürüm donanımı: 3 tipli decode, birleşik tipler ve v3 graf belirtimi | P02-3t; [kart](tasks/p02-3g-continuation-persistence-read.md) | `verified` |
| P02-3u | Continuation v3 graf doğrulaması, zincir/baseline çözümleyici ve tek okuma anlık görüntüsü (P02-3g’den ayrıştırıldı) | P02-3g; [kart](tasks/p02-3u-continuation-graph-validation-and-chain.md) | `verified` |
| P02-3v | Continuation kapasite, bakım, reset önizlemesi ve projeksiyonlar (P02-3g’den ayrıştırıldı) | P02-3u; [kart](tasks/p02-3v-continuation-capacity-and-projection.md) | `ready` |
| P02-3r | Continuation yazma kapıları, soy bağı ve M=0 geçişleri (P02-3g’den ayrıştırıldı; yürütme P02-3v’den sonra, P02-3h’den önce) | P02-3v; [kart](tasks/p02-3r-continuation-write-gates.md) | `draft` |
| P02-3h | Continuation üreticisi, alt küme koordinatörü ve proof | P02-3r; [kart](tasks/p02-3h-continuation-workflow.md) | `draft` |
| P02-3i | Public resume API/CLI ve uçtan uca kesinti yolculukları | P02-3h; [kart](tasks/p02-3i-public-resume-surface.md) | `draft` |
| P02-3j | İndirme sözleşme tipleri, doğrulama sözlüğü ve aralık sınıflandırıcısı | P02-2c; [kart](tasks/p02-3j-download-contract.md) | `draft` |
| P02-3k | İmzalı URL için kimliksiz, akışlı GET taşıması | P02-3j, P02-2f; [kart](tasks/p02-3k-signed-get-transport.md) | `draft` |
| P02-3l | Akışlı yerel yazıcı, sidecar protokolü ve resume doğrulaması | P02-3j, P02-3s; [kart](tasks/p02-3l-download-sink-publisher.md) | `draft` |
| P02-3m | İndirme motoru, resume kararı ve uçtan uca uyumluluk | P02-3k, P02-3l; [kart](tasks/p02-3m-download-engine-resume.md) | `draft` |
| P02-3n | Model ağırlığı tüketicisi ve `models download` yüzeyi | P02-3m, P02-0d; [kart](tasks/p02-3n-model-weights-consumer.md) | `draft` |
| P02-3o | İndirme native ölçümü, kanıt doğrulayıcısı ve kurulu smoke | P02-3n; [kart](tasks/p02-3o-download-native-acceptance.md) | `draft` |
| P02-3p | Veri sürümü tipleri, strict codec ve salt okuma okuyucusu | P02-0d; [kart](tasks/p02-3p-version-domain-reader.md) | `draft` |
| P02-3q | Public `datasets versions` yüzeyi ve bağ artifact’ı | P02-3p, P02-3s; [kart](tasks/p02-3q-public-version-surface.md) | `draft` |
| P02-3s | Ortak no-clobber artifact yayıncısı (manifest yayıncısı genellemesi; indirme ve sürüm hatlarının ortak ihtiyacı) | P02-2c; [kart](tasks/p02-3s-common-artifact-publisher.md) | `draft` |
| P02-4a | Sayfalı veri/model kataloğu ve göreve uygun sabit referans çözümü | P02-0a, ilgili P02-0b kabulü | `draft` |
| P02-4b | Seçilmiş model ağırlığını ortak indirme portuyla teslim etme (P02-3n kesin sürüm kimliğiyle indirmeyi sağlar; bu iş katalog çözümlü seçimi bağlar) | P02-4a, P02-3b | `draft` |
| P02-5a | Tek nonstream metin görevi ve typed yanıt/kullanım sonucu | P02-4a LLM alt kabulü | `draft` |
| P02-5b | Sağlayıcı SSE’sini doğrulanmış StreamEvent/terminal sonucuna dönüştürme | P02-5a | `draft` |
| P02-5c | Sıra/boyut/sonluluğu doğrulanmış embedding sonucu | P02-4a LLM alt kabulü | `draft` |
| P02-5d | İndeks/skor/top-n eşlemesi doğrulanmış rerank sonucu | P02-4a LLM alt kabulü | `draft` |
| P02-5e | Tek keşfedilmiş görsel modelde bounded predict ve typed sonuç | P02-4a ilgili model/hizmet alt kabulü | `draft` |
| P02-6a | Kamu GPU/kuyruk/rezervasyon metadata görünümü | P02-0a; hesap endpoint’i varsa ilgili P02-0b kabulü | `draft` |
| P02-6b | Hizmete bağlı hesap kotası/kredi/ledger okuması | P02-0a, ilgili P02-0b kabulü | `draft` |

**Varsayılan sıra:** P02-0a → P02-0b → P02-1 → P02-2 → P02-3 → P02-4 → P02-5 → P02-6 → P02-7. Bu çalışma sırası teknik olarak gereksiz bir kapı oluşturmaz: yerel P02-1 uzak araştırmadan, P02-4a/P02-6 okumaları upload’dan, LLM işleri Platform hesabından bağımsız ilerleyebilir. P02-3b ilk tüketicisini (kesin model sürümü ağırlığı) P02-3n ile kendi kabul kaydında teslim eder; P02-4b katalog çözümlü seçimi bu yüzeye bağlar. Katalog sorgusu ağırlık indirmeyi beklemez. Dal/PR kapsamı değişirse plan/current aynı anda güncellenir.

P02-2c ilk upload’ın güvenli kesinti durumunu ve en az mevcut kimlikle salt okunur uzlaştırma yolunu kapatır; kullanıcıyı yeni create veya DB düzenlemeye yönlendirmez. P02-3a bunun üzerine dosya/aşama bazlı güvenli devam deneyimini ekler. P02-2’nin hata sonrası asgari toparlanması sonraki epike bırakılmaz.

## P01’den devralınan sınırlar ve karar kapıları

P01 güvenilir temel sağlar; bütün P02 kullanım senaryolarını hazır uygulama haline getirmez. Aşağıdakiler ilgili uygulama kartının `ready` geçişinden önce kapatılır; araştırmanın başlamasını engellemez:

| Sınır | Bugünkü gerçek | P02’de gereken çıktı |
|---|---|---|
| Signed URL ve upload | [HTTP portu](../reference/http-transport.md) göreli endpoint, HTTPS/443, bytes request ≤1 MiB ve raw response ≤1 GiB kabul eder; genel imzalı URL/stream upload portu yok | Ayrı depolama hedef politikası, credential ayrımı, imzalı query gizliliği, süre/host/redirect ve bounded request streaming sözleşmesi; P02-2b/P02-3b öncesi güven sınırı ADR’si |
| Çok aşamalı aktarım | [Operation](../reference/operations.md) plan başına tek kayıt/kalıcı dispatch latch ve sonrası yeni attempt yasağı taşır | Create, presign, PUT, confirm ve yeniden başlatmanın kalıcı aşama/korelasyon modeli; her isteğin etki/replay kuralı, unknown uzlaştırması. Yeni attempt açarak latch aşılamaz; P02-2a öncesi karar gerekir |
| Bütçe ve kapasite | [Execution plan](../reference/execution-plan.md) ≤128 input/64 KiB body, çağrıda ≤1 GiB/30 s; store/operation kotaları ayrı | Büyük manifestin plan bağı, dosya/adet/toplam byte ve iş/istek süre modeli; 30 s validation ile tüm transfer süresi eş tutulmaz. Mevcut sınır değişiyorsa ADR; etkiden önce kapasite denetimi |
| Public producer | Mevcut validator tam girdi kapanışı/uzak yetki/endpoint adaptörü doğrulamaz; plan draft/blocked | İlk yan etkili tüketicide gerçek girdi/model/yetki kapanışı, güncel credential/onay ve ortak CLI/Python composition. Test producer’ını public backend yapmak kabul değildir |
| SSE ve çıkarım | [StreamEvent/NDJSON](../reference/stream-results.md) uygulandı; EVREN SSE codec’i ve native görev yanıtları yok | SSE framing, provider terminal/usage/hata ve message EOF eşlemesi; [ADR-0018](../decisions/0018-stream-results-and-cancellation.md) terminal güvenliği korunur, protokol farkı ayrıca sınanır |
| Context ve yeni state | Context genişlemesi, transfer/artefakt kayıtları ve yeni CLI/API şemaları henüz yok | Gereken tüketiciyle birlikte kapalı referans, compatibility ve [ADR-0015](../decisions/0015-checksummed-data-migrations.md) V2 migration/backup/reset kapsamı; mevcut restore yasağı sessizce açılmaz |

Bu tablo bir yeni tasarımın onayı değildir. P02-0a kararların seçenek/kanıt ve Proposed ADR ihtiyacını çıkarır; gerekli yeni ADR kullanıcı onayına sunulmadan bağımlı ürün kodu başlamaz. SDK kendi idempotency/retry davranışını belgelese bile [ADR-0017](../decisions/0017-bounded-http-transport.md) tek deneme/tek retry sahibi kararı kendiliğinden değişmez.

## Kabul matrisi ve kanıt sınırı

Bu matris gelecekteki kartlara zorunlu kapsamı dağıtır; ayrıntılı test/limit listesi kartta tutulur. Hedefler bugün geçmiş sayılmaz.

| Hat / sahip | Olumlu sonuç | Kritik negatif ve kanıt |
|---|---|---|
| P02-0a/0b | Sürüme/tarihe bağlı resmî kaynak; doğru hizmet/anahtar ve açık hesap/proje | 401/403/429, eksik scope, eski credential, çok/boş proje; ilk UUID seçilmez, 403 platform genelinde unsupported olmaz |
| Yerel dosya / P02-1 | Deterministik sürümlü manifest; her göreli dosya adı, boyut ve güncel hash korunur | Aynı boyutta değişim, symlink/ancestor yarışı, FIFO/device, hardlink/aynı hash farklı ad, Unicode/case çakışması, bozuk manifest; hash dedup dosya kimliklerini silmez. Ağ/sır/state zorunlu değildir |
| P02-2/3a | Private hedef ve dosya bazlı doğrulanmış teslim; kullanıcı aynı operation’a döner | Kayıp create/presign/PUT/confirm cevabı, kill/restart, stale journal/uzak silinme, local değişim, 2xx mantıksal hata ve lease kaybı; kör tekrar ve yeni dataset yok |
| P02-3b/3c/4b | Güvenli geçici dosyadan no-clobber sonuç, sürüm/manifest kökeni ve verify seviyesi | Kesik Range/ETag veya sürüm değişimi, checksum anlamı bilinmeyen ETag, hedef yarışı/path kaçışı/disk dolu; metadata eşliği byte hash doğrulaması diye sunulmaz. Model ağırlığında erişim/lisans/şart engeli ayrı kalır |
| P02-4a/6 | Bounded sayfalı/cache’li liste; sabit kimlik/revision ve kapsamlı kota/zaman | Cursor döngüsü, duplicate/değişen sayfa, N+1, belirsiz slug, eski cache, tarih/saat sınırı; upstream immutable revision yoksa pin garantisi uydurulmaz. Kamu GPU erişim kanıtı değildir |
| Çıkarım / P02-5 | Göreve özel typed çıktı, provider request kimliği ve bilinen kullanım | Boş/gömülü hata, yanlış model/görev, NaN/bozuk indeks/dimension, kesik SSE/terminal sonrası veri, 402/403/429, iptal/BrokenPipe; bilinmeyen kullanım sıfır maliyet değildir, inference POST otomatik tekrarlanmaz |
| Faz kapanışı / P02-7 | Aynı kullanım senaryolarının CLI ve Python’da tutarlı deneyimi | Non-TTY asılı prompt yok; JSON/NDJSON saflığı, doğru hata/exit/ID ve yerel iptal–uzak etki ayrımı; gerekli dosya eksikken success yok |

Her ağ kartı istek/sayfa/deneme ve toplam byte/süre tavanını endpoint verisinden önce açıkça seçer; sağlayıcı limiti ile Yörünge koruma tavanını ayırır. Büyük listeler/batch’ler sınırsız RAM veya stdout gerektirmez; rapor ve dosya çıktısı sınırları belirlenir. Aktarım kabulü gerçek upload/download yolunda 16/256/1.024 MiB, en çok 2 worker ve byte kuyruğu ile [performans standardına](../standards/performance.md) bağlanır. P01’in tek raw download benchmark’ı bu kabulün yerine geçmez. Sistem I/O’suna katı duvar saati garantisi verilmez.

## Faz kabulü

P02-7 şu kanıtları tek kapanış raporunda toplar:

1. Doğru profilden private oluşturma → upload → kesinti → aynı işi uzlaştırma → indirme/verify; yerel ve uzak dosya sayısı/kimliği, aynı hash farklı adlar ve byte doğrulaması bağımsız oracle ile korunur. Dataset baytları API anahtarıyla indirilemediğinden (ADR-0032) uzak byte doğrulaması [P02-R5](tasks/p02-r5-dataset-item-byte-access.md)’e bağlıdır; kapalıysa bu madde P02-7 kapanışında `partial` ve açılma koşuluyla kaydedilir, sessizce küçültülmez.
2. İlgili hesapta katalog/model çözümü → nonstream/stream metin → embedding → rerank → seçilmiş görsel predict; her görev için model/sürüm/format, erişim ve kullanımın doğrulanmış sınırı belirtilir. Model adı veya hız sonucu donanım/servis garantisi olmaz.
3. GPU/rezervasyon görünürlüğü ile hesap kotası ayrı kaynak/zaman/erişimle raporlanır; önceki iki akıştaki bilinmeyen kredi/yetki gizlenmez.
4. Hedefli contract/integration ve gerçek TLS/süreç/SQLite kesinti testleri, tam CI/temiz kurulum, kaynak bağlı startup/jobs kapıları ve yeni aktarım ölçümleri geçer. [Kanıt standardıyla](../standards/research-evidence.md) kompakt rapor/manifest, kayıpsız raw arşiv ve sabit oracle vektörleri ayrılır; mevcut kanıtlar ezilmez.
5. Yetkili küçük pilot, offline/loopback kabulünden ayrı kaydedilir. Pilot öncesi veri/proje/endpoint, azami istek/token/byte/tutar, durdurma koşulu ve geride kalacak kaynağın sahibi bellidir. Bu hazırlık canlı hesap çağrısı, şart kabulü veya uzak silme yetkisi vermez.
6. İlk kullanıcı görevlerinde süre, yardım, yanlış hedef ve çıktı bulma ölçülür; sayısal UX hedefi ilgili kartta **ölçümden önce** sabitlenir. README/örnekler/CLI/Python referansları, capability matrisi ve current gerçek teslimi gösterir; örnekler temiz kurulumda çalıştırılır.

Zorunlu alt işin kabulü eksikse epik/faz `verified` olmaz. Erişim kapalıysa bağımsız işler sürer; eksik hat `blocked`/`partial` ve açılma koşuluyla kalır. Araştırmanın “unknown/kapalı” sonucu araştırma kabulünü karşılayabilir, ürün entegrasyon kabulünü karşılamaz. Bir hedefi P02 dışına alma veya yalnız kısıtlı sürüm teslim etme kararı kullanıcıyla açık kaydedilmeden kapsam küçültülmez; [yayın kapısı](README.md#faz-kapısı-ve-yayın-kapısı) ayrıca geçerlidir.
