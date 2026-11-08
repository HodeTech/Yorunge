# P02-3 — Etkili resume, akışlı indirme ve veri sürüm bağları teslim planı

**Tarih:** 2026-11-06. **Durum:** ADR-0031/0032/0033 kullanıcı 2026-11-06 talimatıyla Accepted; uygulama adım 1’den başlıyor (K4–K6 varsayılanları geçerli, aşağıda). **Dal:** `feat/p02-3-dataset-recovery`, development `94aaaf0` tabanı. Tek development PR; Master/release kullanıcıdadır. Kapsam kararı ve kanıtı [hazırlık incelemesindedir](../research/p02-3-readiness-review.md); adım sonuçları [uygulama ve kabul kaydında](../research/p02-3-implementation-validation.md) tutulur.

## Kullanıcı sonucu

Veri sorumlusu kesintiye uğrayan private yüklemeyi aynı Platform dataset’inde, yeni create veya DB düzenlemesi olmadan, yalnız kanıtlanmış güvenli adımları göndererek tamamlar ve neyin doğrulandığını görür (**P02-3a**). Model geliştirici kesin model sürümünün ağırlığını doğrulama seviyesi görünür ve hedefi ezmeyen biçimde indirir; sağlayıcı güçlü ETag ve Range sunarsa kesilen indirme aynı komutla devam eder (**P02-3b**). Kullanıcı bir veri sürümünü ve bölme sayımlarını görür, değişmez referansa bağlar ve sapmayı denetler; eğitim planı (P03-1) bu referansı tüketir (**P02-3c**). Sonuçlar yetki, fiyat veya dataset baytlarının uzaktan doğrulanması iddiası taşımaz.

**Planlanan kullanıcı akışı (resume).** Komutlar taslaktır; ayrıntı [continuation sözleşmesindedir](../reference/dataset-upload-continuation.md).

```text
datasets upload show --operation-id OP        # unknown; "devam için: datasets upload resume --operation-id OP"
datasets upload resume --operation-id OP --accept-unverified-read
                                              # rapor (exit 0): 57 confirmed, 3 observed, 38 gönderilecek, kota etkisi, önerilen eylem
datasets upload resume --operation-id OP --accept-unverified-read --prepare [--accept-unconfirmed-effects]
                                              # yerel devam planı: PLAN_ID ve digest (uzak yazma yok)
datasets upload review  --plan-id PLAN_ID
datasets upload approve --plan-id PLAN_ID --confirm DIGEST [...ack] [--accept-unconfirmed-effects]
datasets upload start   --plan-id PLAN_ID
```

## Kapsam kararları ve takipler

| Konu | Karar | Kayıt |
|---|---|---|
| Resume modeli | Aynı operation’ı canlandırma yok; soy bağlı (zincirli), yeni onaylı continuation — dosya aktarım fazının kalanı | [ADR-0031](../decisions/0031-upload-continuation.md) |
| Bilinmeyen create | Bloke; sahiplenme ayrı iş | [P02-R6](tasks/p02-r6-adopt-unknown-create.md) |
| Kesin sağlayıcı retleri | Üretim yolu kalıcı `rejected` makbuz yazmaz; continuation dürüst sınırla çalışır, kalıcı makbuz ayrı iş | [P02-R7](tasks/p02-r7-persist-provider-denials.md) |
| Upload plan kotası | Operation’sız planları unutma yolu yok; continuation N dosyayı yeniden sayar | [P02-R8](tasks/p02-r8-forget-unused-upload-plans.md) |
| İndirme | Tek dosya, ≤1 GiB, kimliksiz imzalı GET, kesin model sürümü ilk tüketici | [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) |
| Dataset öğesi baytları | API anahtarıyla erişilemez; indirme kurulmaz; uzak byte doğrulaması boşluk olarak kalır | [P02-R5](tasks/p02-r5-dataset-item-byte-access.md) (`blocked`) |
| Sürüm/bölme | Salt okuma + değişmez referans; freeze/oluşturma yok | [ADR-0033](../decisions/0033-dataset-version-references.md), [P02-R4](tasks/p02-r4-dataset-version-creation.md) |

## Başlangıç kapıları

