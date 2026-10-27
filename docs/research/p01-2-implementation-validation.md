# P01-2 uygulama ve kabul kaydı

**Tarih:** 2026-10-27. **Durum:** Uygulama başladı; kabul tamamlanmadı. **Dal:** `feat/p01-2-identity-context`, ilk uygulama tabanı `d96b65e`; development tabanı `83bcd83`. Tek PR kullanıcı review'sine sunulacak; merge/yayın bu kayıtla yapılmaz.

## Belge incelemesi ve plan

Kullanıcı bütün P01-2'yi ve her adım için commit → iki ayrı yeni ajan review turu → doğrulanmış bulguları düzelt/commit akışını yetkilendirdi. Accepted ADR-0011/0012 ve binding v1 korunur. Yeni ADR gerektiren doğrulanmış karar açığı yoktur; rutin CLI/API isimleri ilgili reference içinde uygulamayla birlikte kesinleştirilir.

Root ve iki bağımsız salt okuma ajanı (`p012_document_audit`, `p012_surface_audit`; GPT-6.1 Sol/high) scope/matris, standartlar, architecture/execution/state, identity modülü, config/CLI/capability/binding, ADR'ler, araştırma ve dört iş kartını mevcut kodla karşılaştırdı. Config belgesinin boş query/fragment anlatımı düzeltildi; eski parser/Plan biçimi değiştirilmez. Guarded secret, seçili env'yi bir kez okuma, ortak bakım kilidi, no-clobber backup, reset/restore ayrımı ve default doctor'ın yan etkisizliği özel kabul noktalarıdır.

| Adım | Teslim | Durum |
|---|---|---|
| 1 | P01-2a — env/taşıyıcı/hedef kapısı | İki yeni review turuyla verified |
| 2 | P01-4a — store/migration/backup/key temeli | İki yeni review turuyla verified |
| 3 | P01-2b — kalıcı kimlik/nesil | İki review turuyla tamamlandı |
| 4 | P01-2b — reset/identity-only restore | Başladı |
| 5 | P01-2c — init/profil/proje/doctor | Önceki kabul bekleniyor |

Her adımın gerçek commit/test/review bulgusu burada kaydedilecek. Tasarım/probe sonucu ürün kabulü sayılmaz. Son kapanışta tam offline suite, lint/type/belge, wheel/sdist iki temiz kurulum, en az 30 süreç başlangıç bütçesi ve son PR head CI kanıtı gerekir. HTTP/cache/operation/uzak kimlik bu paketin teslimi değildir.

Başlangıç doğrulaması: temiz `d96b65e` üzerinde `.venv/bin/pytest -q` → **404 geçti** (3,84 s); `git fetch` sonrası development ile fark 0 geri / 3 hazırlık commit'i ileri. Kullanıcı dosyası/değişikliği bulunmadı.

## Adım 1 — İlk uygulama

Hizmet/ref/immutable gözlem taşıyıcısı ve tek seçili env okuma; strict UTF-8 1–16.384 bayt; saf `service-target-v1` normalleştirme; `api.check_credential` ve `context credential --service` sonucu eklendi. Secret public zarf/JSON'a girmez; açık kontrol hesap/yetki doğrulaması değildir. Eski Profile/Plan parser ve digest üreticisi değiştirilmedi. Subprocess guard varsayılan yollarda credential env okumalarını da reddeder; yalnız açık credential fixture modu izin verir, ağ/DB yasakları korunur.

İlk doğrulama: **460 test geçti** (4,97 s), Ruff format/lint, strict mypy (20 kaynak), 95 belge ve 6 skill/5 kart denetimi geçti. Wheel (20 üye) ve sdist (147 üye) iki ayrı temiz kurulum/köken/smoke kontrolünden geçti. 30 ayrı süreç başlangıç ölçümünün üç bütçesi de geçti; bu ölçüm güç kesintisi veya canlı auth kanıtı değildir. İki yeni review turu tamamlanmadan kart `verified` yapılmaz.

İlk ürün commit'i `41c7dba`. Başlangıç sıcak p95: help 28,196 ms / version 27,717 ms / context 97,353 ms; hedefler 500/500/200 ms (CPython 3.11.18, macOS arm64; komut başına 30 ayrı süreç).

### Adım 1 / review 1

