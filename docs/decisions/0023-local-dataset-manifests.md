# ADR-0023: Sınırlı yerel veri envanteri ve taşınabilir manifest

**Durum:** Proposed — kullanıcı onayı bekleniyor; bağımlı ürün kodu başlamadı. **Tarih:** 2026-11-01. **İş:** P02-1. [Teslim planı](../roadmap/p02-1-delivery-plan.md), [önerilen sözleşme](../reference/dataset-manifest.md).

## Bağlam

P02-1 klasördeki normal dosyaların adını, boyutunu ve güncel SHA-256 değerini koruyan yerel bir envanter ister. P01-3’ün descriptor bağlayıcısı yalnız en çok 128 açık execution referansını okur; recursive envanter, veri manifesti parser’ı veya rapor yayını değildir. Mevcut `data.manifest` yalnız manifest dosyasının baytlarını bağlar. Bu karar o bağı bütün veri dosyalarının execution doğrulaması olarak genişletmez; [ADR-0014](0014-execution-plan-validity-and-approval.md) limitleri ve trusted-local sınırı korunur.

Yeni public dosya biçimi, recursive dosya erişimi ve no-clobber çıktı politikası kullanıcı onayı gerektirir. B15 kanıt kataloğu kapasitesi aynı pakette bağımsız hazırlıktır; ürün manifesti ile araştırma kanıtı manifesti farklı biçimlerdir.

## Karar

### Kullanıcı işi ve kapsam

`datasets inspect ROOT --manifest-out FILE` bütün normal dosyaları tarar, sürümlü manifesti açık hedefe yazar ve küçük bir özet döndürür. `datasets verify ROOT --manifest FILE` manifesti sıkı biçimde okur, ağacı yeniden hash’ler ve aynı göreli dosya/byte kümesini karşılaştırır. Python karşılıkları aynı kullanım senaryolarıdır. Her iki işlem config, profil, credential, SQLite, ağ, EVREN veya eğitim aracı olmadan çalışır; bu seçenekler sessizce yok sayılmaz, CLI’da reddedilir.

Bu teslim dosya envanteri ve byte bütünlüğüdür. Görsel/etiket/JSONL içerik semantiği, arşiv açma, ignore/include/exclude deseni, upload, staging snapshot’ı ve execution producer desteği eklenmez. Kapsam ileride ayrı tüketiciyle genişler. Gizli dosyalar dahil bütün girdiler denetlenir; okunamayan veya desteklenmeyen dosya sessizce atlanmaz.

### İçerik kimliği ve adlar

