# Performans ve optimizasyon standardı

**Durum:** P01 son kaynakta startup, M5 jobs referansı, raw TLS RSS ve yoğun state/migration kapıları geçti; [gerçek ortam/yöntem ve sınırlar](../research/p01-remaining-implementation-validation.md#faz-kapanışı-ve-gerçek-ci) kayıtlıdır. **Tarih:** 2026-10-29. [İlk ölçüm](../research/p01-core-validation.md), [P01-2 yerel/Linux](../research/p01-2-implementation-validation.md), [P01-3 cache/input](../research/p01-3-implementation-validation.md) tarihsel kalır. Hash/raw stream kabulü EVREN veri aktarım desteği veya bütün host'larda kesin süre garantisi değildir.

Performans; kullanıcı bekleme süresi, tepe bellek, ağ/disk işi ve API/kota tüketimiyle ölçülür. Daha az satır kod veya daha çok paralel iş tek başına iyileşme sayılmaz.

## Başlangıç bütçeleri

| Yol | İlk kabul hedefi | Ölçüm sınırı |
|---|---|---|
| `--help`, `--version` | Referans ortamda sıcak p95 ≤ 500 ms | En az 30 ayrı süreç; ağ/DB/sır/GPU import yok |
| Yerel profil/önbellek okuma | Sıcak p95 ≤ 200 ms | Veri boyutu ve disk türü kayıtlı; uzak istek hariç |
| P01-4 yerel jobs list/show | Yeni kabul hedefi: sıcak p95 ≤ 200 ms | Normal/yoğun fixture, kurulu wheel, 30 ayrı süreç; history payload taramayan bounded sorgu; [son kurulu ölçüm ve yerel kabul](../research/p01-4-implementation-validation.md#son-kaynakla-bütünleşik-yerel-kabul) geçti; normal/yoğun dört p95 ≤200 ms |
| Büyük dosya aktarımı | 1 GiB dosyada istemci ek RSS ≤ 64 MiB | Eğitim süreçleri ayrı ölçülür; worker/chunk/buffer sınırı kayıtlı |
| Aktarım belleği | Dosya boyutuyla doğrusal büyümeme | 16 MiB, 256 MiB, 1 GiB fixture karşılaştırması |
| Kuyruk ve eşzamanlılık | Sınırlı worker + byte bütçesi | Başlangıç varsayılanı aktarımda 2 worker; hizmet limitinden düşük tutulur |
| Ağ işlemi | Açık connect/read/total deadline ve deneme bütçesi | Uç ve iş türü bazında; toplam bekleme sınırsız olamaz |

Bu değerler hedef olarak seçildi; donanım/Python/işletim sistemi, veri ve komut kaydedilmeden sonuç kıyaslanmaz. İlk gerçek ölçüm sonrası gerekçeli değişiklik yapılabilir; başarısız hedef sessizce gevşetilmez. Soğuk açılış ve kurulum boyutu ayrıca raporlanır.

### Aynı makinede başlangıç karşılaştırması

2026-10-28 kullanıcı onayıyla başlangıç ölçümü, test araçlarını içermeyen iki ayrı runtime ortamında yapılır. `scripts/check-startup.py`, taban ve aday kaynaklardan ayrı wheel üretir; her birinin `uv.lock` dosyasındaki runtime gereksinimlerini hash doğrulamasıyla yeni venv'e kurar. İki taraf aynı Python build'ini kullanır; kurulan paketin import kökeni doğrulanır. Kullanıcı site paketleri ve ortamdan gelen Python seçenekleri ölçüme taşınmaz; yalnız sentetik benchmark süreçlerinde sabit hash seed kullanılır. Ortam/paket sürümleri, wheel ve kaynak hash'leri raporlanır.

İki ayrı yeni fixture aynı profil baytları ve eşit 1.024 kayıt/payload hacmiyle hazırlanır. Aynı komutun taban/adayı aynı host üzerinde AB/BA sırasıyla dönüşümlü, eşzamanlı çocuk süreç olmadan ölçülür. Her tarafın ilk süreci ayrı tutulur; üç ısınma sonrası en az 30 örneğin tamamı kullanılır. p95 nearest-rank yöntemiyle hesaplanır; v2 raporu örnekleri ve eşik kararındaki p95'i tam hassasiyetle saklar. Aynı kaynağın iki kurulumu ile A/A kontrolü, karşılaştırma gürültüsünü ayrıca incelemek için kullanılabilir.

**Kabul adayın mevcut mutlak 500/200 ms bütçesidir.** Tabanın kötü sonucu veya göreli iyileşme, bütçeyi aşan adayı başarılı yapmaz. Taban ölçümleri ve eşli oranlar tanısaldır; yeni bir göreli eşik uydurulmaz. Eksik/uyumsuz baseline veya fixture kontrollü reddedilir; ilk release'in yalnız belge içeren Git tabanı açık `no_runtime_project_at_baseline` durumuyla raporlanabilir ve adayın bütün mutlak kapıları yine çalışır. Kaynak ölçüm boyunca değişmişse helper başarısız olur; mevcut rapor veya çalışma dizini ezilmez.

CI, PR'da ilan edilmiş base SHA'sını, development/Master push'unda önceki SHA'yı ayrı checkout'a sabitler. Manuel/ilk-ref koşusunda fallback aynı commit'tir ve gerçek bir önce/sonra kazancı sayılmaz. Ubuntu ana sürümü sabittir; gerçek image build'i, kernel, CPU ve kullanılabilir CPU affinity kaydedilir. Bu, GitHub'ın fiziksel CPU'sunu veya VM yükünü sabitlemez; farklı host'lardaki mutlak süre farkı kod kazancı diye yorumlanmaz. PR ve merge aynı ölçüm yolunu kullanır. İlk bakımın dış CI doğrulaması [P01-4 PR/merge akışında tamamlandı](../research/p01-4-implementation-validation.md#development-merge-kapanışı); bu önceki kaynağın tarihsel kabulüdür. Yeni kaynak/bağımlılık için ilgili PR ve merge akışı ayrıca doğrulanır; yerel kabul dış CI yerine geçirilmez.

### Kurulu jobs ve raw stream ölçümü

`scripts/benchmark-jobs.py`, frozen runtime-only wheel kurulumunda normal/yoğun jobs list/show yollarını ayrı ölçer. İlk süreç kaydı, üç ısınma ve her yol için en az 30 ayrı süreçten nearest-rank p95 saklanır. Dört p95'in her biri mevcut 200 ms kapısına tabidir. Fixture hazırlığı ve bağımsız typed çıktı/DB oracle kontrolü kaydedilen süreç süresinin dışındadır; bütün örnekler korunur. Kaynak snapshot'ı, kurulu Python baytları/metadata, fixture ve varsa wheel hash'i öncesi/sonrası denetlenir. İlk süreç fiziksel soğuk disk ölçümü değildir.

`scripts/benchmark-stream.py`, ayrı TLS sunucusu ve her boyut için yeni kurulu `-I` istemci süreciyle 16/256/1024 MiB'ı seri okur. Veri artımlı üretilir/tüketilir; istemci tek stream, en çok 2 bağlantı, 32 KiB chunk ve kuyruksuz tüketici kullanır. Alınan byte/SHA-256, chunk/request/connection sayıları ve farklı server/client PID'leri kaydedilir. Her boyutta ek RSS≤64 MiB olmalı; üç boyutun farkı ve boyut büyüme eğilimi birlikte incelenir. Bu ortak raw taşıma kabulüdür; veri seti endpoint'i, NDJSON veya eğitim worker'ı kabulü değildir.

RSS yöntemi `resource.getrusage(RUSAGE_SELF).ru_maxrss` high-water değeridir: import/köken kontrolü ve 32 KiB TLS ısınmasından sonraki süreç tepe değeri baseline; ölçüm sonrası tepe eksi baseline ek RSS'tir. Bu anlık RSS farkı değildir ve ısınmanın daha önce oluşturduğu tepeyi yeniden saymaz. Native değer Darwin'de byte, Linux'ta KiB olarak açıkça çevrilir; native/baseline/peak/extra birlikte korunur. Ayrı sunucu ve parent hazırlık süreci hariçtir. Boyut başına tek istemci ve tek ölçüm isteği kullanılır; sonuç başarısızsa daha hızlı/az bellekli örnek seçilmez. Raw benchmark'ın açık 120 s total deadline'ı, 5 s phase ve 1 s pool sınırları kontrol noktalarında uygulanır; sistem I/O'sunu zorla kesen fiziksel süre garantisi değildir.

Jobs 200 ms kabulünün referansı, önceki P01-4c kabulündeki aynı host/disk şartını somutlaştıran **Apple M5 Max/arm64, macOS 27.0.1, Python 3.11, internal SSD/APFS** ortamıdır. Linux'taki ilk jobs ölçümünün 206–339 ms reddi ayrıca korunur; yerel başarılı sonuç onu başarılı yapmaz, farkın yalnız CPU'dan doğduğu kanıtlanmış değildir. Değişken GitHub Linux host'unu aynı jobs referansı saymak ilk adım 6 CI tanımındaki yanlış varsayımdı; 200 ms değeri yükseltilmez veya bütün Linux host'larında sağlanmış gösterilmez.

CI Linux 3.11 hücresinde startup ve raw stream'i test/build sonrası seri ölçer; jobs için **kaynağa bağlı referans kanıtı kapısını** zorunlu çalıştırır. `research_evidence.py verify-jobs-reference NAME`, dört 200 ms/30 süreç yolunun tamamı geçmiş referansı; kapalı rapor, hash, typed stdout ve kurulum/fixture sabitliğiyle doğrular. Kaydın bütün runtime/script/fixture/lock/workflow hash haritası ve frozen runtime paketleri güncel checkout ile aynı olmalıdır; eksik/eski/değişmiş kaynak veya başarısız/yabancı ortam kaydı kapıyı geçemez. Doküman/arşiv kapanışı commit SHA'sını değiştirebilir; ölçülen kod baytları değişemez. Yeni ölçümden önce CI'daki referans dosya adı seçilir; ölçüm bu workflow baytlarını da içerir. Kaynak değiştiğinde yeni adla referans tekrar alınır, eski kayıt ezilmez. Bu kapı ölçümü CI'da yeniden çalıştırmaz veya fiziksel donanımı atteste etmez; gerçek yerel ölçüm ve bağımsız review kaydını güncel kaynakla bağlar. Referans olmadan P01 kabulü verilmez.

Linux 3.14 ve macOS 3.11 hücreleri uyumluluk/test/kurulum içindir. CI genel başarısı Linux jobs 200 ms kabulü değildir; ortam bazlı başarısız/çalıştırılmamış performans ayrı belirtilir. Bütün başarılı/başarısız ham örnekler ve kaynak kimliği kanıt arşivinde saklanır. İleride referans donanım değişimi yeni ortam/yöntem kanıtı gerektirir; sessiz hedef veya kapsam değişimi olmaz.

## Veri, ağ ve hesap verimliliği

Dosyalar bloklu hash/stream ile işlenir. Aynı disk üzerinde gereksiz paralel hash taraması yapılmaz. Hash önbelleği güncel içerik kanıtı yerine geçmez; değişmez snapshot veya güvenilir yeniden doğrulama stratejisi gerekir. Yükleme kuyruğu sadece dosya sayısını değil buffer baytını da sınırlar.

Listelemede N + 1 çağrısı ölçülür; varsa sunucunun batch/sayfalama/koşullu GET yetenekleri kullanılır. Desteklenmeyen batch endpoint uydurulmaz. Model/yetenek önbelleği hesap/hizmet/sürüm ve son doğrulama zamanı taşır. Maliyet ve yetki kararı eski önbellekle kesinleştirilmez.

İzleme aralığı iş durumu ve sağlayıcı limitine göre uyarlanır; etkin olmayan iş yüksek frekansta sorgulanmaz. Backoff, jitter, `Retry-After` ve tüm işlem deadline'ı birlikte uygulanır. SDK/uygulama katmanlarında çarpan retry oluşmaz. Bağlantı havuzu kullanılır; tek komut gereksiz arka plan daemon'u başlatmaz.

## Darboğaz doğrulaması

Ölçüm; hazırlık/hash, bekleme, aktarım, uzak çalışma ve çıktı toplama sürelerini ayırır. Bir optimizasyon PR'ı başlangıç/son ölçümü, veri doğruluğunu ve kaynak etkisini içerir. Aşırı yükte kontrollü ret/backpressure beklenir. GPU modeli/hizmeti yavaş olduğunda gecikme Yörünge CPU optimizasyonu diye raporlanmaz.