Üç yeni bağımsız ajan (GPT-6.1 Sol/high): `p012_s1_r1_secrets` (tek okuma/taşıyıcı/sızıntı), `p012_s1_r1_target` (URL sözleşmesi/eski Plan), `p012_s1_r1_surface` (CLI/API/guard/belge). Kök ajan üç P2'yi yeniden üretti: bracketed IPvFuture'ın DNS'e çevrilmesi, Unicode Kelvin host'un parser lowercase ile ASCII'ye dönüşmesi ve `object.__getstate__` yolunda ham slotted secret açılması. Authority'nin özgün ASCII kontrolü, parantezli host'un zorunlu IPv6 doğrulaması ve güvenli `__getstate__` ile giderildi; secret okunmadan ret ve serialization regresyonları eklendi.

Guard'ın iki sabit env adıyla sınırlı kanıtı ürün kusuru sayılmadı; test yapılandırmasından özel env adları ve `os.environb` de kapsandı. Diğer doğrulanmış ürün bulgusu yok. Düzeltme sonrası **466 test**, Ruff format/lint ve strict mypy geçti. İkinci tur yeni ajanlarla bu head üzerinde yapılır.

### Adım 1 / review 2 ve kapanış

İncelenen head `b319001`. Yeni ajanlar: `p012_s1_r2_security` (GPT-6 Astra/high), `p012_s1_r2_target`, `p012_s1_r2_delivery` (GPT-6.1 Sol/high). İlk turdaki üç düzeltme doğrulandı; yeni doğrulanmış bulgu yok. Security reviewer altı serialization yolu ve 332 sentetik hedef/karakter örneğini; target reviewer 2.981 kabul edilen URL'de idempotence ve 15 ek bozuk girdiyi; delivery reviewer tam 466 test, lint/type/belge/ajan, yeniden build ve iki temiz kurulumu doğruladı.

Final adım head'inde wheel 20 üye (`9ef6ff0f0bfe9f6a7283da44e908562e1f2c56ea4d4e06d0a4202c36fc44a084`), sdist 147 üye (`86d4bf3f28082e674602b0bd225cfdcfefed5c178553b401b70d9990411e698d`) ve iki köken/smoke başarılı. [Ham başlangıç ölçümü](p01-2-step-1-startup.json): 30 ayrı süreç sıcak p95 help 79,622 / version 60,863 / context 105,469 ms; build ile eşzamanlı yükte de bütçeler geçti. OS cache'i boşaltılmadı. P01-2a kapanmıştır; P01-2 bütünü tamamlanmadı.

## Adım 2 — İlk uygulama

Özel dosya/dizin ve üst dizin sync zinciri, bounded shared/exclusive bakım kilidi, stdlib SQLite DELETE/EXTRA/fullfsync, üç gerçek tablo ve sıralı checksummed SQL manifesti eklendi. Bootstrap K/key-check'i DB pointer'ından önce kalıcılaştırır; mevcut eksik/bozuk K yeniden oluşturulmaz. Migration her adımda exclusive bakım altında kalıcı no-clobber snapshot alır; backup/hash SQL write transaction'ı dışındadır. Tamamlanma kaydı/snapshot doğrulaması readonly/immutable yapılır. Restore intent normal açılışı engeller; reset/restore/partial bootstrap repair sonraki adımdır. Public `initialize_state` / `state init --state-dir` aynı sır içermeyen sonucu verir, mevcut offline komutlar state açmaz.

İlk doğrulama: **39 state integration testi**, **505 toplam test** geçti (6,58 s); Ruff format/lint, strict mypy (24 kaynak), 96 belge ve 6 skill/5 kart denetimi geçti. İki ayrı migration süreci, iki adımlı hata/yeniden açılış, gerçek hot journal ve commit öncesi/sonrası süreç kesintisi, FK bozulması, izin/symlink, disk/sync ve bozuk backup negatifleri gerçek geçici dosyalarla kapsandı. Bu süreç kesintileri güç kesintisi kanıtı değildir.

İlk wheel 24 üye (`5515aaca3fb05d3d7052fd8802afb57313dfc23d9315f8711e7d467336327758`), sdist 154 üye (`6f67d4a644b6ea0e7392c8060e0948fde19efaa03b8ae757d221b9d584987a76`); iki temiz kurulum/köken/smoke ve 30 süreç başlangıç bütçeleri geçti. İki bağımsız review turu tamamlanmadan P01-4a verified değildir.

### Adım 2 / review 1