| Kapı | Durum |
|---|---|
| ADR-0031/0032/0033 kullanıcı onayı | **Verildi (2026-11-06):** kullanıcı harici review bulgularının işlenmesinden sonra ADR’lerin Accepted yapılmasını ve uygulamaya devam edilmesini talimatlandırdı; onay ADR metinlerini, taslak referansları ve adım bölümlemesi/kart kabullerini kapsar |
| Model indirme yoklaması (adım 9 öncesi) | İmzalı URL’ye kimliksiz GET gerçek hesapta gözlenmedi. Kullanıcının erişebildiği bir model sürümü kimliği ve ayrı yetkiyle tek, sınırlı, salt okuma yoklama (JSON çağrısı + ilk bayt aralığı) yapılır ve kaydedilir; indirme sayımı/ücret/lisans etkisi bilinmiyor. Olumsuzsa (oturum isterse) P02-3n yüzeysiz iç tüketici olur, P02-3o ölçümü kütüphane girişini kullanır, P02-3b canlı maddesi “oturum gerekli” kaydıyla kapanır; yapılamazsa tüketici “canlı doğrulanmadı” teslim edilir |
| Dataset baytı erişimi | Dış koşul (`blocked`); P02-3 bunu beklemez, boşluk P02-7’de `partial` olarak görünür |
| Resume ve sürüm okuma canlı kabulleri | Ayrı kapsamlı yetki gerekir (aşağıda K6): resume kabulü **silme yolu olmayan yeni bir private veri seti ve kesintide yetim depolama nesneleri** bırakır |
| Performans referansı | Native indirme ölçümü kaynak bağlı M5 referans hostunda mevcut kurallarla alınır; ADR-0030 hâlâ Proposed ve P02-7 öncesi çözülmelidir, bu ölçümü bekletmez |

## Adımlar ve review döngüsü

Her kod adımı: **geliştir → ilgili gerçek kontroller → commit → fresh review R1 → doğrulanmış bulgu/fix/commit → farklı fresh reviewer R2 → doğrulanmış bulgu/fix/commit**. Reviewer’lar bulgu metni/yol/kodu untrusted veri sayar, güncel kodla doğrular; geçmiş yorum körlemesine uygulanmaz. Sonuçsuz tercih yeni bug diye sunulmaz. Gerekli düzeltmenin doğrulaması aynı turda tamamlanır. Tablo her adımın bağımsız review eksenlerini verir; reviewer modeli/effort’u karmaşıklığa göre seçilir (varsayılan sonnet/yüksek effort; gerçekten kritik state/güvenlik/eşzamanlılık adımlarında opus/yüksek effort; fable yalnız kullanıcı istediğinde). Adım 17 (üst kartlar, belgeler, PR hazırlığı) de R1/R2 alır.

