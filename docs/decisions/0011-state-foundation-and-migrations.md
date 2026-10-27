# ADR-0011: P01 yerel store ve işlemsel migration temeli

**Durum:** Proposed — kullanıcı onayı bekleniyor. **Tarih:** 2026-10-27. **Kayıt:** B02. ADR-0004'teki SQLite kararını ayrıntılandırır; motor seçimini değiştirmez. Bu belge ürün uygulaması değildir.

## Bağlam

P01-2b'nin kimlik/nesil kaydı süreçler arasında kalmalıdır; P01-4a bu nedenle P01-2 PR'ında teslim edilir. Sonraki capability/operation tüketicileri aynı transaction otoritesine dayanacaktır. [Karşılaştırma, resmî kaynak ve yerel deney raporu](../research/p01-2-state-identity-decision-review.md) önerinin dayanağıdır.

## Önerilen karar

| Konu | Onaya sunulan seçim |
|---|---|
| Motor/bağımlılık | Python 3.11+ standart `sqlite3`; ilk store için bağlı SQLite ≥ 3.37.0; ORM/Alembic veya ayrı SQLite wheel'i eklenmez |
| Yerleşim | macOS/Linux yerel diskte `~/.local/state/yorunge/state.sqlite3`; açık state dizini seçimi ayrıca CLI/Python sözleşmesine bağlanır; `XDG_STATE_HOME` davranış override'ı bu pakette eklenmez |
| Dosya sınırı | Uygulamaya özel dizinler 0700; DB/key dosyaları 0600 ve kullanıcı sahipliği. Bilinen symlink, gevşek izin veya yabancı sahiplikte kontrollü ret; mevcut kullanıcı dosyası otomatik chmod/overwrite edilmez |
| Journal/dayanıklılık | Varsayılan `journal_mode=DELETE`, `synchronous=EXTRA`; macOS'ta `fullfsync=ON`. NFS/bulut senkronizasyon dizini desteklenmiş sayılmaz; ortamın kilit/fsync sözleşmesi gereklidir |
| Bağlantı | Her kullanım senaryosunun açık sahibi ve kapanışı; `foreign_keys=ON`, `trusted_schema=OFF`; ayarlar geri okunur. Global importta bağlantı yok |
| Transaction | Python 3.11 uyumlu `isolation_level=None`; yazma/kimlik gözlemi/migration için açık `BEGIN IMMEDIATE` ve `COMMIT`/`ROLLBACK`; transaction içine HTTP veya uzun hesap taşınmaz |
| Bekleme | Varsayılan SQLite busy beklemesi 1.000 ms; dış kullanım senaryosu ayrıca toplam bütçe taşır. Bu değer bütün disk I/O için katı duvar saati garantisi değildir; uygulama çağrısı otomatik baştan tekrarlanmaz |
| Sahiplik/sürüm | `application_id=0x594F5255` (`YORU`), `user_version` kanonik şema sürümü; sürüm manifesti kodla birlikte gelir. Yabancı, uygulamanın desteklediğinden yeni sürüm veya bozuk DB otomatik yeniden oluşturulmaz |

State dizini aynı güvenilen yerel kullanıcıya ait olmalıdır. Yol kontrolünün ardından SQLite'ın dosyayı kendisinin açması, saldırgan aynı UID altında sürekli yol değiştiriyorsa yarışsız bir güven sınırı sağlamaz; böyle bir koruma iddia edilmez. Metadata komutları ve sır gerektirmeyen mevcut offline işlemler state dizini/DB/key yaratmaz. Doctor'ın temel yerel incelemesi de kayıt yaratmaz; yazma/migration açık store kullanımıdır.

Açık normal store erişimi, sabit sahipli 0600 `store.lock` dosyasında shared bakım kilidini bağlantı ömrü boyunca taşır; migration/restore exclusive kilit alır. Bu advisory dosya kilidi desteklenen bütün store kullanıcılarının ortak sözleşmesidir, SQLite transaction/kilitlerinin yerine geçmez. Mevcut kilit inode'u silinip yeniden yaratılmaz. Normal açılış intent denetimini kilit altında, SQLite'ı açmadan yapar. Yeni store kurulumu kilidi açıkça oluşturur; mevcut store'da eksik/uyumsuz kilit kontrollü onarım gerektirir. Salt tanılama/metadata komutları kilit dosyası yaratmaz. Kilit beklemesi kullanım senaryosunun toplam bütçesine dahildir.

