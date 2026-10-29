# P01-4 uygulama ve kabul kaydı

**Güncellendi:** 2026-10-29. **Durum:** Adım 1 ve 2 ikişer review turuyla kapandı; adım 3 uygulanıyor ve doğrulanıyor. Paket ve P01-4b/4c kabulü tamamlanmadı. **Dal:** feat/p01-4-operations, development tabanı a9f1f2e. [Teslim planı](../roadmap/p01-4-delivery-plan.md), [karar/review disposition](p01-4-readiness-review.md).

## Karar kapanışı

Kullanıcı 29 Ekim review bulgularını doğrulayıp kapattıktan sonra ADR-0016'nın Accepted yapılmasını ve uygulamayı yetkilendirdi. İki ek inceleme ve ikişer fresh reviewer'lı iki revizyon turu sonrasında karar c3dbfe7 ile Accepted kaydedildi. Aynı karar için yeni onay sorulmadı. Önceki startup bakımının dört commit'i ve 8c2dec2 hazırlık commit'i bu dalda korunur; ayrı PR/test merge yapılmaz.

## Adım 1 — Şema ve gerçek kalıcı consumer

Yeni SQL-only V2 5→6 adımı operations, operation_attempts, operation_events ve operation_outcomes tablolarını; plan UNIQUE/FK RESTRICT, deferred dispatch-attempt FK ve sıralama/status/lease indekslerini ekler. Checksum **62ac619e29aaaf2d9c838bde2a0ee795e7496f67107eaf69e26daaf9d4b4b90a**. Yayımlanmış 1–5 checksum'ları ve donmuş capability-expiries handler SHA-256'sı b1ffc8e3ce1dc6fc04c2afe4c2aa50ed6cd2e26deaf0b07ef0caab6fc0c83d18 aynen kaldı; golden testler kimliği sürüm indeksiyle kontrol eder, “son migration daima 5'tir” varsayımı kaldırıldı.

Strict domain modelleri, execution/delivery reducer, authority/admission allowlist'i, immutable approval snapshot, owner tuple ve kapalı hata zarfı eklendi. Gerçek SQLite repository snapshot okuması plan/attempt/event/outcome ve projection ilişkilerini, kotaları ve terminal/dispatch sınırını denetler. Salt modele alan eklemek yerine kayıt/restart/rollback/bozuk veri ve plan forget tüketicisiyle bağlandı. Yeni product run/fixture backend/jobs komutu henüz yoktur.

Operation-capable runtime'ın mevcut restore/recover allowlist kapısı gerçek şema 6 ile kapanır; boş store/eksik hedef/kayıp kaynakta bile I/O öncesi ret testlenir. Tarihsel şema 5 restore/cut testleri açık schema5_runtime fixture ve child replay ile korunur; güncel runtime kapısı gevşetilmez, test skip/xfail eklenmez. P01-3 veri migration probe'u standalone tarihsel şema 5'i açıkça seçer; eski ham ölçümler değiştirilmez. Yeni migration probe'u güncel şema 6'yı ayrı ölçer.

İlk yeni hedefli takım 61 başarılı; schema-5 replay düzeltmeleri sonrası bakım/cache/yeni model/repository hedefli takım 235 başarılı. İlk geniş koşudaki tarihsel CLI/runtime sürüm beklentileri doğrulandı ve fixture sınırları düzeltildi; bu başarısız koşu kabul sayılmaz. Son tam takım **1.387 passed / 181,31 s**; Ruff format (79 dosya)/lint, strict mypy (38 kaynak), 114 Markdown, 6 skill/9 kart ve diff kontrolü başarılı. Review turları henüz başlamadı; adım/kart/paket verified sayılmaz.

Ölçüm yöntemi [p01-4-state-budget-probe.py](p01-4-state-budget-probe.py): sadece yeni sentetik private store, şema 2/3/4/5 ve normal/maksimum geçerli payload hacimleri, her yol üç yeni örnek; yeni worker process, açık 5 s deadline ve korunmuş progress callback. SQL VM-step, backup/hash/sync/DDL/full-validation/commit fazları, orijinal payload/row SHA ve son şema kaydedilir. Ölçüm sırasında kaynak hash'leri sabit kalmalıdır. Henüz ölçülmemiş operation dolu-store/recovery/job performansı bu adımın kanıtı diye anlatılmaz.

### İlk migration kaynak kabulü

[Ham 24 koşu](p01-4-step-1-migration.json): Apple M5 Max, macOS 27.0.1 arm64, CPython 3.11.18, SQLite sürümü ham kayıtta, SSD/APFS. Kaynak c3dbfe7 üzerindeki adım 1 çalışma ağacının dosya SHA-256'larıdır; ölçüm öncesi/sonrası aynıdır. Başka ağır test çalışmadan ölçüldü. Bütün koşular gerçek şema 6'ya, sıfır operation ile ve mevcut 5 s deadline açıkken ulaştı; eski payload satır SHA'ları eşit kaldı. VM progress sayımı deadline callback'ini korudu. Bu tablo her üç örneğin **en yavaşıdır**, p95 veya genel donanım garantisi değildir.

| Kaynak şema | Temsilî hacim en yavaş ms | Maksimum geçerli hacim en yavaş ms |
|---|---:|---:|
| 2 | 1.171,40 | 2.605,47 |
| 3 | 1.422,67 | 4.522,70 |
| 4 | 1.528,91 | 4.528,11 |
| 5 | 1.084,91 | 3.384,84 |

