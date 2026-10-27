# Yerel state kullanım sözleşmesi

**Durum:** P01-4a temeli iki review turuyla doğrulandı; kimlik gözlemi/reset/restore sonraki adımlardır. **Tarih:** 2026-10-27. Tasarım nedeni ve kanonik dayanıklılık/migration kuralları [ADR-0011](../decisions/0011-state-foundation-and-migrations.md), key yaşam döngüsü [ADR-0012](../decisions/0012-credential-identity-and-change-detection.md) içindedir.

## Açık oluşturma ve doğrulama

`yorunge state init [--state-dir PATH]` ile Python `yorunge.api.initialize_state(*, state_dir: Path | None = None)` aynı kullanım senaryosudur. Varsayılan macOS/Linux yerel disk yolu `~/.local/state/yorunge`; DB `state.sqlite3` dosyasıdır. `XDG_STATE_HOME` veya başka davranış env override'ı okunmaz. CLI'da `--state-dir` yalnız `state` ailesinde, `state` ile `init` arasında veya `init` sonrasında verilir. Config/profil/proje seçenekleri bu işte geçersizdir.

İlk açık kullanımda private store, karşılaştırma K'sı ve gerçek şema kurulur. Var olan sağlıklı store'da aynı store/epoch döner; bu çağrı kimlik reset'i veya env çözümleme değildir. Sonuç `Result[StateInfo]`: zarf sürümü 1; data `schema_version=1`, gerçek DB `store_schema_version`, `store_id`, `identity_epoch`. K, key-check ve özel verifier sonuçta yoktur. `state init` mevcut store için tam yapısal/ilişkisel/mantıksal doğrulama yapar.

Metadata/help/version, context, capability, offline Plan ve env credential kontrolü bu store'u açmaz/yaratmaz. State sınıfları explicit kullanımda lazy yüklenir. İlk store yalnız metadata, migration geçmişi ve credential binding tablolarını içerir; operation/lease/jobs yoktur. SQL/key dosyalarının sahipliği/izinleri denetlenir; mevcut kullanıcı dosyası chmod/overwrite edilerek benimsenmez.

## Hata ve süre

Kararlı `state_invalid`, `state_busy`, `state_repair_required`, `state_write_failed`, `state_unsupported` kodları çıkış 2'dir. Hata zarfı path, ham SQLite hatası, K veya özel verifier taşımaz. `state_busy` otomatik bütün kullanım senaryosu tekrarı değildir. Yerel karşılaştırma anahtarı sorunu EVREN auth hatası diye raporlanmaz.

SQLite'ın FULL ve IOERR (genişletilmiş alt kodlar dahil) aileleri disk/I/O için `state_write_failed` olur; bozuk şema diye sınıflanmaz. BUSY/LOCKED/INTERRUPT bütçe/kilit sınıfında kalır; bozuk/yabancı şema `state_invalid` olur.

SQLite/file lock beklemesi en çok 1 saniyedir; bu kullanım senaryosunun varsayılan toplam bütçesi 5 saniyedir. SQLite progress ve backup/hash adımları bütçeyi denetler. İşletim sistemi disk I/O'su, fsync veya scheduler gecikmesi için katı 5 saniye duvar saati garantisi verilmez. Süre dolduysa yarım sonucu başarı sayma veya yeni kimlik oluşturmak için otomatik yeniden başlama yoktur.

Eksik/bozuk key, partial bootstrap, yabancı/bozuk/ileri şema ve restore intent normal açılışta otomatik onarılmaz. Mevcut dosyalar korunur. Açık reset/restore/onarım komutları bu adımda henüz yoktur; ilgili P01-2b adımında aynı sözleşmeye eklenecek.

## Snapshot sınırı

Migration'ın her adımı öncesi exclusive bakım kilidi altında yeni no-clobber snapshot alınır; uzun backup/hash SQL write transaction'ı dışında kalır. Dosya/dizin kalıcılığı ve tam doğrulamadan sonra `complete.json` oluşur; kısmi dizin restore girdisi değildir. Tamamlanan yedek otomatik silinmez. Yedek doğrulama snapshot'ı readonly/immutable SQLite bağlantısıyla okur; yeni journal veya recovery başlatmaz.

Adım başına atomiklik vardır: 1→2 başarılı, 2→3 başarısızsa 2 kalır. İki migration yazarı aynı adımı tekrar uygulamaz. `user_version`, kesintisiz manifest/checksum, şema tanımı ve UTC kayıtları denetlenir. `integrity_check` yanında `foreign_key_check` ve uygulama değişmezleri gerekir. SQLite'ın kendi hot-journal recovery'si normal yazmalı açılışın parçasıdır; süreç kesintisi testi güç kesintisi testi değildir.
