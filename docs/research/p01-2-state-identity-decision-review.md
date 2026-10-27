# P01-2 — B02/B13 karar araştırması ve öneri raporu

**Tarih:** 2026-10-27. **Durum:** Kullanıcı incelemesine sunulan araştırma; ürün uygulaması veya kabul edilmiş karar değildir. **Taban:** `development@83bcd83`, çalışma dalı `feat/p01-2-identity-context`.

## Sonuç ve onaya sunulan kararlar

P01-2 tek PR'da yapılabilir; paket içi sıra env çözümleme → store/migration temeli → credential kimliği/nesli → yerel init/context/doctor'dır. Ortak P01-4a temeli bu PR'dadır; HTTP/cache yerel doctor'ın önkoşulu değildir. [Teslim planı](../roadmap/p01-2-delivery-plan.md) ve alt kartlar bu sınırla düzenlendi.

| Kayıt | Öneri | Kullanıcının kabul edeceği önemli sonuç |
|---|---|---|
| B02 / [ADR-0011](../decisions/0011-state-foundation-and-migrations.md) | Stdlib SQLite, açık işlemsel migration, DELETE + EXTRA, lazy store | Daha geniş SQLite runtime uyumu; küçük deneyde WAL'dan daha yavaş commit; yerel disk ve açık sürüm/izin kapısı |
| B13 / [ADR-0012](../decisions/0012-credential-identity-and-change-detection.md) | Rastgele ID + artan nesil; DB'de özel HMAC tag; ayrı 0600 yerel karşılaştırma anahtarı | Secret-derived hassas tag ve açık K dosyası oluşur; aynı UID/root veya DB+K birlikte kaybına karşı vault güvencesi vermez |

İki ADR **Proposed** durumundadır. Kullanıcının yeni ADR onayı talebi gereği kalıcı şema/koruma mekanizması kodlanmaz. Daha güçlü OS key store tercih edilirse B13'ün backend/unlock/headless sözleşmesi onaydan önce değiştirilmelidir. SQLite seçimi ADR-0004'te zaten Accepted'dır; bu tur motoru yeniden seçmiyoruz.

## Mevcut kod ve gereksinim incelemesi

Mevcut `api.py` yalnız offline kullanım senaryolarını çağırıyor. Profilde env adı doğrulanıyor; değer çözümleme yok. Domain `Scope` içindeki credential ID/revision, authorization scope ve capability zamanları null; Context uzak doğrulanmış değil. SQLite, registry, init/context yazma veya doctor henüz yok. Bu nedenle rapordaki şema ve mekanizmalar uygulanmış API adları değildir.