Maksimum şema 4/5 kaynağı 1.024 cache / 33.554.432 payload byte (her kayıt 32.768), 1.024 plan / 67.108.864 byte (her kayıt 65.536) ve 1.024 onay / 619.520 byte (en büyük 605) taşıdı; onay limitine erişmek için geçersiz padding yapılmadı. Kaynak şema 2/3'te henüz bulunmayan tablolar fixture'a eklenmedi. Backup/sync/DDL/validation ve toplam süreler ham kayıtta ayrıdır. Review sonrası kaynak değişirse etkilenen kabul yeniden değerlendirilir.

### Adım 1 — Birinci review turu

Uygulama a73608a commit'inden sonra iki fresh read-only ajan (GPT-6 Astra high state/dayanıklılık, GPT-6.1 Sol high sözleşme/test/kaynak) mevcut kodu inceledi. Beş ve altı yorumun örtüşenleri birleştirildi; sekiz kök neden doğrulandı. Ana ajan gerçek SQLite üzerinde 18 negatif regresyonu önce çalıştırdı: tamamı beklenen reddi vermeyerek bulguları yeniden üretti. Ardından aşağıdaki düzeltmeler yapıldı; geçersiz bulgu diye atlanan madde yoktur, yinelenenler aynı kök nedende kapandı.

| Doğrulanan konu | Düzeltme ve kabul |
|---|---|
| Terminal geçmişi recovery marker ile yeniden açma | Son normal event terminalse marker/current nonterminal projection kesin ret; terminal summary/attempt/outcome/revision/fence/zaman eşliği |
| Submitted witness / lifecycle / latch | İzinli geçiş ve attempt ilerleme grameri; ilk gönderim event'i submitted, dispatch bağı aynı son attempt'te kalır; submitted→admitted/latch temizliği veya admitted→running ret |
| Attempt değişmezliği | Upsert öncesi mevcut created_at/number/provider ID; terminal/abandoned aynı kayıt dışında yazılamaz. Claimed/abandoned provider çalışması metadata'sı taşıyamaz |
| Neden bağlamı | Ortak reason denetimi dispatch/execution/delivery bağlamını alır; postdispatch approval-expiry/revoke, sahte reset cancellation veya eksik delivery_pending nedeni ret |
| Kabul onay zamanı | prepared_at ≤ approved_at ≤ created_at < approval expiry ≤ plan expiry zinciri |
| Attempt/outcome gözlem zamanı | İlk attempt yaratılışı admission/event'e; güncel attempt summary'ye; terminal outcome terminal event/summary UTC'sine bağlanır. Clock alanı değişimi/gerçek UTC gerilemesi görünür kalır |
| Forget bozuk child | Aynı forget transaction'ında operation ilişkisi/body/history doğrulanır; yalnız sağlıklı bağ plan_in_use, bozulma state_invalid |
| Authority decoder hata sınırı | Persist edilmiş bozuk target'ın domain hatası state_invalid olur; public invalid_service_target olarak kaçmaz |

Düzeltme sonrası yeni model/repository ve mevcut execution approval hedefli takım **131 passed / 28,99 s**; Ruff/lint/strict mypy geçti. İlk migration ham kaydı a73608a kaynaklarını kanıtlar; R1 değişiklikleri mevcut operation kayıtlarının doğrulama/yazma sınırındadır, boş operation migration fixture'ında kayıt decoder döngüsü çalışmaz. Bu eski kaydın yeni head hash'i olduğu iddia edilmez; son kaynak kabulü kapanışta ayrıca değerlendirilecek. İkinci tur farklı fresh reviewer'larla sıradadır; adım/kart verified değildir.

### Adım 1 — İkinci review ve kapanış

R1 düzeltmeleri 1049ab2 ile commit edildikten sonra farklı fresh state/sözleşme reviewer'ları (GPT-6 Astra high ve GPT-6.1 Sol high) ikinci turu yaptı. Bu head'de tam takım **1.410 passed / 193,14 s** oldu. İki kök neden daha doğrulandı: slotsuz predispatch control takeover gereğinden sıkı reddediliyordu; kesinleşmiş execution succeeded bilgisi hem normal event hem recovery projection'ında kaybolabiliyordu. Root gerçek DB'de altı beklenen ret/geçerli kabul hatasını yeniden üretti, dört olumlu kontrolü korudu.

Kontrol takeover artık normal event tüketmez; claimed adayların sırası/abandonment zamanı/fence ve aynı admission clock alanı doğrulanır. İlk submitted event en son adayı, geçerli aynı onay zamanını ve admission clock alanını göstermelidir. Execution success hem event→event hem event→recovery boyunca korunur; recovery marker yeni kesin execution/teslim ilerlemesi de icat edemez. Son delta incelemesinde, üç adayın dispatch event'inde fence=2 kabulü bulundu; root warm/full iki regresyonla doğrulayıp event fence≥candidate number kuralını ekledi.

Son kaynakta yeni model/repository ve mevcut approval hedefli takım **143 passed / 33,28 s**; Ruff/lint/strict mypy ve belge/ajan/diff kontrolleri başarılı. İki ikinci-tur reviewer'ı son düzeltmeleri bağımsız SQLite negatif/pozitifleriyle tekrar doğruladı; açık somut bulgu kalmadı. Cross-clock recovery/terminal ve slotsuz takeover olumlu yolları korunur. Adım 1 iki review turuyla kapandı; P01-4b bütün kartı ve paket hâlâ in_progress, çünkü adım 2/3/4 henüz yoktur. Migration 1–6 SQL/checksum/handler kimlikleri bu review düzeltmelerinde değişmedi; ilk ham migration kaydı aynı DDL ve boş operation consumer maliyetinin tarihsel kanıtı olarak korunur, final kaynak kabulü paket kapanışında yeniden değerlendirilecek.

