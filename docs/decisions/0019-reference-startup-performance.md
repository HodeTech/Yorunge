# ADR-0019: Başlangıç performansının sabit referans ortamda kabulü

**Durum:** Accepted — 2026-10-30 kullanıcı yetkisi; iki P2 belge düzeltmesi, üç uygulama adımı, Sonar bakımı, fresh referanslar ve gerçek CI kabulü [kapanış kaydında](../research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı) doğrulandı. **Tarih:** 2026-10-29; revizyon 2026-10-30. **İş:** P01-6b.

## Bağlam

[Performans standardı](../standards/performance.md) help/version için 500 ms, context/cache için 200 ms sıcak p95 hedefler; en az 30 ayrı süreç ve üç ısınma kullanır. Jobs kabulü zaten açık M5/SSD referansına ve CI'da güncel kaynakla eşleşen ölçüm kaydına bağlıdır. Karar öncesinde startup her GitHub Linux 3.11 host'unda mutlak kapıydı; ubuntu etiketi fiziksel CPU/VM yükünü sabitlemez.

PR #11'in bf652f6 kaynağı [40945597506](https://github.com/HodeTech/Yorunge/actions/runs/40945597506) koşusunda AMD EPYC 9V74 üzerinde cache p95 **168,271 ms**, aynı-host taban **168,318 ms** verdi. Sonraki yalnız belge/kanıt head'i c2d8029, [40948271997](https://github.com/HodeTech/Yorunge/actions/runs/40948271997) koşusunda AMD EPYC 7763 üzerinde **232,641 / 218,998 ms** ile reddedildi. Ürün Python/test/script/lock/workflow baytları aynı; iki koşunun paket/runtime ve komut verileri arşivlidir. README/kanıt değişikliği wheel metadata ve sdist hash’lerini değiştirebilir; bütün dağıtım arşivlerinin byte-identical olduğu iddia edilmez. CPU modeli, anlık paylaşımlı host yükü ve disk etkileri ayrı ayrı nedensel olarak kanıtlanmış değildir. Başarısız örnek ve tüm ölçümleri [son-head kaydında](../research/p01-remaining-implementation-validation.md#son-head-başlangıç-ci-takibi) korunur.

İki koşuda bütün Linux testleri ve temiz kurulumlar geçti; macOS da kendi platform testlerini/kurulumunu geçti. Son kaydın startup reddi nedeniyle jobs/reference ve raw stream adımları çalışmadı. Önceki başarılı Linux raw v2 kabulü bu çalıştırılmayan adımların yerine sayılmaz.

Önceki hedefli import/şema/ASCII optimizasyonları üründe korunur. Yeni profil, cache yolundaki Pydantic modellerinin çoğunun gerçekten kullanıldığını gösterdi; kapsayıcı import süresini bütünüyle tasarruf saymak yanlıştır. Şimdilik 35 ms üzerinde kazanç sağlayacağı kanıtlı dar bir optimizasyon bulunmadı. Toplu deferred validation veya doğrulamayı atlama bu kararın çözümü değildir.

## Karar

### Tekrarlanabilir mutlak kabul

Startup'ın zorunlu **500/200 ms**, üç ısınma, en az 30 ayrı süreç, nearest-rank p95 ve 1.024 kayıtlı cache kapsamı korunur. Kabul ortamı, jobs için zaten kullanılan **Apple M5 Max/arm64, macOS 27.0.1, Python 3.11, internal SSD/APFS** referansı olur. Bu hedefler her CPU/VM için kesin duvar saati garantisi değildir. M5 sonucu Linux'ta 200 ms sağlandığı diye anlatılmaz.

Yeni kaynakta fresh frozen runtime-only wheel/venv, gerçek import/konsol kökeni ve aynı-host AB/BA taban/adayıyla yeni startup ölçümü alınır. İlk süreç ayrıca kaydedilir; OS cache'i boşaltılmış fiziksel soğuk başlangıç iddia edilmez. Dört aday p95'in tamamı mutlak sınırı sağlamalıdır; tabanın kötü sonucu veya adayın göreli kazancı ret sonucunu başarı yapmaz. Test/build/profiler ve diğer ağır işler ölçümle eşzamanlı çalışmaz. Başarısız koşudan en hızlı örnek seçilmez; yeni kaynak veya açıkça belgelenmiş yeni ölçüm koşulu olmadan tekrarla yeşil aranmaz.

