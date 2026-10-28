# ADR-0015: Checksum'lı migration manifest V2

**Durum:** Accepted — 2026-10-28 açık kullanıcı onayı; V2 uygulaması/review/bütçe doğrulandı, PR #9 merge bekliyor. **Tarih:** 2026-10-28. **İş:** [PR #9](https://github.com/HodeTech/Yorunge/pull/9), P01-3 merge sonrası clock düzeltmesi. [ADR-0011](0011-state-foundation-and-migrations.md#şema-ve-migration), [bulgu ve kanıt](../research/p01-3-implementation-validation.md#global-fence-review-1--açık-manifest-engeli).

## Bağlam ve karar ilişkisi

ADR-0013'ün mevcut yeniden-canlanmama garantisi için PR #9, cache/proof/conflict ile plan/onay expiry'lerini kapsayan global indeks prototipi içerir. İlk prototipte şema 4→5'in Python backfill'i V1 checksum'ının dışındaydı; ADR-0011 bu durumu yasaklar. Bu P2, aşağıdaki V2 uygulaması ve iki review turuyla giderildi; merge öncesi kabul kaydı korunur. Global fence davranışı yeni bir yetki veya TTL kararı değildir; migration kimliğinin genişletilmesi ayrı onay gerektirir.

**Bu karar, ADR-0011'in üç alanlı checksum tanımını yalnız V2 adımları için kısmen değiştirir.** V1 tanımı ve migration 1–4 kimlikleri aynen kalır. Kullanıcı üç seçimi de açıkça onayladı. ADR-0011 Accepted kalır; bu karar onu bütünüyle Superseded yapmaz. İndeks ve ADR-0011 notu V1/V2 kapsamını gösterir.

SQLite alt sınırı 3.37'dir. JSON1 bu seride derleme seçeneğine bağlıdır; daha sonraki sürümlerde de çıkarılabilir. Bu karar JSON1 bağımlılığı getirmez. [Resmî SQLite açıklaması](https://www.sqlite.org/json1.html#compiling_in_json_support).

## Karar

### Manifest sürümü adım başınadır

| Adım türü | Kesin anahtar kümesi | Kural |
|---|---|---|
| Yayımlanmış 0→1 … 3→4 | `from_version`, `to_version`, `statements` | Donmuş V1; ek alan, `manifest_version` veya `data_transform: null` kabul edilmez |
| Bundan sonraki SQL-only adım | `manifest_version`, `from_version`, `to_version`, `statements` | V2; `data_transform` anahtarı bulunmaz |
| Bundan sonraki veri dönüşümlü adım | Önceki dört alan ve `data_transform` | V2; descriptor zorunludur |
| Nihai 4→5 | V2 veri dönüşümlü yapı | `capability-expiries-v1` zorunlu; eksik/null descriptor reddedilir |

V1'e opsiyonel alan eklenmez; alanı checksum hesabında sessizce yok saymak da kabul edilmez. Yeni SQL-only adımlar V1 kullanmaz. V1 4→5 bırakıp V2 5→6 ile backfill yapma yolu yoktur. Manifest sürümü store, backup veya public JSON sürümü değildir; karışık V1/V2 geçmişi aynı `schema_migrations(version, checksum, applied_at)` tablosunda tutulur.

V1 checksum girdisi ADR-0011'deki üç alanın mevcut baytlarıdır. V2 checksum girdisi tablodaki tam nesnedir; SQL-only V2 dört, veri dönüşümlü V2 beş alan içerir. İkisinde de SHA-256 girdisi `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` olur. V1 SQL string'leri ve checksum'ları değiştirilmez.

Veri dönüşümlü biçim örneği aşağıdadır; gerçek SQL/hash uygulamada sabitlenir:

```json
{
  "manifest_version": 2,
  "from_version": 4,
  "to_version": 5,
  "statements": ["<sıralı, değişmez SQL>"],
  "data_transform": {
    "id": "capability-expiries-v1",
    "code_sha256": "<64 lowercase hex>"
  }
}
```

Biçim kapalıdır: sürümlerde `type(value) is int`, `from_version >= 0`, `to_version == from_version + 1`; V2'de `manifest_version == 2` gerekir. Bool/float/string sürüm, fazla/eksik alan ve yanlış tür reddedilir. `statements`, en az bir boş olmayan UTF-8/LF string içeren listedir; BOM, CR ve surrogate reddedilir, whitespace normalizasyonu yapılmaz. Her string tek `execute` çağrısıdır; `executescript` veya noktalı virgülden bölme yapılmaz.

