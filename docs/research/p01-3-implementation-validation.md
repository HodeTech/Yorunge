# P01-3 uygulama ve kabul kaydı

**Tarih:** 2026-10-27. **Durum:** Dört adımın yerel kabulü ve ikişer review tamamlandı; development PR/CI teslimi ve kullanıcı incelemesi sürüyor. **Dal:** feat/p01-3-capability-planning; **taban:** development@78d5d77. [Paket planı](../roadmap/p01-3-delivery-plan.md), [iki iş kartı](../roadmap/tasks/README.md).

## Onay ve yöntem

Aşağıdaki adım/koşu kayıtları kronolojiktir. Eski bir adımın “henüz” ifadesi o commit anını anlatır; güncel teslim durumu üstte ve son bütünleşik bölümündedir.

Kullanıcı ADR-0013/0014 ve bağlı ScopeV2 kararlarını onayladı; `6e91690` onay commit'idir. [Ön inceleme ve iki kullanıcı review'inin doğrulanması](p01-3-readiness-review.md) tasarım kanıtıdır; ürün uygulaması yerine sayılmaz. Her adım kod/test/belge → commit → yeni ajanlarla review 1 → doğrulanmış fix/commit → başka yeni ajanlarla review 2 → doğrulanmış fix/commit döngüsünü tamamlar. Sonunda tek development PR'ı kullanıcı incelemesine açılır; otomatik merge yoktur.

## Adım 1 — Açık capability cache ve clock

V1 modelleri ve offline builder değişmeden ayrı kapalı ScopeV2/evidence/record oluşturuldu. Public `query_capabilities` ve CLI `--cached`/`--refresh` aynı use case'i kullanır; arbitrary producer/evidence/authorization girdisi yoktur. Gerçek ürün producer'ı yalnız mevcut yerel politika/not-verified verir. Fixture'daki live-account kanıtı üretim desteği değildir.

SQLite migration 1→2 private store'a cache ve clock tablolarını ekler; eski checksum değişmez. Tam/tek satır validation, canonical key/projection/group, kaynak sürümü, quota/çelişki saklama, son UTC/monotonic süre kapısı ve güncel identity/target kontrolü vardır. Clock generation business rollback'ten bağımsız kalır. Kaynağı kayıp eski restore stage/live çifti aynı intent epoch/K ile yeni şemaya yükseltilir; reset cache'i etkisizleştirir, kimlik geçmişini korur. Unknown operation tüketicili runtime restore'u reddeder.

İlk hedefli scope/cache koşusunda 63 test, daha sonraki tam koşuda 903 test geçti (55,73 s). Foundation state/bakım alt takımı 184 testte başarılıdır. Bunlar Linux, gerçek Windows, canlı EVREN veya fiziksel güç kesintisi kanıtı değildir. Yeni platform kapıları ve son bütünleşik kontroller aşağıda gerçekleşince kaydedilir; review turları henüz tamamlanmadı.

Tarihsel v1 migration fault deneyleri yalnız o testlerde açık identity-only manifest fixture'ına bağlandı; güncel default store/CLI testi şema 2'yi, yeni integration testi gerçek 1→2 geçişini ve doğrulanmış v1 backup'ını denetler. Negatif/rollback kabulü kaldırılmadı. İki süreçli refresh çelişkisi, iki credential/rotation, unknown auth için historical-only sonuç, overflow ve aggregate TTL'den uzun proof saklama, reset/restore, eski intent'in stage yok/stage/live ve kaynak kaybı senaryoları gerçek dosya/DB/süreçlerle sınanır.

### İlk performans kanıtı

[Ham ölçüm](p01-3-step-1-startup.json): macOS 27.0.1 arm64, Apple M5 Max (yerel sysctl), CPython 3.11.18, editable `.venv`, SSD (yerel disk bilgisi). 1.024 gerçek kayıt; toplam payload 1.212.625 bayt, en büyük kayıt 1.233 bayt. Dataset yalnız `tests/fixtures/seed_capability_cache.py` ile sentetik olarak üretildi; public discovery backend'i değildir. Benchmark her komutta ilk süreç + üç ısınma + 30 ayrı süreç kullanır; OS/disk cache boşaltılmaz.

İlk sıcak p95 help 34,383 ms, version 23,605 ms, context 79,017 ms ve cache 159,543 ms; 500/200 ms hedefleri geçti. Bu ilk uygulama ölçümüdür; bütün P01 veya gelecek plan/approval bütçesi sayılmaz. Test/ölçüm sıralı koştu; benchmark ile tam suite eşzamanlı yük oluşturmadı. Cache 32 KiB üst sınırında dolu kayıt deneyi değil, kaydedilen hacim için kanıttır.