## Adım 2 — Admission, sahiplik ve gönderim sınırı

İç coordinator gerçek execution validation tüketir; public run/fixture backend kaydı açılmaz. Yeni admission, predispatch takeover ve arm aynı BEGIN IMMEDIATE içinde saved plan/onay ve her kullanılan credential ID/revision/hedefini tekrar karşılaştırır. Tek çağrının private credential snapshot'ı bir kez çözülür. Aynı planın tekrarı yalnız mevcut job döndürür, ephemeral sahiplik/permit üretmez. Lease 30 s; yenileme semantic revision/fence'i değiştirmez. Geçerli predispatch takeover yeni aday açar, postdispatch takeover aynı attempt için yalnız recovery sahipliği alır. Yetim predispatch kaydın revoke/expiry/yeni approval nedeniyle kesin yerel cleanup'ı env/config okumadan terminalleştirir.

Submitted latch commit'i dış çağrıdan öncedir. Permit PID/thread/tek kullanım sınırını korur; copy/deepcopy/pickle ve fork çocuğu kullanamaz. Dış port mutlak monotonic deadline alır; min(kalan çağrı,kalan lease)−5 s sonuç payı korunur. Deadline için UTC yalnız durable clock transaction'ı içinde gözlenir; commit edilmiş son UTC ile transaction öncesi monotonic örneği birlikte konservatif hesaplanır. Timeout/connection-refused/yanıt kaybı ikinci gönderim hakkı üretmez. Receipt aynı correlation/authority ve current owner tuple ile yazılır.

İlk hedefli takım **30 passed / 11,39 s**. İki ayrı gerçek süreç admission yarışında tek operation/attempt/intent ve tek fsync'li sentetik subprocess etkisi üretildi. İki hizmet × admission/arm final transaction credential yarışları state_changed ve sıfır port verdi. Dokuz gerçek SIGKILL kesiti (admission/arm önce-orta-sonra, etki sonrası yanıt kaybı ve receipt orta-sonra) SQLite yeniden açılışıyla doğrulandı; latch commit edilmişse hiçbir resume ikinci start yapmadı. Paused eski sender lease devri sonrası bir geç dış etki yapabildi; yeni owner kaydını değiştiremedi ve yeni owner start yapmadı. Bu test yerel fencing'in dış etkiyi durdurma garantisi olmadığını somut gösterir. Sonuç payına yakın kooperatif portun receipt'i kalıcı oldu; pay tüketilmişse port sıfır kaldı.

Ruff format/lint ve strict mypy geçti. İlk uygulama 7d75322 ile commit edildi; bu head tam takımda **1.452 passed / 203,00 s** verdi. Aşağıdaki review düzeltmeleri ayrı kanıttır; adım/kart henüz kapanmadı. Sentetik subprocess gerçek EVREN/HTTP/GPU kanıtı, SIGKILL fiziksel disk/güç kaybı kanıtı değildir.

### Adım 2 — Birinci review turu

7d75322 üzerinde farklı iki fresh reviewer (GPT-6 Astra high dayanıklılık, GPT-6.1 Sol high sözleşme/sır/test) dört doğrulanmış bulgu verdi. Root, fork commit sınırında aynı attempt ile iki gerçek subprocess etkisini, iki provider alanında sır yansımasını ve bozuk ID'nin ValueError kaçışını önce başarısız regresyonlarla yeniden üretti. Büyük ama geçerli/onaylı planın admission 8 KiB sınırını aşması bağımsız repro ve root regresyonuyla doğrulandı. Root ayrıca fence taşması/başlangıç bütçesinde bilinen ID kaybını ve başka stateful çağrının lease expiry gözlemi sonrası saat gerilemesinde yanlış hata kodunu doğruladı. Altı kök neden düzeltildi; atlanan bulgu yoktur.

- Permit arm öncesinde oluşturulur; coordinator origin PID'si sabittir. Arm dönüşü/port dönüşü ve catch sınırındaki fork child DB/uncertain yazısı yapamaz. Gerçek arm→fork→iki normal devam regresyonunda yalnız bir etki kalır.
- Provider ID/status, kalıcılık öncesi yakalanmış credential secret'leriyle karşılaştırılır; echo kontrollü unknown olur, sır JobView/attempt payload'a yazılmaz.
- Büyük admission kontrollü plan_not_valid verir; operation/port sıfır kalır. Malformed ID sarmalamadan önce doğrulanır, hata zarfında null kalır.
- Repository ve application hata sınırı bilinen canonical operation ID'yi fence/kapasite/bütçe/validation hatalarında korur; kapalı reason/capacity alanları kaybolmaz.
- Durable stamp anomaly'si mevcut sahip için operation_lease_lost verir; eski lease saat geri dönüşüyle canlanmaz.

Düzeltme sonrası geniş operation/model/approval hedefli takım **180 passed / 46,95 s**; ek hata-bağlamı regresyonlarıyla coordination takımının tamamı **39 passed / 14,32 s**. Ruff/lint ve strict mypy başarılı. İkinci tur farklı fresh reviewer'larla devam eder; Step 3/4'ün planlanan özellikleri ilk iki adımın teslimi diye gösterilmez.

### Adım 2 — İkinci review turu