### Kaynağa bağlı kanıt

Mevcut jobs kapısına benzer **ayrı startup reference kapısı** eklenir. Bu yeni helper/rapor uygulama kapsamındadır; mevcut CI kapısı yeni verifier ve kabul kanıtı tamamlanmadan teslim edilmiş sayılmaz.

- Referans producer'ı ölçümden önce/sonra tam public Python/test/script/fixture haritasını, pyproject.toml, uv.lock, examples/profile.toml ve CI workflow baytlarını bağlar. Kapsam mevcut jobs kaynak haritasından dar olamaz; startup'ın doğrudan tükettiği ek girdiler de kapsanır. CI güncel tam haritayı bağımsız okur. Commit SHA tek başına yeterli değildir; Markdown/kanıt kapanışı kod haritasını değiştirmiyorsa yeni performans koşusu gerekmez.
- Kurulu ürün Python baytları, wheel hash'i, konsol/import kökeni, Python/SQLite ve frozen runtime paketleri kaydedilir. Kaynak ve kurulum değişimi reddedilir. Fixture profil baytları, 1.024 kayıt/payload hacmi ve before/after bütünlüğü bağlanır. Ölçülen komutun beklenen işi yaptığı bounded typed stdout oracle ile süre dışında denetlenir; yalnız exit 0 yeterli değildir.
- **Ölçüm içi sabitlik ile güncel checkout eşliği ayrıdır.** Ölçüm boyunca wheel arşivi, bütün kurulu ürün Python dosyaları, konsol dosyası/entry point, runtime paket sürümleri ve fixture değişemez; tam before/after snapshot karşılaştırılır. Wheel SHA-256 bu koşunun tarihsel dağıtım kimliğidir; sonraki checkout'ta yeniden üretilen wheel'in arşiv SHA-256'sıyla eşitlik aranmaz. Güncel eşlik, tam kaynak haritası ve frozen paket kümesi üzerinden kurulur; kurulu `yorunge/**/*.py` haritası güncel `src/yorunge/**/*.py` ile birebir eşleşir. `pyproject.toml` bütünü (entry point, sürüm, bağımlılık/build/package ayarları dahil), lock, bütün public Python/test/script dosyaları, workflow ve profil kapsam içindedir. Bugünkü Python dışı paket girdisi `py.typed` işaretidir; kaynak/kurulum hash haritasına o da dahildir; böyle bir girdi eklenirse kaynak ve kurulum manifestine dahil edilmeden kabul verilemez. README'nin yalnız metadata açıklamasını değiştirmesi eski referansı geçersiz kılmaz; README'yi çalışma zamanında okumak veya paketleme/entry point/bağımlılık/Python değişimi geçersiz kılar. Konsol dosyasının venv'e özgü shebang hash'i tarihsel kurulum sabitliğidir; güncel entry point tanımı `pyproject.toml` ile bağlanır. Ayrı pozitif README/yeniden paketleme ve negatif runtime/entry point/lock vektörleri zorunludur.
- Yeni kapalı/sürümlü reference raporu; mevcut startup v2 ham örneklerini, tam before/after kaynak/kurulum/fixture kanıtını ve referans ortamını birlikte taşır. Verifier bütün örneklerden p95/kararı bağımsız hesaplar; finite pozitif süre, gerçek int örnek/ısınma sayısı, exact yöntem/bütçe ve dört komut kümesini denetler. Eksik/fazla/duplicate alan, bool-as-int, bozuk hash, farklı ortam, eski kaynak ve elle olumluya çevrilmiş ret kaydı reddedilir. Eski v2 startup arşivleri yeni reference diye yeniden etiketlenmez; yeni formatın alan/tip kümesi kanıt standardında kanonik tanımlanır.
- Referans dosya adı workflow ve testte **ölçümden önce** seçilir; wrapper ölçüm sonrasında eski JSON'a güncel hash ekleyerek geçmiş koşuyu güncel kaynağa bağlayamaz. Fresh ölçüm ve immutable yeni arşiv gerekir. Bütün ham örnekler ve başarısız koşular saklanır.
- Eksik/geçersiz/başarısız veya güncel kodla uyuşmayan referans zorunlu CI'ı kırar. M5 erişimi olmayan bakım sahibi kapıyı skip edemez, eşiği büyütemez veya başka host'u aynı ortam diye etiketleyemez. Referans donanım/runtime değişimi ayrıca gerekçeli ortam/yöntem kabulü gerektirir.