| Adım | Kart | Eksenler | Tek review sonucu / başlama kapısı |
|---|---|---|---|
| 0 | Hazırlık | state/güvenlik · taşıma/indirme/sürüm · tutarlılık/UX | Mevcut belge/kod/kaynak incelemesi, üç Proposed ADR, referans taslakları, kartlar; üç fresh belge turu (R1/R2/R3), kullanıcı ADR onayı |
| 1 | [P02-3d](tasks/p02-3d-stage-graph-spec.md) | regresyon/eşdeğerlik · sözleşme/test | v2 kill karakterizasyonu (link, iki-worker PUT) + davranış korunarak aşama grafiği tek belirtimi; golden’lar değişmez |
| 2 | [P02-3e](tasks/p02-3e-resume-evidence-classifier.md) | doğruluk/oracle · güvenlik/gizlilik | Kapalı kanıt sınıfları (zincir birleşimi), uzak envanter indirgeyicisi, özetler |
| 3 | [P02-3f](tasks/p02-3f-continuation-domain-v3.md) | sözleşme/golden · state/politika | Strict v3 plan/onay/limit/maliyet işi/bağlama tipleri, saf plan/onay üreticileri, politika (96 satır), golden’lar, hata kodları |
| 3 (devam) | [P02-3t](tasks/p02-3t-continuation-records-and-dtos.md) | sözleşme/golden · state/gizlilik | Strict v3 kayıt/kontrol/doğrulama ve kullanıcı özet/rapor DTO’ları, golden’lar, sentinel’lar (P02-3f’den bölündü) |
| 4 | [P02-3g](tasks/p02-3g-continuation-persistence-read.md) | state/kalıcılık · sözleşme/regresyon · test/oracle | Sürüm donanımı: 3 tipli decode, birleşik tipler ve gönderim yardımcıları, `StageGraphSpec` v3, v2’ye özgü gönderim noktalarının kilitli kontrol listesi |
| 4 (devam) | [P02-3u](tasks/p02-3u-continuation-graph-validation-and-chain.md) | state/doğruluk · güvenlik/gizlilik · test/oracle | v3 graf doğrulama, zincir/baseline çözümleyici, `operation_journal` v3 ve tek okuma anlık görüntüsü (P02-3g’den bölündü) |
| 4 (devam) | [P02-3v](tasks/p02-3v-continuation-capacity-and-projection.md) | state/kalıcılık · UX/projeksiyon · test/oracle | Kapasite/rezerv, bakım/reset önizlemesi, özet projeksiyonu ve rapor kota okuması (P02-3g’den bölündü) |
| 5 | [P02-3r](tasks/p02-3r-continuation-write-gates.md) | state/atomiklik · güvenlik/eşzamanlılık · test/kill | Yazma kapıları, soy bağı/donma, dataset tekilliği, namespace, M=0, kill |
| 6 | [P02-3h](tasks/p02-3h-continuation-workflow.md) | doğruluk/oracle · güvenlik/gizlilik · test/TLS | Üretici: günlük engelleri, uzak okuma, sınıflandırma, `resume` raporu ve `--prepare` (dondurma, plan mührü, kayıt) |
| 6 (devam) | [P02-3w](tasks/p02-3w-continuation-stage-executor.md) | protokol/ağ güvenliği · state/atomiklik · test/kill | Aşama yürütücüsü: v3 port ve okuyucu, alt küme koordinatörü (hepsi presign → en çok iki PUT → seri confirm), confirm sayaç tabanı, istek özeti bağı (P02-3h’den bölündü) |
| 6 (devam) | [P02-3y](tasks/p02-3y-continuation-start.md) | state/protokol · hata/iptal eşlemesi · test/kill | Başlatma: taze envanter yeniden sınıflama (`continuation_remote_changed`), `M=0` doğrulama ve N-dosya proof, hata/iptal/belirsizlik eşlemesi, TLS ve kill yolculukları (P02-3h’den bölündü) |
| 6 (devam) | [P02-3x](tasks/p02-3x-continuation-reconcile.md) | state/protokol · v1/v2 regresyon | v3 `reconcile` bağlaması, devam edilmiş kaynak kararı (P02-3h’den bölündü) |
| 7 | [P02-3i](tasks/p02-3i-public-resume-surface.md) | UX/CLI sözleşmesi · state/güvenlik sentinel | Ortak `resume` (rapor/`--prepare`), onay bayrağı, gerçek yolculuklar, belgeler |
| 8 | [P02-3s](tasks/p02-3s-common-artifact-publisher.md) | dosya güvenliği/yarış · sözleşme/regresyon | Manifest yayıncısı genellemesi: ortak no-clobber artifact yayıncısı |
| 9 | [P02-3j](tasks/p02-3j-download-contract.md) | sözleşme/oracle · güvenlik | Doğrulama sözlüğü, DownloadPartial, tipli yanıt sınıflandırıcısı, hata kodları; **model yoklama kapısı bu adımdan önce** |
| 10 | [P02-3k](tasks/p02-3k-signed-get-transport.md) | ağ güvenliği · sır sızıntısı · test | Kimliksiz akışlı GET, kapalı başlıklar, guard, süre |
| 11 | [P02-3l](tasks/p02-3l-download-sink-publisher.md) | dosya güvenliği/yarış · kilitleme/çökme tutarlılığı · test/kill | Akışlı yazıcı, sidecar protokolü, flock/sahiplik, resume doğrulaması |
| 12 | [P02-3m](tasks/p02-3m-download-engine-resume.md) | protokol doğruluğu · çökme/durum · test | Motor, resume kararı, Range/ETag matrisi, protokol dönüşü |
| 13 | [P02-3n](tasks/p02-3n-model-weights-consumer.md) | UX/CLI sözleşmesi · sır/hedef güvenliği | `models download` tüketicisi ve yüzeyi (kod ve çevrimdışı testler çalışma dalında; canlı kabul yapılmadı) |
| 14 | [P02-3o](tasks/p02-3o-download-native-acceptance.md) | ölçüm/kanıt · test/oracle | Native 16/256/1.024 MiB ölçüm donanımı ve kapalı `download_budget_v1` raporu (doğrulayıcı, saklama, kurulu smoke ve CI P02-3z’ye ayrıldı) |
| 14 (devam) | [P02-3z](tasks/p02-3z-download-evidence-installation-ci.md) | ölçüm/kanıt · CI/kurulum · gizlilik | Referans doğrulayıcısı, tanı saklaması, kurulu `resume`/`versions`/`download` smoke’ları, `installation_v4`, CI orkestratörü ve workflow (P02-3o’dan bölündü) |
| 15 | [P02-3p](tasks/p02-3p-version-domain-reader.md) | sözleşme/codec · güvenlik/PII | Sürüm/bölme tipleri, strict codec, okuyucu, sapma |
| 16 | [P02-3q](tasks/p02-3q-public-version-surface.md) | UX/CLI sözleşmesi · yayın/regresyon | `datasets versions list/show/bind/check`, artifact |
| 17 | [P02-3a](tasks/p02-3a-upload-resume-acceptance.md), [P02-3b](tasks/p02-3b-download-acceptance.md), [P02-3c](tasks/p02-3c-dataset-version-acceptance.md) | belge tutarlılığı · uçtan uca kabul | Üst kartlar: kurulu yolculuk, belge/matris/current, **son kaynak M5 referans serisi (startup/jobs/dataset/upload/download; onaylanan hatların kaynağı için) ve üç ortam CI/altı kurulum/Sonar**, kalıcı kanıt, yetkili canlı kabuller, tek development PR |