R1 fix 2ba731e sonrasında iki farklı fresh reviewer (GPT-6 Astra high ve GPT-6.1 Sol high) aynı iki P2 kök nedenini bağımsız doğruladı. Final transaction'da lease expiry veya clock generation/anomaly reddi güvenle rollback olmasına rağmen capability_expired/state_changed dönüyordu. Yarışın kaybedeni mevcut operation'ı bulup son kontrolde hata alınca kullanılmamış aday UUID'sini döndürebiliyor; hızlı lookup da ID'yi null bırakabiliyordu. Root dört başarısız negatifle doğruladı.

TimeGate varsayılan capability davranışını koruyup kontrol sahibine özgü clock/range hata kodu taşır. Ownership transaction'ı clock gereksinimini ilk pre-yield kontrolden önce kurar; giriş ve son kontrol lease_lost verir. Credential/approval state_changed ve execution bütçesi topluca yeniden sınıflandırılmaz. İlk delta review'u stamp ile transaction girişindeki ek saat yarışı penceresini buldu; root bir negatif/bir pozitif kontrolle doğrulayıp kapattı. OperationPhase, mevcut DB kimliğini canonical olarak doğrulayıp decode'dan önce hata bağlamına alır; read/final-transaction/post-check aynı kalıcı ID'yi kullanır.

İlk geniş delta takımı **237 passed / 69,08 s**; son giriş/final expiry/gerileme ve lookup/race read/bütçe regresyonları **8 passed / 2,46 s**. Ruff/strict mypy geçti. Son fix ee7f7a3 üzerinde tam takım **1.469 passed / 196,27 s**. İki reviewer son giriş/final hata ve ID deltalarını kapattı; sözleşme reviewer'ı giriş anomaly/default cache/credential değişimini ayrıca bağımsız SQLite örnekleriyle doğruladı. Ruff/lint/strict mypy, belge/ajan/diff başarılı. Adım 2 iki fresh review turu ve doğrulanmış fix commit'leriyle kapandı; açık bulgu yok. P01-4b adım 3 ve public jobs adım 4 hâlâ uygulama/kabul bekler.

## Adım 3 — Trusted read, terminal sonuç ve reset v3

İç ReadPort için current read authorization ile typed observation ayrıldı. Yeni public run/reconcile/backend kaydı yoktur. Eski plan/onay expiry'si read-reconcile yolunda execution validation/hash tekrarı başlatmaz; hedef/account/project korunur, yeni credential nesli yalnız current read için kullanılır. Tam credential snapshot son transaction'da tekrar karşılaştırılır. Wrong target/run/correlation, not_found, 401/yetkisizlik, cancel-accepted, timeout ve yanlış delivery/exit kanıtları unknown kalır; execution succeeded teslim belirsizliği yüzünden kaybolmaz. Terminal OperationOutcome yalnız başarılı kalıcılıkta döner; write/commit belirsizliği operation_uncertain/5 ve outcome_write_failed/unknown ile sınırlandırılır. Zaten commit edilmiş terminal kayıt yeniden açılmaz.

Preview v3 strict root/snapshot/count/digest doğrulaması ve tam operation semantic fingerprint'iyle bağlandı. Heartbeat digest'i değiştirmez, owner/result değişimi değiştirir. Modern reset aynı writer transaction'da consent+tam başlangıç doğrulaması ve mutasyon sonrası tam doğrulama yapar. Yeni epoch/K owner'ı düşürür; prearm cancelled, armed unknown olur; immutable event/terminal outcome/plan/onay snapshot'ı korunur. +1 yıl UTC→düzelt→reset→reconcile gerçek eski timestamp'leri koruyarak beklemeden çalışır. Yeni reset UTC gözlemi yeni clock watermark'ında kalıcıdır. Tarihsel schema-5 runtime replay'i v2 tipleriyle, güncel runtime tek v3 tipiyle çalışır; restore/recover kapısı genişletilmedi.

Yeni yedi SIGKILL kesiti terminal outcome öncesi/ortası/sonrası ve armed/unarmed reset ortası/sonrasını gerçek süreçte sınadı; **7 passed / 3,45 s**. Forget/admission ve revoke/arm'ın iki yanı, ayrıca aktif composition/exclusive reset yarışı ayrı süreçte **5 passed / 3,37 s** verdi. 16 adayda cleanup ve fence MAX durumunda credential reset, 1.024 lease'in başka stateful çağrıda expiry gözlemi/geri saatte dirilmeme ve tüm plan slotlarının pinlenmesi **3 passed / 4,05 s**. Son kaynakta geniş coordination/reconcile/crash hedefli takım **100 passed / 37,29 s**, bağımsız strict scalar wire/preview matrisi **33 passed / 0,46 s**, warmed row-proof/live relationship negatifleri **14 passed / 4,23 s**. Bunlar full takım ve Step 3 review kapanışının yerine geçmez.

Uygulama sırasında root iki süreçli credential yarışını predispatch takeover'a da genişletti: iki hizmette önce iki negatif başarısız oldu. İkinci aşamadaki private current snapshot kontrolü cleanup kararından önceye alındı; ilk DB-only cleanup hâlâ env/config okumaz. Şimdi admit/arm/takeover × iki hizmet **6 passed / 3,11 s**. Sahip scope/expiry bozulmalarının altı warm/full negatifi ve current store'un gelecekteki recovery generation'ının iki negatifi de önce yeniden üretilip decoder/clock denetimleriyle kapandı. Terminal persist belirsizliği üç regresyonla önce yanlış kodu üretti; fix sonrası **3 passed / 1,24 s**. Bu kaynaklar yeni core'un doğrulamasıdır, canlı EVREN veya güç kesintisi kabulü değildir.