Bu kapı donanımı fiziksel olarak atteste etmez; projedeki mevcut jobs kanıtı gibi, maintainer'ın gerçek ölçüm ve bağımsız review kaydını güncel kodla bağlar. Bu güven/erişilebilirlik sınırı kullanıcı ve katkı belgelerinde açık kalır.

### Linux tanısı ve korunan dış kapılar

Linux 3.11 aynı PR/base kaynakları ve gerçek runtime ortamlarıyla seri AB/BA startup ölçmeye devam eder; aday/taban p95 ve ham örnekler aynen saklanır. Yalnız **yapısal olarak geçerli, kaynak/kurulum/fixture ve çıktı doğruluğu geçmiş bir kaydın mutlak süre aşımı**, `diagnostic_budget_exceeded` olarak CI tanı sonucu olur. Bu Linux performans başarısı değildir.

Bu, Linux'a özgü performans regresyonunu otomatik engelleyen mutlak kapının bilinçli kaldırılmasıdır: örneğin taban cache 200 ms iken aday 2 saniye olabilir; süreç 10 s timeout'a ulaşmıyor ve diğer doğrulamalar/M5 kapısı geçiyorsa aggregate yeşil olabilir. M5'te 200 ms'nin korunması bu Linux regresyonunu dışlamaz. Böyle bir aşım PR incelemesinde insan tarafından değerlendirilir; gerekçesiz regresyonla merge önerilmez. Yeni göreli eşik veya yönetilen Linux referansı bu kararda eklenmez.

### Linux tanısının görünürlüğü ve kalıcı saklanması

Workflow her tamamlanan ölçümde aday/taban p95, tam kaynak kimliği, `passed` veya `diagnostic_budget_exceeded`, rapor dosyası ve run bağlantısını step summary'ye yazar; aggregate özeti de tanı durumunu açıkça gösterir. Aşım bir warning üretir, performans başarısı diye sunulmaz. Strict doğrulanmış ham rapor ve makine tarafından okunabilen sonuç receipt'i `always()` artifact adımında **90 gün** saklanır; eksik dosya veya upload başarısızlığı başarılı saklama sayılmaz ve tamamlanan ölçümün CI işini başarısız yapar.

Kalıcı Git arşivinin sorumlusu işi teslim eden ajan/maintainer'dır. Merge önerisinden önce son incelenen kaynak kapsamındaki Linux ölçümleri (başarılı ve başarısız) indirilir; özgün baytlar `research_evidence.py archive` ile gzip/manifest/indekse alınır, doğrulanır ve kabul kaydında run/outcome/ortam ile bağlanır. Arşivleme başarısızsa PR kabulü açık kalır; artifact tek kalıcı kanıt sayılmaz. Son kanıt/belge commit'inin aynı ölçülen kaynak haritasıyla ürettiği ek CI ve kullanıcının merge koşusu, kullanıcıya açık bir saklama takibi olarak kaydedilir; bunların arşivi mevcut çalışma dalında veya kullanıcının yetkilendirdiği bir sonraki iş dalında, sonraki kabul/merge önerisinden **önce ve artifact süresi dolmadan** tamamlanır. Aynı kaynak olması yeni örnekleri atma yetkisi vermez; bu kapanış döngüsü kod değişmeden sonsuz belge/CI tekrarı gerektirmez.

