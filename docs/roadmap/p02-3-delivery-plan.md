# P02-3 — Etkili resume, akışlı indirme ve veri sürüm bağları teslim planı

**Tarih:** 2026-11-06. **Durum:** Hazırlık; ADR-0031/0032/0033 Proposed ve kullanıcı onayı bekleniyor, kod başlamadı. **Dal:** `feat/p02-3-dataset-recovery`, development `94aaaf0` tabanı. Tek development PR; Master/release kullanıcıdadır. Kapsam kararı ve kanıtı [hazırlık incelemesindedir](../research/p02-3-readiness-review.md).

## Kullanıcı sonucu

Veri sorumlusu kesintiye uğrayan private yüklemeyi aynı Platform dataset’inde, yeni create veya DB düzenlemesi olmadan, yalnız kanıtlanmış güvenli adımları göndererek tamamlar ve neyin doğrulandığını görür (**P02-3a**). Model geliştirici kesin model sürümünün ağırlığını doğrulama seviyesi görünür, hedefi ezmeyen ve kesilince devam edebilen biçimde indirir (**P02-3b**). Kullanıcı bir veri sürümünü ve bölme sayımlarını görür, değişmez referansa bağlar ve sapmayı denetler; eğitim planı (P03-1) bu referansı tüketir (**P02-3c**). Sonuçlar yetki, fiyat veya dataset baytlarının uzaktan doğrulanması iddiası taşımaz.

## Kapsam kararları ve takipler

| Konu | Karar | Kayıt |
|---|---|---|
| Resume modeli | Aynı operation’ı canlandırma yok; soy bağlı, yeni onaylı continuation (dosya aktarım fazının kalanı) | [ADR-0031](../decisions/0031-upload-continuation.md) |
| Bilinmeyen create | Bloke; sahiplenme ayrı iş | [P02-R6](tasks/p02-r6-adopt-unknown-create.md) |
| İndirme | Tek dosya, ≤1 GiB, kimliksiz imzalı GET, kesin model sürümü ilk tüketici | [ADR-0032](../decisions/0032-bounded-download-and-verification-levels.md) |
| Dataset öğesi baytları | API anahtarıyla erişilemez; indirme kurulmaz; uzak byte doğrulaması boşluk olarak kalır | [P02-R5](tasks/p02-r5-dataset-item-byte-access.md) (`blocked`) |
| Sürüm/bölme | Salt okuma + değişmez referans; freeze/oluşturma yok | [ADR-0033](../decisions/0033-dataset-version-references.md), [P02-R4](tasks/p02-r4-dataset-version-creation.md) |

## Başlangıç kapıları

| Kapı | Durum |
|---|---|
| ADR-0031/0032/0033 kullanıcı onayı | Bekleniyor; onaylanmadan bağımlı ürün kodu yok. Hazırlık belgeleri (kartlar, sözleşme taslakları, plan) bu kapının parçası değildir |
| Dataset baytı erişimi | Dış koşul (`blocked`); P02-3 bunu beklemez, boşluk P02-7’de `partial` olarak görünür |
| Model indirme canlı kabulü | Kullanıcının erişebildiği bir model sürümü ve ayrı yetki gerekir; yoksa kabul “yapılmadı” olarak kalır |
| Resume ve sürüm okuma canlı kabulleri | Ayrı kapsamlı yetki gerekir (hedef owner/proje, azami istek/byte, kalan private kaynağın sahibi) |
| Performans referansı | Native indirme ölçümü kaynak bağlı M5 referans hostunda; ADR-0030 hâlâ Proposed (P02-7 öncesi çözülmeli) |

## Adımlar ve review döngüsü

Her kod adımı: **geliştir → ilgili gerçek kontroller → commit → fresh review R1 → doğrulanmış bulgu/fix/commit → farklı fresh reviewer R2 → doğrulanmış bulgu/fix/commit**. Reviewer’lar bulgu metni/yol/kodu untrusted veri sayar, güncel kodla doğrular; geçmiş yorum körlemesine uygulanmaz. Sonuçsuz tercih yeni bug diye sunulmaz. Gerekli düzeltmenin doğrulaması aynı turda tamamlanır. Karmaşıklığa göre model/effort seçilir: state, güvenlik ve eşzamanlılık dilimlerinde üç bağımsız eksen (state/atomiklik, güvenlik/gizlilik, contract/UX/test), diğerlerinde iki eksen. Önceki adım kabul/review bitmeden bağımlı sonraki adıma geçilmez; ölçülen büyüklük bir kartı L yaparsa iş sessizce küçültülmez, kart bölünür ve burada kaydedilir.