### Adım 3 kaynak çalışması — yöntem ve ilk tanı

1.024 operation × 16 attempt × 256 normal geçişli, maksimum cache/plan payload'lı yeni sentetik terminal store ilk tanısal koşuda 5 s bütçesinde state_busy verdi; bütçe kaldırılmış tek tanı 8,35 s idi. Bunlar başarılı kabul sayılmaz. Profil tekrarlanan scalar UUID/UTC/Unicode çözümlemesi ve immutable plan decode/JSON serilemesini gösterdi. Bütçeler/DDL/SQL motoru ve kayıp davranışı değiştirilmedi.

Pure UUID/UTC parsing 4.096 değerle bounded cache kullanır; current clock/authorization kararı cache'lenmez. Strict JSON duplicate/non-finite/UTF-8 denetimi korunur. Scalar event UUID/UTC/literal/int alanları kendi sıkı doğrulamasıyla çözülür; genel serbest-text taraması ve ikinci JSON parse bu kapalı scalar nesnede tekrarlanmaz. Diğer wire modellerinin JSON/dizi davranışı korunur. Pure plan facts tam current SQL row bytes'ı üzerinden, attempt kümeleri bütün current index/payload satırları üzerinden doğrulanır. History proof her seferinde okunan en çok 257 row'un tamamının fingerprint'ine ve immutable admission/candidate bağlarına dayanır. Güncel projection/counter/clock/DB ilişkileri her okumada yeniden denetlenir. Toplam 4.096 scoped memo sınırı korunur; bütün 262.144 event bellekte tutulmaz. Bozulan row/index/plan/outcome'un warmed proof'u kullanarak kaçması negatiflerle sınanır.

Tanısal aynı-fixture koşuları yaklaşık 3,0 s full/2,9 s preview/3,7 s reset'e indi; **henüz nihai kaynak kabulü değildir**. Sonraki ölçüm [probe](p01-4-operation-budget-probe.py) ile normal/azami terminal/karma, her biri üç yeni store ve fresh worker'da yapılır. Deadline callback'in n=1.000 quantum'u ve bütün çağrıları korunur; VM kaydı callback×quantum örneklemesidir, exact opcode sayısı iddia edilmez. Probe helper'ının interrupt/delegation/işaretlenmemiş-store ve yanlış import/interpreter ret kontrolleri son kaynakta **5 passed / 0,09 s**. Normal/azami hacim ölçümü aşağıda kayıtlıdır. Full test, raw bütçe kabulü, commit ve iki fresh review turu tamamlanmadan P01-4b verified yapılmaz.

### Adım 3 ilk bütünleşik doğrulama ve kaynak kabulü

Runtime kaynakları sabitken tam takım **1.580 passed / 239,09 s**; Ruff format/lint, strict mypy (49 kaynak), 114 Markdown ve 6 skill/9 kart denetimi geçti. Sonrasında probe ortam guard'ının iki ek negatif testiyle beş helper testi ayrıca geçti. Bu sayıların toplamı yeni bir full test koşusu diye sunulmaz. Ürün commit'i sonrası iki fresh review turu sıradadır; P01-4b henüz verified değildir.

[Ham 27 işlem](p01-4-step-3-operation-budget.json): Apple M5 Max, macOS 27.0.1 arm64, CPython 3.11.18, SQLite sürümü ham kayıtta, doğrulanmış SSD/APFS; repo frozen .venv/editable import kökeni açıkça denetlendi. Her layout için üç yeni store ve her işlem için ayrı worker; hazırlık/hash maliyeti kullanım senaryosu süresine dahil değil, OS/disk cache'i boşaltılmadı. Test/build/başka profiler eşzamanlı çalıştırılmadı. İlk kaynak çalışma ağacı tabanı 0b8c2cf; runtime/seeder/probe SHA-256'ları ölçüm boyunca sabit. Commit hash'i yerine bu tam kaynak haritası ölçülen içeriği tanımlar.

Aşağıdakiler her grubun üç örneğindeki **en yüksek** değerdir; 3 örnek p95 diye adlandırılmaz. 27/27 çağrı kendi özgün 5 s kontrol deadline'ıyla ve wall ölçümünde 5.000 ms altında tamamlandı; timeout başarı sayılmadı, örnek atılmadı. SQLite VM bilgisi özgün n=1.000 progress callback'inin çağrı×quantum örneklemesidir; her callback deadline'a delege edildi, exact opcode sayısı iddia edilmez.

| Fixture | Operation / attempt / normal event / terminal outcome | Full ms | Preview ms | Reset ms | Tepe süreç RSS MiB |
|---|---|---:|---:|---:|---:|
| Normal | 1.024 / 1.024 / 3.072 / 0 | 474,87 | 551,79 | 1.123,24 | 58,17 |
| Terminal yoğun | 1.024 / 16.384 / 262.144 / 1.024 | 3.730,45 | 3.749,24 | 4.672,95 | 73,25 |
| Karma yoğun | 1.024 / 16.384 / 261.632 / 512 | 3.735,61 | 3.758,50 | 4.961,40 | 83,66 |

