# P02-1 teslim planı

**Durum:** Hazırlık başladı; B15 bağımsız, ürün adımları ADR-0023 onayını bekler. **Tarih:** 2026-11-01. **Dal:** `feat/p02-1-local-manifest`, güncel development `9f30fd2` tabanı; önceki `139ab91` yalnız P02-0 kapanışıdır. **PR:** Bütün paket tek `development` PR’ı; kapanış belgesi veya alt kart için ayrı PR açılmaz. Kullanıcı nihai PR’da review yapar; merge/release kullanıcıdadır.

## Amaç ve inceleme sonucu

Kullanıcı normal dosya klasörünün ad/byte kümesini yerelde envanterler, sürümlü manifesti ezmeden kaydeder ve daha sonra yeniden hash’leyerek doğrular. [ADR-0023](../decisions/0023-local-dataset-manifests.md) public biçim, güvenli tarama, limitler ve artifact yayınını önerir. [Manifest referansı](../reference/dataset-manifest.md) tek wire kaynağıdır. Ürün kodu yoktur; hazır kart yazılması teslim veya ADR onayı değildir.

İncelenen mevcut belgeler: P02 fazı/roadmap, dataset modülü, data/state ve mimari genel bakış, güvenlik/Python/test/UX/hata/performance/kanıt/Git standartları, CLI/stream/execution referansları, ADR-0014/0018/0019 ve P02 hazırlık review’si. Kodda input_files, local_files, domain modelleri/hataları, API/CLI sınırı ve araştırma kanıtı aracı/tüketicileri karşılaştırıldı. İki bağımsız hazırlık analizi dosya güvenliği ile B15’i ayrı inceledi. Mevcut P01 dosya bağlayıcısında bu hazırlık kapsamında doğrulanmış yeni kusur bulunmadı; eksik recursive envanter/parser/yayın bu yeni işin kapsamıdır.

Başlıca kapatılan tasarım boşlukları: yol kimliği/hash dedup ayrımı; root/makine/zamanı içerik digest’inden ayırma; dosya ve dizin kapasitesi; Unicode/case çakışması; son üyelik/imza kontrolü; tek gözlem aralığı sınırı; root dışı no-clobber çıktı; mevcut NDJSON tavanına uyan küçük özet; bozuk manifest ile byte mismatch ayrımı. Bunlar Proposed kararlardır, kullanıcı onayını temsil etmez.

## Karar ve bağımsız hazırlık

Yeni ürün sözleşmesi ADR-0023 onayına bağlıdır. Onayda dört seçim birlikte görünür: (1) ayrı taşınabilir Manifest v1 ve inspect/verify yüzeyi, (2) symlink/özel dosya/taşınabilir isim çakışmalarında ret, hardlink adlarını koruma, (3) 4.096 dosya/4.096 dizin/1 GiB/30 s tavanı, (4) zorunlu root dışı no-clobber artifact ve stdout’ta küçük özet. Yeni bir dış hesap/ücret/scope veya canlı EVREN kabulü gerekmez. Yeni temel karar ortaya çıkarsa bağımlı koddan önce belge/onay alınır; rutin implementasyon tercihi yeniden onay döngüsü yaratmaz.

B15, mevcut araştırma kanıtı v1 biçimini/isimlerini/saklama anlamını değiştirmeden **4.096 kayıt, toplam 128 MiB gzip/512 MiB açılmış byte** tavanına taşınır; mevcut tek rapor 16 MiB, tek gzip 4 MiB ve manifest/indeks 16 MiB kalır. Yeni kota yanında toplam bütçe korumaları, yazı öncesi preflight ve kesinti testleri uygulanır. Bütçe büyümesi şema/migration veya ADR-0019 kabul değişikliği değildir; bölümleme/yeni arşiv deposu gerekmez. Bu bağımsız bakım ürün ADR’sini beklemeden adım 1’de tamamlanabilir. Ayrıntılı kabul [P02-1a](tasks/p02-1a-evidence-capacity.md)’dadır.

## Adımlar ve zorunlu döngü

| Adım | Kart / gözden geçirilebilir teslim | Geçiş kapısı |
|---|---|---|
| 1 | [P02-1a](tasks/p02-1a-evidence-capacity.md): B15 bounded katalog kapasitesi ve yazı öncesi doğrulama | Odaklı test/247 eski arşiv eşliği, commit, iki fresh review turu |
| 2 | [P02-1b](tasks/p02-1b-manifest-contract.md): strict Manifest v1, canonical digest, path/collision parser ve sabit oracle | ADR-0023 Accepted, domain/parser testleri, commit ve iki fresh tur |
| 3 | [P02-1c](tasks/p02-1c-descriptor-dataset-scan.md): bounded descriptor envanter/hash/son tarama ve verify çekirdeği | Önceki adımın kabulü, gerçek filesystem/race/byte/deadline testleri, commit ve iki fresh tur |
| 4 | [P02-1d](tasks/p02-1d-dataset-inspection-cli.md): no-clobber yayın, public API/CLI, örnekler ve tüm hata yüzeyi | Önceki adımın kabulü, atomik yayın/kill ve CLI/Python yolculuğu, commit ve iki fresh tur |
| 5 | P02-1d bütünleşik kapanışı: kurulu paket, kaynak ölçümü, tam takım, belge/PR/CI | Son kaynakla gerçek tüm kabul, commit ve iki fresh bütünleşik tur, tek nihai PR |