İptal edilmiş koşu tamamlanmış ölçüm/kabul sayılmaz. Üretilmiş rapor varsa aynı şekilde korunur; rapor yoksa run kimliği ve hangi adımda iptal edildiği kabul kaydına yazılır. İptal nedeniyle upload yapılamadıysa eksik kanıt açık takip olarak kalır; olmayan örnek uydurulmaz. Bu insan saklama/inceleme yükümlülüğü aggregate'in tek başına doğruladığı bir işlem diye anlatılmaz. Görünürlük, aşım sonrası sonraki kapıların çalışması, upload hatası ve iptal/eksik rapor durumları test edilir.

Kurulum/komut hatası, timeout, eksik rapor, yanlış çıktı, kaynak/fixture değişimi, bozuk/nonfinite örnek, yöntem/bütçe uyumsuzluğu veya beklenmeyen exit yine CI'ı kırar. Genel `continue-on-error` veya koşulsuz `|| true` kullanılmaz. Tanı helper'ı bildirilen exit ile yeniden hesaplanan bütçe sonucunu da karşılaştırır; uyuşmazlık reddedilir. Geçerli mutlak aşımda sonraki zorunlu jobs reference ve gerçek Linux raw v2 ölçümü çalışmaya devam eder.

Üç ortamın tam test/statik/build/iki kurulum işleri, state 5 s/coordinator 30 s deadline'ları, kaynak bağlı jobs dört 200 ms kapısı, gerçek Linux raw v2 **64/8 MiB** kapıları, 120 s aktarım bütçesi ve mandatory aggregate korunur. Başarısız/atlanan uyumluluk işi yeşil aggregate olamaz. Ürün API/wire, secret, onay/dispatch latch veya model doğrulama kuralı bu kararla değişmez.

## Alternatifler

- Her değişken GitHub host'unda mevcut mutlak startup kapısını bırakmak: mevcut davranış; aynı ürün baytlarını farklı donanım/yükte yeniden reddedebiliyor. Referans ortam iddiası tam sağlanmıyor.
- Sabit ve yönetilen Linux runner: güçlü seçenek; yeni runner/altyapı/bakım ve erişim kararı gerekir. Bu PR kapsamında hazır kaynak/yetki yoktur; otomatik kurulmaz. Böyle ortam sağlanırsa ayrıca ölçülmüş referans olarak değerlendirilebilir.
- p95'i/200 ms sınırını yükseltmek, baseline'a bölerek mutlak reddi geçirmek veya başarısız koşuyu yeniden çalıştırarak en hızlısını seçmek: seçilmedi.
- Yalnız model defer veya validation atlamasıyla gözlenmemiş 35+ ms tasarruf varsaymak: ilk-use/deadline semantiğine geniş etki yapar ve kanıtı yoktur; seçilmedi. Gerçek dar optimizasyonlar ölçüm/uyumluluk kanıtıyla ayrıca yapılabilir.

## Sonuçlar ve kabul kapısı

Referans güncelleme yükü aynı M5 sahibi üzerinde artar; yeni kod için startup ve jobs ölçümleri seri alınır. Kaynak kapsamı daraltılmaz. CI Linux'un yavaş ölçümünü saklar; ürünün referans bütçesini güncel kod üzerinden yine zorunlu doğrular.

**Tarihsel uygulama planı (2026-10-30 onay anı):** Kullanıcı onayı ve iki fresh belge review turu tamamlandı; uygulama başlar. Önce kapalı rapor/verifier ve bağımsız sabit pozitif/negatif vektörler; ardından CI/katkı/performans belge uyumu, iki fresh review turu, sabit son kaynakta yeni M5 startup/jobs ve Linux tanı/raw kabulü tamamlanır. Tam test ve üç ortamın kurulum/aggregate kapıları tekrar geçmelidir. Sahte kaynak bağlama, eksik örnek, yanlış fixture/çıktı, eski runtime ve doğrulanmamış JSON'a sonradan metadata ekleme negatifleri ayrı test edilir. Bu planın uygulama/kabulü üstbilgideki son kaynak kaydında tamamlanmıştır. Mevcut c2d8029 başarısızlığı değiştirilmez; yeni kabul onu geriye dönük başarı yapmaz.