**Büyüme kuralı.** Ölçülen büyüklük bir kartı L yaparsa iş sessizce küçültülmez; kart s–z harfleriyle (s, t, u, v, w, x, y ve z kullanıldı — harfler bitti: sonraki bölünme için yeni bir plan kuralı gerekir; P02-3z, P02-3o’nun ölçüm donanımı yapıldıktan sonra kanıt/saklama/kurulu smoke/CI tarafı olarak ayrıldı; P02-3t, P02-3f’nin ölçülen büyüklüğü L’ye çıkınca plan tarafı 3f, kayıt/kanıt/DTO tarafı 3t olarak; P02-3u ve P02-3v, P02-3g’nin kapsamı ölçüldüğünde — v2’ye özgü 58 gönderim noktası (ilk metin tabanlı sayım), create-ilk graf doğrulayıcıları, kapasite/bakım/projeksiyon — sürüm donanımı 3g, graf doğrulama ve zincir 3u, kapasite/bakım/projeksiyon 3v olarak bölündü; P02-3w, P02-3x ve P02-3y, P02-3h’nin ölçülen kapsamı — salt okuma üretici, etkili aşama yürütücüsü ve başlatma/proof, reconcile bağlaması: dört ayrı risk alanı ve ayrı review ekseni — bölündüğünde üretici 3h, aşama yürütücüsü 3w, başlatma 3y, reconcile 3x olarak) bölünür ve burada kaydedilir. P02-3l, P02-3m ve P02-3o için bu kural önceden ilan edilmiştir (yazıcı/race ile sidecar/resume; ölçüm/doğrulayıcı/CI ayrı birimler olabilir).

**Otomatik ilerleme ve durma.** Bir adım R2 sonrası temiz kapandığında kullanıcıya dönmeden sonraki adıma geçilir. Dururum ve sorarım: (a) yeni veya değişen ADR, DDL/migration ya da kapsam küçültme gerektiren yeni bir bilinmez çıkarsa; (b) K6’da önceden verilmemiş veya kapsamı aşan canlı yetki gerekiyorsa; (c) giderilemeyen engelleyici hata varsa. Kart bölünmesi durma sebebi değil, kayıt ve bildirimdir.

