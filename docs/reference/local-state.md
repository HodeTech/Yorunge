# Yerel state kullanım sözleşmesi

**Durum:** P01-4a temeli iki review turuyla doğrulandı; kimlik gözlemi uygulandı; reset/restore adımı iki review turuyla doğrulandı. **Tarih:** 2026-10-28. Tasarım nedeni ve kanonik dayanıklılık/migration kuralları [ADR-0011](../decisions/0011-state-foundation-and-migrations.md), key yaşam döngüsü [ADR-0012](../decisions/0012-credential-identity-and-change-detection.md) içindedir.

## Açık oluşturma ve doğrulama

State oluşturma/gözlem ve tüm bakım önizleme/uygulama girişleri desteklenmeyen platformda veya `fcntl` bulunmadığında I/O ve env çözümlemesi öncesi `state_unsupported` verir. Platforma özgü import eksikliği ham `ModuleNotFoundError` olarak public API/CLI sınırına çıkmaz.

`yorunge state init [--state-dir PATH]` ile Python `yorunge.api.initialize_state(*, state_dir: Path | None = None)` aynı kullanım senaryosudur. Varsayılan macOS/Linux yerel disk yolu `~/.local/state/yorunge`; DB `state.sqlite3` dosyasıdır. `XDG_STATE_HOME` veya başka davranış env override'ı okunmaz. State ailesinde `--state-dir`, `state` ile `init` arasında veya `init` sonrasında verilir; doctor, identity, açık cache ve execution ailesinde kendi komutunda da desteklenir. Config/profil/proje seçenekleri bu işte geçersizdir.

İlk açık kullanımda private store, karşılaştırma K'sı ve gerçek şema kurulur. Var olan sağlıklı store'da aynı store/epoch döner; bu çağrı kimlik reset'i veya env çözümleme değildir. Sonuç `Result[StateInfo]`: zarf sürümü 1; data `schema_version=1`, gerçek DB `store_schema_version`, `store_id`, `identity_epoch`. K, key-check ve özel verifier sonuçta yoktur. `state init` mevcut store için tam yapısal/ilişkisel/mantıksal doğrulama yapar.

Metadata/help/version, varsayılan context/capability, offline Plan ve env credential kontrolü bu store'u açmaz/yaratmaz. Açık capability `--cached`/`--refresh` modu private store/clock kullanır; normal capability komutuna gizli DB erişimi eklenmez. State sınıfları explicit kullanımda lazy yüklenir. Tarihsel şema 1 metadata/migration/credential tablolarıdır; şema 2 `cache_clock` ve `capability_cache`, şema 3 `execution_plans`, şema 4 `execution_approvals` ekler. Operation/lease/jobs yoktur. SQL/key dosyalarının sahipliği/izinleri denetlenir; mevcut kullanıcı dosyası chmod/overwrite edilerek benimsenmez.

## Hata ve süre

Kararlı `state_invalid`, `state_busy`, `state_repair_required`, `state_write_failed`, `state_unsupported` kodları çıkış 2'dir. Hata zarfı path, ham SQLite hatası, K veya özel verifier taşımaz. `state_busy` otomatik bütün kullanım senaryosu tekrarı değildir. Yerel karşılaştırma anahtarı sorunu EVREN auth hatası diye raporlanmaz.

SQLite'ın FULL ve IOERR (genişletilmiş alt kodlar dahil) aileleri disk/I/O için `state_write_failed` olur; bozuk şema diye sınıflanmaz. BUSY/LOCKED/INTERRUPT bütçe/kilit sınıfında kalır; bozuk/yabancı şema `state_invalid` olur.

SQLite/file lock beklemesi en çok 1 saniyedir; bu kullanım senaryosunun varsayılan toplam bütçesi 5 saniyedir. SQLite progress ve backup/hash adımları bütçeyi denetler. İşletim sistemi disk I/O'su, fsync veya scheduler gecikmesi için katı 5 saniye duvar saati garantisi verilmez. Süre dolduysa yarım sonucu başarı sayma veya yeni kimlik oluşturmak için otomatik yeniden başlama yoktur.