## Sonraki adımlar

İlk adımın iki fresh review turu ve doğrulanmış düzeltmeleri bitmeden P01-3a verified veya P01-3b ready yapılmaz. Sonra execution hazırlığı/validity, ardından onay/yönetim/bakım ve bütünleşik PR kabulü aynı dalda sürer. Kalıcı plan/onay, run, operation/lease/jobs, HTTP, uzak keşif ve gerçek adaptör bu ilk cache adımında uygulanmış sayılmaz.

### Adım 1 / review 1

İlk ürün commit'i `a3287b0`. Üç yeni ajan state/saat (GPT-6 Astra/high), evidence/scope ve CLI/API/teslim (GPT-6.1 Sol/high) boyutlarını bağımsız inceledi. Ortak bulgular tekilleştirildi ve gerçek SQLite/public API ile doğrulandı:

- Son transaction örneği kayıt TTL'sini denetlemiyordu: commit öncesi TimeGate eklendi; tam expiry'de business yazımı rollback olur, gözlenen clock invalidation kalır.
- Clock COMMIT gecikmesi ve sonraki kayıt sorgusu önceki sonucu eskitebiliyordu: commit sonrası gözlenen saat kalıcılaştırılır; tüm public kayıtlar ortak son snapshot ile yeniden değerlendirilir. Kilit bekledikten sonraki UTC örneği kullanılır; eşzamanlı süreçlerin eski örneği sahte rollback üretmez.
- Bazı yerel nedenlerin insan açıklaması genelleşiyordu: proje/runtime/uyumsuzluk/araç açıklamaları tamamlandı.
- DB decoder duplicate key'i zaten reddediyordu; doğrudan v2 model JSON parser'ı reddetmiyordu: yalnız yeni WireModel sınırına recursive duplicate/nonfinite/UTF-8 kontrolü eklendi. V1 parser değişmedi.

Regresyonlar son transaction örneğini, COMMIT sonrası expiry/rollback'i ve iki kayıt arasında expiry/rollback'i doğrudan tetikler; tüm sonuçlar unknown'a düşer ve clock fence kalır. Eksik proje CLI açıklaması ve üst/iç JSON duplicate ayrıca sınanır. İlk yeni koşu iki süreç testinde kilit öncesi alınan UTC örneğinin yanlış fence üretmesini yakaladı; örnek kilit sonrasına taşındı, kabul/eşik gevşetilmedi.

Temiz kurulum smoke'u macOS `/var` symlink'ini güvenli state kökü olarak reddetti; denetim scratch konumunu kanonik fiziksel yola bağladı. Wheel/sdist iki temiz ortamda gerçek kurulu CLI/import ve refresh→cached smoke'u geçti; bunlar review düzeltmelerinin ara build kanıtıdır, final paket yerine sayılmaz.

### Adım 1 / review 2

Üç farklı yeni ajan invariants/state/saat (GPT-6 Astra/high), trust/scope ve CLI/teslim (GPT-6.1 Sol/high) incelemesini `cd8e812` üzerinde tamamladı. Trust ve teslimde doğrulanmış yeni bulgu yok: sırasıyla 77 ve 565 hedefli test; parser ve gerçek SQLite overflow/kota probları başarılı. State/saat ajanı producer başlangıcındaki UTC örneğinin sonradan üzerine yazılması nedeniyle gözlenen ileri→geri dönüşün ret/restart sonrasında eski supported'ı canlandırmasını doğruladı. Ara gözlemlerin high-watermark ve gereken nesil bağı kayıpsız tutuldu; producer öncesi/başarı/hata sonrası kısa kalıcı saat kapıları eklendi. İki sıçrama yönü, producer hatası ve restart; ayrıca tick öncesi üzerine yazılan örnek yeni regresyonlardır. Düzeltme sonrası cache integration 29 test ve strict lint/type başarılıdır. `cd8e812` tam suite sonucu 926 testtir (77,59 s); son düzeltmenin final kontrolleri ayrıca kaydedilir.


### Adım 1 kapanışı — 2026-10-28

Round2 saat bulgusu aynı reviewer'ın dört gerçek SQLite başarı/hata probuyla yeniden doğrulandı: ret, unknown, kalıcı generation2 ve restart miss; bulgu kapandı. Çok kayıtlı okuma tek transaction ve ortak son snapshot'a toplandı; iki kayıt arasındaki saat değişimi regresyonu gerçek `_read` sınırında sürer.