**Hat bağımlılıkları.** Resume: 3d → 3e → 3f → 3t → 3g → 3u → 3v → 3r → 3h → 3w → 3y → 3x → 3i → 3a. Ortak yayıncı: 3s (yalnız P02-2c’ye dayanır). İndirme: 3j → 3k ve 3j + 3s → 3l; 3k + 3l → 3m → 3n → 3o → 3b. Sürüm: 3p → 3q (3p + 3s) → 3c. Üç hat bu graftaki kollar kadar bağımsızdır; yalnız yayıncı 3s, indirme ve sürüm hatlarının ortak önkoşuludur ve hiçbir ADR’ye bağlı değildir.

**Sıra gerekçesi.** Resume en riskli ve kararlı olması gereken hattır; en önce yapılır. Adım 1 salt refaktördür ve v1/v2 geçmişini koruyan, önceden genişletilmiş regresyon ağıyla kanıtlanır. İndirme (9–14) ve sürüm (15–16) resume’dan teknik olarak bağımsızdır; P02-3c’nin eski P02-3a/b bağımlılığı kullanıcı akışı sırasıdır, kod bağımlılığı değildir.

**Kısmi onay.** ADR’lerden yalnız bazıları onaylanırsa onaylanan hat başlar (3s hiçbir ADR beklemediğinden ilk onaylanan indirme veya sürüm hattıyla birlikte öne alınır). ADR-0031 revizyon isterse indirme ve sürüm hatları önce yürür ve resume revizyon sonrası başlar. Reddedilen veya revizyon bekleyen hattın üst kartı (P02-3a/b/c) `deferred` işaretlenir; PR, siz aksini istemedikçe onaylı hatlarla kapanır ve P02-7 faz kabulü ilgili maddeyi `partial` + açılma koşuluyla kaydeder (K5).

