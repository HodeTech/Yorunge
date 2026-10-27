# ADR-0012: Opak credential kimliği ve gözlenen anahtar değişimi

**Durum:** Proposed — kullanıcı onayı bekleniyor. **Tarih:** 2026-10-27. **Kayıt:** B13. ADR-0005 ve execution/capability bağlarını ayrıntılandırır. Yerel HMAC kaydı ve koruma anahtarı dosyası için açık onay gerekir; henüz uygulanmadı.

## Bağlam

Env referansı aynı kalırken değer değişebilir. Offline çözümlemede kullanılabilecek güvenilir sağlayıcı key ID/rotation metadata'sı henüz yoktur. Aynı değerde süreçler arası kararlı kimlik ve sessiz değişimi yakalama hedefi, önceki değerle ilişki kuran kalıcı veya güvenilir dış kanıt gerektirir. Ham credential/hash saklanamaz. [Seçenekler, tehdit sınırı ve deney raporu](../research/p01-2-state-identity-decision-review.md) bu kararın dayanağıdır.

## Önerilen karar

Public `credential_id` sırdan bağımsız UUIDv4; `credential_revision` pozitif, SQLite signed-64 sınırında tamsayıdır. İlk gözlem 1, farklı değer gözlemi +1; taşmada otomatik sarma/reset yoktur. Sır bir kez çözülür; hizmet/hedef/kimlik ve guarded secret taşıyıcısı aynı snapshot'a bağlanır. Env adına geri dönüp ikinci kez sır okunmaz.

DB'de yalnız yerel, dışarı aktarılmayan **HMAC-SHA-256 doğrulayıcısı** tutulur; bu ham SHA-256 değildir ama sırdan türetilmiş hassas bir kayıttır. Public kimlik, plan digest'i, capability, log, repr/str, hata veya genel JSON içine girmez. HMAC şifreleme veya uzak kimlik doğrulaması değildir.

### Kapsam, kayıt ve kodlama

`credential_bindings` alanları: identity epoch, `service_id`, kanonik HTTPS origin/etkin port, API kökü, referans türü/adı, UUID credential ID, pozitif revision, tag biçimi, 32 bayt tag ve UTC gözlem zamanı. Etkin epoch + hizmet/origin/API kökü/referans türü/adı benzersiz ve NOT NULL'dır; env adı uzunluğu mevcut v1 sınırını korur. Hesap/proje/izinler credential ID yerine geçirilmez; kullanım senaryosunun ayrı context bağlarıdır ve sonraki cache/plan anahtarında ayrıca karşılaştırılır.

Farklı hizmet/hedef/referanslar aynı değeri taşısa da varsayılan olarak kayıt/ID paylaşmaz. Profil adı namespace değildir. Hedef değişimi yeni binding/ID üretir; eski bağ sessizce başka hedefe yönelmez. Origin/API kökü bir kez kanonikleştirilir; bu host'a güven veya API uyumu kanıtı değildir.

Önerilen v1 tag mesajı: sabit `yorunge:credential-observation:v1` purpose + NUL + 8 bayt big-endian binding uzunluğu + kanonik UTF-8 binding JSON + 8 bayt secret uzunluğu + tam UTF-8 secret baytları. Binding JSON etkin epoch, hizmet/hedef ve referans alanlarını içerir; anahtarları sıralı/kompakt ve sürümlüdür. Sırda trim/lowercase/dönüşüm yapılmaz; encoding/şema hatası kontrollü reddedilir. Key kontrolü farklı purpose kullanır. Karşılaştırma `hmac.compare_digest` ile aynı uzunlukta byte tag'ler arasında yapılır; özel kripto geliştirilmez.

### Yerel karşılaştırma anahtarı ve dosya yaşam döngüsü

K, `secrets.token_bytes(32)` ile oluşturulan 256 bit yerel karşılaştırma anahtarıdır; EVREN credential'ı değildir. [ADR-0011](0011-state-foundation-and-migrations.md) state dizini altında ayrı 0700 `keys` dizininde `<random-key-id>.key` dosyasında 0600/yalnız sahip erişimiyle, tam 32 bayt tutulması önerilir. K DB, config, paket, gözlem logu veya normal çıktı içine yazılmaz. **Bu dosya açık key baytlarını taşır; 0600 şifreleme değildir.** Otomatik keychain erişimi veya yeni runtime bağımlılığı eklenmez.

Dosyalar immutable ve no-clobber oluşturulur; no-follow, sahiplik/izin ve boyut denetimi, dosya + dizin fsync gerekir. DB `active_key_id` ve store'a bağlı ayrı purpose HMAC key-check taşır; yanlış 32 bayt dosya credential rotation sanılmaz. K eksik/bozuk/yanlışsa mevcut epoch'ta otomatik yeniden üretilmez.