Son tam takım **929 passed (60,14 s)**; Ruff format/lint, strict mypy 34 kaynak, 104 belge/0 sorun ve altı skill/yedi kart/0 sorun geçti. Wheel34/sdist197 üyeli build ve iki temiz kurulu import/CLI/refresh→cached smoke başarılıdır; son paket bütün epik sonunda yeniden üretilir.

[Clock kapıları sonrası ilk ölçüm](p01-3-step-1-clock-gate-startup.json) cache p95 223,335 ms ile 200 ms bütçesini **geçemedi**. Profiling, her kayıt için ayrı clock commit'lerini gösterdi. İşlem/süre/güven kapıları kaldırılmadan çoklu okuma ortak transaction'a alındı. [Son ölçüm](p01-3-step-1-final-startup.json): aynı CPU/SSD/editable kurulumda 1.024 kayıt, toplam payload 1.212.625 bayt; 30 ayrı süreçte p95 help23,565, version25,217, context91,039 ve cache157,082 ms. Her örnek gerçek fresh hit olduğunu doğrular. Eşik gevşetilmedi; başarısız ham kayıt da tutuldu.

P01-3a kendi kabulüyle verified; P01-3b adım 2 başladı. Cache temizliğinin gerçek plan/onayları koruması P01-3b/bütünleşik kabulde ayrıca tamamlanacaktır. Epik ve PR henüz tamamlanmadı.

## Adım 2 — Kalıcı execution hazırlığı ve validity

2026-10-28: Ayrı ExecutionPlan v2 ve immutable digest; prepare/list/show/validate API/CLI, trusted validation portu ve ürünün açık blocked politikası uygulandı. SQLite2→3 gerçek plan tüketicisi, bounded cursor listesi, 1.024 plan/64KiB/128 input limiti, plan-aware preview v2 ve restore/reset full validation eklendi. API yalnız composition yapar; güncel validation uygulama katmanında, dosya/SQL adaptörleri tipli portların arkasındadır. Cache ile ortak tam scope builder kullanılır; v1 modelleri değişmedi.

Descriptor walk her root/ara/son bileşende no-follow kullanır; FIFO okunmaz. Önce/sonra stat ve zincir kimliği, içerik hash'i, root anchor/inode, CWD değişimi ve byte-identical root değişimi sınanır. 16MiB/256MiB/1GiB sparse sentetik dosyada tam okuma ve Python allocation peak<8MiB testi geçti; gerçek model/data closure veya fiziksel I/O garantisi değildir. 1GiB+ ve toplam30s retleri, hash sırasında root/içerik değişimi, path traversal ve descriptor kapanışı testlidir.

İlk execution/input alt takımı37 test geçti. İlk tam takım965 başarılı/1 başarısızdı: yeni execution_plans tablosu eski exact şema assertion'ında yoktu; assertion gerçek şemayla güncellendi. Sonraki execution/input/state/platform alt takımı253 testte başarılı; mypy38 kaynak ve Ruff geçti. Yeni komutlarda üç platform/fcntl senaryosu gerçek ayrı süreçte simüle edilir; gerçek Windows koşusu değildir. İki review turu henüz başlamadan bu kanıt ürün kapanışı sayılmaz. Approval/revoke/forget sonraki adımdadır.

### Adım 2 / review 1

İlk execution commit'i `57fe22c`; son tam takım bu head'de **991 passed (101,62 s)**. Üç yeni reviewer input/TOCTOU (GPT-6 Astra/high), validity/scope ve CLI/state/teslim (GPT-6.1 Sol/high) inceledi. Teslim reviewer'ında yeni bulgu yok;247 hedefli test, gerçek public CLI smoke ve schema2 legacy intent/stage/live-source-lost recovery probları geçti.

İki doğrulanmış P2 giderildi: producer proof account/project ve görev için gerekli service namespace'i istekle karşılaştırılmıyordu (remote→local proof ile prepared mümkün); ortak pure scope invariant hem fresh admission'a hem persisted body'ye eklendi. Eksik/yanlış remote namespace, hesap/proje/hedef ve yalnız planning.offline kanıtı preparation sağlayamaz. İkinci bulgu ilk root/dup-root fstat hatasında FD sızıntısıydı; metadata işlemleri cleanup kapsamına alındı. Her iki noktaya gerçek descriptor/EIO enjeksiyonu artık bütün FD'lerin kapandığını doğrular.