Eksik/bozuk key, partial bootstrap, yabancı/bozuk/ileri şema ve restore intent normal açılışta otomatik onarılmaz. Mevcut dosyalar korunur. Açık reset/restore/recover akışları aşağıda tanımlıdır.

## Snapshot sınırı

Migration'ın her adımı öncesi exclusive bakım kilidi altında yeni no-clobber snapshot alınır; uzun backup/hash SQL write transaction'ı dışında kalır. Dosya/dizin kalıcılığı ve tam doğrulamadan sonra `complete.json` oluşur; kısmi dizin restore girdisi değildir. Tamamlanan yedek otomatik silinmez. Yedek doğrulama snapshot'ı readonly/immutable SQLite bağlantısıyla okur; yeni journal veya recovery başlatmaz.

Adım başına atomiklik vardır: 1→2 başarılı, 2→3 başarısızsa 2 kalır. İki migration yazarı aynı adımı tekrar uygulamaz. `user_version`, kesintisiz manifest/checksum, şema tanımı ve UTC kayıtları denetlenir. `integrity_check` yanında `foreign_key_check` ve uygulama değişmezleri gerekir. SQLite'ın kendi hot-journal recovery'si normal yazmalı açılışın parçasıdır; süreç kesintisi testi güç kesintisi testi değildir.

## Açık reset, restore ve kesilmiş restore kurtarması

`state reset [--state-dir PATH]`, `state restore --backup BACKUP_DIR [--state-dir PATH]` ve `state recover [--state-dir PATH]` önce salt okuma önizlemesi verir. Etkiyi uygulamak için aynı komuta `--confirm DIGEST` eklenir. Non-TTY dahil prompt yoktur. Digest, action ve sır içermeyen store/epoch/sürüm/kayıt sayısı ile UUID/nesil/zaman fingerprint'ine bağlıdır; salt kayıt sayısı onay yerine geçmez. Başka gözlem nesli değiştirmişse `state_changed` ile yeni önizleme gerekir. Public digest'e ham DB hash'i, secret veya HMAC tag'i girmez.

Python karşılıkları `preview_identity_reset` / `reset_identity(confirmation, *, state_dir=None)`, `preview_state_restore(backup_dir, *, state_dir=None)` / `restore_state(backup_dir, confirmation, *, state_dir=None)` ve `preview_state_recovery` / `recover_state(confirmation, *, state_dir=None)`'dır. Önizleme `Result[MaintenancePreview]`, uygulama `Result[StateInfo]` döner. State-dir iki yüzeyde Path/yerel disk seçimi olarak kullanılır. Reset/restore/recover config/profil/proje seçenekleri kabul etmez, env sırrı okumaz.

Reset doğrulanmış canlı DB üzerinde yeni epoch/K kurar; eski binding ve varsa operation geçmişini silmez. Eski K eksik/yanlışsa dahi DB bütünlüğü doğrulanırsa açık reset mümkündür; eski credential kurtarıldı diye anlatılmaz. Önceki epoch kayıtları arşivde kalır ve sonraki gözlem yeni UUID/1 üretir. Referanslanmayan key dosyaları otomatik kullanılmaz veya temizlenmez.

Restore yalnız tamamlanmış `purpose=migration` backup'ında ve **runtime açık identity/cache/clock/plan/approval tablo allowlist'indeyse** açılır. Bu P01-3 genişlemesi [Accepted ADR-0014](../decisions/0014-execution-plan-validity-and-approval.md) kapsamındadır. Operation tablosu veya bilinmeyen tüketici eklenen runtime, eski/boş snapshot veya eksik hedefte dahi `state_restore_unsupported` verir. Restore snapshot sonrası geçmişi kaybedebilir; önizleme ve Result uyarısı bunu açıkça gösterir. Sağlıklı canlı DB varsa `purpose=pre_restore` güvenlik snapshot'ı korunur; bu güvenlik kopyası genel restore girdisi değildir. Eksik hedefe restore desteklenir. Bozuk/yabancı/partial hedefin üzerine yazılmaz.