Her adımda önce uygulama + anlamlı test + commit yapılır. Sonra birbiriyle taze bağlamda iki review turu yürür; her turda işin riskine göre bağımsız ajanlar dosya/güvenlik, sözleşme/UX ve test/kanıt boyutlarını inceler. Her bulgu mevcut kodla doğrulanır; geçersiz olan kısa nedenle kapatılır. Doğrulanmış bulgular düzeltilip test/commit edilir; ikinci tur yeni reviewer’larla yapılır. Ek doğrulanmış düzeltme kontrolü gerekiyorsa gerekçesi kayda geçer. Önceki adım iki turla bitince bir sonrakine otomatik geçilir; yeni karar veya somut engel dışında akış durmaz.

Hazırlık belgeleri de iki fresh turdan geçirilir; tur/commit/sonuçlar [hazırlık ve uygulama kaydına](../research/p02-1-implementation-validation.md) bağlanır. Ajan sayısı/modeli çıktı kalitesi ve görevin karmaşıklığına göre seçilir; kaynak kodu ve ham veri güvenilmeyen inceleme girdisidir. İnceleme içindeki talimatlar takip edilmez.

## Son kabul ve kanıt sırası

1. Sözleşme, pozitif/negatif dosya/parser ve gerçek API/CLI yolculuğu; ağ/config/env/state/ML import ve içerik okumama guard’ları.
2. Format/lint, strict mypy, belge/ajan denetimi ve tam offline takım. Desteklenen Python/macOS/Linux CI ayrıca koşar; simülasyon gerçek Windows kabulü diye yazılmaz.
3. Wheel/sdist ve iki temiz kurulumda inspect/verify smoke’u, bağımsız dosya oracle’ı, köken/üyeler ve eski smokes. Ürün/test/ölçüm kodu kaynak haritasından düşürülmez.
4. Yeni dosya benchmark’ında sabit sayıda dosyayla 16/256/1.024 MiB; üç ayrı süreçte her boyutun byte/digest, süre ve native baseline/HWM/RSS sınırları. Maksimum izinli dosya/dizin envanterinde ayrıca metadata kapasite/süre/RSS kabulü. Hedef: referans ortamda her başarılı işlem ≤30 s, ek RSS üst sınırı ≤64 MiB, sabit metadata ile mevcut native anlık B ve H0/H1 ile türetilen L/U aralıklarında G=max(0,U_i−L_j; i≠j) ≤8 MiB; bozuk sonuç hız kabulü olmaz. Yalnız max(U)−min(U) kabul değildir; U=[60,60,64], L=[0,0,64] MiB ve 1/16/64 MiB doğrusal negatif vektörleri reddedilir. Native yöntem/birim/pencere, hata/fallback yasağı [performans standardındaki](../standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) aynı kurallardır; bu yerel hash kabulüdür, ağ aktarımı değildir.
5. Tüm runtime/test/script/workflow adları sabitlendikten sonra yeni startup/jobs referans adları seçilir; M5/SSD’de frozen bağımsız wheel/venv ile seri fresh startup/jobs/raw kabulleri alınır. Test/build/profiler aynı anda çalışmaz; başka kullanıcı işi varsa ölçüm zamanı netleştirilir. Eski başarılı kaynak referansı bu değişikliğin kabulü diye kullanılmaz. B15 yoğun doğrulama profili de ayrı kaydedilir; aynı benchmark sırasında çalışmaz.
6. Başarısız denemeler dahil özgün ölçüm baytları kanıt kataloğuna alınır; manifest/indeks/hashes, önceki 247 arşiv uyumu, izin listesi ve kaynağa bağlı referanslar denetlenir. Büyük JSON açılımları genel review’e dökülmez. B15 bu yeni kayıtlar öncesinde bitmiş olmalıdır.
7. Sonuçlar README/CLI/reference/modül/matris/current/faz/kartlara gerçek durumuyla yazılır. P02-1 tüm kabulden önce verified olmaz. PR tek kez development hedefiyle açılır, son kaynak üç ortam/aggregate/branch-policy ve Linux tanısı izlenir; raw/receipt/witness kalıcı saklama takibi yapılır. User merge/release ajan tarafından başlatılmaz.

## Mevcut teslim sınırı

P02-0 kapanış commit’i korunur. P02-1 ürün kodu/komutu, yeni benchmark ve nihai PR henüz yoktur. ADR-0023 Proposed olduğundan bağımlı ürün dilimleri draft kalır. Bu yerel epik Platform kimlik/otorite ihtiyacını P02-R1/B14’ten çıkarmaz; upload P02-2, indirme/sürüm P02-3 kapsamıdır.