Yoğun fixture'lar 1.024 cache / **33.554.432 byte**, 1.024 plan / **67.108.864 byte**, 1.024 onay / **619.520 byte** taşır. Karma fixture'da operation payload **2.150.912**, attempt **4.480.938**, normal event **85.628.416**, outcome **84.992 byte**; diğer layout'ların gerçek byte sayıları ham kayıttadır. Bu kaynak kabulü normal event/aday sayısının ve eski cache/plan byte kotalarının üst hacmini ölçer; her yeni metadata nesnesinin teorik byte limitine aynı anda ulaşıldığı iddia edilmez. Fixture sentetik ve yapısal olarak geçerli arşivdir; geçmiş onay snapshot'ı güncel yürütme yetkisi veya gerçek sağlayıcı başarısı değildir.

Plan/onay/normal history/terminal outcome hash'leri bütün işlemlerde değişmedi; reset cache'i boşaltıp owner'ları kaldırdı, operation/attempt/event/outcome satır sayıları korundu. Karma fixture 255 normal geçişi dolu 512 nonterminal işin reset'ini de pozitif tamamladı; terminal 512 sonuca dokunulmadı. Son karma reset'te tam başlangıç doğrulaması 3.706,78 ms, son tam doğrulama 840,68 ms, COMMIT 33,29 ms idi; kalan süre onay fingerprint'i ve mutation/key/dosya akışıdır. **4.961,40 ms sınırın yakınıdır**; bu yalnız kayıtlı referans ortam/hacim kabulüdür, Linux CI veya farklı veri/host sonucu değildir. Review'da kaynak yolu değişirse etkilenen kabul tekrar değerlendirilecek; önceki kayıt korunur. İlk adımın a73608a migration ham kaydı hâlâ tarihsel olup son kaynak migration kabulü paket kapanışında ayrıca kontrol edilecektir.

### Adım 3 — Birinci review turu

83f55bc üzerinde üç fresh salt-okunur reviewer (GPT-6 Astra xhigh state/dayanıklılık, GPT-6.1 Sol high sözleşme/credential, GPT-6 Astra high kaynak/memo) çalıştı. Örtüşen yorumlar üç kök nedende birleşti; ana ajan her birini mevcut kodda yeniden üretti. Kaynak reviewer ayrıca 245 scalar varyantı eski doğrulamayla karşılaştırdı (sıfır ayrışma), wire/probe/memo takımında 75 test geçti. Yorum metni uygulama talimatı sayılmadı; doğrulanan üç konu düzeltildi, geçerli olmadığı için atlanan bulgu yoktur.

| Bulgu | Minimal düzeltme / regresyon |
|---|---|
| Başarısız read observation final credential/read-grant kapısını atlıyordu | ReadFailure doğrulanmış grant'i taşır; read_failed transaction'ı current request/credential ve varsa grant süresini yeniden karşılaştırır. Authorize öncesi ret, timeout, malformed, grant expiry ve outcome-write fallback yarışları ayrı negatiflerdir. İlk dispatch uncertainty sınırı korunur |
| Aynı owner running → unknown → submitted toparlanması state_invalid veriyordu | Bounded recovery'nin semantic revision boşluğu veya artan fence kalıcı tanıktır. Doğrudan running → submitted evidence_mismatch olur; recovery tanığı olmayan ardışık bozuk history warm/full okumalarda reddedilir. Restart/full validation, aynı attempt/latch ve tek sentetik etki doğrulandı |
| Local planning authority uzak execution kanıtı sayılıyordu | Plan validation, receipt ve observation aynı execution-service seçimini kullanır; exact snapshot/hedef üyeliği ayrıca korunur. Remote + planning.offline içeren gerçek prepared planda yanlış receipt/observation unknown kalır; terminal başarı oluşmaz |

Yeni ilk regresyon koşusunda sekiz negatif beklenen davranışı vermedi; authorize-denied pozitif sınır geçti. Son hedefli 167 testin 165'i geçti; iki yeni bozuk-history fixture'ı transaction dışı append yaptığı için düzeltildi ve ikisi ayrıca geçti. Bunlar ürün kusuru diye sayılmadı. Son kaynakta tam takım **1.594 passed / 251,88 s**; Ruff format/lint, strict mypy (42 kaynak), 114 Markdown, 6 skill/9 kart ve diff kontrolleri geçti. İkinci fresh review turu sıradadır.

83f55bc kaynak haritasını taşıyan önceki 27/27 kaynak ölçümü tarihsel olarak korunur. Bu review'da runtime değiştiğinden güncel kabul yerine kullanılmaz; ikinci fresh review sonrası son kaynak haritasıyla yoğun kaynak kabulü yeniden yapılacaktır. 4.961,40 ms'lik ilk karma reset marjı açık performans sınırıdır; eşik gevşetilmez.

### Adım 3 — İkinci review ve son kaynak kabulü

0092d40 üzerinde farklı üç fresh salt-okunur reviewer (GPT-6 Astra xhigh state/dayanıklılık, GPT-6.1 Sol high sözleşme/credential, GPT-6 Astra high doğrulama/kaynak) yeni doğrulanmış kusur bulmadı. State reviewer 27 gerçek-store/kesinti/recovery negatifini; sözleşme reviewer 56 reconciliation + 47 wire/relationship testini; kaynak reviewer 52 wire/probe + 23 memo testini çalıştırdı. Bağımsız eski/yeni scalar event karşılaştırması **486 varyantta sıfır ayrışma** verdi. Bu hedefli sayılar yeni full koşu diye toplanmaz. Son runtime kaynağındaki tam takım 1.594 testtir; default strict mypy src/scripts birlikte 49 kaynakta da geçti. Yeni fix gerekmedi.

