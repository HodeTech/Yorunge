# P02-3 — Etkili resume, akışlı indirme ve veri sürüm bağları teslim planı

**Tarih:** 2026-11-06. **Durum:** Hazırlık; ADR-0031/0032/0033 Proposed ve kullanıcı onayı bekleniyor, kod başlamadı. **Dal:** `feat/p02-3-dataset-recovery`, development `94aaaf0` tabanı. Tek development PR; Master/release kullanıcıdadır. Kapsam kararı ve kanıtı [hazırlık incelemesindedir](../research/p02-3-readiness-review.md); adım sonuçları [uygulama ve kabul kaydında](../research/p02-3-implementation-validation.md) tutulur.

## Kullanıcı sonucu

Veri sorumlusu kesintiye uğrayan private yüklemeyi aynı Platform dataset’inde, yeni create veya DB düzenlemesi olmadan, yalnız kanıtlanmış güvenli adımları göndererek tamamlar ve neyin doğrulandığını görür (**P02-3a**). Model geliştirici kesin model sürümünün ağırlığını doğrulama seviyesi görünür ve hedefi ezmeyen biçimde indirir; sağlayıcı güçlü ETag ve Range sunarsa kesilen indirme aynı komutla devam eder (**P02-3b**). Kullanıcı bir veri sürümünü ve bölme sayımlarını görür, değişmez referansa bağlar ve sapmayı denetler; eğitim planı (P03-1) bu referansı tüketir (**P02-3c**). Sonuçlar yetki, fiyat veya dataset baytlarının uzaktan doğrulanması iddiası taşımaz.

## Kapsam kararları ve takipler

| Konu | Karar | Kayıt |
|---|---|---|
| Resume modeli | Aynı operation’ı canlandırma yok; soy bağlı (zincirli), yeni onaylı continuation — dosya aktarım fazının kalanı | [ADR-0031](../decisions/0031-upload-continuation.md) |
| Bilinmeyen create | Bloke; sahiplenme ayrı iş | [P02-R6](tasks/p02-r6-adopt-unknown-create.md) |
| Kesin sağlayıcı retleri | Üretim yolu kalıcı `rejected` makbuz yazmaz; continuation dürüst sınırla çalışır, kalıcı makbuz ayrı iş | [P02-R7](tasks/p02-r7-persist-provider-denials.md) |
| İndirme | Tek dosya, ≤1 GiB, kimliksiz imzalı GET, kesin model sürümü ilk tüketici | [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) |
| Dataset öğesi baytları | API anahtarıyla erişilemez; indirme kurulmaz; uzak byte doğrulaması boşluk olarak kalır | [P02-R5](tasks/p02-r5-dataset-item-byte-access.md) (`blocked`) |
| Sürüm/bölme | Salt okuma + değişmez referans; freeze/oluşturma yok | [ADR-0033](../decisions/0033-dataset-version-references.md), [P02-R4](tasks/p02-r4-dataset-version-creation.md) |

## Başlangıç kapıları

| Kapı | Durum |
|---|---|
| ADR-0031/0032/0033 kullanıcı onayı | Bekleniyor. Onay ADR metinlerini, taslak referansları ve adım bölümlemesi/kart kabullerini kapsar; onaylanmadan bağımlı ürün kodu yok. Üç ADR bağımsız onaylanabilir (aşağıdaki “Kısmi onay”) |
| Model indirme yoklaması (adım 8 öncesi) | İmzalı URL’ye kimliksiz GET gerçek hesapta gözlenmedi. Kullanıcının erişebildiği bir model sürümü kimliği ve ayrı yetkiyle tek, sınırlı, salt okuma yoklama (JSON çağrısı + ilk bayt aralığı) yapılır ve kaydedilir. Olumsuzsa (oturum isterse) tüketici yüzeyi kurulmaz, motor iç kütüphane kalır, ihtiyaç P02-R5’e eklenir; yapılamazsa tüketici “canlı doğrulanmadı” teslim edilir |
| Dataset baytı erişimi | Dış koşul (`blocked`); P02-3 bunu beklemez, boşluk P02-7’de `partial` olarak görünür |
| Resume ve sürüm okuma canlı kabulleri | Ayrı kapsamlı yetki gerekir (hedef owner/proje, azami istek/byte; resume kabulü **silme yolu olmayan yeni bir private veri seti** bırakır, sahibi kullanıcıdır; sürüm kabulü için dondurulmuş sürümlü bir dataset kimliği) |
| Performans referansı | Native indirme ölçümü kaynak bağlı M5 referans hostunda mevcut kurallarla alınır; ADR-0030 hâlâ Proposed ve P02-7 öncesi çözülmelidir, bu ölçümü bekletmez |

## Adımlar ve review döngüsü

