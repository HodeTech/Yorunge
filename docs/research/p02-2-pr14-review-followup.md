# PR #14 kullanıcı review takibi

**Tarih:** 2026-11-04. **Kaynak:** fd083a2 yerel /7e5675c uzak PR başı; development 50d68b1. **Durum:** Doğrulanmış düzeltmeler uygulanıyor; P02-2/a/b/c ve PR draft. Bu kayıt review iddialarını bağımsız kaynak denetimiyle sınıflar; bütün ajan iddiaları doğru kabul edilmez. Yeni source/test/script değişiklikleri nedeniyle 06 referansı artık önceki kaynağın tarihsel kabulüdür. Son bütün düzeltmeler/review ve gerekli karar kapanmadan yeni native seri veya source push yapılmaz.

## Uygulama sırası

1. **Ağ dayanıklılığı:** RST sonrası kaybolan peer metadata’sı, doğrulanmış DNS alternatifleri, 5 s keepalive ve owned TLS keylogging; aynı HTTP isteği/ortak deadline/peer/TLS sınırları korunur. Gerçek TLS ve bounded unit retleri; commit ve iki farklı fresh review turu.
2. **PUT receipt bütünlüğü:** Aynı anda biten veya cleanup sırasında tamamlanan başarılı task’ların tek publish denemesi; ilk hatadan sonra yeni arm/confirm yok, cancellation ve owner/lease kapıları korunur. Ayrı commit/iki fresh tur.
3. **Kullanıcı yolu ve anlamlı testler:** Onay/plan bayraklarının gerçek CLI negatifleri, v2 binding, populated migration/checksum, ctime recheck, consent/isolation, offline DNS/UDP koruması ve sinyal başlangıç koşulu; hız/süre/kota/hidden-file/unknown rehberi ve doğru hata mesajları. Yeni davranış uydurulmaz.
4. **Belge/kanıt ve teslim:** Aktif durum/head bilgileri, r5’in tarihsel kapsamı, yanlış original_commit ve gerçek proje literal’inin temizliği; gizlilik kararından sonra kişisiz çalışma kökünde bir son kaynak ölçüm serisi, üç ortam CI/altı kurulum/Sonar ve var olan bütün çıktının kalıcı saklanması.

Her kaynak dilimi commit → fresh R1 → doğrulanmış fix → farklı fresh R2 → fix teyidiyle kapanır. Önceden geçmiş bütün takımlar liste doldurmak için tekrarlanmaz; hedefli kontroller seçilir, tam takım final CI’ındır. Linux/macOS kapasite sorunu test veya workflow bypass’ıyla aşılmaz.

## Doğrulanan ürün kusurları

| Bulgu grubu | Bağımsız sonuç ve işlem |
|---|---|
| RST / peer=None | Doğrulanmış stream’in tamponlanmış cevabı okunmadan invalid_service_target verilebiliyor. Başlangıç TCP/TLS peer doğrulaması zorunlu; aynı stream’in sonradan kaybolan metadata’sı alttaki read/write sonucuna bırakılır. Görünen başka/bozuk IP yine reddedilir. |
| İlk DNS adresi | Bütün küme önceden doğrulanır; yalnız TCP kuruluş hatasında aynı tek çözümleme/ortak deadline altında sonraki numeric IP denenir. TLS/peer/HTTP hatasında fallback veya replay yoktur. |
| Keepalive | Guarded pool varsayılan None yerine mevcut hizmet yolu gibi 5 s ile sınırlanır. Bayat bağlantının her koşulda önlendiği iddia edilmez. |
| SSLKEYLOGFILE | Owned TLS context’lerinde keylogging kapatılır; sertifika/hostname/trust-store korunur. Context kurulumu header-only keylog dosyası açabilir; sıfır filesystem etkisi garantisi verilmez. |
| Eşzamanlı PUT | _drain ve _put_batch cleanup başarılı ayrı outcome’ları publish denemeden kaybedebiliyor. Her task en çok bir publish denemesi; publish sonrası belirsizlikte yeniden deneme yok. |
| Sınır/hız mesajları | 33,34 Mbit/s ve 120 s help/plan görünürlüğü ADR-0025 gereğidir. input_budget_exceeded yalnız 1 GiB dememeli; sayısal upload sınırları rehber/help’te açık olmalı. |