Bütün reviewer/test süreçleri bittikten sonra, kaynak sabitken [yeni ham 27 işlem](p01-4-step-3-reviewed-operation-budget.json) aynı doğrulanmış SSD/APFS/M5 Max/editable .venv ortamında çalıştırıldı. Kaynak haritası 0092d40'a aittir ve ölçüm boyunca değişmedi; önceki kayıt ezilmedi. **27/27** işlem özgün 5 s deadline ve n=1.000 callback delegasyonuyla pozitif tamamlandı. Plan/onay/event/outcome hash ve hacimleri, satır sayıları ve reset etkileri korundu; örnek atılmadı. Aşağıdaki değerler üç örneğin maksimumudur:

| Fixture | Full ms | Preview ms | Reset ms | Tepe RSS MiB |
|---|---:|---:|---:|---:|
| Normal | 471,95 | 560,53 | 1.101,16 | 57,98 |
| Terminal yoğun | 3.719,60 | 3.734,19 | 4.646,95 | 73,59 |
| Karma yoğun | 3.705,52 | 3.778,71 | 4.936,65 | 83,44 |

Hacimler önceki kaynak kabulündekiyle aynı kotalardadır; gerçek her örneğin byte/row bilgisi ham kayıttadır. Karma reset'in **63,35 ms** marjı hâlâ dardır; bu kayıt diğer host/işletim sistemi veya her olası payload için kesin süre garantisi değildir. Eşik gevşetilmedi, timeout başarı sayılmadı.

Ardından aynı sabit 0092d40 runtime kaynağıyla [24 yeni migration örneği](p01-4-step-3-reviewed-migration-budget.json), özgün 5 s deadline/callback açıkken eski şema 2/3/4/5'ten şema 6'ya ulaştı; **24/24 geçti**. Her şema/hacim için üç fresh store/worker; normal maksimumları sırasıyla 1.112,27 / 1.356,27 / 1.407,47 / 957,51 ms, yoğun maksimumları **2.468,95 / 4.337,37 / 4.336,78 / 3.270,34 ms** oldu. Kaynak payload/satırları korundu, yeni operation tabloları boş kaldı ve son full validation geçti. CPU/OS/Python/SSD/APFS, kaynak hash'leri, VM/faz kayıtları ham dosyadadır. Bu yeni kabul ilk adımın tarihsel a73608a ölçümü yerine güncel kodu bağlar; eski kayıt silinmedi.

**P01-4b bu dalda verified:** adım 1–3 uygulama, her adımda iki fresh review turu ve doğrulanmış fix'ler, 1.594 test, 27 operation + 24 migration pozitif kaynak kabulü tamamlandı. Public jobs/kurulu artefakt/200 ms kabulü adım 4'te tamamlanacak; paket PR'ı henüz açılmadı.

## Adım 4 — Public yerel jobs ve ilk bütünleşik doğrulama

`api.list_jobs/show_job` ve `jobs list/show` Accepted exact sözleşmeyle eklendi. Query Result v1 completed/null + local_history_only döner; iş durumu data'dadır. CLI text execution/delivery'yi ayrı gösterir ve kaydın stale olabileceğini söyler. Public run/backend/reconcile/watch/stop açılmadı; normal prepare job yaratmaz. Stateful query state'i açıkça açar; config/env/girdi/provider çözümü yapmaz.

Liste sayfada en çok 101 operation/plan satırı, 1.601 attempt satırı, sayfa başına bounded outcome/son event alır. Beş SELECT ve BEGIN/ROLLBACK ile sayfa başına yedi statement; 1 ve 7 kayıtta aynı query sayısı gerçek SQLite trace ile doğrulandı. History count/min/max indeks üzerinden, yalnız son payload toplu join'le okunur; bütün geçmiş payload zinciri show/full doğrulamadadır. Strict ortak plan/approval/attempt/outcome/clock/projection kuralları saf yardımcıya ayrıldı; current clock snapshot'ı listede bir kez okunur, execution/full consumer'ları canlı ilişkileri ve bütün history zincirini doğrulamayı sürdürür. Immutable migration 1–5/handler/şema 6 manifesti değiştirilmedi.

Kapalı cursor store/filtre ve artan immutable created_at/ID anahtarına bağlıdır; bool/float/duplicate/non-finite/UTF-8/extra/padding/oversize ve yanlış store/filtre reddedilir. İki sayfa arasında durum değişirse ilan edilen yeni snapshot sınırı korunur. Gerçek ikinci SQLite bağlantısında atomik sahiplik/attempt değişimi hazırken açık reader snapshot'ı commit'i bekletir; list/show eski tutarlı kaydı, sonraki sorgu yeni kaydı görür. İlk test düzeni coordinator'ın daha erken clock transaction'ında bloklandığından, doğrudan geçerli ownership transaction'ıyla interleaving sınırı düzeltildi; ürün kusuru sayılmadı.

İlk ürün kaynağında **1.686 passed / 274,40 s**, Ruff ve strict mypy (51 src/script kaynağı), 114 Markdown ve 6 skill/9 kart kontrolleri geçti. Sonrasında kayıp ID'nin CLI hata eşliği ve liste metninin cursor/boş durum kabulü ayrıca genişletildi; son hedefli jobs/fixture/probe takımı **93 passed / 21,14 s** verdi; bunlar yeni full koşu diye sunulmaz. Ölçüm helper'ındaki göreli executable yolu ön kontrolde hata verdi ve hiç örnek üretmedi; venv symlink'i korunarak mutlak yol kullanımı düzeltildi, altı helper testi yeniden geçti. İlk ham ölçümler aşağıdadır; iki fresh review turu henüz tamamlanmadı.

