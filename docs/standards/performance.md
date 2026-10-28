# Performans ve optimizasyon standardı

**Durum:** Başlangıç/profil hedefleri ilk referans ortamda ölçüldü; aktarım/ağ hedefleri henüz ölçülmedi. **Tarih:** 2026-10-27. [İlk ölçüm](../research/p01-core-validation.md), [P01-2 yerel/Linux ölçümleri](../research/p01-2-implementation-validation.md), [P01-3 cache/input ölçümleri](../research/p01-3-implementation-validation.md). Büyük hash ölçümü gerçek aktarım desteği sayılmaz.

Performans; kullanıcı bekleme süresi, tepe bellek, ağ/disk işi ve API/kota tüketimiyle ölçülür. Daha az satır kod veya daha çok paralel iş tek başına iyileşme sayılmaz.

## Başlangıç bütçeleri

| Yol | İlk kabul hedefi | Ölçüm sınırı |
|---|---|---|
| `--help`, `--version` | Referans ortamda sıcak p95 ≤ 500 ms | En az 30 ayrı süreç; ağ/DB/sır/GPU import yok |
| Yerel profil/önbellek okuma | Sıcak p95 ≤ 200 ms | Veri boyutu ve disk türü kayıtlı; uzak istek hariç |
| P01-4 yerel jobs list/show | Yeni kabul hedefi: sıcak p95 ≤ 200 ms | Normal/yoğun fixture, kurulu wheel, 30 ayrı süreç; history payload taramayan bounded sorgu; uygulama ölçümü henüz yok |
| Büyük dosya aktarımı | 1 GiB dosyada istemci ek RSS ≤ 64 MiB | Eğitim süreçleri ayrı ölçülür; worker/chunk/buffer sınırı kayıtlı |
| Aktarım belleği | Dosya boyutuyla doğrusal büyümeme | 16 MiB, 256 MiB, 1 GiB fixture karşılaştırması |
| Kuyruk ve eşzamanlılık | Sınırlı worker + byte bütçesi | Başlangıç varsayılanı aktarımda 2 worker; hizmet limitinden düşük tutulur |
| Ağ işlemi | Açık connect/read/total deadline ve deneme bütçesi | Uç ve iş türü bazında; toplam bekleme sınırsız olamaz |

Bu değerler hedef olarak seçildi; donanım/Python/işletim sistemi, veri ve komut kaydedilmeden sonuç kıyaslanmaz. İlk gerçek ölçüm sonrası gerekçeli değişiklik yapılabilir; başarısız hedef sessizce gevşetilmez. Soğuk açılış ve kurulum boyutu ayrıca raporlanır.

### Aynı makinede başlangıç karşılaştırması

2026-10-28 kullanıcı onayıyla başlangıç ölçümü, test araçlarını içermeyen iki ayrı runtime ortamında yapılır. `scripts/check-startup.py`, taban ve aday kaynaklardan ayrı wheel üretir; her birinin `uv.lock` dosyasındaki runtime gereksinimlerini hash doğrulamasıyla yeni venv'e kurar. İki taraf aynı Python build'ini kullanır; kurulan paketin import kökeni doğrulanır. Kullanıcı site paketleri ve ortamdan gelen Python seçenekleri ölçüme taşınmaz; yalnız sentetik benchmark süreçlerinde sabit hash seed kullanılır. Ortam/paket sürümleri, wheel ve kaynak hash'leri raporlanır.

İki ayrı yeni fixture aynı profil baytları ve eşit 1.024 kayıt/payload hacmiyle hazırlanır. Aynı komutun taban/adayı aynı host üzerinde AB/BA sırasıyla dönüşümlü, eşzamanlı çocuk süreç olmadan ölçülür. Her tarafın ilk süreci ayrı tutulur; üç ısınma sonrası en az 30 örneğin tamamı kullanılır. p95 nearest-rank yöntemiyle hesaplanır; v2 raporu örnekleri ve eşik kararındaki p95'i tam hassasiyetle saklar. Aynı kaynağın iki kurulumu ile A/A kontrolü, karşılaştırma gürültüsünü ayrıca incelemek için kullanılabilir.

**Kabul adayın mevcut mutlak 500/200 ms bütçesidir.** Tabanın kötü sonucu veya göreli iyileşme, bütçeyi aşan adayı başarılı yapmaz. Taban ölçümleri ve eşli oranlar tanısaldır; yeni bir göreli eşik uydurulmaz. Eksik/uyumsuz baseline veya fixture kontrollü reddedilir; ilk release'in yalnız belge içeren Git tabanı açık `no_runtime_project_at_baseline` durumuyla raporlanabilir ve adayın bütün mutlak kapıları yine çalışır. Kaynak ölçüm boyunca değişmişse helper başarısız olur; mevcut rapor veya çalışma dizini ezilmez.

CI, PR'da ilan edilmiş base SHA'sını, development/Master push'unda önceki SHA'yı ayrı checkout'a sabitler. Manuel/ilk-ref koşusunda fallback aynı commit'tir ve gerçek bir önce/sonra kazancı sayılmaz. Ubuntu ana sürümü sabittir; gerçek image build'i, kernel, CPU ve kullanılabilir CPU affinity kaydedilir. Bu, GitHub'ın fiziksel CPU'sunu veya VM yükünü sabitlemez; farklı host'lardaki mutlak süre farkı kod kazancı diye yorumlanmaz. PR ve merge aynı ölçüm yolunu kullanır. Sonuçların dış CI doğrulaması sonraki P01-4 PR/merge akışında ayrıca yapılır; yerel kabul bu doğrulamanın yerine geçirilmez.

## Veri, ağ ve hesap verimliliği

Dosyalar bloklu hash/stream ile işlenir. Aynı disk üzerinde gereksiz paralel hash taraması yapılmaz. Hash önbelleği güncel içerik kanıtı yerine geçmez; değişmez snapshot veya güvenilir yeniden doğrulama stratejisi gerekir. Yükleme kuyruğu sadece dosya sayısını değil buffer baytını da sınırlar.

Listelemede N+1 çağrısı ölçülür; varsa sunucunun batch/sayfalama/koşullu GET yetenekleri kullanılır. Desteklenmeyen batch endpoint uydurulmaz. Model/yetenek önbelleği hesap/hizmet/sürüm ve son doğrulama zamanı taşır. Maliyet ve yetki kararı eski önbellekle kesinleştirilmez.

İzleme aralığı iş durumu ve sağlayıcı limitine göre uyarlanır; etkin olmayan iş yüksek frekansta sorgulanmaz. Backoff, jitter, `Retry-After` ve tüm işlem deadline'ı birlikte uygulanır. SDK/uygulama katmanlarında çarpan retry oluşmaz. Bağlantı havuzu kullanılır; tek komut gereksiz arka plan daemon'u başlatmaz.

## Darboğaz doğrulaması

Ölçüm; hazırlık/hash, bekleme, aktarım, uzak çalışma ve çıktı toplama sürelerini ayırır. Bir optimizasyon PR'ı başlangıç/son ölçümü, veri doğruluğunu ve kaynak etkisini içerir. Aşırı yükte kontrollü ret/backpressure beklenir. GPU modeli/hizmeti yavaş olduğunda gecikme Yörünge CPU optimizasyonu diye raporlanmaz.