## Mevcut kararlar ve yanlış genişletilmiş bulgular

- **M5/Linux:** 06 M5 cache 147,0188 ms geçti; Linux 348,0745/208,4823 ms diagnostic_budget_exceeded tarihsel olarak saklanır. Birincisi ikincisinin performans başarısı değildir; H-1’in bunları aynı kapı sayması yanlıştır.
- **Discovery hedefi:** ADR-0017/0022 açık custom target’ı destekler. Credential/service/origin/API-root ve prepared wire eşliği zaten denetlenir; official-origin pin eklemek ayrı uyumluluk değişikliği olur. Transfer’in public-IP politikası normal discovery’ye sessizce taşınmaz.
- **Kalıcı kota:** ADR-0024, 128 plan/operation, 4.096 dosya ve 16 MiB rezervi birlikte uygular; tavanların hepsine aynı anda ulaşma garantisi yoktur. Otomatik geçmiş silmeme kabul edilmiştir. Forget/prune bu bugfix’e eklenmez; kapasite ve doluluk yolu görünür anlatılır.
- **Ayrı ad/hedef:** Exact namespace kilidi bilinçlidir; başka adla bilinçli ayrı iş ADR-0024’te mümkündür. Unknown işi yeni ad/store ile retry etmeyi uygulama önermez; hesap genelinde content kilidi eklenmez.
- **ID’siz unknown:** Ad tahminiyle yeni dataset ID/baseline üretilmez. Aynı yerel ID korunur; olası Platform kalıntısı ve otomatik kurtarmanın yokluğu açıklanır. Silme veya yeniden gönderim önerisi yoktur.
- **120/900 s:** Süreler, 5 s sonuç payı ve geç-start sınırlaması Accepted kararlardır. Yeni minimum throughput/admission veya daha uzun timeout seçilmez; mevcut sınırlar kullanıcıya açıklanır.
- **Proof sonrası hata / SQLite busy:** Geç çağrı hata verebilirken commit edilmiş başarı korunur; bu testle sabittir. SQLite’ın 1.000 ms busy beklemesi ve commit öncesi kayıpta same-ID uncertainty ADR-0011/0027 sınırıdır. Bunlar _drain’in publish’i hiç denememesiyle karıştırılmaz.
- **V1 golden:** write_access_digest, 37cbc6e’de ADR-0026 kabulünden önce eklendi. 37cbc6e, e58ea85 kabulü ve fd083a2’de journal-v1 golden SHA-256 aynıdır: c9e739fec4dcbd7c643ca375742a39de5531d5b190577238cafc29915f310091. Freeze sonrası byte değişimi yoktur; tarihsel decode/sürüm aileleri kaldırılmaz.
- **Ctime / fork:** Metadata imzası ctime_ns içerir; eksik olan captured recheck negatifidir. Xattr toleransı eklenmez. Ebeveyn permit’inin child’a miras kaldığı testi fork gerektirir; toplu spawn dönüşümü oracle’ı değiştirir. Diğer iki kill testinde deadlock kanıtı yoktur.
- **Probe consent:** Operatörün bounded pilot yetkisi ürün risk onayına çevrilir; TOS endpoint’i veya şart kabulü yoktur. storage --confirm ek confirm etkisini açar; presign/PUT izni ayrı accept-storage-probe bayrağıdır. Frozen kaynaklar düzenlenmez; tarihsel transport/exit sınırı README’de açıklanır.
- **Yeni özellik önerileri:** Filename-list DTO, forget/prune, content-wide kilit, write resume, yeni timeout/admission politikası, v1 aile silme ve paket bölme bu incelemenin doğruladığı bugfix’ler değildir. Mevcut sözleşmeyi değiştirmeden gerekli görünürlük sağlanır.