Düzeltme sonrası input/execution **45 passed (10,50 s)**; Ruff ve strict mypy38 kaynak başarılı. Bu turdaki fixture pozitifliği public uzak destek veya execution değildir. İkinci fresh review turu kapanmadan adım3'e geçilmez.

### Adım 2 / review 2 ve kapanışı

Üç farklı yeni reviewer time/scope (GPT-6 Astra/high), input/state ve public sözleşme (GPT-6.1 Sol/high) `6d68120` üzerinde inceledi. Public reviewer308 test ve11 görevin draft/blocked kaldığı CLI/API problarında yeni bulgu bulmadı. Input/state reviewer155 test;71 ayrı FD I/O enjeksiyonu,21 body/corruption ret yolu ve schema2 legacy intent/stage/live-source-lost→3 recovery problarında yeni bulgu bulmadı.

Bir P2 son clock commit'inden sonra UTC'nin tekrar örneklenmemesiydi. Durable clock noktası ile terminal geçerlilik noktası ayrıldı: tüm DB işleri sonrası UTC/monotonic örneği kullanılır. Yeni geçilen expiry sınırı kalıcılaştırılıp tekrar örneklenir; döngü sınır sayısıyla sınırlıdır, producer/env/discovery tekrar çağrılmaz. Gerileme kalıcı generation fence ile geçersiz kalır. Ortak cache okuyucusu aynı kapıyı kullanır. Prepare/validate ve fresh assessment, gerçek expiry'lerini bu kapıya verir.

Son cache+execution **54 passed (16,16 s)**, lint/type38 kaynak ve105 belge denetimi geçti. Aynı reviewer orijinal COMMIT+0,3s probunu yeniden çalıştırdı: expiry öncesi gerçek terminal nokta geçerli, expiry'yi geçen varyant false; ileri/geri iki regresyon da geçti. Bulgu kapandı. Adım2 tamamlandı; P01-3b in_progress olarak adım3 onay/yönetim/bütün bakım kabulüne otomatik ilerler. Final tam suite/build/performans bütünleşik adımda güncel head üzerinde yapılır.

## Adım 3 — Açık onay, revoke/forget ve bakım v2

2026-10-28: Güncel validation ardından tam digest onayı; ayrı immutable-bound approval kaydı/schema3→4; idempotent onay, revoke ve seçili atomik forget uygulandı. Onay kaydı insan kimliği/dispatch bileti değildir. Public producer blocked kaldığı için public doğru digest de plan_not_valid verir; pozitif akış yalnız test portundadır. Eksik/yanlış digest çıkış4, geçersiz plan2; post-commit geçersiz kaydın varlığı text/JSON details ile açık gösterilir.

Plan, güncel onay ve credential bağları final transaction/çıktı kapısında tekrar okunur. Aynı onay dahi son UTC/mono kapısını atlayamaz; yeni daha kısa producer süresi effective valid_until'u kısaltır. Plan/onay expiry'si terminal clock watermark'a dahildir. Saat anomalisi sırasında revocation yapılabilir. Forget onayın önceki durumunu pinlemez; seçili plan ve transaction anındaki current approval FK/cascade ile birlikte silinir. Gelecek operation tüketicisine silmeyi sınırlayan FK/transaction sorumluluğu açık devredildi.

İlk onay/cache koşusu60, son genişletilmiş alt takım **63 passed (27,12 s)**; önceki execution/cache/platform alt takımı218 başarılıdır. Ayrı süreçte validation sırasında forget, commit edilmiş approve/revoke sonrası forget; quota dolu→list→forget→prepare; cascade hata/rollback; onay INSERT hata/rollback; idempotent/precommit/clock-COMMIT expiry; secret tek snapshot; reset/restore/clock invalidation ve bozuk approval epoch reddi testlidir. Cache quota/expiry temizliği gerçek plan/onay geçmişini korur. Schema1/2/3 eski runtime intent/stage/live kesintilerinin dokuzu yeni4'e kurtarılır; tamamlanmış pair kaynak kaybında ve schema3 tarihsel plan gövdesiyle ayrıca doğrulanır.

Ruff format/lint, strict mypy38 kaynak,105 belge ve altı skill/yedi kart denetimi başarılıdır. İlk commit ardından iki fresh review turu beklenir; kart/epik henüz verified değildir. Bütünleşik final build/ölçüm/PR adım4'tedir.

### Adım 3 / review 1