### Dosya ve dizin kalıcılığı

Yeni dizin için yalnız içindeki dosyayı sync etmek yeterli kabul edilmez. Güvenilen mevcut üst dizinden başlayarak oluşturulan her state/keys/backups alt dizini için yeni dizin descriptor'ı ve adını taşıyan üst dizin descriptor'ı senkronlanır. Yeni alt dizin zincirindeki bütün oluşturulan adlar kapsanır; örneğin yeni `keys` için `keys` ile onu içeren state dizini, state de yeniyse onun üst dizini de kapsanır. Mevcut ilgisiz dizinlerin izinleri değiştirilmez.

Linux'ta normal dosya için flush + `fsync`, dizin kayıtları için descriptor üzerinden `fsync` gerekir. macOS'ta normal key/backup dosyalarında flush + `fsync`, dizin kayıtlarında `fsync` ve ilgili dizin sync'lerinden sonra aynı dosya sistemi üzerindeki normal dosyada son `F_FULLFSYNC` bariyeri kullanılır; SQLite'ın kendi dosyaları için `fullfsync=ON` ayrıca geçerlidir. Bu dosya/dizin ağacı aynı desteklenen yerel dosya sisteminde kalır. Gerekli sync'in desteklenmemesi veya hata vermesi başarı sayılmaz: yeni key pointer'ı commit edilmez, migration DDL'si başlamaz. Dosya sistemi/donanım bu çağrıların sözleşmesini sağlamalıdır; API'nin başarılı dönmesi güç kesintisi testi değildir. [Linux fsync](https://man7.org/linux/man-pages/man2/fsync.2.html), [Apple fsync/F_FULLFSYNC](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html) (erişim: 2026-10-27).

### Şema ve migration

İlk sürüm yalnız gerçek tüketicileri olan `state_meta`, `schema_migrations` ve `credential_bindings` tablolarını içerir. `state_meta` tek store UUID'si, aktif identity epoch, yerel key kimliği/doğrulaması ve biçim sürümünü taşır; ikinci bir şema sürümü otoritesi değildir. `schema_migrations`, sıralı sürüm, kod manifestindeki SHA-256 checksum ve UTC uygulanma zamanını taşır. Credential kayıt alanları [ADR-0012'de](0012-credential-identity-and-change-detection.md) tanımlanır. Operation/attempt/lease için boş tablo kurulmaz.

Tablolar `STRICT` ve açık `NOT NULL`/`CHECK`/`UNIQUE` sınırları kullanır; bu Pydantic strict doğrulamasının yerine geçmez. SQLite `STRICT` kayıpsız tür dönüşümünü hâlâ yapabilir. Bağlam/enum/UUID/uzunluk ve zaman değerleri okuma/yazma sınırında uygulama modeliyle doğrulanır.

Yalnız yeni ve uygulama tarafından özel olarak oluşturulan DB başlatılır. Mevcut sıfır bayt/yabancı dosya adı nedeniyle benimsenmez; kesik ilk kurulum kontrollü hata ve açık onarım yoludur. Başlatılmış DB'de `user_version == max(schema_migrations.version)` olmalı; geçmiş 1'den bu sürüme kadar kesintisiz, tekrarsız ve kod manifestindeki checksum'larla aynı olmalıdır. Ayrışma otomatik sürüm düzeltmesiyle gizlenmez; kontrollü tutarsız store hatasıdır.

Manifestin kanonik kaynağı kodla gelen değişmez, sıralı SQL adımlarıdır. Her adımın `from_version`, `to_version` tamsayıları ve sıralı `statements` string listesi vardır. Checksum, yalnız bu üç alanın `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` baytlarının SHA-256'sıdır; tüm modülün hash'i değildir. SQL string'leri UTF-8/LF kaynakta sabittir; çalışma anında whitespace normalizasyonu yapılmaz. Yayımlanmış adım değiştirilmez, yeni adım eklenir. Her string tek `execute` çağrısıdır; `executescript`/noktalı virgülden bölme veya checksum'a girmeyen Python veri dönüşümü bu v1 manifestine eklenmez.