İncelenen ilk head `0b668ed`. Üç yeni ajan: `p012_s2_r1_files` (GPT-6 Astra/high), `p012_s2_r1_sql`, `p012_s2_r1_surface` (GPT-6.1 Sol/high). Kök ajan üç P2 ve bir P3'ü geçici gerçek dosyalarda yeniden üretti: deadline kontrolünde lock FD sızıntısı; `LIKE 'sqlite_%'` jokeri nedeniyle atlanan kullanıcı şema nesneleri; aktif key bağını bozan migration'ın hata vermeden önce commit edilmesi; filesystem'e kodlanamayan Unicode Path'in ham istisnası. FD'nin immediate try/finally sahibi, literal reserved-prefix filtresi, commit öncesi key-check ve upfront filesystem encoding denetimiyle giderildi.

Kabul kanıtındaki bootstrap/sync boşluğu da kapatıldı: **22 bootstrap sınırı × süreç çıkışı/I/O hatası = 44 ayrı subprocess senaryosu**; root/üst dizin, lock, keys/üst dizin, key file/fsync/fullsync, DB dosyası ve metadata/commit/final sync kapsandı. Kesilmiş kilit oluşturma sonrası aynı inode'un bariyeri yeniden tamamlanır. Ayrıca backup tamamlanma kaydının öncesi/sonrası süreç kesintisi, backup üst dizin sync hatası, key symlink/hardlink ve varsayılan/Unicode state path testleri eklendi. Bu deneyler güç kesintisi veya disk donanımı kanıtı değildir.

Düzeltme sonrası **96 state / 562 toplam test geçti** (11,63 s); Ruff format/lint ve strict mypy geçti. İlk head'in bağımsız yüzey incelemesinde API/CLI zarfı ve forbidden-option reddi, on kez iki eşzamanlı ilk bootstrap ve paket hash/üye eşleşmeleri doğrulandı. İkinci tur yeni ajanlarla düzeltme head'inde yapılır.

### Adım 2 / review 2

İncelenen head `494799b`. Yeni ajanlar: `p012_s2_r2_durability` (GPT-6 Astra/high), `p012_s2_r2_sql`, `p012_s2_r2_delivery` (GPT-6.1 Sol/high). R1 düzeltmeleri doğrulandı. Dosya reviewer'ı 20 bariyerli eşzamanlı iki-süreç bootstrap ve nested parent sync hatası sonrası yeniden bariyer probe'unu; delivery reviewer'ı 96 state testi, belge/ajan, iki temiz kurulum ve başlangıç bütçelerini bağımsız doğruladı.

Tek yeni P2: gerçek SQLite FULL kodu 13, yanlışlıkla bozuk state diye sınıflanıyordu; kök ajan gerçek max_page_count sınırıyla yeniden üretti. FULL/IOERR ve genişletilmiş alt kodlar persistence hata sınıfına taşındı; gerçek SQLite FULL rollback/backup ve iki IOERR hata sınırı testi eklendi. Eşzamanlı ilk bootstrap kalıcı, iki child'ın bariyerde buluşup aynı UUID/epoch sonucu verdiği test olarak da eklendi. Kapanış doğrulaması ve bu dar düzeltmenin odak kontrolü bekleniyor.

### Adım 2 kapanışı

Düzeltme head'i `93c4de4`: kök ajan **100 state / 566 toplam test**, format/lint/type/belge/ajan denetimlerini geçti. Bulgu sahibi yeni head'de odak kontrolü yaptı; 12 ilgili test ve 11 hata eşleme örneğiyle FULL/IOERR fix'i ve diğer hata sınıfları doğrulandı, yeni bulgu yok. İki tam tur ve doğrulanmış bulguların kapanışı tamamlandı.

Son kaynaklardan wheel 24 üye (`b2f90c1111b08ae5e52362d46becb0db40333a6afa06e4b6d2f0bc68ff4d4f8b`), sdist 155 üye (`30415c7109982d56e0b9ead037e068d101d5a920431d08167d1217d240676f05`); iki ayrı temiz kurulum/köken/smoke geçti. [Ham başlangıç ölçümü](p01-2-step-2-startup.json): 30 süreç sıcak p95 help 22,318 / version 22,866 / context 84,391 ms; üç bütçe geçti. Bu adım macOS/arm64 üzerinde doğrulandı; Linux ve son PR CI bütünleşik kapanıştadır. P01-4a verified; sonraki adım P01-2b gözlemidir.

## Adım 3 — İlk uygulama