**PR sınırı.** Epik başına tek development PR kullanıcı talimatıdır (önceki PR #14 428 dosya/+58 bin satırla incelendi). Hatlar (resume 1–7, ortak yayıncı 8, indirme 9–14, sürüm 15–16) ardışık, bağımsız commit aralıklarıdır; kullanıcı isterse başlamadan PR’lar hat bazında bölünebilir, kapsam küçülmez. Bir hat onaylanmaz/revizyon bekler ve siz beklemeyi seçmezseniz PR onaylı hatlarla kapanır (K5).

## Kullanıcı kararları

Her karar için öneri ve reddedilirse varsayılan aşağıdadır; onayın bilmeniz gereken sonuçları tablonun altında karar başına listelenir (ADR’lerin yalnız özeti; ayrıntı ADR’lerdedir).

**Durum (2026-11-06):** Kullanıcı K1–K3 için, harici review bulgularının işlenmesinden sonra ADR’lerin Accepted yapılmasını ve uygulamaya devam edilmesini talimatlandırdı. K4–K6 ayrıca yanıtlanmadı; **varsayılanlar geçerlidir:** R4–R8 ertelenmiş (açılma ölçütü ve hedef kartlarda), tek PR, canlı girdiler verilmedi (model yoklaması ile resume ve sürüm canlı kabulleri “yapılmadı” kaydı alır; üst kartlar bunu açıkça taşır). Kullanıcı bu varsayılanları istediği zaman değiştirebilir; değişiklik ilgili adımdan önce bildirilmelidir.

| # | Karar | Öneri | Reddedilirse / varsayılan |
|---|---|---|---|
| K1 | [ADR-0031](../decisions/0031-upload-continuation.md): soy bağlı, yeni onaylı continuation (aynı operation canlandırılmaz; kapalı kanıt sınıfları; `pending_uncertain` için ayrı insan onayı; create/proje/bilinen olumsuz belirsizse bloke) | Onayla | Resume hattı durur, diğer hatlar sürer; P02-3a `deferred`, P02-7 resume maddesi `partial`. Alternatif “yalnız salt okuma raporu” (3d + 3e + 3f’nin rapor tipi + 3i’nin yalnız rapor yüzeyi). Değiştirmeden ilerlemem |
| K2 | [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md): motor + kesin model sürümü `models download`; dataset öğesi indirme yok; 1 GiB; resume yalnız güçlü ETag + 206; yalnız `transfer_complete`/`sha256_matched` seviyeleri | Onayla | Seçenekler: yalnız kütüphane (komutsuz) veya hat durur; varsayılan: durur, P02-3b `deferred` |
| K3 | [ADR-0033](../decisions/0033-dataset-version-references.md): salt okuma sürüm referansı; freeze ertelenir | Onayla | Freeze dahil istenirse ayrı ADR ve ek adımlar; aksi hat durur, P02-3c `deferred` |
| K4 | Ertelenen takipler: [R4](tasks/p02-r4-dataset-version-creation.md) (freeze), [R5](tasks/p02-r5-dataset-item-byte-access.md) (dataset/model baytı: sağlayıcı yolu **veya** kullanıcı onaylı, ücreti gösterilen export tabanlı doğrulama araştırması), [R6](tasks/p02-r6-adopt-unknown-create.md) (bilinmeyen create sahiplenmesi), [R7](tasks/p02-r7-persist-provider-denials.md) (kesin ret makbuzu), [R8](tasks/p02-r8-forget-unused-upload-plans.md) (operation’sız plan unutma) | Hepsi ertelenmiş kalsın; her kartta açılma ölçütü ve hedef yazılıdır | Herhangi biri P02-3’e alınırsa ayrı Proposed ADR ve ek adım(lar) gerekir. R7/R8’i 3h/3i öncesine çekmek mümkündür (R7 upload v2 hata yolunu değiştirir; her biri ≈ADR + M kart + iki review turu ekler); R5 için “export tabanlı doğrulamayı şimdi araştır” ayrı ADR ve ücret onayı ister. Varsayılan: ertelenmiş |
| K5 | Tek PR | Tek PR | Hat bazında bölme istenirse başlamadan bildirilir. Bir hat onaylanmaz/revizyon bekler ve beklemeyi seçmezseniz PR onaylı hatlarla kapanır; durmuş hattın üst kartı `deferred` olur |
| K6 | Canlı girdiler (hepsi isteğe bağlı; verilmeyen kabul “yapılmadı” kaydı alır): (a) model sürümü kimliği + salt okuma yoklama — JSON çağrısı + ≤1 MiB aralık; indirme sayımı/ücret/lisans etkisi bilinmiyor; (b) resume canlı kabulü — azami create/istek/bayt tavanınız; yeni private veri seti ve kesintide yetim depolama nesneleri kalır, **silme yolu yok**; bu kabul `actual_count`’un dolu veri setindeki anlamını gözleyen **tek** canlı kanıttır; (c) sürüm okuma canlı kabulü — dondurulmuş sürümlü bir dataset kimliği (yoksa UI’da oluşturmak sizin ayrı işleminizdir); ≤8 mantıksal GET (ADR-0017 yeniden denemesiyle en çok 16 fiziksel) | Üçünü de ver ya da “yok” de | Verilmeyen kabul “yapılmadı” olarak kayda geçer, üst kart bunu açıkça taşır; model yoklaması yoksa tüketici “canlı doğrulanmadı” |

**K1 — onayın sonuçları.** (1) v3 satırı oluşunca aynı state dizinini paylaşan **eski binary** tüm upload komutlarını, reset önizlemesini ve tam doğrulama yapan `backup`/`restore`/`maintain`/`verify` yollarını yitirir (`state_invalid`); upload dışı komutlar etkilenmez. (2) Her devam N dosyayı kotada **yeniden sayar** (128 dosyalık iş için kök dahil ≈32 plan/devam denemesi store kotasını doldurur; geçmişi veya planı silen yol yok → P02-R8). (3) Üretim yolu kesin 401/403’ü kalıcı yazmadığından reddedilmiş bir istek continuation’da taze kontrolle **en çok bir kez** yeniden gönderilebilir (P02-R7). (4) **Kabul edilmiş ADR’lere etkisi:** ADR-0024’ün “restart yalnız read” hükmü yalnız bu kapalı yol için tamamlanır; ADR-0026/0027/0028’in “tam 2+3N graf ve kendi CreateReceiptV2’si” başarı hükümleri yalnız v3 kayıtları için değişir (v1/v2 aynı; ilgili ADR’lere tarihli Proposed geri işaretçileri eklendi). (5) Confirm yanıtındaki `actual_count`’un dolu bir veri setindeki anlamı **gözlenmedi**; oracle iki olası anlamı (`taban+k+1` ve `k+1`) kabul eder ve resume canlı kabulü (K6b) hangisinin geçerli olduğunu kayda geçirir; ikisine de uymazsa karar yeniden açılır. (6) Continuation için ayrı native ölçüm yapılmaz (PUT akışı aynı koddur; ek yükler — tam kök hash’i, ≤1.024 item envanter okuması — mevcut dataset hash ve items bütçeleriyle kapsanır; gerekçe kabul kaydına yazılır).

**K2 — onayın sonuçları.** (1) İlk tüketici `models download`; dataset öğesi baytı API anahtarıyla alınamadığından indirme kurulmaz (R5 `blocked`). (2) **ADR-0025’in iki kısmi değişikliği:** imzalı GET için `expires_at` aranmaz (sağlayıcı sunmuyor; süresi dolmuş URL ağdan önce reddedilemez, 401/403 ile gözlenir) ve storage portu private tipli GET’i de taşır; PUT kuralları değişmez. (3) Model yoklaması (K6a) olumsuz veya yapılamazsa tüketici yüzeysiz iç tüketici ya da “canlı doğrulanmadı” olarak teslim edilir. (4) Tam indirilmiş yarım dosya ağsız yayımlanır ve sağlayıcıdaki nesnenin hâlâ aynı olduğu iddia edilmez. (5) `--sha256` uyuşmazlığında stage silinir (yeniden indirme maliyeti ≤1 GiB).

**K3 — onayın sonuçları.** Salt okuma `list/show/bind/check`; referans üyeliği kanıtlamaz ve `is_frozen` sağlayıcı iddiasıdır; `is_partial=true` sürüm bağlanır ve alan kaydedilir (P03-1 isterse reddeder); bağ yeni bir dosya biçimidir, SQLite değişmez; freeze/oluşturma ertelenir (R4).

**Hatırlatma.** ADR-0030 (performans kabulü) hâlâ Proposed; P02-7 ve ilk release önerisi öncesi çözülmelidir.

## Kabul ve kanıt planı

Her adım kendi kartındaki olumlu/negatif oracle’ları ve gerçek kontrolleri çalıştırır. Resume için gerçek SIGKILL matrisi mevcut sekiz sınıra link ve iki-worker PUT ile genişler (önce v2 yolunda karakterizasyon, sonra v3); indirme için ayrı kurulu `-I` süreçte 16/256/1.024 MiB native ölçüm (U≤64 MiB, G≤8 MiB, disk yazımı pencere içinde) ve `verify-download-reference` doğrulayıcısı eklenir; kurulu paket altı temiz kurulumda yeni komutları çalıştırır. Kaynak değiştiği için son kaynak M5 referans serisi (startup/jobs/dataset/raw/upload/download) kod dondurulduktan sonra yenilendi (`p02-3-reference-*-1`). Sonuçlar [uygulama ve kabul kaydında](../research/p02-3-implementation-validation.md) ve [kanıt standardına](../standards/research-evidence.md) göre kalıcı arşivde tutulur. CI üç ortamda tam takımı çalıştırır; başarısız ölçümler ve eski kabuller korunur.

## Teslim kaydı

Uygulama kartları P02-3d–z (yirmi dört) `verified`; üst kartlar P02-3a–c `in_review`. Adım adım uygulama, iki fresh review turu ve düzeltmeler [uygulama ve kabul kaydındadır](../research/p02-3-implementation-validation.md) (Adım 1–22 ve tam paket). Tek development PR’ı bu dalla açılır; üç ortam CI, altı temiz kurulum ve Sonar PR aşamasında görülür. Yetkili canlı kabuller (K6a, K6b, K6c) yapılmadı. Son kaynak M5 referans serisi: `p02-3-reference-{startup,jobs,datasets,raw,upload,download}-1`, kod `a574c5b`’de dondurulduktan sonra kişisiz kökte bir kez alındı ve arşivlendi (altısı da ilk denemede geçti; beş kaynak bağlı doğrulayıcı geçti). ADR-0030 (performans kabulü) hâlâ Proposed; Master/release bu planın işi değildir.