İlk anahtar veya açık reset'teki yeni anahtar, DB'nin aktif key/epoch pointer'ı commit edilmeden önce kalıcılaştırılır. Aynı store yazma transaction'ı aktif key'i tekrar denetler. Kesinti öncesi oluşmuş fakat referanslanmayan dosya, key/DB durumu doğrulanmadan benimsenmez veya silinmez; aktif pointer eksik dosyayı gösteriyorsa hata olur. Bu iki dosyanın tek transaction'la atomik güncellendiği iddiası kurulmaz. Ürün kabulü, her sınırda hata enjeksiyonu ve iki süreç başlatmasını gerektirir.

### Gözlem, concurrency ve kurtarma

Seçili değer çözülüp hedef snapshot'ı sabitlenir. `BEGIN IMMEDIATE` içinde etkin epoch/key-check ve binding tekrar okunur. Kayıt yoksa yeni ID/1; tag aynıysa aynı ID/revision; farklıysa aynı ID/revision+1 ve yeni tag birlikte commit edilir. UTC zaman yalnız ilk/değişmiş gözlemde yazılır; aynı tag için gereksiz kayıt güncellemesi yapılmaz. Aynı B değerini gören eşzamanlı süreçler tek değişim kaydeder. Bağımsız süreçlerde A/B env snapshot'ları dönüşümlü görülürse nesil her yeni gözlemde ilerleyebilir; evrensel bir env değeri varmış gibi anlatılmaz.

Gözlenen A→B→A sırası 1→2→3 olur; gözlenmeyen ara değişimi veya değeri aynı kalan sunucu izin/revocation değişimini yerel HMAC bulamaz. Credential kaydı uzak `supported`, `remote_verified` veya execution izni sağlamaz. Sonraki yürütme, snapshot'ın hâlâ etkin bağa/nesle ait olduğunu ayrıca denetler.

K kaybı veya desteklenen backup restore'unda açık, etkisi gösterilen **identity reset** yeni epoch/key ve yeni credential ID'leri üretir. Önceki epoch kayıtları aktif kabul edilmez; eski plan/cache bağları yeniden geçerli olmaz. Gelecekte operation geçmişi bu işlemle silinmez ve unknown iş yeniden gönderilmez. K olmadan DB'deki tag'den eski credential doğrulanamaz; otomatik recovery başarısı ilan edilmez. Desteklenen backup/restore DB ve key kimliği eşleşmesini doğrulamalıdır; sır içeren key normal JSON export'una katılmaz.

## Tehdit ve garanti sınırı

Öneri, tek başına DB/normal log kopyasından credential'ı veya ham hash'ini öğrenmeyi önler; K ele geçirilmediği varsayılır. Aynı UID/root/debugger, process memory veya DB+K birlikte ele geçirilmesine karşı vault/hardware koruması vermez; Python memory zeroization garantisi yoktur. HMAC DB bütününü imzalamaz. DB/key'in eski snapshot'a birlikte dışarıdan döndürülmesini güvenilir haricî monotonic otorite olmadan saptayamayız; uygulama dışı dosya restore'u desteklenen reset/restore akışı değildir.

Bu kapsam kabul edilmiyorsa K için OS secret store gerekir; keychain/secret-service bağımlılığı ve headless erişim politikası onaylanmadan şeffaf fallback yapılmaz. Dosya yaklaşımı OWASP'ın vault/hardware yönlendirmesiyle eşdeğer güvence diye sunulmaz.

## Değerlendirilen alternatifler

- Env adı/manuel nesil tek başına sessiz değişimi kaçırır; her çözümlemede rastgele yeni ID ise süreçler arası kararlı bağ/cache hedefini karşılamaz.
- Raw SHA-256 veya credential'dan türetilen public ID mevcut sır/hash yasağına uymaz. Credential'ı şifreleyip DB'ye koymak gereksiz geri çözme/anahtar yönetimi ve kapsam genişlemesidir.
- Sağlayıcıya ait güvenilir key ID/version gelecekte değerlendirilebilir; mevcut offline env referansında doğrulanmış böyle bir kaynak yoktur.
- OS keychain/secret service K'yi daha güçlü koruyabilir; ilk env-only/headless dilime OS backend/unlock/erişim politikası ekler. Bu, kullanıcının tercih edebileceği daha güçlü alternatiftir.

## Sonuçlar ve kabul kapısı

Onay, DB'de özel HMAC doğrulayıcısı ve ayrı açık K dosyasını belirtilen tehdit sınırıyla kabul eder. Bu kabul olmadan mekanizma kodlanmaz. Gerçek env/DB ve ayrı süreçlerde kararlı ID, hizmet/hedef ayrımı, A→B→A, concurrency, key kayıp/bozulma, bootstrap/reset kesintisi, desteklenen restore ve sızıntı testleri gerekir. Araştırma prototipi bu kabulün yerine geçmez; uygulama ve CLI/API sınırları P01-2 kartlarında doğrulanır.
