# ADR-0012: Opak credential kimliği ve gözlenen anahtar değişimi

**Durum:** Accepted — 2026-10-27 kullanıcı onayıyla benimsendi; henüz uygulanmadı. **Tarih:** 2026-10-27. **Kayıt:** B13. ADR-0005 ve execution/capability bağlarını ayrıntılandırır. Yerel HMAC kaydı, koruma anahtarı dosyası ve bağlı binding v1 sözleşmesi bu onaya dahildir.

## Bağlam

Env referansı aynı kalırken değer değişebilir. Offline çözümlemede kullanılabilecek güvenilir sağlayıcı key ID/rotation metadata'sı henüz yoktur. Aynı değerde süreçler arası kararlı kimlik ve sessiz değişimi yakalama hedefi, önceki değerle ilişki kuran kalıcı veya güvenilir dış kanıt gerektirir. Ham credential/hash saklanamaz. [Seçenekler, tehdit sınırı ve deney raporu](../research/p01-2-state-identity-decision-review.md) bu kararın dayanağıdır.

## Karar

Public `credential_id` sırdan bağımsız UUIDv4; `credential_revision` pozitif, SQLite signed-64 sınırında tamsayıdır. İlk gözlem 1, farklı değer gözlemi +1; 2^63−1'de değişim kontrollü hata ve rollback üretir, otomatik sarma/reset yoktur. Açık identity reset ayrı etkili kurtarma yoludur. Sır bir kez çözülür; hizmet/hedef/kimlik ve guarded secret taşıyıcısı aynı snapshot'a bağlanır. Env adına geri dönüp ikinci kez sır okunmaz.

DB'de yalnız yerel, dışarı aktarılmayan **HMAC-SHA-256 doğrulayıcısı** tutulur; bu ham SHA-256 değildir ama sırdan türetilmiş hassas bir kayıttır. Public kimlik, plan digest'i, capability, log, repr/str, hata veya genel JSON içine girmez. HMAC şifreleme veya uzak kimlik doğrulaması değildir.