Altı alanın tam kanonik binding'i, onaylı uzunluk çerçevesiyle HMAC-SHA-256, constant-time karşılaştırma ve BEGIN IMMEDIATE altında opak UUID/nesil kaydı eklendi. Aynı değer zaman/satır değiştirmez; gözlenen değişim aynı UUID'nin neslini bir artırır, taşma kontrollü ret olur. `BoundCredential` aynı immutable context/target/secret snapshot'ını kimliğe bağlar; env yeniden okunmaz. `observe_credential` / `context identity` public sonucu sır/reference adı/tag içermez, uzak doğrulama false kalır. Eski offline Plan biçimi/digest'i değişmedi.

Reset/restore ön incelemesi (GPT-6 Astra/high, `p012_recovery_protocol_audit`) mevcut ADR'lerle uygulanabilir sınırları doğruladı; yeni kullanıcı kararı gerekmiyor. Eksik lock ile geride key kalan partial store'un lock'u yeniden yarattığı doğrulandı; payload varsa ilk lock oluşturma da fail-closed yapıldı, DB var/yok regresyonları eklendi.

İlk kabul: **583 test geçti** (13,52 s), Ruff format/lint, strict mypy (25 kaynak), 96 belge ve 6 skill/5 kart denetimi geçti. Tam iki bağımsız HMAC byte vektörü, rotation/taşma/tek okuma, altı eşzamanlı gerçek child süreçte aynı nesil, farklı değerlerin işlemsel sıralanması ve API/CLI negatifleri kapsandı. İki temiz kurulum: wheel 25 üye (`a5d937dc9171552f3325f86e43fb85d7f045b32f2e87a2c5321c3fc99fa52f34`), sdist 158 üye (`34afb059e2040fe5325625f64ff4d5e9faa34aa825c53e26dcc6a3ca177a62f8`). [30 süreç ölçümü](p01-2-step-3-startup.json): sıcak p95 help 33,113 / version 24,735 / context 98,229 ms; bütçeler geçti. İki yeni review turu bekleniyor; P01-2b reset/restore olmadan kapanmaz.

### Adım 3 / review 1

İlk head `ad54dc6`; üç yeni ajan: `p012_s3_r1_security` (GPT-6 Astra/high), `p012_s3_r1_transactions`, `p012_s3_r1_delivery` (GPT-6.1 Sol/high). Tek P2 doğrulandı: erken `state_directory` kontrolünde erişilemeyen üst dizin ham PermissionError/CLI traceback üretiyordu. Kök ajan yeniden üretti; path kontrolüne ortak OSError dönüşümü ve runtime desteğinin secret öncesi kontrolü eklendi. CLI/API izin ve unsupported-platform regresyonları geçti.

Diğer alanlarda doğrulanmış bulgu yok: security 79 hedefli test; delivery 310 test ve yedi invalid-request probe; transaction reviewer 117 identity/state testi, bozuk satır/rollback probe'ları ve on ayrı eşzamanlı child süreçte tek kimlik/nesil doğruladı. Sonraki tur farklı yeni ajanlarla yapılır.

### Adım 3 / review 2

Head `b66d266`; yeni ajanlar `p012_s3_r2_security` (GPT-6 Astra/high), `p012_s3_r2_sql`, `p012_s3_r2_delivery` (GPT-6.1 Sol/high). İlk izin hatası düzeltmesi doğrulandı. Tek yeni P2: eksik-lock kontrolü ile dizin taraması arasında başka bootstrap tamamlanırsa sağlıklı store yanlış onarım hatası alabiliyordu. Kök ajan kontrollü interleaving ile yeniden üretti; payload görüldüğünde lock'un hâlâ eksik olması şartı eklendi. Deterministik regresyon ve 120 identity/state testi geçti.

Diğer alanlar temiz: security 81 identity/credential + 100 state testi ve serializer/UTF-8 probe'ları; delivery 585 tam test, lint/type/belge/ajan, dokuz invalid API/dört CLI hatası, eski head ile tam Plan byte/digest eşitliği, geçici build/iki temiz kurulum ve 30 süreç bütçesi geçti. Bu son ölçümün p95'i help 24,697 / version 24,823 / context 117,223 ms. Reset/restore kabulü bundan sonraki adımdır.

Adım 3 kapanışı: `3891479` üzerindeki odak kontrolünde bulgu sahibi yarış/partial lock/migration regresyonlarından beşini geçti, bulgu kapandı. İki bağımsız tur tamamlandı; P01-2b kartı reset/restore tamamlanana kadar in_progress kalır.