Ortak exclusive `store.lock` boyunca yeni K, özel `restore-intent.json`, özel stage kopyası ve yeni epoch/key-check kalıcılaştırılır; stage doğrulanmadan canlıya geçilmez. Intent varken normal açılış `state_repair_required` olur. Açık recover aynı ilan edilmiş epoch/K ile tamamlar; yeni kimlik alanını her denemede yeniden üretmez. Tam yeni canlı/stage çifti doğrulanıyorsa kaynak backup'a yeniden erişmek gerekmez. Eksik/yanlış yeni K veya belirsiz canlı dosyada intent korunur. Intent'e ait yarım stage yalnız açık recover sırasında özel `interrupted-*.sqlite3` adına alınarak korunabilir ve pinlenmiş sağlam kaynaktan yeniden kurulur. Eski canlı DB veya kullanıcı dosyası bu yolla karantinaya alınmaz.

Önizleme DB/key/lock yaratmaz, migration veya hot-journal recovery başlatmaz; mevcut journal varsa açık normal `state init` ile SQLite'ın kendi recovery'si veya inceleme gerekir. Eksik/bozuk bakım kilidi, belirsiz partial bootstrap veya bozuk canlı DB otomatik sahiplenilmez. Böyle durumda eski dizini olduğu gibi koruyun; yeni açık `--state-dir` ile init veya bilinen sağlam migration backup'ından restore kullanın. Yeni dizin kimlik geçmişini kurtardığı anlamına gelmez. Bu koruma sınırı elle journal silme, chmod veya lock inode'u yeniden yaratma önerisi değildir.

Tamamlanmış/yarım backup, orphan key, interrupted stage ve `upgrade-*.sqlite3` gölge yükseltme dosyaları (journal dahil) otomatik silinmez. Temizleme ve saklama kullanıcının açık yerel yönetimine aittir. Süreç kesintisi testleri fiziksel güç kesintisi/disk firmware garantisi değildir.

Cache/clock şema geçişinde snapshot/manifest ve tam payload/index tutarlılığı doğrulanır; yanlış projection/group/key veya bozuk payload cache miss diye gizlenmez. Reset cache'i temizler, clock alanını yeni identity epoch'a bağlar; kimlik geçmişini silmez. Önceki runtime'ın tamamlanmış eski stage/live restore çifti, kaynak backup kayıpken de intent'in aynı epoch/K'sı korunarak yeni şemaya yükseltilir. Yükseltme ayrı, private no-clobber `upgrade-*.sqlite3` kopyasında tamamlanıp doğrulanır ve sync edilir; ardından tamamlanmış stage/live yerine atomik yayımlanıp dosya/dizin sync edilir. İkinci bir kesinti yayına kadar özgün çifti korur; başarısız gölge ve journal otomatik kaynak sayılmaz. Önizleme gölgeyi açıp journal recovery yapmaz. Tam hedef sürüm ve kalıcılık tamamlanmadan intent kaldırılmaz. Plan/onay tüketicileri ve bakım preview v2 de uygulanmıştır; aşağıdaki bölüm güncel şema/sayaç sınırını verir. Cache temizliği plan/onay geçmişini silmez.


## Execution planı tüketicisi

P01-3 adım 2 migration2→3 ile execution_plans ekler; [exact plan/bakım sözleşmesi](execution-plan.md#state-ve-bakım). MaintenancePreview schema_version=2 ve cache_invalidated=true alanlarını, current/source özetinde plan_count ve plan_fingerprint'i taşır. Plan değişimi digest'i değiştirir; cache/clock-only güncelleme değiştirmez. Reset geçmiş planları tutup epoch ile etkisizleştirir; restore geçmiş kaybını açık gösterir. Migration3→4 gerçek approval tüketicisini, plan FK/cascade bağını ve preview v2 approval sayısı/fingerprint'ini ekler; exact sözleşme execution referansındadır. Operation/unknown runtime kapısı açılmadı.