Bu karar, [Accepted ADR-0004'teki](0004-local-durable-operation-state.md) “Sırlar DB'ye yazılmaz” sınırını yalnız bu özel keyed verifier için **2026-10-27 kullanıcı onayıyla daraltır**; ham credential, ham hash veya geri çözülebilir credential DB'ye yazılamaz. Genel kayıt/export yasağı korunur. Bu daraltma tasarım kuralıdır; yerel verifier'ın uygulanmış veya ürün kabulünün tamamlanmış olduğu anlamına gelmez.

### Kapsam, kayıt ve kodlama

Hedef/UNIQUE/HMAC alanları ve byte encoding'in tek normatif kaynağı [credential binding v1 sözleşmesidir](../reference/credential-binding-v1.md). `credential_bindings`, sözleşmedeki altı NOT NULL/UNIQUE alanına ek olarak UUID credential ID, pozitif revision, tag biçimi, 32 bayt tag ve UTC gözlem zamanı taşır. Hesap/proje/izinler credential ID yerine geçirilmez; ayrı context bağlarıdır ve sonraki cache/plan anahtarında ayrıca karşılaştırılır. Sözleşme env adı için mevcut 1–128 ASCII sınırını ve secret için önerilen 1–16.384 UTF-8 bayt sınırını açıkça tanımlar.

Farklı hizmet/hedef/referanslar aynı değeri taşısa da varsayılan olarak kayıt/ID paylaşmaz. Profil adı namespace değildir. İlk kez görülen hedef için yeni binding/ID oluşur; aynı hedefe dönüşte kendi kaydı kullanılabilir, başka hedefin bağı kullanılamaz. Origin/API kökü ortak `service-target-v1` kuralıyla bir kez kanonikleştirilir; bu host'a güven veya API uyumu kanıtı değildir. Etkin port 443'tür fakat origin metninde `:443` bulunmaz; mevcut offline plan yazımı/digest'i yeniden yazılmaz.

Sözleşmedeki HMAC mesajı, key-check mesajı ve sentetik byte vektörleri aynen kullanılır; alan kümesi/JSON seçenekleri uygulamada yeniden yorumlanmaz. Sırda trim/lowercase/dönüşüm yapılmaz; encoding/şema/boyut hatası kontrollü reddedilir. Karşılaştırma `hmac.compare_digest` ile aynı uzunlukta byte tag'ler arasında yapılır; özel kripto geliştirilmez.

### Yerel karşılaştırma anahtarı ve dosya yaşam döngüsü

K, `secrets.token_bytes(32)` ile oluşturulan 256 bit yerel karşılaştırma anahtarıdır; EVREN credential'ı değildir. [ADR-0011](0011-state-foundation-and-migrations.md) state dizini altında ayrı 0700 `keys` dizininde `<random-key-id>.key` dosyasında 0600/yalnız sahip erişimiyle, tam 32 bayt tutulması önerilir. K DB, config, paket, gözlem logu veya normal çıktı içine yazılmaz. **Bu dosya açık key baytlarını taşır; 0600 şifreleme değildir ve aynı UID'deki diğer süreçler K'yı okuyabilir.** DB+K, özellikle düşük entropili credential için offline tahmin doğrulaması sağlar; bu tehdit kabul edilen yerel kullanıcı sınırının dışındadır. Otomatik keychain erişimi veya yeni runtime bağımlılığı eklenmez.

Dosyalar immutable ve no-clobber oluşturulur; no-follow, sahiplik/izin ve boyut denetimi gerekir. Key dosyası ve yeni `keys`/state dizinlerinin **üst dizin girdileri dahil** kalıcılık sırası/platform sync kapısı [ADR-0011'deki tek kurala](0011-state-foundation-and-migrations.md#dosya-ve-dizin-kalıcılığı) uyar. Her sync hatası yeni pointer commit'ini durdurur. DB `active_key_id` ve store'a bağlı ayrı purpose HMAC key-check taşır; yanlış 32 bayt dosya credential rotation sanılmaz. K eksik/bozuk/yanlışsa mevcut epoch'ta otomatik yeniden üretilmez.

İlk anahtar veya açık reset'teki yeni anahtar, DB'nin aktif key/epoch pointer'ı commit edilmeden önce kalıcılaştırılır. Aynı store yazma transaction'ı aktif key'i tekrar denetler. Kesinti öncesi oluşmuş fakat referanslanmayan dosya, key/DB durumu doğrulanmadan benimsenmez veya silinmez; aktif pointer eksik dosyayı gösteriyorsa hata olur. Bu iki dosyanın tek transaction'la atomik güncellendiği iddiası kurulmaz. Ürün kabulü, her sınırda hata enjeksiyonu ve iki süreç başlatmasını gerektirir.

### Gözlem, concurrency ve kurtarma

Seçili değer çözülüp hedef snapshot'ı sabitlenir. `BEGIN IMMEDIATE` içinde etkin epoch/key-check ve binding tekrar okunur. Kayıt yoksa yeni ID/1; tag aynıysa aynı ID/revision; farklıysa aynı ID/revision+1 ve yeni tag birlikte commit edilir. UTC zaman yalnız ilk/değişmiş gözlemde yazılır; aynı tag için gereksiz kayıt güncellemesi yapılmaz. Aynı B değerini gören eşzamanlı süreçler tek değişim kaydeder. Bağımsız süreçlerde A/B env snapshot'ları dönüşümlü görülürse nesil her yeni gözlemde ilerleyebilir; evrensel bir env değeri varmış gibi anlatılmaz.

Gözlenen A→B→A sırası 1→2→3 olur; gözlenmeyen ara değişimi veya değeri aynı kalan sunucu izin/revocation değişimini yerel HMAC bulamaz. Credential kaydı uzak `supported`, `remote_verified` veya execution izni sağlamaz. Sonraki yürütme, snapshot'ın hâlâ etkin bağa/nesle ait olduğunu ayrıca denetler.

Farklı env snapshot'larının sürekli yarışması eski nesli yeniden kullanma veya revision'ı cache anahtarından çıkarma gerekçesi değildir. P01-3 cache'i binding başına güncel nesille ve sınırlı saklamayla çalışmalı; stale nesiller cache'i sınırsız büyütmemeli, yan etki kullanım senaryosu otomatik yeniden çözümleme döngüsüne girmeden kontrollü bağ çatışması vermelidir. Cache uygulaması P01-3'tedir; bu kart onu hazır göstermez.

### Identity reset ve DB restore ayrımı

**Identity reset**, mevcut doğrulanmış canlı DB üzerinde açık, etkisi gösterilen işlemdir; DB dosyasını geçmiş snapshot'la değiştirmez. Yeni epoch/key ve sonraki gözlemlerde yeni credential ID'leri üretir. Önceki epoch kayıtları aktif kabul edilmez; eski plan/cache bağları yeniden geçerli olmaz. Mevcut operation geçmişine dokunulmaz; reset, unknown iş için yeniden gönderim izni değildir. K kayıp/bozuksa eski tag doğrulanamaz; reset yalnız DB'nin sahiplik/sürüm/bütünlük/metadata denetimleri geçtiğinde açık kullanıcı isteğiyle yapılabilir. Eski K'nın doğrulandığı veya credential'ın kurtarıldığı iddia edilmez.

**DB restore**, geçmiş snapshot'ın yeniden canlı hale getirilmesidir ve snapshot'tan sonraki kayıtları geri getiremez. P01-2'de destek yalnız identity şemasına ait, tam/sağlam/sahipliği ve kaynak UUID/sürümü doğrulanmış migration backup'ı içindir. Hedefe sessiz overwrite yoktur; varsa mevcut canlı DB ayrı no-clobber güvenlik snapshot'ıyla korunur. Restore'a özel geçici hedefte doğrulama + yeni epoch/key reset'i tamamlanıp file/dizin kalıcılık sırası sağlanmadan canlıya geçilmez; bütün normal store kullanıcılarının katıldığı dış dosya kilidiyle erişim durdurulur, açık bağlantılar kapanır. Restore kesintisinde hangi dosyanın canlı olduğu belirlenemiyorsa normal açılış kontrollü onarım hatası verir; eski kimlik bağı kabul edilmez. Kimlik geçmişi kaybolabilir; yeni kimlik alanı yalnız eski plan/cache'i geçersizleştirir, kayıp kaydı geri üretmez. K backup/normal JSON export'una katılmaz; yeni K üretilir. Backup'ın eski K/key-check'i restore öncesi doğrulandı diye sunulmaz; reset, yeni key-check'i kurar.

Canlı dosyayı değiştirmeden önce state dizinindeki özel/no-clobber `restore-intent.json`, kaynak/hedef store ve yeni epoch/key kimlikleriyle kalıcılaştırılır; sır taşımaz. Normal store açılışları [ortak bakım kilidi altında](0011-state-foundation-and-migrations.md) bu kaydı denetleyip açık restore/onarım dışında erişimi reddeder. Geçici hedef desteklenen eski şemadaysa canlıya alınmadan önce hedef uygulama sürümüne migration/reset tamamlanır; canlıda downgrade yapılmaz. Yeni canlı DB + K ve ilgili dizin girdileri kalıcı ve birlikte doğrulanmış olduktan sonra intent kaldırılıp üst dizin sync edilir. Kesintiden kalan intent otomatik silinmez; açık kurtarma eski snapshot'ı normal aktif kimlik diye açamaz. Salt tanılama bu marker'ı okuyabilir ama store/key veya kilit dosyası yaratmaz.

**Operation tüketicisinin ilk eklendiği uygulama sürümünde DB restore desteği kapalıdır**, kaynak snapshot eski/boş veya hedef DB eksik olsa da. Eski bir snapshot'ta operation olmaması, daha sonra iş gönderilmediğinin kanıtı değildir. P01-4b, backup sonrası gönderilmiş/unknown işlemi içeren kabulde bu ret kapısını doğrular. Operation restore ancak kayıp zaman aralığını güvenilir haricî geçmişle uzlaştıran kalıcı karantina/yeniden yan etki kapısı ayrı kararla kurulunca desteklenebilir. Bu altyapıyı bugünkü identity reset varmış gibi saymayız; operation geçmişi korunuyor garantisi yalnız mevcut canlı DB üzerindeki reset içindir.

## Tehdit ve garanti sınırı

Öneri, tek başına DB/normal log kopyasından credential'ı veya ham hash'ini öğrenmeyi önler; K ele geçirilmediği varsayılır. Aynı UID/root/debugger, process memory veya DB+K birlikte ele geçirilmesine karşı vault/hardware koruması vermez; Python memory zeroization garantisi yoktur. HMAC DB bütününü imzalamaz. DB/key'in eski snapshot'a birlikte dışarıdan döndürülmesini güvenilir haricî monotonic otorite olmadan saptayamayız; uygulama dışı dosya restore'u desteklenen reset/restore akışı değildir.

Bu kapsam kabul edilmiyorsa K için OS secret store gerekir; keychain/secret-service bağımlılığı ve headless erişim politikası onaylanmadan şeffaf fallback yapılmaz. Dosya yaklaşımı OWASP'ın vault/hardware yönlendirmesiyle eşdeğer güvence diye sunulmaz.

## Değerlendirilen alternatifler

- Env adı/manuel nesil tek başına sessiz değişimi kaçırır; her çözümlemede rastgele yeni ID ise süreçler arası kararlı bağ/cache hedefini karşılamaz.
- Raw SHA-256 veya credential'dan türetilen public ID mevcut sır/hash yasağına uymaz. Credential'ı şifreleyip DB'ye koymak gereksiz geri çözme/anahtar yönetimi ve kapsam genişlemesidir.
- Sağlayıcıya ait güvenilir key ID/version gelecekte değerlendirilebilir; mevcut offline env referansında doğrulanmış böyle bir kaynak yoktur.
- OS keychain/secret service K'yi daha güçlü koruyabilir; ilk env-only/headless dilime OS backend/unlock/erişim politikası ekler. Bu, kullanıcının tercih edebileceği daha güçlü alternatiftir.

## Sonuçlar ve kabul kapısı

Kullanıcı onayı, DB'de özel HMAC doğrulayıcısı ve ayrı açık K dosyasını, ADR-0004'ün daraltmasını, ortak binding v1 sözleşmesini ve sınırlı restore desteğini belirtilen tehdit sınırıyla kapsar. Tasarım kararı kabul edildi; ürün kabulü henüz yoktur. Gerçek env/DB ve ayrı süreçlerde kararlı ID, hedef örnekleri/byte vektörleri/uzunluk sınırları, eski Plan uyumu, A→B→A, concurrency/taşma, key kayıp/bozulma, bütün mkdir/üst dizin/file sync hataları, bootstrap/reset/identity-only restore kesintisi ve sızıntı testleri gerekir. Operation restore ret kabulü P01-4b'nin kapısıdır. Araştırma prototipi bu kabulün yerine geçmez; uygulama ve CLI/API sınırları P01-2 kartlarında doğrulanır.