Her kod adımı: **geliştir → ilgili gerçek kontroller → commit → fresh review R1 → doğrulanmış bulgu/fix/commit → farklı fresh reviewer R2 → doğrulanmış bulgu/fix/commit**. Reviewer’lar bulgu metni/yol/kodu untrusted veri sayar, güncel kodla doğrular; geçmiş yorum körlemesine uygulanmaz. Sonuçsuz tercih yeni bug diye sunulmaz. Gerekli düzeltmenin doğrulaması aynı turda tamamlanır. Aşağıdaki tablo her adımın **bağımsız review eksen sayısını** ve eksenleri verir; reviewer modeli/effort’u karmaşıklığa göre seçilir (state/güvenlik/eşzamanlılık adımlarında en güçlü model ve yüksek effort). Adım 16 da (üst kartlar, belgeler, PR hazırlığı) R1/R2 alır.

| Adım | Kart | Eksen | Tek review sonucu / başlama kapısı |
|---|---|---:|---|
| 0 | Hazırlık | 3 | Mevcut belge/kod/kaynak incelemesi, üç Proposed ADR, referans taslakları, kartlar; iki fresh belge turu, kullanıcı ADR onayı |
| 1 | [P02-3d](tasks/p02-3d-stage-graph-spec.md) | 2 | v2 kill karakterizasyonu (link, iki-worker PUT) + davranış korunarak aşama grafiği tek belirtimi; golden’lar değişmez |
| 2 | [P02-3e](tasks/p02-3e-resume-evidence-classifier.md) | 2 | Kapalı kanıt sınıfları (zincir birleşimi), uzak envanter indirgeyicisi, özetler |
| 3 | [P02-3f](tasks/p02-3f-continuation-domain-v3.md) | 2 | Strict v3 tipleri, politika, golden’lar, hata kodu |
| 4 | [P02-3g](tasks/p02-3g-continuation-persistence-read.md) | 3 | 3 tipli decode, v3 graf doğrulama, kapasite/rezerv, reset/bakım |
| 5 | [P02-3r](tasks/p02-3r-continuation-write-gates.md) | 3 | Yazma kapıları, soy bağı/donma, dataset tekilliği, namespace, M=0 geçişleri, kill |
| 6 | [P02-3h](tasks/p02-3h-continuation-workflow.md) | 3 | Taze envanter, confirm sayaç tabanı, alt küme koordinatörü, N-dosya proof, TLS/kill |
| 7 | [P02-3i](tasks/p02-3i-public-resume-surface.md) | 2 | Ortak `resume` (rapor/`--prepare`), onay bayrağı, gerçek yolculuklar, belgeler |
| 8 | [P02-3j](tasks/p02-3j-download-contract.md) | 2 | Doğrulama sözlüğü, DownloadPartial, aralık sınıflandırıcısı, hata kodları; **model yoklama kapısı bu adımdan önce** |
| 9 | [P02-3k](tasks/p02-3k-signed-get-transport.md) | 3 | Kimliksiz akışlı GET, kapalı başlıklar, guard, süre, sızıntı |
| 10 | [P02-3l](tasks/p02-3l-download-sink-publisher.md) | 3 | Akışlı yazıcı, sidecar protokolü, flock/sahiplik, ortak no-clobber yayın, kill/race |
| 11 | [P02-3m](tasks/p02-3m-download-engine-resume.md) | 3 | Motor, resume kararı, Range/ETag matrisi, protokol dönüşü |
| 12 | [P02-3n](tasks/p02-3n-model-weights-consumer.md) | 2 | `models download` tüketicisi ve yüzeyi |
| 13 | [P02-3o](tasks/p02-3o-download-native-acceptance.md) | 2 | Native 16/256/1.024 MiB, doğrulayıcı, kurulu smoke, CI, kanıt arşivi |
| 14 | [P02-3p](tasks/p02-3p-version-domain-reader.md) | 2 | Sürüm/bölme tipleri, strict codec, okuyucu, sapma |
| 15 | [P02-3q](tasks/p02-3q-public-version-surface.md) | 2 | `datasets versions list/show/bind/check`, artifact |
| 16 | [P02-3a](tasks/p02-3a-upload-resume-acceptance.md), [P02-3b](tasks/p02-3b-download-acceptance.md), [P02-3c](tasks/p02-3c-dataset-version-acceptance.md) | 2 | Üst kartlar: kurulu yolculuk, belge/matris/current, kalıcı kanıt, yetkili canlı kabuller, tek development PR |

**Büyüme kuralı.** Ölçülen büyüklük bir kartı L yaparsa iş sessizce küçültülmez; kart s–z harfleriyle bölünür ve burada kaydedilir. P02-3l ve P02-3m için bu kural önceden ilan edilmiştir (yazıcı/race ile sidecar/resume ayrı birimler olabilir).

**Otomatik ilerleme ve durma.** Bir adım R2 sonrası temiz kapandığında kullanıcıya dönmeden sonraki adıma geçilir. Dururum ve sorarım: (a) yeni veya değişen ADR, DDL/migration ya da kapsam küçültme gerektiren yeni bir bilinmez çıkarsa; (b) bir adım canlı hesap yetkisi gerektiriyorsa; (c) giderilemeyen engelleyici hata varsa. Kart bölünmesi durma sebebi değil, kayıt ve bildirimdir.