`data_transform` tam olarak `id` ve `code_sha256` string'lerini taşır. ID kapalı katalogdaki `capability-expiries-v1` değeridir; yeni ID yeni değişmez handler ve migration gerektirir. Hash ASCII `^[0-9a-f]{64}$` biçimindedir. Adımın SQL-only/veri dönüşümlü oluşu kod manifestinde sabittir; descriptor silinerek 4→5 SQL-only yapılamaz. JSON gösterimi çözümlendiğinde duplicate key, geçersiz UTF-8 ve non-finite sayı reddedilir. Runtime manifesti paket kodudur; DB/config/CLI için yeni manifest import yüzeyi açılmaz.

### Tek dosya ve doğrulanan baytlardan yürütme

Handler tek ve kendi kendine yeterli UTF-8/LF dosyasıdır; en çok 64 KiB'dir. Yerel yardımcı, mevcut domain decoder'ı veya mutable expiry modülü import edemez. Bütün parser/dönüşüm yardımcıları aynı dosyada ve aynı hash kapsamındadır. Yalnız `json`, `datetime`, `re`, `typing` standart modüllerine ihtiyaç duyabilir; izin listesi kapalıdır. Python/SQLite/standart kütüphane desteklenen runtime'ın parçasıdır; `code_sha256` bunların bundle hash'i değildir.

Bekleyen V2'nin DDL/veri yazımından önce yükleme sırası şöyledir:

1. Sabit ID yalnız paket içindeki sabit kaynağa eşlenir; caller veya DB yol/modül/kod seçemez.
2. Kaynak **bir kez** immutable `bytes` buffer `B` olarak okunur; boyut/UTF-8/LF ve SHA-256 kontrol edilir.
3. Aynı `B`, yeniden dosya okunmadan `compile(B, fixed_filename, "exec", flags=0, dont_inherit=True, optimize=0)` ile derlenir. Metin/whitespace dönüştürülmez.
4. Kod her pending çalıştırmada yeni, loader'ın kurduğu namespace'te yürütülür; yalnız buradan elde edilen `apply(connection)` çağrılır. Namespace `sys.modules`'a kaydedilmez ve önceki handler namespace'i tekrar kullanılmaz.