İlk commit `db9ee74`; bu head'de tam takım **1.053 passed (114,96 s)**. Üç yeni reviewer approval/time (GPT-6 Astra/high), state/recovery ve public sözleşme (GPT-6.1 Sol/high) inceledi. Ortak tek P2 doğrulandı: onay commit edildikten sonraki monotonic timeout veya son kontrol hatası kaydın oluştuğunu açıklamıyordu. Başarılı commit'i bilinen noktanın ardından kontrollü hatalar artık plan_not_valid/recorded=true/approval_id ve alttaki reason_code ile güvenli inceleme yolunu bildirir. Adaptör son kontrolün SQLite/OSError sınırını da kontrollü port hatasına çevirir. Bu, kaydın daha sonra etkin olabileceğini sessizce varsaymaz veya otomatik tekrar etmez; yalnız son kontrol tamamlanamadığını açıklar.

Yeni/idempotent kayıt için monotonic timeout, EIO ve SQLite read denial altı regresyonla sınandı. İlk read-denial beklentisi var olan SQLite hata eşlemesinin state_invalid döndürdüğünü gösterdi; eşleme değiştirilmedi, denial ile EIO ayrı sınandı. Son approval takımı **34 passed (14,54 s)**; lint/type ve belge/ajan kontrolleri başarılıdır.

State reviewer20 yarış/cascade/corruption/legacy testinde yeni bulgu bulmadı. Liste index özetinin payload doğrulamadığı gözlemi ADR'nin açık payload okumama kararıyla karşılaştırılıp kod bulgusu olarak alınmadı; referanstaki aşırı geniş “her okumada” ifadesi tam kayıt okuması olarak açıklaştırıldı. İkinci fresh review turu beklenir.


### Adım 3 / review 2 ve kapanışı

Üç farklı yeni reviewer invariants/time (GPT-6 Astra/high), storage/recovery ve public sözleşme (GPT-6.1 Sol/high) `988bbc3` üzerinde inceledi. Invariants reviewer60 test ve yeni/idempotent onayın commit öncesi/sonrası credential rotation dört bağımsız probunda R1 düzeltmesini doğruladı. Public reviewer424 testi (iki kapasite testi seçilmeden), storage reviewer179 integration testi başarıyla koştu. Onay/state/recovery alanında yeni bulgu yok.

Bir P2 bozuk cursor'un UUID eleman türünü kontrol etmeden canonical_uuid'ya iletmesiydi; integer/bool/object/list, public CLI'da traceback üretebiliyordu. Adım2'den mevcut bu kusur ertelenmedi: parse öncesi strict string-pair kapısı ve iki eleman için16 negatif tip + gerçek CLI JSON hata regresyonu eklendi. Düzeltme sonrası plan+approval **77 passed (26,25 s)**; Ruff/strict mypy ve belge denetimi başarılıdır.

Adım3 tamamlandı. Kalıcı cache/plan/onay, seçili yönetim, reset/restore/recover ve bütün public yüzey uygulanmıştır; henüz run/operation/HTTP/gerçek producer yoktur. Adım4 son build/iki temiz kurulum, memory/başlangıç ölçümü, kanonik durum kapanışı ve tek development PR'ına geçilir; kullanıcı review'i için merge yapılmaz.

## Adım 4 — Bütünleşik teslim kabulü

2026-10-28: Tam yerel takım **1.077 passed (111,03 s)**. Ruff format65 dosya, lint, strict mypy38 kaynak,105 public Markdown, altı skill/yedi kart ve diff whitespace kontrolleri başarılıdır. `.venv/bin/python`/import kökeni bu checkout'taki editable src olarak doğrulandı. Ağ/ML import guard'ları, frozen offline v1 golden/digest, yeni stateful API/CLI ve negatif JSON hata yolları aynı takımdadır.

Wheel38/sdist208 üyeli build ve iki ayrı temiz kurulum geçti. Arşiv izin listesi ve kurulu import kökeni; metadata, eski offline plan, refresh→cached ve yeni prepare→list→show→validate→eksik onay4/blocked onay2→revoke→forget→empty list akışı gerçek kurulu console üzerinden sınandı. Onay pozitifliği bu kurulum smoke'unda beklenmez; gerçek ürün producer'ı blocked kalmalıdır. Script artık beklenen negatif çıkışı da doğrular. Bu yerel geliştirme build'idir; paket yayınlanmadı, son PR CI kendi artefaktını yeniden üretir.