Kanonik gereksinimler: [kimlik/context](../modules/identity-context.md), [planın bağları](../architecture/execution-model.md#planın-içerdiği-bağlar), [capability kapsamı](../reference/capability-record.md), [yerel state](../architecture/data-and-state.md), [güvenlik](../standards/security.md). Kritik kayıt yan etkiden önce kalıcı olmalı; profil/env adı yetki kimliği sayılmamalı; ham credential/hash saklanmamalı. Gelecekteki lease/unknown sözleşmesi uzak exactly-once garantisi değildir.

## B02 — Store ve migration değerlendirmesi

| Seçenek | Değerlendirme | Öneri |
|---|---|---|
| SQLite / DELETE + EXTRA | İlk kimlik kaydı iş yüküne uygun; stdlib ile dağıtım; ek checkpoint yaşam döngüsü yok | Varsayılan |
| SQLite / WAL + FULL | Eşzamanlı okuma/yazma ve deneyde daha düşük commit süresi; runtime düzeltmesi/checkpoint yönetimi gerektirir | Geçerli güçlü alternatif; bu pakette varsayılan değil |
| WAL + NORMAL | Son kritik commit'in güç kesintisinde geri alınabilmesi kabul edilmek zorunda | Kritik kimlik/operation kaydı için seçilmiyor |
| JSON/JSONL veya RAM | İşlemsel çok süreçli kimlik güncellemesi, migration ve restart için ek mekanizma gerekir | Seçilmiyor |
| ORM/genel migration framework'ü | Üç gerçek tablo için yeni bağımlılık/katman; kanıtlanmış ihtiyaç yok | Stdlib açık migration önerisi |

SQLite aynı anda tek yazarı kabul eder; `BEGIN IMMEDIATE` yazma hakkını transaction başında alır. Bu, değişim karşılaştırması ve nesil artışının tek atomik adım olmasını kurmak için kullanılabilir. Kaynak: [SQLite transaction](https://www.sqlite.org/lang_transaction.html). WAL da tek yazarlıdır; okuyucu/yazar davranışı ve checkpoint yükü farklıdır: [WAL belgesi](https://www.sqlite.org/wal.html).

Dayanıklılık tercihi hızdan bağımsız bir kabul kararıdır. DELETE/EXTRA ve WAL/FULL karşılaştırması, `NORMAL` ile commit kaybını kabul etme seçeneğiyle karıştırılmamalıdır. Önerilen ayarlar ve macOS fullfsync sınırı [SQLite PRAGMA sözleşmesinden](https://www.sqlite.org/pragma.html) incelendi. Dosya sistemi/donanımın doğru flush/kilit sağlaması ayrıca gerekir; [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) bu varsayımları açıklar.

### Runtime sürümü ve güncel WAL bulgusu

Python 3.11 sürümü bağlı SQLite sürümünü sabitlemez. Bu yerel yorumlayıcı SQLite **3.54.1** kullanıyor; `uv.lock` bunu taşınabilir bir SQLite pin'ine dönüştürmez. SQLite'ın resmî WAL belgesindeki WAL-reset bulgusu 3.51.3'te düzeltilmiş; bazı eski dallar için 3.44.6 ve 3.50.7 backport'ları var. İki bağlantının eşzamanlı yazma/checkpoint koşulu önemlidir. Genel `>=3.44.6` kontrolü doğru değildir: ara sürümler etkilenebilir. Kaynak: [WAL-reset açıklaması](https://www.sqlite.org/wal.html), [3.51.3 sürüm kaydı](https://www.sqlite.org/releaselog/3_51_3.html).

Bu güncel bulgu WAL'ı genel olarak kullanılamaz yapmaz; sürüm/dağıtıcı düzeltmesi doğrulanmış runtime gerekir. Önerilen DELETE varsayılanı WAL'a özgü yolu açmaz. `STRICT` için ayrı minimum **3.37.0** öneriyoruz; uygulama strict doğrulaması yine zorunlu, çünkü kayıpsız SQL dönüşümleri mümkündür. Kaynak: [SQLite STRICT](https://www.sqlite.org/stricttables.html).

### Transaction ve hata sınırı

Python 3.11 için `isolation_level=None` + açık SQL transaction, yeni sürümlerin `autocommit` API'sine bağımlılık oluşturmaz. Migration'da `executescript()` kullanmak açık transaction'ı önceden commit edebilir; yerel deney bunu yeniden üretti. **Her adımın** DDL/veri/sürüm/manifesti aynı transaction'da, tek tek `execute` ile ilerlemelidir. Zincirin ikinci adımı başarısızsa son başarılı sürüm kalır; başlangıç sürümüne otomatik dönüş önerilmiyor. Kaynak: [Python 3.11 sqlite3 transaction davranışı](https://docs.python.org/3.11/library/sqlite3.html#transaction-control).

Yabancı/bozuk/gelecek sürümlü kayıt silinerek toparlanılmaz. Yeni DB'nin sahipliği, mevcut sürüm ve migration manifesti doğrulanır. Her mevcut sürüm adımı öncesindeki backup yeni no-clobber hedefte alınır, ilişkisel/mantıksal kontrol ve file/dizin kalıcılığı sonrasında tamamlanma kaydı yayımlanır; otomatik silinmez. Canlı SQLite dosyasını gelişigüzel kopyalamak yerine [SQLite backup API](https://www.sqlite.org/backup.html) kullanılabilir; API'nin mevcut hedefi koruduğu varsayılmaz. Ayrıntılı yaşam döngüsü ADR-0011'de tek yerde tutulur. Yerel proposal'daki 1.000 ms busy bütçesi bütün I/O'nun katı üst sınırı değildir; [busy handler](https://www.sqlite.org/c3ref/busy_timeout.html) kilit beklemesini yönetir. İlk probe 100 ms ayarında 123,665 ms gözledi.

Default state yolu olarak `~/.local/state/yorunge` önerisi mevcut env-yalnız-sır kuralını genişletmez. XDG standardı `XDG_STATE_HOME` ve onun varsayılanını tanımlar; bu pakette yalnız varsayılan dizin düzeninden yararlanıp env override davranışı eklememek bilinçli ürün tercihidir, tam XDG uyumu iddiası değildir. Kaynak: [XDG Base Directory](https://specifications.freedesktop.org/basedir/latest/). Public API/CLI'da açık dizin seçimi ve dosya izinleri ürün sözleşmesine ayrıca bağlanır.

## B13 — Credential kimliği ve değişim kanıtı değerlendirmesi

Offline env-only modelinde şu üç hedef, ek kanıt olmadan birlikte sağlanamaz: süreçler arası kararlı ID, sessiz değer değişimini yakalama ve secret ile ilişkili hiçbir kalıcı kanıt tutmama. Önceki değere ilişkin bilgi veya güvenilir dış sürüm kimliği yoksa yeni değerle karşılaştırma yapılamaz. Bu, kaynakların ilan ettiği bir ürün yeteneği değil, mevcut bilgi akışından çıkan mühendislik sonucudur.

| Seçenek | Sonuç | Karar önerisi |
|---|---|---|
| Profil/env adını credential ID saymak | Aynı ad altında değişimi kaçırır | Reddedilsin |
| Kullanıcıdan her rotation'da elle nesil artırmasını istemek | Habersiz/sessiz değişimi yakalamaz | Tek başına yeterli değil |
| Her çözümlemede yeni rastgele ID | Eski bağlar reddedilebilir; fakat değişmeyen değer için süreçler arası kararlılık/cache kaybolur | Ana yöntem olmasın |
| Ham SHA-256 veya secret-derived public ID | Mevcut ham hash/public sır yasağına aykırı | Reddedilsin |
| Sağlayıcı key ID/version | Güvenilir ve güncelse uygun olabilir; şu an doğrulanmış offline kaynak yok | Gelecek adaptörde değerlendirilsin |
| Şifreli credential'ı DB'de saklamak | Geri çözme ve ek key yönetimi; burada asıl ihtiyaç değeri geri almak değil | Kapsama eklenmesin |
| Ayrı K ile HMAC-SHA-256 + rastgele ID/nesil | K bilinmeden DB tag'i raw hash gibi doğrudan tahmin oracle'ı olmaz; gözlenen değişim karşılaştırılabilir | Önerilen mekanizma |

HMAC standart bir keyed MAC'tir; public kimlik olarak kullanılması önerilmiyor. 32 bayt K üretimi `secrets`, karşılaştırma `hmac.compare_digest` ile yapılabilir. Kaynaklar: [RFC 2104](https://www.rfc-editor.org/rfc/rfc2104), [Python hmac](https://docs.python.org/3.11/library/hmac.html), [Python secrets](https://docs.python.org/3.11/library/secrets.html). Algoritmanın doğruluğu uygulamanın tüm dosya/çıktı/yarış sınırlarını otomatik doğrulamaz.

### K'nın korunması asıl ürün kararıdır

Yerel dosya önerisi keychain'siz/headless çalışma ve ek runtime bağımlılığı istemeyen temel istemciyle uyumludur. Bunun karşılığında K düz key baytları olarak disktedir; 0600/0700 erişim izinleridir, şifreleme değildir. DB ve K birlikte ele geçirilirse veya saldırgan aynı UID/root/process memory erişimine sahipse öneri vault koruması sağlamaz. Key-check yanlış/bozuk K'yı credential rotation sanmayı engellemek içindir; bütün DB'nin kötü niyetli rollback'ini engellemez.

Bu nedenle dosya çözümü [OWASP key storage/lifecycle](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html) yönlendirmelerinin yüksek güvence seviyesiyle eşdeğer diye sunulmamalıdır. Anahtar saklama, backup ve kayıp kurtarma ayrı ele alınmalıdır. Daha güçlü seçenek, K'yı OS secret store'da tutmaktır; [Apple Keychain](https://developer.apple.com/documentation/security/keychain-services) küçük sırları şifreli store'da saklar ve erişim kontrolü sağlar. Bu seçenek için macOS/Linux backend, kilitli oturum ve headless erişim sözleşmesi gerekir. Bu tur gerçek kullanıcı keychain'i okunmadı ve böyle bir adaptör kurulmadı.

Önerilen uygulama; key dosyasını ve yeni dizinlerin üst dizin girdilerini DB aktif pointer'ından önce kalıcılaştırır, key-check/ID'yi doğrular ve SQL gözlemini tek transaction'da yapar. Kayıp key otomatik üretilmez. **Canlı DB üzerindeki reset** yeni epoch/ID'lerle eski plan/cache bağlarını geçersiz kılar ve mevcut operation geçmişine dokunmaz. **Eski DB restore'u** snapshot sonrasındaki geçmişi kaybedebilir; reset bu kaydı geri üretemez. P01-2'de yalnız identity şemasına sınırlı açık restore, operation tüketicisinin ilk uygulama sürümünden itibaren ise restore ret kapısı öneriliyor. Daha sonra destek için haricî güvenilir geçmişle uzlaştırma ve kalıcı yan etki karantinası gerekir. Dışarıdan eski DB+key dosyalarının birlikte geri kopyalanmasını haricî güvenilir monotonic kayıt olmadan algılama garantisi verilemez. Kesinti/intent ve recovery önerisi ADR-0012'dedir.

### Gözlemin gerçek sınırı

A→B→A, her ara değer gerçekten çözümlendiyse 1→2→3 olarak ilerler. Görülmeyen B geçişi veya değeri aynı kalan sunucu yetki değişimi HMAC ile keşfedilemez. İki süreç farklı env snapshot'ı taşıyabilir; registry gözlem sırasını serialize eder, küresel tek env değeri yaratmaz. P01-3 plan geçerliliği, kayıtlı scope/nesli güncel bağla karşılaştırmalı; P02 uzak yetkiyi ayrı doğrulamalıdır. Bu paket credential bulunmasını `supported` veya execution onayı yapmaz.

## Yerel deneyler ve gerçek sonuçlar

[Tekrar çalıştırılabilir probe](p01-2-state-identity-probe.py), [ham sonuç](p01-2-state-identity-probe.json). Yalnız stdlib, geçici dizin, sentetik değerler ve alt süreçler kullanıldı; kullanıcı credential'ı veya yerel state'i okunmadı.

```sh
.venv/bin/python docs/research/p01-2-state-identity-probe.py --output dist/p01-2-decision-probe.json
```

Ortam: CPython 3.11.18, macOS 27.0.1 arm64, SQLite 3.54.1; SQLite source ID ve probe SHA-256 ham sonuçtadır. Bu mikroprototip ürün store'u, tam namespace/ID modeli, file-safety/reset/backup akışı veya CLI/API implementasyonu değildir.

| Deney | Gözlenen sonuç | Kanıtlamadığı sınır |
|---|---|---|
| DDL/veri/user_version + constraint hatası | Yeni tablo ve v2 geri alındı; sürüm 1 kaldı | Tüm gerçek migration zinciri |
| Transaction içinde executescript | Önceki DDL ve insert kalıcı oldu; transaction bölündü | Bir ürün kusuru değil, kullanılmaması gereken pattern |
| İki bağlantı yazma kilidi | SQLITE_BUSY; 100 ms bekleme ayarında 123,665 ms | Katı total deadline veya üretim lock adaptörü |
| Alt süreç os._exit, commit öncesi/sonrası | Kayıt sayısı 0 / 500; quick_check ok | Güç kesintisi, SSD arızası, farklı OS/FS |
| RFC 4231 HMAC-SHA-256 vektörü | Eşleşti | Özel kripto veya tüm ürün güvenliği |
| Sekiz süreç aynı B değerini gözledi | Tek nesil artışı; A→B→A sonucu 1→2→3 | Dağıtık makine veya ürün namespace entegrasyonu |
| Ayrı purpose/hizmet mesajı | Tag ayrıldı | Bütün gerçek target normalization uygulaması |
| DB içerik denetimi | İki sentetik raw değer ve düz SHA-256 kaydı yok | Bütün ürün log/JSON/memory sınırları |
| K dosyası oluşturma | 0600 görüldü | Vault şifrelemesi, başlatma yarışı veya kurtarma |
| SQLite STRICT'e sayısal string | INTEGER'a dönüştü | Uygulama strict doğrulamasına alternatif |

Her journal politikasında **100 ardışık küçük write transaction** için gözlem:

| Politika | Medyan | p95 |
|---|---:|---:|
| DELETE + EXTRA | 11,947 ms | 12,725 ms |
| WAL + FULL | 3,883 ms | 4,269 ms |

Her iki bağlantıda macOS fullfsync açıldı. Journal politikalarının sync sayısı/işi farklıdır; bu bir eşit fsync maliyeti kıyası değildir. Başlangıç/şema işi hariçtir; CLI'nın 30 ayrı süreç kabulünün yerine geçmez. Ölçüm, WAL'ın bu küçük deneyde hızlı olduğunu gösterir; gerçek operation yükünü veya her makinede aynı oranı kanıtlamaz. DELETE önerisi hız birinciliğine değil, ilk kimlik iş yükü ile kurulum/uyumluluk/dayanıklılık dengesine dayanır.

## Uygulamadan önce kapanacak ve kabulde sınanacak işler

1. Kullanıcı ADR-0011'de journal/runtime/adım başına migration/kalıcı backup önerisini ve ADR-0012'de özel HMAC + ayrı açık K dosyası/tehdit, ortak binding v1 ve reset/restore sınırını kabul eder veya değiştirir.
2. Onaylanan kararlar P01-4a/P01-2b kartlarına bağlanır; alt işler ancak kendi doğrudan bağımlılığı gerçek commit/test/review ile doğrulanınca başlar. Bu rapor hepsini ready yapmaz.
3. Ürün testleri doğru namespace/ID, gerçek resolver, key/DB dosya yarışları, eksik/bozuk durum, migration/backup/reset kesintisi, izinler, CLI/Python hata/çıktı ve lazy guard'ı kapsar. Araştırma probe'ları tek başına bu kabulü sağlamaz.
4. P01-4b operation/lease/fencing somut DDL ve saat/restart kabulü kendi epik paketinde gerçek tüketiciyle tamamlanır; önceki temel yeniden yazılmaz, future tablo iskeleti kurulmaz.

Resmî kaynakların erişim tarihi 2026-10-27'dir. Kaynak incelemesi, sentetik yerel mekanizma deneyi ve bu projeye ait önerilen karar birbirinden ayrıdır. Canlı EVREN/auth, OS key store, Windows/NFS veya donanımsal güç kaybı doğrulaması yapılmadı. B02/B13 kararları kullanıcı onayı gelene kadar açık kalır.

## Onay öncesi review bulgularının doğrulanması

2026-10-27'de iletilen iki inceleme mevcut kod/ADR'lerle karşılaştırıldı. A1–A6 ilk incelemedir; B11–B16 ikinci incelemenin ADR-0011, B21–B25 ADR-0012 maddeleridir. Bunlar mevcut ürün kusuru değil, henüz Proposed tasarımdaki açıklık/garanti sorunlarıdır.

| Bulgu | Doğrulama ve alınan aksiyon |
|---|---|
| A1 — restore/operation geçmişi | Geçerli. Snapshot sonrası unknown işlem kaydı yoktur; identity reset ile DB restore ayrıldı. Operation tüketicisi sürümünde restore kapalı; ret kabulü P01-4b'ye bağlandı. |
| A2 — yeni dizinlerin kalıcılığı | Geçerli. Yeni state/keys/backups zincirinin üst dizin kayıtları, Linux/macOS sync sırası ve hata halinde commit/DDL ret kapısı ADR-0011'de tek yerde tanımlandı. |
| A3, B15 — backup hedefi/ömrü | Geçerli. No-clobber özel hedef, tamamlanma kaydı, sync, kısmi çıktı, saklama ve açık restore/temizleme kuralı eklendi. Uzun backup/hash, exclusive bakım kilidiyle SQL write transaction'ı dışına alındı; disk dolması ve kesinti ürün kabulüne bağlandı. |
| A4 — çok adımlı migration | Geçerli belirsizlik. Adım başına atomiklik seçildi; 1→2 başarılı/2→3 başarısızsa 2 kalır, yeniden açılışta 3 denenir. Her adım öncesi snapshot tutulur. |
| A5, B21 — hedef/JSON/alan kümesi | Geçerli. [Ortak Proposed binding v1](../reference/credential-binding-v1.md): 443 metinden çıkarılır, host/IPv6/path/escape eşlemesi, eski Plan uyumu, UNIQUE ile aynı altı alan, tam JSON/framing/key-check ve byte vektörleri tanımlandı. |
| A6 — ilişkisel bütünlük | Geçerli. `integrity_check` yanında `foreign_key_check` ve mantıksal değişmezler kaynak/snapshot/migration kabulüne eklendi. |
| B11 — genel sır saklama kuralı | ADR-0004'te genel ifade var; data-and-state'te aynı cümle birebir yok, yorum belirsizliği var. HMAC için onaya bağlı daraltma ADR-0012'de açık; Accepted karar ve mimari yalnız Proposed ilişki notuyla bağlandı, istisna etkinleştirilmedi. |
| B12 — sürüm otoritesi | Geçerli açıklık ihtiyacı. `user_version == max(schema_migrations.version)`, kesintisiz geçmiş ve checksum eşitliği açık değişmez; ayrışma kontrollü hata. |
| B13 — sürüm terimleri | Geçerli ifade belirsizliği. “Uygulamanın desteklediğinden yeni” DB ile “eski desteklenen sürümden daha yenisine yükseltme” ayrıldı. |
| B14 — hot journal | Yeni ürün kusuru değil, yararlı netleştirme. Manuel silme yasak; SQLite'ın kendi açılış rollback'i normaldir. Salt tanılama yazmalı recovery'yi gizlice başlatmaz. |
| B16 — manifest checksum kaynağı | Geçerli açıklık ihtiyacı. Kodla gelen değişmez sıralı SQL listesi; checksum'ın tam üç alanlı JSON byte kapsamı tanımlandı, mevcut adım değiştirilmez. |
| B22 — aynı UID tehdidi | Zaten tehdit bölümünde kapsanmış; yeni güvenlik açığı olarak sayılmadı. Aynı UID'nin K'yı okuyabildiği ve DB+K'nın düşük entropili sır için tahmin oracle'ı olduğu yaşam döngüsünde öne alındı. |
| B23 — revision taşması | Geçerli netlik ihtiyacı. Kontrollü hata/rollback; otomatik reset/sarma yok. |
| B24 — cache thrash | Risk geçerli. Revision'ı cache bağından çıkarmak güvenliği zayıflatır; bu örnek çözüm seçilmedi. P01-3 için güncel nesil/sınırlı saklama ve kontrollü çatışma, otomatik döngüsüz kabul tanımlandı. |
| B25 — env/secret sınırı | Env 1–128 ASCII sınırı mevcut `EnvName` koduyla doğrulandı ve config referansına yazıldı. Secret için 1–16.384 UTF-8 bayt yeni Proposed kaynak sınırı eklendi; sağlayıcı limiti veya uygulanmış davranış sayılmaz. |

`application_id` yanına `YORU` açıklaması da eklendi. Genel olumlu değerlendirmeler doğrulama yerine geçirilmedi; ilk probe backup/dizin sync/reset/restore'u kanıtlamıyordu. İlk kaynak/ham sonuç ve zaman ölçümleri değiştirilmedi.

### Ek yerel kanıt

[Review probe'u](p01-2-review-probe.py) ve [ham sonucu](p01-2-review-probe.json), yalnız geçici gerçek SQLite/dosyalar ve sentetik verilerle çalıştırıldı:

```sh
.venv/bin/python docs/research/p01-2-review-probe.py --output dist/p01-2-review-probe.json
```

- İkinci migration adımı hata verdi; yeniden açılan sürüm 2/geçmiş `[1, 2]`, düzeltilen sonraki adım sonrası sürüm 3 oldu. Bu, ürün manifest/migration uygulamasının testi değildir.
- `integrity_check=ok` ve `foreign_keys=ON` iken `foreign_key_check` bir eski ihlal buldu. Resmî dayanak: [SQLite PRAGMA](https://www.sqlite.org/pragma.html).
- Ayrı read bağlantısından, yazma bağlantısı `BEGIN IMMEDIATE` tutarken backup tamamlandı. Bu API davranış deneyidir; önerilen ürün sırası uzun backup/hash'i SQL write transaction'ı dışında bakım kilidi altında yapar. Backup API yalnız deneyin mevcut hedef içeriğini değiştirdi; `O_EXCL` aynı hedefi değiştirmeden reddetti.
- Canlı fixture işlem kimlikleri `[1, 2]`, snapshot `[1]` kaldı; backup sonrası unknown işlemin geçmişi snapshot'ta yoktu. Bu risk kanıtıdır, restore ret kapısının uygulanmış testi değildir.
- Yerel macOS'ta yeni state/keys + üst dizin descriptor sync'leri, normal file fsync ve son `F_FULLFSYNC` çağrıları tamamlandı. Linux davranışı [fsync(2)](https://man7.org/linux/man-pages/man2/fsync.2.html), macOS flush sınırı [Apple belgesi](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html) üzerinden incelendi; burada Linux veya güç kesintisi deneyi yapılmadı.
- Altı alanlı binding JSON'u 222 bayt; sentetik secret'lar 11/14 UTF-8 bayt. İki observation ve bir ayrı-purpose key-check HMAC vektörü bağımsız OpenSSL komutuyla da eşleşti. Raw JSON'da tam mesaj/tag hex'i ve üretici SHA-256 vardır; gerçek sır yoktur.

Disk dolması/sync hatası enjeksiyonu, yarışan migration yazarları, normalizer uygulaması, ürün backup/reset/restore kilidi/intent akışı ve güç kesintisi bu deneyle doğrulanmadı; ilgili ürün kartlarının kabul kapısıdır. İki ADR ve bağlı yeni sözleşme hâlâ **Proposed**; bu düzeltmeler kullanıcı onayı veya ürün teslimi yerine geçmez.
