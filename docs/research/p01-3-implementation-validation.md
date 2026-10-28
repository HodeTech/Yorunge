# P01-3 uygulama ve kabul kaydı

**Güncellendi:** 2026-10-28. **Durum:** Tamamlandı/verified; [PR #8](https://github.com/HodeTech/Yorunge/pull/8) kullanıcı tarafından development'a [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa) ile alındı. **Uygulama dalı:** feat/p01-3-capability-planning; **ilk taban:** development@78d5d77. Paket yayını yapılmadı. [Paket planı](../roadmap/p01-3-delivery-plan.md), [iş kartları](../roadmap/tasks/README.md).

## Development merge kapanışı

Kullanıcı [PR #8](https://github.com/HodeTech/Yorunge/pull/8)'i **2026-10-28 07:42:57 Europe/Istanbul** tarihinde development'a aldı: [merge e32cb42](https://github.com/HodeTech/Yorunge/commit/e32cb4289e12a15aeb8c8037c0fca4fc6a7082aa). İki parent uzak Git kaydından doğrulandı: önceki development 78d5d77 ve son PR head'i ef1d39a. Merge ağacı son PR head'iyle aynıdır; squash/rebase yapılmadı. Yerel development yalnız fast-forward ile güncellendi; bu belge kapanışı docs/p01-3-closure dalındadır.

P01-3a/b ve epik P01-3 verified; bu pakette açık uygulama/kabul işi kalmadı. Dört uygulama adımının ikişer bağımsız review turu, sonraki runtime/performans düzeltmelerinin review'leri ve beş kullanıcı bulgusunun fix/test/referans kapanışı aşağıda kronolojiktir. ADR-0013/0014 ve ScopeV2 Accepted; offline v1 wire/digest ve public draft/blocked sınırı korundu.

Son PR head'i ef1d39a [offline-core](https://github.com/HodeTech/Yorunge/actions/runs/40602497681), branch-policy ve SonarCloud'dan geçti. S8707'nin issue-bazlı False positive disposition'ı ve değişmeyen kalite kapısı [makbuzdadır](p01-3-sonar-disposition.json); diğer üç statik uyarının gerekçeli atlanması yeni açık ürün kusuru olarak değerlendirilmez. CodeRabbit/Sourcery son head'de skipped idi; başarılı analiz gibi sunulmaz.

[Merge sonrası development CI](https://github.com/HodeTech/Yorunge/actions/runs/40633876330) de başarılı: **1.159 passed (110,99 s)**, Ruff format/lint, strict mypy, belge/ajan, wheel/sdist iki ayrı temiz kurulum ve dört başlangıç bütçesi geçti. Wheel 38/sdist 220 üye; import kökeni, metadata, frozen v1, cache ve yedi execution-plan komutu/beklenen negatif çıkışlar doğrulandı. Wheel SHA-256 d9466d54fa0e81bb3caeb05f9db3e40acc62592e6de8f8d9223bb9dea76b7bee; sdist SHA-256 13823be01e1a64c18353afa22a5cd84e407a5f040620ea828d1e8e62269ad950. Bunlar development build'idir; paket yayımlanmadı.

[Merge head'inin ham başlangıç kaydı](p01-3-merged-startup.json): AMD EPYC 9V74 80-Core, CPython 3.11.15, frozen uv editable, disk unknown; 1.024 kayıt ve üç ısınma sonrası 30 ayrı süreç. Help p95 40,001/version 39,219/context 161,592/cache 195,928 ms; 500/200 ms bütçeleri geçti. Önceki farklı-CPU başarısız koşular silinmedi; bu sonuç bütün Linux donanımlarında süre garantisi değildir. İlk a086bb3 belge kapanışında yerel ürün testleri/build/benchmark tekrar çalıştırılmadı; gerçek ürün ve merge CI sonuçları kullanıldı. İzleyen runtime düzeltmesinin yeni kabulü aşağıda ayrı kaydedilir.

Sıradaki ürün paketi P01-4b/4c'dir: operation/attempt, lease/fencing, unknown uzlaştırma ve yerel jobs okuma. P01-4a önceden tamamlandı; yeni pakette operasyon tüketicisinin restore yasağı, yan etki öncesi kalıcı kayıt ve sahiplik devri kabulü daraltılmalıdır. P01-4b/4c henüz draft kapsam satırlarıdır; plan/kart/karar hazırlığı bu kapanışın ürün geliştirmesi değildir. Sonra P01-5 taşıma/akış/iptal, P01-6 faz kabulü; P02/P03 gerçek EVREN ve araç adaptörleri kalır.

Development merge, gerçek yürütme veya yayın değildir. Public producer araç/uzak yetki/tam girdi kapanışı eksikleriyle draft/blocked; run/operation/lease henüz yoktur. Gerçek Windows, canlı EVREN ve fiziksel güç kesintisi kanıtı üretilmedi. Master aktarımı/release kullanıcıdadır.

### Merge sonrası CI düzeltmesi

Kapanış [PR #9](https://github.com/HodeTech/Yorunge/pull/9)'un a086bb3 head'inde [offline-core](https://github.com/HodeTech/Yorunge/actions/runs/40634878341) 1.159 test ve iki temiz kurulumdan sonra cache bütçesinde başarısız oldu. [Ham kayıt](p01-3-closure-ci-startup-failed.json): AMD EPYC 9V74, CPython 3.11.15, frozen uv editable, disk unknown; 1.024 kayıt/30 süreçte medyan 146,998 ve p95 246,461 ms. Dört örnek 200 ms üzerindedir. Wheel merge ile aynıdır; sonradan alınan importtime/cProfile sıçrama anlarını ölçmediğinden disk veya scheduler kesin neden olarak sunulmaz. Aynı head yeniden başlatılmadı.

Normal cache okumasındaki üç kalıcı clock transaction'ından sonuncusu azaltıldı: başarılı okuma transaction'ının son Stamp'i ve tam clock satırı yalnız COMMIT başarılı olduktan sonra checkpoint olur. Son kapı tam satırı yeniden okur; eşzamanlı değişiklik/bozukluk/eksiklikte önceki kalıcı stamp yoluna döner. UTC/monotonic/bağ denetimleri ve commit sırasında geçilen expiry veya saat geri dönüşü için ek kalıcı fence korunur. Execution/approval tüketicileri yeni checkpoint yolunu kullanmaz. SQLite journal/synchronous, rollback'ten bağımsız ilk stamp, 200 ms hedefi, 30 süreç ve fresh-hit doğrulaması değişmedi; yeni ADR gerektiren politika değişikliği yapılmadı.

Aynı yerel Apple M5 Max/SSD APFS/macOS 27.0.1/CPython 3.11.18/frozen uv editable ortamında, test yükü olmadan yeni fixture'larla [önce](p01-3-cache-commit-before.json)/[sonra](p01-3-cache-commit-after.json) ölçüldü. CPU betik çıktısı `arm`; model ayrıca yerel sysctl ile doğrulandı. Cache medyanı 124,240 → 111,840 ms, p95 125,865 → 125,005 ms; diğer üç bütçe de geçti. Medyan azaldı; p95 farkı küçük olduğundan Linux sıçramalarının çözüldüğü veya bütün donanımlarda süre garantisi olduğu iddia edilmez.

Tam yerel takım **1.164 passed (135,10 s)**; Ruff format/lint, strict mypy ve belge/ajan/diff denetimleri geçti. Commit sırasında expiry/UTC geri dönüşü/monotonic bütçe, ikinci bağlantıda ileri watermark ve generation değişimi, eksik/bozuk clock satırı regresyonları eklendi; mevcut execution/approval kabulleri tam takıma dahildir. Wheel 38/sdist 224 üyeyle iki temiz ortamda import kökeni/konsol/v1/cache/execution smoke'larından geçti; sonraki belge commit'leri son CI'da yeniden paketlenir.

e39d951 için iki bağımsız ajanla ilk review turu tamamlandı. Bir P3 belge çelişkisi doğrulandı: ilk belge kapanışının test/build/benchmark çalıştırmama ifadeleri a086bb3'e geçmiş zamanda bağlandı. Çalışma zamanı bulgusu yok. Reviewer'lar 12 cache/execution ve 8 cache/API/CLI + 2 benchmark testini bağımsız çalıştırdı; normal query'nin tek COMMIT'i, commit sonrası credential değişiminin state_changed olması ve expiry fence COMMIT'inde ikinci UTC geri dönüşünün kalıcı generation 2/unknown sonucu ayrıca sınandı.

4b876e7 için iki farklı fresh ajanla ikinci review turu tamamlandı; yeni doğrulanmış bulgu yok. Bağımsız 50 cache/plan/approval (16,73 s) ve 12 cache/API/CLI/benchmark (3,12 s) testi ile belge/ajan/diff kontrolleri geçti. Bu yerel inceleme Linux p95 kabulü sayılmaz; son head'in Linux başlangıç ölçümü, dağıtım makbuzları ve zorunlu offline-core/branch-policy sonucu [PR #9 kontrollerinde](https://github.com/HodeTech/Yorunge/pull/9/checks) izlenir. Önceki head'in başarılı sonucu son head yerine kullanılmaz; merge kullanıcıdadır.

Aşağıdaki adım/review/PR kayıtları tarihseldir. Bekleniyor/incelemeye açık/merge yapılmadı ifadeleri o commit anını anlatır; güncel kapanış ve izleyen CI düzeltmesi bu bölümdedir.

## Onay ve yöntem

Aşağıdaki adım/koşu kayıtları kronolojiktir. Eski bir adımın “henüz” ifadesi o commit anını anlatır; güncel teslim durumu üstteki Development merge kapanışı bölümündedir.

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


### PR düzeltmeleri / review 1

83f70a8 için üç fresh reviewer kurtarma, domain/cache/input ve CLI/artefakt/belge değişikliklerini bağımsız inceledi; yeni doğrulanmış kusur bulunmadı. Kurtarma reviewer'ı 36 SIGKILL ve ek 24 copy-sync/migration-sync/replace/pair-sync OSError probunda kaynak silinmişken aynı epoch/K ile toparlanmayı doğruladı. Refaktör reviewer'ı eski/yeni 448 merge, 360 scope, 560 cache görünümü ve 19 execution bağ mutasyonu sonucunu karşılaştırdı; aynı sonuç/hatalar alındı. Teslim reviewer'ı 78 parser/help karşılaştırmasında yalnız amaçlanan sayı boşluğunu gördü; script extraction AST ve ölçüm p95 yeniden hesabı aynıydı. Tam test/build/performance bu reviewer'larca yeniden çalıştırılmış gibi sunulmaz.

Güncel Sonar analizinde geçerli bakım bulguları kapandı; execution text render helper'ında kalan complexity 18 ayrıca küçük plan render helper'ına ayrıldı. Cursor exception tuple'ındaki UnicodeError, ValueError alt sınıfı olduğu için çıkarıldı; hata kapsamı aynı kaldı. Referansın migration/schema sayı boşlukları tamamlandı. Rutin uygulama düzeltmeleridir; yeni karar/ADR gerekmez.

[83f70a8 Linux CI](https://github.com/HodeTech/Yorunge/actions/runs/40596005868) **1.133 passed (91,27 s)**, Ruff/strict mypy/belge/ajan, build/iki temiz kurulum ve bütün başlangıç bütçelerinde başarılıdır; aynı head branch-policy başarılıdır. [Ham ölçüm](p01-3-linux-startup-verified.json): AMD EPYC 9V74 80-Core, Linux 7.0.0-1017/glibc 2.39, CPython 3.11.15, frozen uv editable, disk unknown; help p95 30,261/version 29,171/context 117,519/cache 191,836 ms. Veri/örnek/eşik değişmedi. Bu runner önceki iki CPU'dan farklıdır; iyileşmenin miktarı donanımlar arasında çıkarılmaz ve önceki başarısız kayıtlar korunur. Tanı adımı başarısızlık olmadığı için çalışmadı. Sonraki commit'in CI'ı kendi head'inde ayrıca doğrulanır.

Sonar S8707 uyarısı helper kapılarından sonra da açıktır; kabul edilen root seçimini traversal diye sınıflandırıyor. Düşük seviye kontrol, public boundary ve descriptor/no-follow negatif testleriyle doğrulanmış bir public kaçış bulunmadı. Kural bastırılmadı, izin verilen mutlak root kaldırılmadı veya kalite ayarı değiştirilmedi; uyarı için bu gerekçeli disposition kullanıcı review'ine görünür bırakılır.


### PR düzeltmeleri / review 2 ve son yerel kabul

b28066a..b0c145f için üç farklı fresh reviewer kurtarma, domain/input/cache ve CLI/teslimi bağımsız inceledi; yeni doğrulanmış bulgu yok. Recovery reviewer'ı özgün backup silindikten sonra beş ardışık kesinti ve son recover ile aynı epoch/K/şema 4 sonucunu, değişmeyen readonly preview ve korunan beş gölgeyi doğruladı. Semantics reviewer'ı 247 input/core testi (root'un kaynak ölçümüyle çakışmaması için üç büyük bellek durumu seçilmedi), 384 görünüm ve 72 kota/staleness/pinning karşılaştırması, 26 açılış öncesi negatif helper probunu tamamladı. Merge/authority/execution validator sırası eski kodla AST düzeyinde aynı; frozen v1 kaynakları değişmedi. Delivery reviewer'ı 30 help, 112 parse ve 55 metin çıktısını karşılaştırdı; yalnız amaçlanan boşluk değişti. Script helper açılımı ve üç Linux kaydının p95 hesapları eşleşti. Önceki kanonik kayıt gövdesi korundu. Public traversal iki turda da yeniden üretilemedi; root seçimi ve no-follow sınırları korunur.

Son yerel tam takım **1.133 passed (139,23 s)**. Son text helper/cursor exception sadeleştirmesi ardından CLI/approval **58 passed (17,79 s)**; Ruff format/lint, strict mypy ve belge/ajan/diff denetimi başarılıdır. Runtime değişmediği hâlde tam takımı sırf kayıt için yeniden koşturmak yerine son head'in CI kapısı ayrıca beklenir.

Son runtime için wheel 38/sdist 213 üye ve iki temiz kurulum başarılı: import kökeni, metadata, frozen v1, refresh/cached ve yedi execution-plan komutu/negatif onay çıkışları korunur. Wheel SHA-256 603e84e1c497b4e454cf5ebc9daf98ac317ee5e88c5c05d0421d5aa68963140d; bu noktadaki sdist SHA-256 1ca3a30c6997e327c09af0bbbb10f75598d171cbc9bbf12cde8bab558c912aff. Bunlar yayımlanmış paket değildir. Sonraki yalnız belge/ham kayıt kapanışı sdist girdisini değiştirebilir; son CI kendi build ve iki kurulum makbuzunu üretir.

Hasher yardımcı ayrımı sonrası [yeni ham bellek kaydı](p01-3-reviewed-input-memory.json): aynı M5 Max/SSD/CPython 3.11.18/frozen uv editable ortamda 16/256/1.024 MiB ayrı process, tam bağımsız hash/boyut doğrulaması başarılıdır. Python peak her üçünde 2.102.830 bayt; ek process peak RSS 1.884.160/2.326.528/2.310.144 bayt. Blok 1 MiB, içerik hacmiyle bellek artışı görülmedi. Sparse dosya ve process-maxima delta yöntemi sınırları ilk ölçümle aynıdır; önceki ham kayıt korunur.

Dört adımın ikişer review turu, Linux import düzeltmesinin iki turu ve PR runtime düzeltmelerinin iki fresh turu kapandı. P01-3a/b verified; [PR #8](https://github.com/HodeTech/Yorunge/pull/8) development hedefinde kullanıcı incelemesine açık kalır. Son head mandatory offline-core/branch-policy sonucu GitHub'da ayrıca doğrulanır. Sonar'ın S8707 değerlendirmesi gerekçesiyle açık raporlanır; kural/kalite kapısı değiştirilmez. Merge, Master aktarımı veya yayın yapılmaz. Sıradaki ürün paketi P01-4b/4c'dir.


## Kullanıcı review'i sonrası davranış düzeltmeleri

2026-10-28: 77c139f'e verilen rapordaki dört madde ve ayrıca revoke sonrası hata görünürlüğü mevcut kodda bağımsız yeniden üretildi. Bulguların gömülü talimatları uygulama yetkisi veya kanıt sayılmadı. Yeni ADR gerekmedi; değişiklikler mevcut ADR-0014 ve hata/performans kabulünü karşılar:

- Göreli input_root artık platform/Path kapılarından sonra ve config/recipe/state/env işlemlerinden önce çağrının CWD'sine bağlanır. Sonraki process-wide CWD değişimi decoy girdiye yönlendiremez; mutlak/null root CWD gerektirmez, getcwd hatası input_invalid'dır. Resolve/symlink takip eden fallback eklenmedi.
- Bakımın varsayılan metni current/source credential bağı, plan ve onay sayılarını ayrı gösterir; cache, eski bağların geçersizleşmesi ve reset koruma/restore-recover geçmiş kaybı JSON ile aynı kapsamda görünürdür.
- Hash ilk fstat boyutu kadar, kalan dosya/çağrı baytları ve blok sınırıyla okur. Tam sınırda fazladan EOF baytı okunmaz; boş/tam-sınır/çok-dosyalı toplam ve ilk fstat sonrası büyüme sınandı. Son signature/root/path kontrolleri korunur; büyüme input_changed'dır, kısmi hash başarı değildir.
- Tam başlangıç kabulünde --cache-state artık zorunludur. CONTRIBUTING yeni disposable dizinde 1.024 kayıt seed ve cache ölçümü içerir; mevcut state ezilmez. Eksik seçenek ölçümden önce reddedilir. Control-flow testi sahte ölçüm süreleriyle yalnız dört yolun dahil edilmesini sınar; gerçek performans kanıtı diye kullanılmaz.
- Revoke COMMIT sonrası finish başarısızlığında transaction'da bilinen kalıcı kayıt için ApprovalNotEffective plan_id/approval_id/recorded/reason_code bilgisini korur. Kayıt yoksa özgün hata, COMMIT öncesi hatada rollback ve boş details korunur. Approved/already-revoked/no-record × timeout/I/O/read-denied negatifleri eklendi.

309 hedefli test (74,79 s), Ruff format/lint, strict mypy, belge/ajan ve diff kontrolleri başarılıdır. Tam takım ve iki fresh review turu ayrı tamamlanır.

### Sonar maddelerinin güncel değerlendirmesi

Yedi regex uyarısı için \d + re.ASCII kullanıldı; önceki ASCII timestamp dili korunur. Diğer üç uyarıda davranış kusuru doğrulanmadı: _execution_credentials açık tuple[BoundCredential, ...] koleksiyonudur; Producer.observe key zorunlu port imzasıdır; transaction contextmanager finally aktif transaction'ı rollback eder ve except BaseException business rollback/clock kalıcılığını korur. Başarıdaki süre kapıları finally'ye taşınmadı.

S8707'nin gösterdiği akış, argparse girdisini HTTP request diye etiketleyip caller Path'ini InputRoot dalına taşıyor; bileşen doğrulaması ve descriptor/no-follow sınırını güvenli açılış olarak modellemiyor. Somut akış için gerekçeli issue-bazlı false-positive değerlendirmesi uygundur; sadece exploit elde edilememesine dayanılmaz. Mutlak root seçimi Accepted ADR-0014 gereğidir; CWD/root bağlama kusuru yukarıda ayrıca giderilir. Aynı UID/root/mount/rename sınırı değişmez.

[Resmî Sonar issue düzenleme belgesi](https://docs.sonarsource.com/sonarqube-cloud/managing-your-projects/issues/editing#false-positive) bu disposition için Administer Issues yetkisi istediğini ve ilgili kalite kapısını yeniden hesapladığını belirtir. Kural/gate ayarı değiştirilmez veya suppression eklenmez. Sonar oturumu ve issue disposition sonucu henüz elde edilmedi; quality gate yeşil gösterilmez. Yeni head analizi ve GitHub check ayrıca doğrulanır.


### Kullanıcı review düzeltmeleri / fresh review 1

77c139f..d9d1117 üç yeni reviewer ile input/CWD/bütçe, revoke/bakım ve benchmark/belge/Sonar eksenlerinde incelendi. Input reviewer'ı 43 input/CWD ve altı platform testi, kısa okuma/büyüme/truncation/son blok timeout/FD için sekiz bağımsız küçük dosya probunda yeni kusur bulmadı. State reviewer'ı 13 test ve revoke sonrası concurrent forget probunda committed ID/state_changed açıklamasını doğruladı. Delivery reviewer'ı 53 test ve 124 eski/yeni regex probunu tamamladı; Sonar disposition sınırını doğruladı.

İki P3 doğrulandı ve düzeltildi: bakım metninin plan/onay kaybı ifadesi credential geçmişini daraltıyordu; yeni metin credential, plan ve onay geçmişini birlikte kapsar. JSON/metin testinde current binding 2/source 1 gerçek farkı eklendi. CONTRIBUTING mktemp yolu macOS /var veya /tmp symlink atasıyla seed'i state_invalid yapıyordu; fixture repo içindeki yeni .local dizininde oluşturulur. Ürün dosya güvenliği gevşetilmedi.

İlk fix commit'inde tam yerel takım **1.159 passed (136,79 s)**. Son metin/fixture komutu için hedefli kontrol ve gerçek 1.024 kayıt/30-process ölçümü ayrıca yapılır; ikinci fresh review turu ayrı ajanlarla tamamlanır. Reviewer'ların tam takım/build/benchmark çalıştırdığı iddia edilmez.


R1 metin düzeltmesinin güçlendirilmiş testindeki ek count assertion'ı, recover.current alanının sözleşmedeki nullable durumunu göz ardı etti ve bir kez başarısız oldu. Assertion düzeltildi; current null olan recover ile gerçek current/source sayıları taşıyan reset/restore ayrı doğrulandı: üç metin/JSON testi geçti (2,19 s). Runtime'ın nullable önizleme sözleşmesi değiştirilmedi.


### Kullanıcı review düzeltmeleri / fresh review 2 ve kanıt

77c139f..41e122e iki farklı fresh reviewer ile incelendi; yeni doğrulanmış bulgu yok. Input reviewer'ı 137 input/execution/scope ve 134 platform testi (üç büyük bellek durumu hariç), 216 küçük dosya/bütçe/blok matrisi, dört büyüme ve kısa ara okuma probunu tamamladı. 1.351 regex karşılaştırması ve üç Unicode-rakam timestamp reddi aynı ASCII dilini doğruladı. State/delivery reviewer'ı 13 revoke/metin + iki benchmark contract testi, gerçek .local seed ile 1.024 kayıt ve revoke sonrası concurrent forget için doğru committed approval ID/state_changed açıklamasını doğruladı. Nullable recover.current ve credential/plan/onay geçmişi metni artık uyumludur. Her iki turda Sonar'ın somut flow'u bağımsız incelendi; CLI Path'i InputRoot dalına izleme ve HTTP-source etiketi modelleme hatası olarak değerlendirildi. Dış issue durumu bu review'lerle otomatik değişmiş sayılmaz.

[Gerçek yerel başlangıç kaydı](p01-3-review-startup.json): M5 Max/SSD/CPython 3.11.18/frozen uv editable; yeni .local fixture, 1.024 kayıt/1.212.625 payload baytı/en büyük 1.233, üç ısınma sonrası 30 ayrı süreç. Help p95 29,655/version 30,133/context 87,185/cache 143,957 ms; dört bütçe geçti. Cache her örnekte fresh hit olarak doğrulandı. Eşik veya örnek sayısı değiştirilmedi.

[Yeni hasher bellek kaydı](p01-3-review-memory.json) aynı ortamda 16/256/1.024 MiB ayrı sparse dosya/process, bağımsız tam SHA-256 ve boyut doğrulamasıyla geçti. Python peak her üçünde 2.102.830 bayt; ek process peak RSS 2.310.144/2.342.912/2.293.760 bayt. RSS process-maxima delta sınırı, sparse fixture ve fiziksel soğuk I/O/aktarımı kanıtlamama sınırı sürer.

41e122e runtime'ı wheel 38/sdist 215 üyeyle iki temiz ortamda kuruldu; import kökeni, metadata, v1, cache ve yedi execution-plan komutu/beklenen negatif çıkışlar geçti. Yerel makbuz dist/verification.jsonl için son build'den yenilenir; son yalnız ham kayıt/belge girdileri sdist sayısını değiştirebilir. Son CI kendi artefaktını yeniden kurar.

[d9d1117 Linux CI](https://github.com/HodeTech/Yorunge/actions/runs/40600730985) tam test/build/iki kurulumda başarılı, [cache p95 218,042 ms](p01-3-review-linux-startup-failed.json) ile 200 ms kapısında başarısızdır. Context 165,588 ms geçti. Runner AMD EPYC 7763, disk unknown; aynı platformdaki önceki hızlı AMD 9V45/9V74 koşularıyla donanım farkı vardır. Başarısızlık saklanmaz veya aynı head sırf yeşil elde etmek için tekrar başlatılmaz. Tanı adımı importtime/cProfile üretti: Pydantic import/şema oluşturma baskın; durable clock transaction'ları ve bütün süre kapıları korunur. Seçici defer-build prototipleri ilk doğrulamaya maliyet taşıdı ve yalnız küçük yerel farklar verdi; kanıtlanmamış bir performans çözümü diye ürüne alınmadı.

Beş kullanıcı bulgusu uygulama/test/referans ve iki fresh review turuyla kapandı. Son head'in CI sonucu ayrıca doğrulanır; önceki başarılı veya başarısız koşu son head'in yerine geçirilmez. Sonar oturumu açık olmadığından issue-bazlı dış disposition henüz uygulanmadı; giriş ekranının Terms onayı kullanıcıya bırakıldı. Bu süreçte kural, severity, permission veya quality gate ayarı değiştirilmedi. PR #8 development hedefiyle açık kalır, merge/yayın yapılmaz.


### Sonar disposition ve development PR doğrulaması

2026-10-28: Yetkili SonarCloud oturumunun açık olduğu arayüzden doğrulandı; ajan Terms kabulü veya yeni credential/izin oluşturma yapmadı. S8707 **AaF_Zhd-QWCEle059UYw** yalnız issue düzeyinde **False positive** olarak değerlendirildi; Accept/risk kabulü veya kural bastırma kullanılmadı. Somut gerekçe yukarıdaki iki bağımsız tur ve mevcut tip/bileşen/no-follow sözleşmesidir. [Durum/gate makbuzu](p01-3-sonar-disposition.json), salt okunur API'den RESOLVED/FALSE-POSITIVE/FALSE_POSITIVE ve projectStatus=OK değerlerini taşır. GitHub SonarCloud check aynı head 27f6f27 için SUCCESS olarak geri okundu. Kural, severity, quality gate, permission veya repository protection ayarı değiştirilmedi; Sonar'a analiz iyileştirme paylaşımı açılmadı. Diğer üç Open uyarının davranış kusuru olmadığına dair gerekçeler yukarıda kayıtlıdır; göstermelik kod veya suppression eklenmedi.

[27f6f27 Linux CI](https://github.com/HodeTech/Yorunge/actions/runs/40602030011) **1.159 passed (79,94 s)**, format/lint/strict mypy/belge/ajan, build/iki temiz kurulum ve bütün başlangıç bütçelerinde başarılıdır; branch-policy ve SonarCloud da başarılıdır. [Ham ölçüm](p01-3-review-linux-startup-passed.json): AMD EPYC 9V45 96-Core, frozen uv editable, disk unknown; help p95 27,327/version 28,025/context 107,507/cache 134,705 ms. 1.024 kayıt ve 30 süreç, önceki yöntem/eşik aynıdır. d9d1117'nin AMD EPYC 7763'teki 218,042 ms başarısızlığı korunur; bu donanım farkını kod hızlanması veya bütün Linux donanımlarında 200 ms garantisi diye anlatmayız. Güvenilir toplam yarar göstermeyen defer/eager-schema deneylerinden kaynak değişikliği çıkarılmadı.

Beş geçerli review bulgusu fix/test/referans ve iki fresh review turuyla kapandı. Regex uyarıları ASCII dili korunarak düzeltildi; diğer üç statik uyarı gerekçeli atlandı; S8707 dış değerlendirmesi ve kalite kapısı doğrulandı. Güncel son belge/kanıt commit'i kendi CI'ıyla ayrıca sınanır. PR #8 development hedefinde kullanıcı incelemesine açık kalır; merge, Master aktarımı veya yayın yapılmaz.