Final başlangıç fixture'ında sabit schema2 assertion'ı yeni şemayı reddetti; seed artık Store'un gerçek migration manifest'ini doğrular. 1.024 gerçek kayıt ve mevcut dizini ezmeme regresyonu eklendi; başarısız seed'in oluşturduğu sentetik dizin yeniden kullanılmadı. Eşik değiştirilmedi.

### Son performans ve kaynak kanıtı

[Ham başlangıç ölçümü](p01-3-final-startup.json): macOS27.0.1 arm64/Apple M5 Max/SSD/CPython3.11.18/editable `.venv`. Her komutta ilk süreç, üç ısınma ve30 ayrı süreç; OS/disk cache kontrol edilmez. Veri1.024 kayıt, toplam payload1.212.625 bayt, en büyük1.233 bayt. Her cache örneği gerçek fresh hit olduğunu doğrular. Sıcak p95 help24,687, version24,395, context81,620 ve cache142,181 ms;500/200ms hedefleri başarılıdır. Bu kayıt hacmi için kanıttır; tüm kayıtların32KiB dolu payload olması veya soğuk disk performansı değildir. CI'da CPU model etiketi Linux /proc/cpuinfo'dan okunur; bulunamayan disk türü unknown kalır.

[Input bellek ham ölçümü](p01-3-input-memory.json):16MiB/256MiB/1GiB ayrı sparse sıfır dosyası, üç ayrı process, aynı CPU/SSD/editable ortam. Descriptor üzerinden tam okunan içerik bağımsız beklenen SHA-256 ve boyutla doğrulandı; blok1MiB. Python allocation peak üçünde de2.102.830 bayt; ek process peak RSS sırasıyla2.293.760/3.391.488/4.505.600 bayt. Dosya boyutuyla doğrusal bellek büyümesi görülmedi. RSS farkı ru_maxrss process maxima farkıdır; import baseline ve işletim sistemi allocator etkileri raw kayıttadır. Sparse fixture gerçek model/veri closure, ağ aktarımı veya fiziksel soğuk I/O kanıtı değildir.

### Güncel sınır ve PR kapısı

Ürün işi private SQLite cache/clock/plan/approval ve yerel dosya bağlamayla sınırlıdır. Gerçek EVREN/HTTP, araç/runtime yürütümü, operation/attempt/lease/jobs ve maliyetli yan etki yoktur. Public görevler draft/blocked; pozitif preparation/approval yalnız trusted test fixture'dır. Gerçek Windows ve fiziksel güç kesintisi denenmedi. Yerel user/root/inode/mount/rename ve gözlenmeyen zaman değişimi sınırları ADR'lerde korunur. Cache temizliğinin plan/onayları koruduğu ve restore'un bütün eski bağları emekliye ayırdığı gerçek tüketicilerle kanıtlandı.

Adım4 ilk commit'i ardından iki fresh bütünleşik review turu yapılır; sonra P01-3b yerel kabulü verified ve tek development PR'ı kullanıcı incelemesine açık kaydedilir. PR/son head CI henüz oluşmadığından burada geçmiş gibi yazılmaz. Master/release işlemi ve PR merge kullanıcıda kalır.

### Adım 4 / review 1

İlk bütünleşik commit `d34986a`. Üç yeni reviewer delivery/paket/kaynak (GPT-6.1 Sol/high), acceptance/invariants (GPT-6 Astra/high) ve docs/public sözleşme (GPT-6.1 Sol/high) inceledi. Delivery66 contract testi,38/208 arşiv üyesi ve30 örnekten dört p95'nin yeniden hesabında yeni kusur bulmadı. Acceptance159 test (dört kota/kapasite testi seçilmeden) ve11 görevin ayrı gerçek API/SQLite probunda draft/false/onay reddi sınırını doğruladı; yeni kod bulgusu yok.

İki P3 belge kapsamı doğrulandı ve düzeltildi: local-state referansında eski cache-only restore allowlist/“plan-onay henüz yok” ifadeleri, configuration referansında env okumayan yolların stateless v1 ile sınırlanmaması. Güncel identity/cache/clock/plan/approval allowlist, açık cached/execution tek seçili env snapshot'ı ve YAML/offline parser ile descriptor execution bağının ayrımı netleştirildi. Belge değişikliği için link/heading/fence ve diff denetimi yeterlidir; runtime testleri tekrar edilmedi.