**Sıra gerekçesi.** Resume en riskli ve kararlı olması gereken hattır; en önce yapılır. Adım 1 salt refaktördür ve v1/v2 geçmişini koruyan, önceden genişletilmiş regresyon ağıyla kanıtlanır. İndirme (8–13) ve sürüm (14–15) resume’dan teknik olarak bağımsızdır; P02-3c’nin eski P02-3a/b bağımlılığı kullanıcı akışı sırasıdır, kod bağımlılığı değildir (P02-3q yalnız P02-3l’nin ortak yayın ilkesini kullanır).

**Kısmi onay.** Üç hat bağımsızdır. ADR’lerden yalnız bazıları onaylanırsa onaylanan hat başlar; ADR-0031 revizyon isterse indirme (8–13) ve sürüm (14–15) hatları önce yürür ve resume revizyon sonrası başlar.

**PR sınırı.** Epik başına tek development PR kullanıcı talimatıdır (önceki PR #14 428 dosya/+58 bin satırla incelendi). Hatlar (resume 1–7, indirme 8–13, sürüm 14–15) ardışık, bağımsız commit aralıklarıdır; kullanıcı isterse başlamadan PR’lar hat bazında bölünebilir, kapsam küçülmez.

## Kullanıcı kararları

Her karar için öneri, onaylanırsa/reddedilirse sonuç ve varsayılan:

| # | Karar | Öneri | Onaylanırsa | Reddedilirse / varsayılan |
|---|---|---|---|---|
| K1 | ADR-0031: soy bağlı, yeni onaylı continuation (aynı operation canlandırılmaz; kapalı kanıt sınıfları; `pending_uncertain` için ayrı insan onayı; create/proje/rejected belirsizse bloke) | Onayla | Adım 1–7 başlar | Resume hattı durur, diğer hatlar sürer; alternatif “yalnız salt okuma raporu” (adım 1–2 + rapor). Değiştirmeden ilerlemem |
| K2 | ADR-0032: motor + kesin model sürümü `models download`; dataset öğesi indirme yok; 1 GiB; resume yalnız güçlü ETag + 206; seviyeler | Onayla | Adım 8–13 başlar | Seçenekler: yalnız kütüphane (komutsuz) veya hat durur; varsayılan: durur |
| K3 | ADR-0033: salt okuma sürüm referansı; freeze ertelenir | Onayla | Adım 14–15 başlar | Freeze dahil istenirse ayrı ADR ve ek adımlar; aksi hat durur |
| K4 | Ertelenen takipler R4 (freeze), R5 (dataset baytı, dış koşul), R6 (bilinmeyen create sahiplenmesi), R7 (kesin ret makbuzu) | Ertelenmiş kalsın; gerekçe ve açılma ölçütü kartlarda | Epik bunlarsız kapanır, boşluklar P02-7’de görünür | R6 veya R7 P02-3’e alınırsa her biri ayrı Proposed ADR ve ek adım(lar) ister; varsayılan ertelenmiş |
| K5 | Tek PR | Tek PR | Plan aynen | Hat bazında bölme istenirse başlamadan bildirilir |
| K6 | Canlı girdiler: (a) model sürümü kimliği + salt okuma yoklama, (b) resume canlı kabulü (kalıcı private veri seti), (c) sürüm okuma canlı kabulü (dondurulmuş sürümlü dataset kimliği) | Üçünü de ver ya da “yok” de | İlgili kapı/kabul gerçek yapılır | Verilmeyen kabul “yapılmadı” olarak kayda geçer, üst kart bunu açıkça taşır; model yoklaması yoksa tüketici “canlı doğrulanmadı” |

**Hatırlatma.** ADR-0030 (performans kabulü) hâlâ Proposed; P02-7 ve ilk release önerisi öncesi çözülmelidir.

## Kabul ve kanıt planı

Her adım kendi kartındaki olumlu/negatif oracle’ları ve gerçek kontrolleri çalıştırır. Resume için gerçek SIGKILL matrisi mevcut sekiz sınıra link ve iki-worker PUT ile genişler (önce v2 yolunda karakterizasyon, sonra v3); indirme için ayrı kurulu `-I` süreçte 16/256/1.024 MiB native ölçüm (U≤64 MiB, G≤8 MiB, disk yazımı pencere içinde) ve `verify-download-reference` doğrulayıcısı eklenir; kurulu paket altı temiz kurulumda yeni komutları çalıştırır. Sonuçlar [uygulama ve kabul kaydında](../research/p02-3-implementation-validation.md) ve [kanıt standardına](../standards/research-evidence.md) göre kalıcı arşivde tutulur. CI üç ortamda tam takımı çalıştırır; başarısız ölçümler ve eski kabuller korunur.

## Teslim kaydı

Hazırlık dışında teslim yoktur. Bu plan hiçbir kartı `ready` yapmaz; kartlar ADR onayı ve doğrudan bağımlılıkların `verified` olmasıyla sırayla `ready` olur.