Handler için normal `import`, `importlib`, hazır code object veya `.pyc` kullanılmaz. Önceden yüklenmiş handler ve geçerli görünen eski bytecode yürütülecek kodu seçemez. Disk dosyası okuma sonrası değişse bile doğrulanmış aynı buffer derlenir veya yazmadan kontrollü ret verilir; başka baytlara sessiz geçiş olmaz. Kaynak okumak ve ardından normal import etmek yeterli değildir. [Python import/bytecode](https://docs.python.org/3.11/reference/import.html#cached-bytecode-invalidation), [compile semantiği](https://docs.python.org/3.11/library/functions.html#compile).

Bu, sabit paket kaynağının doğrulanmış buffer'ından sınırlı yüklemedir; kullanıcı kodu/plugin/SQL-UDF sistemi değildir. Hash paket imzası veya aynı UID'deki keyfî Python koduna karşı sandbox güvencesi değildir. Yayımlanmış handler ve hash değiştirilmez; yeni davranış yeni ID/adım ister. Güncel store'un normal açılışı statik manifest kimliğini doğrular; geçmiş handler'ı yeniden okumaz, derlemez veya hash'lemez. Wheel/sdist doğrulanan aynı kaynak baytlarını taşır.

### Handler saflığı ve transaction sahipliği

Handler çıktısı yalnız verilen bağlantıdaki doğrulanmış kaynak satırlara bağlıdır. Env, config, dosya, ağ, wall/monotonic saat, locale, rastgelelik ve çağrılar arasında mutable global durum okunmaz. `datetime` yalnız kaynak tarihini çözümlemek içindir; `now`/`today` kullanılmaz. Modül üst düzeyi yalnız izinli import, değişmez sabit ve yardımcı fonksiyon tanımı içerir; yan etki yapmaz. İzinli import/builtin ve kaynak biçimi yükleme sırasında denetlenir; yasak girdi/yan etki kontrollü reddedilir.

`connection`, caller'ın mevcut SQLite transaction'ını temsil eden dar bir SQL facade'dır; raw connection/cursor vermez. Yeni bağlantı, commit/rollback/savepoint, `executescript`, `ATTACH`, `PRAGMA`, DDL ve extension/UDF erişimi yoktur. Yalnız parametre bağlı, tek-statement işlemler vardır. Bu handler'ın tablosal izni `capability_cache` için SELECT, `capability_expiries` için INSERT'tür; canonical source değiştirilemez. SQLite authorizer, facade kısıtını handler çalışırken destekler; transaction/DDL/PRAGMA/ATTACH ve izin dışı tablo/fonksiyon işlemini reddeder. Gerekli deterministic şema fonksiyonları dışında saat/rastgelelik/UDF yoktur. Cursor sonuçları connection geri kapısı açmaz.

Caller transaction'ı başlatır, deadline'ı denetler, tam doğrulama yapar ve commit/rollback eder. Handler SQL/veri hatasını başka bir sınıfa yeniden eşlemez; hatalı kaynak için private `ValueError` kullanabilir. Facade deadline kontrolü handler'a saat girdisi vermez. Authorizer/guard caller doğrulaması ve rollback öncesinde güvenli biçimde kaldırılır; caller'ın kendi transaction işlemleri engellenmez. Commit denemesi veya başka sözleşme ihlali `state_invalid` olur ve etkilenen adım rollback edilir.

Bu kısıtlar kod/sözleşme hatalarını önler; aynı UID'deki kasıtlı nesne-introspection saldırısına karşı sandbox iddiası yoktur.

### Atomiklik, kanonik doğrulama ve hatalar

Sıra: preflight → tamamlanmış migration snapshot'ı → `BEGIN IMMEDIATE` ve kaynak sürüm/geçmiş denetimi → DDL → doğrulanmış handler → transaction içi manifest/user_version → **güncel kanonik tam doğrulama** → COMMIT. Handler'ın kendi parser'ı nihai otorite değildir; `decode_entry`/`validate_cache`, FK ve diğer schema tüketicileri güncel sıcak okuma ile aynı kayıt/indeks kurallarını uygular.

Handler en çok 1.024 kayıt, payload başına 32 KiB UTF-8, sekiz evidence ve 10 ayrı expiry/kayıt işler. Aggregate, her evidence expiry'si ve null olmayan `conflict_until` dahil edilir; eşit tarihler tekilleştirilir. Key/payload/proof zamanı değiştirilmez. Snapshot, dosya/dizin sync, DELETE/EXTRA/fullfsync, bakım kilidi ve bilinmeyen operation tüketicisi ret kuralları korunur.

| Durum | Public hata |
|---|---|
| Bozuk/eksik/fazla manifest alanı, ID/sürüm/hash uyuşmazlığı, eksik handler, UTF-8/compile/guard/veri-şema hatası, eski prototip checksum'ı | `state_invalid` |
| Handler kaynağı okumasında eksik kaynak dışındaki I/O; SQLite FULL/IOERR ve extended aileleri | `state_write_failed` |
| Deadline veya SQLite BUSY/LOCKED/INTERRUPT | `state_busy` |
| Mevcut platform/SQLite desteğinin dışında runtime | `state_unsupported` |

Ham SQLite/ImportError, path veya traceback public çıktıya sızmaz. Onay ya da migration otomatik baştan tekrarlanmaz. Commit öncesi hatada DDL/veri/manifest/version birlikte rollback edilir. COMMIT sırasında süre/I/O sorunu çıkarsa committed durumu varsayımla geri çevrilmez: son atomik sürüm korunur, sonraki açık erişim geçmişi doğrular. Commit öncesi rollback kabulü, commit sonrası rollback vaadine genişletilmez.

### Bağımsız expiry oracle'ları

[Sabit schema-4 vektörleri](../research/p01-3-expiry-migration-vectors.json), gerçek source-row alanları ve **elle seçilmiş** `(cache_key, expires_at)` kümelerini taşır. Beklenen kümeler handler, `cache_expiries`, `combine` veya nihai validator'dan üretilmez/güncellenmez. Kapsam: yalnız aggregate, tek/birden çok proof, evidence'sız conflict marker, çakışan üç tür tarih ve sekiz evidence + aggregate + farklı blocker ile 10 ayrı tarih.

Her vektör gerçek schema-4 dosyasına konur; V2 ile migration sonrası SQL satırları literal beklentiyle karşılaştırılır. Ardından güncel warm query ve global next-boundary/restart regresyonu çalışır. Böylece handler ve validator'ın aynı alanı atlaması tek başına kabul sağlayamaz. Duplicate key, non-finite, 32 KiB üstü ve dokuz evidence negatiflerinde güncel kanonik decoder ile controlled ret ve değişmemiş DB doğrulanır. Onay öncesindeki yalnız prototype/vektör kontrolü tarihsel araştırma kanıtıdır. Güncel V2, gerçek migration/literal/warm/negatif testleri ve yoğun bütçe ölçümleriyle [kabul kaydında](../research/p01-3-implementation-validation.md#v2-uygulaması--adım-2) doğrulandı.

### Migration bütçesi ve ölçülebilir kabul

**Karar mevcut toplam 5 saniye ve en çok 1 saniye busy bütçesini korur; ayrı migration bütçesi eklemez.** Kilit, snapshot/sync, hash/compile, backfill ve doğrulama toplam bütçeye dahildir; zincirde süre sıfırlanmaz. Handler'ın row/SQL geçişlerinde caller deadline kontrol edilir. Mevcut fsync/disk/scheduler nedeniyle katı fiziksel duvar saati garantisi iddia edilmez.

Başarı ölçümü en az üç yeni disposable store üzerinde her yol için yapılır. Kaynak şema 2'de 1.024 cache; şema 3'te ayrıca 1.024 plan; şema 4'te ayrıca 1.024 onay bulunur. Var olmayan eski tablo fixture'a eklenmez. İki veri hacmi gerekir: temsilî sekiz-proof/9.200-expiry ve geçerli kayıtların 32 KiB cache/64 KiB plan/4 KiB onay byte limitlerine en yakın hacmi. Gerçek ulaşılan byte sayıları kaydedilir; modelin kabul etmediği padding ile sahte üst sınır fixture'ı üretilmez. Eski intent/stage/live çifti ve kaynak backup kaybı ayrıca kapsanır.

Her adım ve tüm çağrı için wall/monotonic süre, SQLite VM adımları, payload/row/expiry sayısı, source/komut/ortam/disk bilgisi ham JSON'da saklanır. Backup/sync, DDL, handler load/compile, backfill, full validation ve commit süreleri ayrılır. Pass/fail eşiği mevcut toplam deadline'dır; VM sayısı aynı fixture'daki DDL-only baseline ile maliyet karşılaştırmasıdır, ölçülmemiş ayrı bir VM tavanı eklenmez. Ölçüm mevcut deadline callback'ini devre dışı bırakamaz. Python CPU maliyeti ayrıca toplam süreye dahildir.

Pozitif kabul: desteklenen referans ortamda tüm yoğun/limit fixture yolları mevcut deadline içinde hedef şemaya ulaşmalı ve full/warm doğrulamayı geçmelidir. Failclosed testi ayrı bir negatif kabuldür; süreyi aşarak `state_busy` dönmesi başarılı migration ölçümü sayılmaz. Herhangi bir pozitif yol tamamlanamıyorsa bu kabul kapanmaz; optimizasyon veya açık bütçe kararı gerekir, eşik sessizce artırılmaz.

Enjekte edilmiş commit-öncesi tükenmede `state_busy`, I/O tükenmesinde `state_write_failed` ve adım rollback'i doğrulanır; tamamlanmış önceki adımlar kalır. Ham ölçüm, aynı schema-4 girdisindeki V1 DDL-only izolasyon baseline'ıyla birlikte saklanır. DDL-only baseline, backfill/full validation içermediği ve tamamlanmış geçerli indeks üretmediği için ürün başarısı olarak sunulmaz. Önceki 4,922/3,121/2,039 s sonuçları sırasıyla schema 2/3/4 prototip zincirleridir; bağımsız V2 veya maksimum byte fixture kabulü değildir.

### Prototip DB ve güvenli kurtarma

Development teslimi şema 4'tür; şema 5 yalnız merge edilmemiş PR #9 prototipidir. İlk nihai 4→5 V2 olur. Prototip V1 checksum'lı user_version=5 otomatik benimsenmez, yeniden etiketlenmez, silinmez veya downgrade edilmez.

Disposable test verisi için yeni bir `--state-dir` ile temiz store seçilir. Gerçek veri varsa eski dizin korunur; `schema_migrations`/checksum elle değiştirilmez. Şema 1–4'e ait doğrulanabilir, tamamlanmış `purpose=migration` backup'ı varsa desteklenen restore akışı **yeni boş hedefte** kullanılır. Uygun backup yoksa DB korunur ve destek incelemesi yapılır; prototip DB için otomatik dönüşüm vaadi yoktur. Bu sınır yayımlanmamış geliştirme/test verisi içindir.

## Alternatifler ve sonuçlar

Checksum dışı hook, SQL yorumu/UDF içine gizli dönüşüm, migration sonrası görünmez repair, salt ad etiketi veya cache'i boşaltma seçilmez. JSON1 zorunluluğu mevcut runtime desteğini değiştirir. Çok dosyalı bundle yerine tek dosya seçilmiştir; yerel helper import'u bu kararın dışında kalır.

Bu karar V1 1–4'ü korurken sonraki bütün adımları V2'ye taşır. CLI/Python wire'ı, TTL, kotalar, bütçe, kimlik/K yaşam döngüsü ve gerçek EVREN yetkisi değişmez. V2 uygulaması bu onaya dayanır; checksum P2 kod/review/kabul ile kapandı. PR #9 development merge öncesinde kullanıcı incelemesine sunulur; son head kontrolleri PR üzerinde izlenir.

## Kabul matrisi

| Alan | Ayrı zorunlu kontroller |
|---|---|
| Manifest kimliği | Eski 1–4 golden SQL/checksum; V2 SQL-only ve veri checksum vektörleri; 4→5'in tek V2 adım olması |
| Kapalı biçim | V1'e her ek alan/null descriptor; bilinmeyen version; bool/float version; fazla/eksik/duplicate key; yanlış statements/UTF-8/LF; SQL-only V2'de descriptor ve data V2'de eksik/null descriptor |
| Handler kimliği | Bilinmeyen ID, bozuk/truncated/uppercase hash, eksik kaynak, hash ayrışması; DDL/veri/manifest/version değişmeden ret |
| Yürütülen baytlar | Kaynakla aynı size/mtime taşıyan eski/farklı pyc; önceden yüklenmiş modül; kaynak read sonrası değişimi; doğrulanan B'nin çalışması veya yazmadan ret |
| Tek dosya/saflık | Yerel helper/env/saat/dosya/ağ/config/locale/random/global state kullanımı; yeni bağlantı ve commit/rollback/DDL/PRAGMA/ATTACH/executescript; aynı kaynak satırlarında ortam değişiminin aynı veri kümesini vermesi |
| Veri doğruluğu | Sabit literal schema-4 oracle'ları; duplicate/non-finite/oversize/9-evidence negatifleri; güncel full decoder ve warm sorgu; aggregate/proof/conflict bağımsız sınırları |
| Atomiklik | Handler ortası/validation/commit-öncesi kesinti; aynı adımın tam rollback'i; iki writer ve zincirin kalan adımdan resume'u; handler guard'larının caller rollback'ini engellememesi |
| Uyumluluk | user_version=5 + prototip V1 checksum reddi; schema 2/3/4→5; eski intent/stage/live ve kaynak kaybı; payload eşitliği/indeks tamlığı |
| Kaynak ve süre | Yukarıdaki pozitif/negatif migration bütçesi, phase/VM/raw JSON/baseline; global clock/concurrency/churn; 30-process normal/yoğun startup |
| Dağıtım/teslim | Wheel/sdist'te aynı handler baytları; iki temiz kurulum; tam test/lint/type/belge; fix/commit sonrası farklı fresh reviewer'larla ikinci tur ve son head zorunlu CI |

Ret testleri tam kararlı hata kodunu ve DB içeriği/manifest/user_version'ın korunmasını doğrular. Matris bu kararın normatif kabul şartlarını tanımlar; güncel V2 bu şartlarla [kabul kaydında](../research/p01-3-implementation-validation.md#v2-uygulaması--adım-2) doğrulandı. Geçmiş test sayısı veya tek başına prototip başarısı kabul yerine kullanılmaz.