### Kurulu jobs performansı ve veri hacmi

[İlk jobs ham kaydı](p01-4-step-4-initial-jobs-budget.json), M5 Max/macOS 27.0.1/CPython 3.11.18/SSD/APFS üzerinde, geliştirme araçları içermeyen ayrı frozen runtime venv'e kurulu wheel'i kullanır. Her modda ilk süreç ayrı, üç warmup ve **30 yeni süreç**; nearest-rank p95, tüm örnekler ve tam kaynak hash haritası korunur. Kaynak ölçüm boyunca değişmedi, kurulu tüm Python kaynak baytları checkout adayıyla eşleşti. Setup/hash/ek tanısal worker süreleri komut ölçümüne katılmadı; OS cache'i boşaltılmadı ve fiziksel soğuk başlangıç iddiası yoktur. Yeni jobs için önceki sürüm karşılaştırması uydurulmadı; mutlak 200 ms hedefidir.

| Yol | p95 ms | Sınır ms | Ayrı tanısal worker tepe RSS MiB |
|---|---:|---:|---:|
| Normal list | 111,119 | 200 | 46,11 |
| Normal show | 104,767 | 200 | 45,25 |
| Yoğun list | 165,678 | 200 | 53,61 |
| Yoğun show | 104,372 | 200 | 45,98 |

Normal fixture bir operation/plan/onay/cache, bir attempt ve üç event; yoğun fixture 1.024 operation/plan/onay/cache, **16.384 attempt / 262.144 event / 1.024 outcome** taşır. Yoğun plan payload'ı **67.108.864 byte**, cache 33.554.432 byte, attempt 4.854.784 byte, event 85.798.912 byte, outcome 169.984 byte'dır. Her plan 65.536 byte; current provider ID/status 256/128 karakter sınırındadır. Kapalı historical attempt/outcome nesneleri serbest padding alanı taşımadığından teorik bütün byte kotalarının aynı anda doldurulduğu iddia edilmez; gerçek maksimum payload'lar ham kayıttadır. Yoğun show dış Result 71.063 byte'dır; JobView'un 256 KiB sınırı ayrıca decoder'da korunur.

Ek tanısal worker bütün interpreter/import yaşamının RSS tepesini ölçer; timed CLI süreçlerinin tek tek RSS'i diye sunulmaz. Açılış dahil list/show 44/46 SQLite statement üretir; saf sayfa sorgusunun yedisi bunun alt kümesidir. Özgün n=1.000 deadline callback'i korunur; yoğun list/show örneklenmiş VM quanta 203.000/2.000'dir ve bütün callback'ler orijinale delege edilir. Normal örnekte callback sıfır olması gerçek VM adımının sıfır olduğu anlamına gelmez. Bütün jobs sorgularından sonra kaydedilen logical hacimler, immutable history/plan/outcome hash'leri, epoch, lease sayısı ve durum sayıları aynı kaldı. Bu snapshot bütün mutable payload baytlarının hash'ini kaydetmez.

### Artefakt, yardım ve mevcut başlangıç kapıları

[İlk iki temiz kurulum](p01-4-step-4-initial-installations.json): wheel **50**, sdist **310** izinli üye. İkisinde de konsol/import kökeni ve eski v1/cache/execution + yeni boş olmayan jobs CLI/API/text smoke geçti. Kurulu ölçüm wheel SHA-256'sı ve temiz kurulum wheel'i aynıdır: `03829c63cd3e0b2c0206ddcb92a8456489c7c5a4711566be000201ac200398b3`. Fixture kaynak geliştirme ortamında hazırlanır; temiz runtime'a pytest veya fixture backend kurulmaz. Bu ilk build kanıtıdır, yayın veya son review head artefaktı değildir.

[30 yardım çıktısı](p01-4-initial-help-parity.json) adım 3 sonuyla karşılaştırıldı: 29'u bayt düzeyinde aynı, kökte yalnız beklenen jobs seçeneği/açıklaması değişti. Yeni jobs/aile/fiil yardımının metadata guard'ı da geçti.

[İlk eşli startup kabulü](p01-4-step-4-initial-startup.json), development a9f1f2e detached checkout'u ile bu adayın ayrı frozen wheel/runtime ortamlarını aynı host'ta AB/BA sırasıyla ölçer. Üç warmup + 30 çift, eşit 1.024 cache/1.212.625 payload byte ve bütün örnekler korunur; kaynak sabittir. Aday p95 help **24,766**, version **23,005**, context **72,323**, cache **112,890 ms** ile mevcut 500/200 ms kapılarını geçti. Bu yerel kabul Linux PR/merge çıktısı değildir; kullanıcının açık tercihiyle o dış takip paket PR'ında değerlendirilecektir.

## Sonraki adımlar

Adım 1–3 commit ve ikişer fresh review turuyla kapandı; adım 4 ilk uygulama/kabulü sonrası commit ve iki fresh review turu sıradadır. Son runtime kaynağı değişen operation decoder yolu için yoğun kabul paket kapanışında tekrar değerlendirilecek. Fiziksel güç kesintisi, gerçek EVREN/ForgeLM, Windows veya yayımlanmış paket kanıtı yoktur. PR ancak bütün paket tamamlandıktan sonra development'a açılır ve kullanıcı incelemesine bırakılır.
