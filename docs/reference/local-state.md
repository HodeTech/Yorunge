# Yerel state kullanım sözleşmesi

**Durum:** P01-4a temeli iki review turuyla doğrulandı; kimlik gözlemi uygulandı; reset/restore adımının kabulü sürüyor. **Tarih:** 2026-10-27. Tasarım nedeni ve kanonik dayanıklılık/migration kuralları [ADR-0011](../decisions/0011-state-foundation-and-migrations.md), key yaşam döngüsü [ADR-0012](../decisions/0012-credential-identity-and-change-detection.md) içindedir.

## Açık oluşturma ve doğrulama

`yorunge state init [--state-dir PATH]` ile Python `yorunge.api.initialize_state(*, state_dir: Path | None = None)` aynı kullanım senaryosudur. Varsayılan macOS/Linux yerel disk yolu `~/.local/state/yorunge`; DB `state.sqlite3` dosyasıdır. `XDG_STATE_HOME` veya başka davranış env override'ı okunmaz. CLI'da `--state-dir` yalnız `state` ailesinde, `state` ile `init` arasında veya `init` sonrasında verilir. Config/profil/proje seçenekleri bu işte geçersizdir.

İlk açık kullanımda private store, karşılaştırma K'sı ve gerçek şema kurulur. Var olan sağlıklı store'da aynı store/epoch döner; bu çağrı kimlik reset'i veya env çözümleme değildir. Sonuç `Result[StateInfo]`: zarf sürümü 1; data `schema_version=1`, gerçek DB `store_schema_version`, `store_id`, `identity_epoch`. K, key-check ve özel verifier sonuçta yoktur. `state init` mevcut store için tam yapısal/ilişkisel/mantıksal doğrulama yapar.

Metadata/help/version, context, capability, offline Plan ve env credential kontrolü bu store'u açmaz/yaratmaz. State sınıfları explicit kullanımda lazy yüklenir. İlk store yalnız metadata, migration geçmişi ve credential binding tablolarını içerir; operation/lease/jobs yoktur. SQL/key dosyalarının sahipliği/izinleri denetlenir; mevcut kullanıcı dosyası chmod/overwrite edilerek benimsenmez.

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

Restore yalnız tamamlanmış `purpose=migration` backup'ında ve **mevcut runtime yalnız identity tabloları içeriyorsa** açılır. Operation tablosu eklenen runtime, eski/boş snapshot veya eksik hedefte dahi `state_restore_unsupported` verir. Restore snapshot sonrası geçmişi kaybedebilir; önizleme ve Result uyarısı bunu açıkça gösterir. Sağlıklı canlı DB varsa `purpose=pre_restore` güvenlik snapshot'ı korunur; bu güvenlik kopyası genel restore girdisi değildir. Eksik hedefe restore desteklenir. Bozuk/yabancı/partial hedefin üzerine yazılmaz.

Ortak exclusive `store.lock` boyunca yeni K, özel `restore-intent.json`, özel stage kopyası ve yeni epoch/key-check kalıcılaştırılır; stage doğrulanmadan canlıya geçilmez. Intent varken normal açılış `state_repair_required` olur. Açık recover aynı ilan edilmiş epoch/K ile tamamlar; yeni kimlik alanını her denemede yeniden üretmez. Tam yeni canlı/stage çifti doğrulanıyorsa kaynak backup'a yeniden erişmek gerekmez. Eksik/yanlış yeni K veya belirsiz canlı dosyada intent korunur. Intent'e ait yarım stage yalnız açık recover sırasında özel `interrupted-*.sqlite3` adına alınarak korunabilir ve pinlenmiş sağlam kaynaktan yeniden kurulur. Eski canlı DB veya kullanıcı dosyası bu yolla karantinaya alınmaz.

Önizleme DB/key/lock yaratmaz, migration veya hot-journal recovery başlatmaz; mevcut journal varsa açık normal `state init` ile SQLite'ın kendi recovery'si veya inceleme gerekir. Eksik/bozuk bakım kilidi, belirsiz partial bootstrap veya bozuk canlı DB otomatik sahiplenilmez. Böyle durumda eski dizini olduğu gibi koruyun; yeni açık `--state-dir` ile init veya bilinen sağlam migration backup'ından restore kullanın. Yeni dizin kimlik geçmişini kurtardığı anlamına gelmez. Bu koruma sınırı elle journal silme, chmod veya lock inode'u yeniden yaratma önerisi değildir.

Tamamlanmış/yarım backup, orphan key ve interrupted stage dosyaları otomatik silinmez. Temizleme ve saklama kullanıcının açık yerel yönetimine aittir. Süreç kesintisi testleri fiziksel güç kesintisi/disk firmware garantisi değildir.