Ignored dist/verification.jsonl önceki17/130 üyeli denemeyi taşıyordu; aynı başarılı son38/208 üyeli .local doğrulama makbuzu o konuma kopyalandı. Kod/commit kanıtı olarak eski dosya kullanılmadı. İkinci fresh bütünleşik review turu ve son PR/CI kapısı beklenir.


### Adım 4 / review 2 ve yerel kapanış

Üç farklı yeni reviewer integration/invariants (GPT-6 Astra/high), artifacts ve docs (GPT-6.1 Sol/high) `271a6fb` üzerinde inceledi. Integration501 hedefli test ve bağımsız5s cost-expiry/idempotence/tam expiry/geri-saat probunda yeni kusur bulmadı. Artifact reviewer mevcut wheel/sdist SHA'larını makbuzla, runtime ve sdist src/scripts/tests baytlarını checkout ile karşılaştırdı; izin listesi ve kaynak ölçümü iddialarında yeni bulgu yok. Build/benchmark tekrarı yapılmadı.

Tek P3 referans indeksinin restore'u hâlâ identity-only diye özetlemesiydi; yaşayan indeks güncel genişlemeyi yanlış daraltıyordu, ibare kaldırıldı. Belge/ajan/diff kontrolü geçti. Dört adımın her biri iki ayrı fresh review turuyla, doğrulanmış bulguların fix/commit ve gerekli regresyonlarıyla tamamlandı. P01-3a/b yerel kabulü verified; bu, development merge veya yayın değildir.

Sıradaki işlem tek development PR'ı açmak, son head'in offline-core/branch-policy CI'ını doğrulamak ve kullanıcı incelemesi için açık bırakmaktır. Sıradaki ürün paketi P01-4b/4c: operation/attempt, lease/fencing, unknown uzlaştırma ve yerel jobs; ardından P01-5 ve faz kapanışı. Master/release kullanıcıdadır.

## Development PR ve Linux bütçe düzeltmesi