## Test ve kanıt boşlukları

Gerçek CLI approve/plan negatifleri ve yedi ek v2 binding predicate; migration 7 literal checksum ve dolu schema-6 geçmişinin byte koruması; ayrı consent/isolation negatifleri; production resolver/port/Unix/header sınırı; gerçek literal-secret dump assertion; current recheck ctime-only farkı; hata testlerinde exact kod/istek sayısı tamamlanır. Mevcut olan testler yok sayılmaz ve aynı aşama tekrar tekrar geniş koşulmaz.

Paylaşılan başarısız tam test günlüğünde SIGINT testleri ready bariyerini geçmiş; ayrıca in-process raise_signal(SIGINT) da beklenen istisnayı üretmemiştir. Bunu yalnız yük veya sıra bağımlılığına bağlamak kanıtlı değildir. Ignored/blocked başlangıç sinyaliyle uyumludur; hangisi ve nereden geldiği kaydedilmemiştir. Test launcher’ı foreground sinyal baseline’ını bir kez açık kurup önceki durumu geri yüklemeli; ürün çağrıları baseline’ı değiştirmemeli. Per-test kör reset veya timeout büyütme yapılmaz.

R5 ca0d29c/runtime07’de iki 79-byte dosyayı kapsar. Sonraki 128 KiB okuma/codec değişiklikleri TLS/native/CI ile çevrimdışı doğrulandı; yeni canlı kaynak kabulü diye sunulmaz. Public r5 receipt runner’ın exact private proof kontrollerinin sonucunu/sayaçlarını kaydeder; arşiv verifier’ı tek başına private exact metadata eşliğini yeniden hesaplatmaz. Ham receipt’e sonradan alan uydurulmaz.

## Gizlilik kararı

Belgelemenin kişisel yol yasağı ile orijinal kanıt baytlarını koruma kuralı çakışıyor. 442 arşivde bilinen yerel hesap yolu ve yayımlanmış Git author e-posta literal’lerinin dar taraması 90 eşleşen arşiv buldu: 87 yerel yol, 8 e-posta (örtüşür). Bu genel PII/secret veya gömülü ZIP taraması değildir; değerler yeni belgeye kopyalanmaz. Gizlilik/retention değişikliği ayrı [Proposed ADR-0029](../decisions/0029-evidence-provenance-privacy.md) ile kullanıcı onayına sunulur; bu karar bağımsız ürün kusurlarını bekletmez. Secret sızıntısı bulunduğu iddia edilmez; tarihsel gzip/history yeniden yazılmaz.

## Dilim 1 ilk doğrulama

Yeni bounded/fallback/peer/idle/keylog ve mevcut network unit seçkisi **84 passed**. Gerçek guarded 8 MiB PUT/RST’nin tam cevabı ve eksik cevap taşıma hatası ayrı sınandı. İlk iki test son resource assertion’ında olmayan closed özelliğine baktı; ürün beklentileri geçmişti. Test gerçek descriptor alanlarına düzeltildi, dar iki case geçti; ardından storage/gerçek TLS cancel/normal HTTP regresyonu **76 passed /41,99 s**. Bu iki son seçki ayrıdır. Strict mypy 144 ve değişen dosyalarda Ruff geçti. Kaynak review turları henüz beklenir; native/CI veya hesap çağrısı yapılmadı.


Dilim 1 /9815f70, R1 Astra/high contract + Sol/high safety ve farklı fresh R2 Sol/high contract + Astra/high safety tarafından bulgusuz kapandı. Reviewer’lar geçen testleri/ölçümleri tekrar çalıştırmadı. Literal socket-options iterator ve TLS-failure fallback için ek test fikri opsiyonel kapsam olarak kaydedildi; mevcut kod kusuru bulunmadı. İkinci kod dilimi artık receipt toplama bütünlüğüne geçebilir. Proposed ADR-0029 yalnız gizlilik/retention politikasını bekletir; ağ düzeltmesinin onay kapısı değildir.
