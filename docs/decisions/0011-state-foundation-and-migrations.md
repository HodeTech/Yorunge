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
| Sahiplik/sürüm | `application_id=0x594F5255`, `user_version` kanonik şema sürümü; sürüm manifesti kodla birlikte gelir. Yabancı, gelecek sürüm veya bozuk DB otomatik yeniden oluşturulmaz |

State dizini aynı güvenilen yerel kullanıcıya ait olmalıdır. Yol kontrolünün ardından SQLite'ın dosyayı kendisinin açması, saldırgan aynı UID altında sürekli yol değiştiriyorsa yarışsız bir güven sınırı sağlamaz; böyle bir koruma iddia edilmez. Metadata komutları ve sır gerektirmeyen mevcut offline işlemler state dizini/DB/key yaratmaz. Doctor'ın temel yerel incelemesi de kayıt yaratmaz; yazma/migration açık store kullanımıdır.

### Şema ve migration

İlk sürüm yalnız gerçek tüketicileri olan `state_meta`, `schema_migrations` ve `credential_bindings` tablolarını içerir. `state_meta` tek store UUID'si, aktif identity epoch, yerel key kimliği/doğrulaması ve biçim sürümünü taşır. `schema_migrations`, sıralı sürüm, kod manifestindeki SHA-256 checksum ve UTC uygulanma zamanını taşır. Credential kayıt alanları [ADR-0012'de](0012-credential-identity-and-change-detection.md) tanımlanır. Operation/attempt/lease için boş tablo kurulmaz.

Tablolar `STRICT` ve açık `NOT NULL`/`CHECK`/`UNIQUE` sınırları kullanır; bu Pydantic strict doğrulamasının yerine geçmez. SQLite `STRICT` kayıpsız tür dönüşümünü hâlâ yapabilir. Bağlam/enum/UUID/uzunluk ve zaman değerleri okuma/yazma sınırında uygulama modeliyle doğrulanır.

Yalnız yeni ve uygulama tarafından özel olarak oluşturulan DB başlatılır. Mevcut sıfır bayt/yabancı dosya adı nedeniyle benimsenmez; kesik ilk kurulum kontrollü hata ve açık onarım yoludur. Her migration adımının DDL/verisi, manifest kaydı ve `user_version` aynı transaction'da commit edilir. `executescript()` bu transaction'ın içine eklenmez. Hata ve süreç kesintisi tam adımı geri alır; doğrulanmış eski sürüm korunur. İki süreç sürümü yazma kilidi alındıktan sonra tekrar okur.

Desteklenmeyen sürüme downgrade yoktur. İleri sürüm yükseltmesinde yazma kilidi ve sürüm tekrar denetlendikten sonra, ilk değişiklikten önce ayrı read bağlantısından ayrı hedefe SQLite backup API snapshot'ı alınır; snapshot bütünlüğü/sahipliği ve kaynak sürümü doğrulanır. Açık write transaction taşıyan bağlantının kendisinde `backup()` çağrısı yapılmaz. Yedekleme beklemesi ayrıca bütçelenir; başarısızlıkta migration başlamaz ve transaction kapatılır. Eksik/yabancı journal silerek onarım yapılmaz. Tam quick/integrity kontrolü tanılama/migration kabulündedir; her sıcak okumada tüm DB taranmaz.

### Sonraki operation/lease tüketicisine bağ

P01-4b aynı DB'de operation/attempt geçişi, rastgele owner ve monoton artan fencing token'ını transaction içinde denetlemelidir. Lease süresi tek başına yeni yan etki izni değildir; `unknown` uzlaştırma ister. Saat sıçraması/restart ve eski sahibin devam etmesi kabul senaryolarıdır. Somut operation DDL'si ve saat/lease uygulaması P01-4b kartında gerçek tüketiciyle tamamlanır; bu ADR bunların uygulanmış olduğunu veya uzak exactly-once garantisini ilan etmez.

## Değerlendirilen alternatifler

- **WAL + FULL:** Yerel küçük deneyde daha hızlı; eşzamanlı okuyucu/yazarı destekler. Runtime sürümü ve checkpoint yaşam döngüsü ek kapı getirir. WAL-reset düzeltmesi olmayan kitaplıkla etkinleştirilmez; sessiz journal dönüşümü yapılmaz. Bu paketteki düşük hacimli kimlik yazıları için varsayılan önerilmiyor.
- **DELETE + FULL/NORMAL veya WAL + NORMAL:** Son commit'in güç kaybında korunması için seçilen hedefle uyumlu değil; hız uğruna varsayılan yapılmıyor.
- **JSON/JSONL:** Çok süreçli güncelleme ve migration için ikinci transaction mekanizması gerektirir. **ORM/genel migration altyapısı:** Şimdiki üç tabloya ek bağımlılık ve soyutlama getirir; somut ihtiyaç görülmedi.

## Sonuçlar ve kabul kapısı

Yeni varsayılan ürün koduna ancak kullanıcı onayıyla girer. Geçici gerçek DB'de DDL/veri/sürüm rollback, iki migration yazarı, sınırlı busy, bozuk/yabancı/ileri sürüm, izin/symlink, disk yazma hatası, ayrı süreçte commit/kesinti ve backup/yeniden açma kanıtı gerekir. Mevcut komutların lazy guard'ları korunur. Süreç öldürme deneyi güç kesintisi/SSD arızası testi diye raporlanmaz. Daha ağır operation yükü için journal değişikliği gerekirse ölçüm, runtime uyumu ve migration ayrı açık kararla ele alınır.