`DatasetManifest v1` kapalı, strict UTF-8 JSON’dur. Tam biçim ve digest algoritması [kanonik referanstadır](../reference/dataset-manifest.md#manifest-v1). Her göreli dosya yolu ayrı kimliktir; aynı hash veya aynı inode taşıyan iki ad iki kayıt olarak kalır. Her yolun içeriği bağımsız okunur; boyut bütçesinde iki kez sayılır. Boş dosya ve boş ağaç geçerlidir. Boş dizinler dosya içeriği manifestine girmez; tarama güvenliği ve kapasitesinde sayılır.

Mutlak root, device/inode, timestamp ve makine bilgisi manifest gövdesine girmez. Aynı kabul edilen göreli ad/byte kümesi farklı kökte aynı digest’i üretir. SHA-256 kimlik imzası, kaynağın güvenilirliği, uzak teslim veya gelecekteki güncellik kanıtı değildir.

Orijinal UTF-8 ad korunur; yeniden adlandırma/normalizasyon yapılmaz. Her kardeş bileşende NFC → casefold → NFC karşılaştırmasıyla çakışma reddedilir; kontrol dizinleri ve dosya/dizin çakışmalarını da kapsar. Kullanılan Python Unicode verisi sürümü işlem özetinde bildirilir. Yeni Unicode sürümü yeni bir çakışmayı kontrollü reddedebilir; kabul edilen aynı adlar için içerik kodlaması/digest değişmez. Bu bir bütün dosya sistemleri/Windows ad uyumluluğu garantisi değildir. Taşınabilir adların kesin yasakları referansta kapalı tanımlıdır; surrogate/bozuk UTF-8 reddedilir.

### Descriptor üzerinden tarama ve güncellik

Destek macOS/Linux yerel disktir. Gerekli `dir_fd`, descriptor `scandir`, `O_NOFOLLOW`, `O_DIRECTORY`, `O_NONBLOCK` ve güvenli yayın primitive’i yoksa içerik okunmadan kontrollü ret verilir. `/` descriptor’ından root’un her bileşeni no-follow açılır; root dahil hiçbir symlink takip edilmez. Göreli root başlangıç CWD’sine bir kez bağlanır; `..` kabul edilmez.

Tarama descriptor’a göre yapılır. Dizin girdileri sınırı aşmadan toplanır ve orijinal UTF-8 baytlarına göre sıralanır; `DirEntry` önbelleği otorite değildir. Taze stat ve açılan descriptor’ın `fstat` bilgisi karşılaştırılır. Yalnız normal dosya ve dizin kabul edilir; FIFO/socket/device/symlink ve root’tan farklı `st_dev` reddedilir. Aynı device mount/aynı UID saldırısını bütünüyle engelleyen sandbox iddiası yoktur. Root dışına da bağlı hardlink’in root içindeki adı geçerlidir; root dışındaki diğer linkler keşfedilmez.

Dosya ilk gözlenen boyutu kadar en çok 1 MiB bloklarla hash’lenir; önce/sonra device/inode, mode, size, mtime_ns, ctime_ns ve okunan byte sayısı denetlenir. Son tarama geçişinde bütün dosya imzaları, her dizinin üyelik kümesi/imzası, ara bileşen kimlikleri ve mutlak root zinciri yeniden denetlenir. Gözlenen değişim tüm işlemi reddeder; eski hash cache’i veya otomatik tekrar kullanılmaz. Atime hash/üyelik kontrolüne dahil edilmez. Bütün descriptor’lar başarı, hata ve iptalde kapanır.

Bu seri bir gözlem aralığıdır; bütün ağacın atomik snapshot’ı veya son kontrol sonrası değişmezlik iddia edilmez. İşbirliği yapmayan aynı UID/root yazıcısı, inode yeniden kullanımı, mount/rename ve gözlenmeyen değişim sınırı ADR-0014 ile aynıdır. Gelecekte upload/çalıştırma kendi güncel içerik ve etki kapısını uygulamalıdır.

### Sayısal korumalar

| Bütçe | Önerilen sabit tavan |
|---|---:|
| Normal dosya | 4.096 |
| Dizin, root dahil | 4.096 |
| Root altındaki bileşen derinliği | 32 |
| Bir bileşen / göreli yol | 255 / 1.024 UTF-8 byte |
| Bir dosya / toplam mantıksal içerik | 1 GiB / 1 GiB |
| Hash bloğu / eşzamanlı worker | 1 MiB / 1 |
| Manifest dosyası | 8 MiB |
| JSON container derinliği / node | 8 / 50.000 |
| Kullanım senaryosu | 30 s monotonic toplam deadline |
| Açık scanner descriptor’ı | En çok 64 |

Manifest okuma ve metadata tarama kendi byte/adet sınırlarını ayrıca uygular; içerik bütçesi dosyaların mantıksal boyut toplamıdır. Sayısal tavanlar caller override’ıyla yükseltilmez. Deadline kontrol noktalarında uygulanır; engellenemeyen sistem I/O’suna katı fiziksel duvar saati garantisi verilmez. İptal başarısız hash’i başarılı kayıt yapmaz.

### Atomik dosya yayını ve sonuç

Inspect hedefi zorunludur ve kaynak root dışında olmalıdır. Manifest girdi dosyası da verify root dışında kalır; kendisini taramaya katacak örtük exclusion yoktur. Parent önceden mevcut olmalıdır; işlem dizin yaratmaz. Parent zinciri no-follow descriptor ile açılır, root kimliğiyle karşılaştırılarak root/alt dizini hedefi reddedilir; yalnız metin prefix’i yetkilendirme değildir.

Tam doğrulanmış manifest aynı parent içinde rastgele, `O_EXCL`, 0600 stage’e yazılır; byte sayısı, file sync ve parent/root zinciri son kontrolü tamamlanır. Hedef yalnız exclusive hardlink publication ile oluşturulur; mevcut dosya/dizin/dangling symlink ezilmez. `rename` ile overwrite fallback’i yoktur. Stage kaldırılır, parent sync tamamlanır; macOS’ta mevcut full-sync ilkesi kullanılır. Sonuç ancak yayın ve dayanıklılık kontrollerinden sonra başarılıdır. Caller kendi artifact’ının ad/konumunu açık seçer; artifact dosya adları/hash’ler içeren özel veri sayılabilir.

Yayın öncesi hata hedefi oluşturulmuş gibi anlatılmaz. Kritik link çağrısı başlamış fakat sonucu bilinmiyorsa (hedefi oluşturup dönüşünde iptal/istisna dahil) veya publication sonrası final sync/zincir/cleanup/deadline kontrolü bitmemişken hata oluşursa hedef oluşmuş olabilir; `manifest_write_uncertain`, exit 5 ve statik güvenli mesajla kullanıcı hedefi incelemeye yönlendirilir, otomatik tekrar yapılmaz. Süreç öldürülürse stage veya tamamı yazılmış hedef kalabilir; startup bunları kendiliğinden silmez. Kullanıcı seçtiği hedefi verify ile yeniden denetleyebilir. Kesin EEXIST mevcut hedefin başka kayıt olduğunu gösteren ayrı manifest_output_exists ret yoludur. Kalıcılık ve son kontroller tamamlanıp API başarıyla döndükten sonraki renderer BrokenPipe/I/O veya SIGINT mevcut output_closed/6, output_write_failed/1 veya request_cancelled/6 davranışını korur; tamamlanmış artifact bu nedenle belirsiz yapılmaz. Daha önce belirlenmiş gerçek manifest_write_uncertain sonucu ise exit 5 olarak korunur. Bu fiziksel güç kesintisi testi yapıldığı iddiası değildir.

Verify tam eşitlikte küçük `Result[DatasetVerification]` döndürür. İçerik/yol kümesi uyuşmazlığı `manifest_mismatch`, exit 7 ve digest/sayı özetli kapalı hata ayrıntısıdır; sınırsız dosya listesi stdout’a taşınmaz. Tam makine biçimi/hata önceliği referanstadır. Root yolu veya dosya içeriği ham istisna/hata mesajına eklenmez; inspect’in başarı özeti caller’ın seçtiği çıktı konumunu gösterebilir. JSON ve NDJSON mevcut Result v1’i korur.

## Değerlendirilen alternatifler

- **Execution input limitini büyütmek:** Büyük dosya listesini plan içine taşır ve mevcut 64 KiB/128 referans sınırını bozar; seçilmedi. Manifest dosyası ile tam girdi kapanışı ayrı kalır.
- **Stat/mtime veya önceki digest’i güncel içerik saymak:** Aynı boyutlu değişimi kaçırır; her doğrulama yeniden hash’ler.
- **Symlink takip etmek, sorunlu girdiyi atlamak:** Envanteri sessizce eksiltir; ilk sürümde açık ret seçildi.
- **Hash/inode ile dedup:** Farklı dosya adlarını kaybettirir; her göreli ad korunur.
- **Tam manifesti tek NDJSON event’ine koymak:** mevcut 1 MiB payload / 1 MiB + 1 KiB event sınırıyla çatışır; açık dosya artifact’ı ve küçük özet seçildi.
- **Kaynak altında çıktı veya overwrite:** Kendini dahil etme ve hedef yarışı yaratır; root dışında exclusive yayın seçildi.
- **Arşiv/etiket formatı denetimini birlikte eklemek:** Yerel normal dosya teslimini bağımsız içerik sözleşmelerine bağlar; bu karar bunları desteklenmiş ilan etmez.

## Kabul ve sonuçlar

Kartlar olumlu/negatif bağımsız digest vektörlerini, dosya yarışlarını, bütün sayısal retleri, CLI/Python eşliğini, disk-full/yayın/kill davranışını ve kurulu paketi kapsar. 16/256/1.024 MiB hash yolunda ek RSS ≤64 MiB ve mevcut native B/H0/H1 ölçümünden türeyen L/U ve G=max(0,U_i−L_j; i≠j) ≤8 MiB; yoğun dosya/dizin metadata kabulü ve 30 s referans hedefi ölçülür. Bunlar ölçüm öncesi hedeflerdir, geçmiş sonuç değildir. Kaynak bağlı startup/jobs referansları bütün script/test/runtime değişiklikleri bittikten sonra yenilenir.

Onay ürün manifesti, dosya/çıktı politikası ve sayısal korumaları açar; gerçek EVREN isteği, upload veya yan etkili plan yürütme yetkisi üretmez. Onaydan önce [P02-1b/c/d kartları](../roadmap/p02-1-delivery-plan.md) draft kalır. B15 aynı araştırma kanıtı v1 biçimiyle bağımsız tamamlanabilir.

## Teknik dayanak ve sınır

2026-11-01 tarihinde [Python 3.11 os](https://docs.python.org/3.11/library/os.html#os.scandir), [Unicode verisi](https://docs.python.org/3.11/library/unicodedata.html), [Linux link](https://man7.org/linux/man-pages/man2/link.2.html) ve [fsync](https://man7.org/linux/man-pages/man2/fsync.2.html) belgeleri incelendi. Enumeration sırası ve eşzamanlı üyelik garantili değildir; link mevcut hedefi ezmez; dosya sync’i parent directory kalıcılığını tek başına sağlamaz. Bu kaynaklar macOS uygulama/gerçek disk kabulünün yerine geçmez; desteklenen iki platformda gerçek primitive ve hata yolları ayrıca sınanır.