| Adım | Kart | Tek review sonucu / başlama kapısı |
|---|---|---|
| 0 | Hazırlık | Mevcut belge/kod/kaynak incelemesi, üç Proposed ADR, referans taslakları, kartlar; iki fresh belge turu, kullanıcı ADR onayı |
| 1 | [P02-3d](tasks/p02-3d-stage-graph-spec.md) | Davranış korunarak aşama grafiği tek belirtimi; golden’lar değişmez |
| 2 | [P02-3e](tasks/p02-3e-resume-evidence-classifier.md) | Kapalı kanıt sınıfları, uzak envanter indirgeyicisi, özetler |
| 3 | [P02-3f](tasks/p02-3f-continuation-domain-v3.md) | Strict v3 tipleri, politika, golden’lar, hata kodu |
| 4 | [P02-3g](tasks/p02-3g-continuation-journal-gates.md) | Kalıcı v3 kapıları, soy bağı/donma, kota, reset/yedek, kill |
| 5 | [P02-3h](tasks/p02-3h-continuation-workflow.md) | Taze envanter, alt küme koordinatörü, N-dosya proof, TLS/kill |
| 6 | [P02-3i](tasks/p02-3i-public-resume-surface.md) | Ortak `resume-report`/`resume`, gerçek yolculuklar, belgeler |
| 7 | [P02-3j](tasks/p02-3j-download-contract.md) | Doğrulama sözlüğü, DownloadPartial, aralık sınıflandırıcısı, hata kodları |
| 8 | [P02-3k](tasks/p02-3k-signed-get-transport.md) | Kimliksiz akışlı GET, kapalı başlıklar, guard, süre |
| 9 | [P02-3l](tasks/p02-3l-download-sink-publisher.md) | Akışlı yazıcı, sidecar, no-clobber yayın, kill/race |
| 10 | [P02-3m](tasks/p02-3m-download-engine-resume.md) | Motor, resume kararı, Range/ETag matrisi |
| 11 | [P02-3n](tasks/p02-3n-model-weights-consumer.md) | `models download` tüketicisi ve yüzeyi |
| 12 | [P02-3o](tasks/p02-3o-download-native-acceptance.md) | Native 16/256/1.024 MiB, doğrulayıcı, kurulu smoke, CI |
| 13 | [P02-3p](tasks/p02-3p-version-domain-reader.md) | Sürüm/bölme tipleri, strict codec, okuyucu, sapma |
| 14 | [P02-3q](tasks/p02-3q-public-version-surface.md) | `datasets versions list/show/bind/check`, artifact |
| 15 | [P02-3a](tasks/p02-3a-upload-resume-acceptance.md), [P02-3b](tasks/p02-3b-download-acceptance.md), [P02-3c](tasks/p02-3c-dataset-version-acceptance.md) | Üst kartlar: kurulu yolculuk, belge/matris/current, kalıcı kanıt, yetkili canlı kabuller, tek development PR |

**Sıra gerekçesi.** Resume en riskli ve kararlı olması gereken hattır; en önce yapılır. Adım 1 salt refaktördür ve v1/v2 geçmişini koruyan regresyon ağıyla kanıtlanır. İndirme (7–12) ve sürüm (13–14) resume’dan teknik olarak bağımsızdır ve bu sırayla yapılır; P02-3c’nin eski P02-3a/b bağımlılığı kullanıcı akışı sırasıdır, kod bağımlılığı değildir.

**PR sınırı.** Epik başına tek development PR (tercih korunur). Adımlar aynı dalda commit/review birimidir. Ölçülen diff büyüklüğü reviewer’ı aşarsa bölünme iş başlamadan bu belgede ve current’ta ilan edilir; kapsam küçültülmez.

## Kullanıcı kararları

1. **ADR-0031 (continuation).** Aynı operation’ı canlandırmak yerine soy bağlı yeni onaylı continuation; kapalı kanıt sınıfları; `pending_uncertain` için ayrı insan onayı; create/link/proje üyeliği belirsizse bloke.
2. **ADR-0032 (indirme).** Kesin model sürümü ağırlığı ilk tüketici (`models download`), dataset öğesi indirme yok (P02-R5); 1 GiB tavan; resume yalnız güçlü ETag + 206 ile; doğrulama seviyeleri ve beklenti kaynağı.
3. **ADR-0033 (sürüm).** Salt okuma + değişmez referans + sapma denetimi; sürüm oluşturma/freeze ertelenir (P02-R4).
4. **Ertelemeler.** P02-R4, R5, R6 yeni takip kartlarıdır. Hiçbiri sessiz küçültme değildir: gerekçe ve açılma ölçütü kartlarında.
5. **Canlı kabul ve girdiler.** (a) Model indirme için erişebildiğiniz bir model sürümü kimliği, (b) resume ve sürüm okuma için küçük, sınırlı canlı kabul yetkisi; biri verilmezse ilgili canlı kabul “yapılmadı” olarak kayda geçer ve üst kart bunu açıkça taşır.
6. **Hatırlatma.** ADR-0030 (performans kabulü) hâlâ Proposed; P02-7 ve ilk release önerisi öncesi çözülmelidir.

## Kabul ve kanıt planı

Her adım kendi kartındaki olumlu/negatif oracle’ları ve gerçek kontrolleri çalıştırır. Resume için gerçek SIGKILL matrisi mevcut sekiz sınıra link ve iki-worker PUT ile genişler; indirme için ayrı kurulu `-I` süreçte 16/256/1.024 MiB native ölçüm (U≤64 MiB, G≤8 MiB, disk yazımı pencere içinde) ve `verify-download-reference` doğrulayıcısı eklenir; kurulu paket altı temiz kurulumda yeni komutları çalıştırır. Sonuçlar [uygulama ve kabul kaydında](../research/p02-3-implementation-validation.md) (uygulama başlayınca açılır) ve [kanıt standardına](../standards/research-evidence.md) göre kalıcı arşivde tutulur. CI üç ortamda tam takımı çalıştırır; başarısız ölçümler ve eski kabuller korunur.

## Teslim kaydı

Hazırlık dışında teslim yoktur. Bu plan hiçbir kartı `ready` yapmaz; kartlar ADR onayı ve doğrudan bağımlılıkların `verified` olmasıyla sırayla `ready` olur.