[PR #8](https://github.com/HodeTech/Yorunge/pull/8) development hedefiyle açıldı; merge yapılmadı. GitHub connector create yetkisi403 olduğundan mevcut PR durumu okunup authenticated gh CLI ile aynı yetkili işlem tamamlandı. İlk head4101763 için [Linux CI](https://github.com/HodeTech/Yorunge/actions/runs/40592076037) test, lint/type/belge ve iki temiz kurulumda başarılıdır; cache p95202,724ms ile200ms bütçesini geçemedi. [Ham CI JSON'u](p01-3-linux-startup-initial.json) logdan çıkarıldı: CPython3.11.15/Linux6.17/glibc2.39, Intel Xeon Platinum8370C, disk_type unknown, frozen uv editable ortam,1.024 kayıt ve30 süreç; profile p95160,885ms geçti.

Eşik veya örnek yöntemi değiştirilmedi. Yerel import profilinde reçetesiz cache komutunun YAML yüklediği (yaklaşık9,75ms cumulative) doğrulandı. RecipeLoader/YAML importu yalnız load_recipe yoluna taşındı; aynı SafeLoader alt sınıfı, duplicate/non-string key, tag/scalar, anchor/alias, node/depth ve public hata kapıları korundu. Yedi gerçek CLI komutu artık recipe yokken YAML importunu audit guard ile reddederek başarıyla tamamlanır. CLI/validation/v1 boundary takımı282 test geçti; strict lint/type başarılıdır.

[Değişiklik sonrası yerel ölçüm](p01-3-import-startup.json) aynı Apple M5 Max/SSD/editable ortamında30 süreç ve1.024 kayıtla cache p95132,584ms; help28,113/version27,653/context85,920ms hedefleri geçti. Önceki kayıtlar tutuldu. Bu yerel ölçüm Linux kapısını geçmiş sayılmaz; yeni head gerçek CI ile sınanır. Parse davranışı ve v1 digest'i değişmediği için yeni ADR gerekmez; bu son bütünleşik kabulün performance düzeltmesidir. Runtime değişikliği için iki yeni bağımsız review turu ve güncel tam test/kurulum kabulü ayrıca yapılır.

### Linux düzeltmesi / review 1

İki yeni reviewer parser/v1 (GPT-6 Astra/high) ve imports/kanıt (GPT-6.1 Sol/high),4101763..4772d26 farkını inceledi. AST karşılaştırması loader sınıfı ve parser kurallarının aynı olduğunu doğruladı;108 parser/CLI ve50 import/validation testi başarılıdır. Yeni guard bağımsız negatif kontrolle YAML importunu gerçekten engeller; API importu aynı guard altında YAML yüklemez. Runtime bulgusu yok.

Bir P2 belge regresyonu doğrulandı: son kayıt eklenirken yanlış yerel metin değişkeni kullanılması kanonik kabul gövdesini araştırma indeksiyle değiştirmişti.4101763'teki tam dört adım/review geçmişi eksiksiz geri getirildi, yalnız yeni Linux bölümü sonuna eklendi. Önceki kayıt Git'te korunuyordu; çalışma dosyası ve public PR kaydı düzeltildi. Heading/link/fence kontrolü gövde kaybını anlamsal olarak yakalamadığı için bu review bulgusu özellikle kaydedilir. İkinci fresh review turu yeni runtime ve düzeltilmiş kanıtı tekrar inceler.


### Linux düzeltmesi / review 2 ve PR bulguları

İki farklı fresh reviewer YAML/v1 ve teslim/kanıt sınırını tekrar inceledi; runtime bulgusu yok. Kanonik kaydın önceki tam gövdesi 4101763 ile bayt düzeyinde karşılaştırıldı ve korundu. Güncel tam takım 1.084 testte başarılıdır; bu sonuç aşağıdaki yeni PR düzeltmelerinden öncedir.

b28066a için [ikinci Linux koşusu](https://github.com/HodeTech/Yorunge/actions/runs/40593339188) test/build/iki temiz kurulumda başarılı, cache bütçesinde başarısızdır. [Ham kayıt](p01-3-linux-startup-second.json): AMD EPYC 7763, CPython 3.11.15, disk unknown, frozen uv editable; cache p95 231,595 ms, context 186,041 ms. Önceki Intel runner ile aynı donanım değildir; iki sonuçtan YAML değişikliğinin etkisi sayısal olarak çıkarılmaz. Eşik/örnek/senaryo korunur; sonraki başarısız koşu import/cProfile tanısını da kaydeder. Son Linux kapısı henüz geçmedi.

CodeRabbit ve Sonar bulguları mevcut koda karşı doğrulandı. Gerçek dayanıklılık kusuru: tamamlanmış eski stage/live çiftini yerinde migrate ederken ikinci SIGKILL, hot journal bırakıp readonly recovery preview'ını engelliyordu. Yükseltme ayrı private/no-clobber gölgede yapılıp validate/sync sonrası atomik yayımlanır; orijinal çift yayına kadar korunur. Eski şema 1/2/3 × stage/live × migration-write/committed/shadow-sync/publish-before/after/pair-sync için 36 gerçek süreç kesintisi testi geçti. Kaynak backup önce silindi; epoch/K ve hedef şema korundu. Yazma ortasında gerçek hot journal yalnız gölgede kaldı; preview dosya baytlarını değiştirmedi. Gölge/journal artıkları otomatik silinmez veya authority seçilmez. Fiziksel güç kesintisi kanıtı değildir.

Sonar path traversal uyarısı public sınırda yeniden üretilemedi: mutlak root kabulü ADR-0014 gereğidir, girdi referansı root'tan göreli ve her bileşen no-follow descriptor açılır. Bununla birlikte düşük seviye directory/relative yardımcıları artık kendi ham bileşen kapılarını da açılıştan önce uygular; mutlak/Unicode ve POSIX root adları korunur. 35 input testi geçti. Yalnız gösterilen helper eksikliği güçlendirilmiştir; public sandbox veya doğrulanmış exploit iddiası yoktur.

Doğrulanan cognitive complexity uyarılarında CLI render/parser/dispatch, cache prune/reserve/presentation, scope/evidence/plan validator ve kurulu dağıtım denetimi küçük yardımcılarla ayrıldı. S5778 testlerinde constructor/serialization hazırlığı raises dışına taşındı. 246 hedefli capability/execution/CLI/dağıtım testi, Ruff/strict mypy, belge/ajan ve diff denetimi geçti. ADR'nin eski öneri durumu, CLI sayı boşlukları ve public plan komutlarıyla gerçek yürütme ayrımı düzeltildi.

Atlanan uyarılar: ASCII timestamp'te [0-9] yerine Unicode kapsayan \d sözleşmeyi genişletirdi; Producer.observe key parametresi port imzasıdır; credential tuple uzunluğu gereken hizmet sayısına bağlıdır; contextmanager transaction yield sonrası cleanup mevcut except BaseException/finally ile korunur. Bu uyarılar için davranış, kural veya kalite eşiği gevşetilmedi. Yeni çalışma iki fresh review turuyla ayrıca incelenir.