Her adımın DDL/verisi, manifest kaydı ve `user_version` aynı `BEGIN IMMEDIATE` transaction'ında commit edilir. Atomiklik **adım başınadır**, bütün yükseltme zinciri için değildir. 1→2 başarılı, 2→3 başarısızsa canlı DB 2'de kalır; bir sonraki açılış 2'nin geçmişini doğrulayıp yalnız 2→3'ü dener. 1'e otomatik dönüş yapılmaz. Her adımda yazma kilidi alındıktan sonra sürüm/geçmiş tekrar okunur; başka süreç adımı tamamlamışsa tekrar uygulanmaz. Tam hedef sürüme gelmeden o sürümün kullanım senaryosu başlatılmaz.

`integrity_check`/gereken yerde `quick_check`, foreign key bulunan şemada ayrıca boş sonuç veren `foreign_key_check` ve şemaya özgü mantıksal kontroller gerekir. Bunlar kaynak ve snapshot kabulünde, migration öncesi ve yeni adım commit edilmeden uygulanır; `foreign_keys=ON` eski ilişkisel bozulmayı taramış sayılmaz. Aktif epoch/key bağı, tek store metadata satırı ve manifest sürekliliği mantıksal kontrol örnekleridir. Her sıcak okumada tüm DB taranmaz. [SQLite PRAGMA](https://www.sqlite.org/pragma.html) (erişim: 2026-10-27).

### Migration yedeği ve kurtarma

Desteklenmeyen sürüme downgrade yoktur. Eski desteklenen sürümden daha yenisine **her adımda** exclusive bakım kilidi altında kaynak sürüm/geçmiş doğrulanır, ayrı read bağlantısından SQLite backup API snapshot'ı alınır ve aşağıdaki kalıcılık/validasyon tamamlanır. Normal bağlantılar kapalıdır; shared kilidi tutarken exclusive'e kontrolsüz yükseltme yapılmaz. Uzun backup/hash işlemi açık SQL write transaction'ında bekletilmez. Snapshot tamamlandıktan sonra `BEGIN IMMEDIATE` alınır, kaynak sürüm/geçmiş tekrar denetlenir ve adım uygulanır. Uyumsuz kaynak varsa DDL başlamaz. Açık write transaction taşıyan bağlantının kendisinde `backup()` çağrısı yapılmaz. Hedef uygulamanın yeni oluşturduğu özel snapshot'tır; API'nin mevcut hedefi değiştirebilmesi kullanıcı dosyasını açma izni değildir. [SQLite Backup API](https://www.sqlite.org/backup.html) (erişim: 2026-10-27).

Her snapshot `<state>/backups/<random-backup-id>/snapshot.sqlite3` altında ayrı 0700 dizinde, no-clobber/no-follow ve 0600 olarak oluşturulur; önceden var olan hedef sahipli görünse de açılmaz. Kaynakla aynı DB/file kimliği reddedilir. Backup bağlantıları kapatılır; snapshot'ın sahipliği, kaynak store UUID/sürümü/manifesti, bütünlüğü ve ilişkisel/mantıksal kontrolleri doğrulanır. Snapshot dosyası yukarıdaki platform sync kuralıyla kalıcılaştırılır. Ardından kaynak UUID/sürüm, snapshot SHA-256, amaç ve UTC zamanı içeren 0600 `complete.json` no-clobber yazılıp sync edilir; snapshot dizini ve yeni üst dizin kayıtları da sync edilir. Bu tamamlanma kaydı kalıcılaşmadan migration DDL'si başlamaz.

Backup beklemesi ayrıca bütçelenir. Disk dolması, doğrulama, sync veya hedef çatışmasında SQL migration transaction'ı başlamaz; açıksa hata yolunda rollback/kapatma gerekir. Bağlantı/bakım kilidi bırakılır; canlı şema değiştirilmez. `complete.json` bulunmayan/uyuşmayan kısmi dizin restore girdisi sayılmaz, mevcut kullanıcı dosyasına müdahale edilmez; kendi kısmi çıktısı tanıda gösterilir ve yalnız açık temizleme işleminde kimliği doğrulanarak kaldırılır. Tamamlanan snapshot başarıdan veya hatadan sonra korunur; otomatik yaş/sayı temizliği yoktur. Disk bütçesi yetmezse eski yedeği sessizce silmek yerine yeni migration reddedilir. Snapshot ve metadata normal log/JSON export'una katılmaz; K dosyası backup'a eklenmez.

Yedek inceleme/kurtarma içindir; otomatik canlı DB değiştirme veya downgrade değildir. 1→2→3 örneğinde 1 ve 2 snapshot'ları korunur; son commit edilen canlı sürüm önceliklidir. Eski snapshot'a dönüş sonraki kayıtları geri getirmez. P01-2 yalnız identity içeren store için [ADR-0012'deki ayrı restore kapısını](0012-credential-identity-and-change-detection.md#identity-reset-ve-db-restore-ayrımı) tanımlar; operation tüketicisi bulunan uygulama sürümünde bu restore desteği kapalıdır.

Manuel journal silerek onarım yapılmaz; SQLite'ın kendi hot-journal açılış rollback'i normal kurtarma yoludur ve engellenmez. Hot-journal kurtarması da yazma gerektirebilir; salt tanılama bunu gizlice başlatmaz, açık onarım gereksinimini bildirir. [SQLite locking/recovery](https://www.sqlite.org/lockingv3.html) (erişim: 2026-10-27).

### Sonraki operation/lease tüketicisine bağ

P01-4b aynı DB'de operation/attempt geçişi, rastgele owner ve monoton artan fencing token'ını transaction içinde denetlemelidir. Lease süresi tek başına yeni yan etki izni değildir; `unknown` uzlaştırma ister. Saat sıçraması/restart ve eski sahibin devam etmesi kabul senaryolarıdır. Somut operation DDL'si ve saat/lease uygulaması P01-4b kartında gerçek tüketiciyle tamamlanır; bu ADR bunların uygulanmış olduğunu veya uzak exactly-once garantisini ilan etmez.

## Değerlendirilen alternatifler

- **WAL + FULL:** Yerel küçük deneyde daha hızlı; eşzamanlı okuyucu/yazarı destekler. Runtime sürümü ve checkpoint yaşam döngüsü ek kapı getirir. WAL-reset düzeltmesi olmayan kitaplıkla etkinleştirilmez; sessiz journal dönüşümü yapılmaz. Bu paketteki düşük hacimli kimlik yazıları için varsayılan önerilmiyor.
- **DELETE + FULL/NORMAL veya WAL + NORMAL:** Son commit'in güç kaybında korunması için seçilen hedefle uyumlu değil; hız uğruna varsayılan yapılmıyor.
- **JSON/JSONL:** Çok süreçli güncelleme ve migration için ikinci transaction mekanizması gerektirir. **ORM/genel migration altyapısı:** Şimdiki üç tabloya ek bağımlılık ve soyutlama getirir; somut ihtiyaç görülmedi.

## Sonuçlar ve kabul kapısı

Yeni varsayılan ürün koduna ancak kullanıcı onayıyla girer. Geçici gerçek DB'de DDL/veri/sürüm rollback, ikinci adımı başarısız zincirin yeniden açılması, sürüm/manifest ayrışması, iki migration yazarı, sınırlı busy, bozuk/yabancı/yeni sürüm, izin/symlink ve ayrı süreçte commit/kesinti kanıtı gerekir. Backup'ta mevcut hedef, disk dolması, ilişkisel bozulma, tamamlanma kaydından önce/sonra kesinti; yeni dizin/üst dizin/file sync hataları ve açık kurtarma sınırları kabulde sınanır. Mevcut komutların lazy guard'ları korunur. Süreç öldürme deneyi güç kesintisi/SSD arızası testi diye raporlanmaz. Daha ağır operation yükü için journal değişikliği gerekirse ölçüm, runtime uyumu ve migration ayrı açık kararla ele alınır.
