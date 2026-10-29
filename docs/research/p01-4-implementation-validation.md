# P01-4 uygulama ve kabul kaydı

**Güncellendi:** 2026-10-29. **Durum:** Dört adım ve her adımın iki bağımsız inceleme turu tamamlandı. PR #10 kullanıcı bulguları kapandı; **182f695 ürün kaynağında bütünleşik yerel kabul tamamlandı**. **Dal:** feat/p01-4-operations, development tabanı a9f1f2e. İlk paket kabulü 17de965; kalite/bütçe takipleri ve sonraki kullanıcı bulgusu aşağıda ayrı kaynaklarla kayıtlıdır. [Teslim planı](../roadmap/p01-4-delivery-plan.md), [karar/inceleme kaydı](p01-4-readiness-review.md). Önceki durum ve ölçümler kendi kaynaklarının tarihsel kanıtıdır; güncel durum bu giriş ve son bölümde belirtilir. PR #10 açıktır; development merge'i, Master aktarımı ve release ayrı kalır.

## Karar kapanışı

Kullanıcı 29 Ekim review bulgularını doğrulayıp kapattıktan sonra ADR-0016'nın Accepted yapılmasını ve uygulamayı yetkilendirdi. İki ek inceleme ve ikişer fresh reviewer'lı iki revizyon turu sonrasında karar c3dbfe7 ile Accepted kaydedildi. Aynı karar için yeni onay sorulmadı. Önceki startup bakımının dört commit'i ve 8c2dec2 hazırlık commit'i bu dalda korunur; ayrı PR/test merge yapılmaz.

## Adım 1 — Şema ve gerçek kalıcı consumer

Yeni SQL-only V2 5→6 adımı operations, operation_attempts, operation_events ve operation_outcomes tablolarını; plan UNIQUE/FK RESTRICT, deferred dispatch-attempt FK ve sıralama/status/lease indekslerini ekler. Checksum **62ac619e29aaaf2d9c838bde2a0ee795e7496f67107eaf69e26daaf9d4b4b90a**. Yayımlanmış 1–5 checksum'ları ve donmuş capability-expiries handler SHA-256'sı b1ffc8e3ce1dc6fc04c2afe4c2aa50ed6cd2e26deaf0b07ef0caab6fc0c83d18 aynen kaldı; golden testler kimliği sürüm indeksiyle kontrol eder, “son migration daima 5'tir” varsayımı kaldırıldı.

Strict domain modelleri, execution/delivery reducer, authority/admission allowlist'i, immutable approval snapshot, owner tuple ve kapalı hata zarfı eklendi. Gerçek SQLite repository snapshot okuması plan/attempt/event/outcome ve projection ilişkilerini, kotaları ve terminal/dispatch sınırını denetler. Salt modele alan eklemek yerine kayıt/restart/rollback/bozuk veri ve plan forget tüketicisiyle bağlandı. Yeni product run/fixture backend/jobs komutu henüz yoktur.

Operation-capable runtime'ın mevcut restore/recover allowlist kapısı gerçek şema 6 ile kapanır; boş store/eksik hedef/kayıp kaynakta bile I/O öncesi ret testlenir. Tarihsel şema 5 restore/cut testleri açık schema5_runtime fixture ve child replay ile korunur; güncel runtime kapısı gevşetilmez, test skip/xfail eklenmez. P01-3 veri migration probe'u standalone tarihsel şema 5'i açıkça seçer; eski ham ölçümler değiştirilmez. Yeni migration probe'u güncel şema 6'yı ayrı ölçer.

İlk yeni hedefli takım 61 başarılı; schema-5 replay düzeltmeleri sonrası bakım/cache/yeni model/repository hedefli takım 235 başarılı. İlk geniş koşudaki tarihsel CLI/runtime sürüm beklentileri doğrulandı ve fixture sınırları düzeltildi; bu başarısız koşu kabul sayılmaz. Son tam takım **1.387 passed / 181,31 s**; Ruff format (79 dosya)/lint, strict mypy (38 kaynak), 114 Markdown, 6 skill/9 kart ve diff kontrolü başarılı. Review turları henüz başlamadı; adım/kart/paket verified sayılmaz.

Ölçüm yöntemi [p01-4-state-budget-probe.py](p01-4-state-budget-probe.py): sadece yeni sentetik private store, şema 2/3/4/5 ve normal/maksimum geçerli payload hacimleri, her yol üç yeni örnek; yeni worker process, açık 5 s deadline ve korunmuş progress callback. SQL VM-step, backup/hash/sync/DDL/full-validation/commit fazları, orijinal payload/row SHA ve son şema kaydedilir. Ölçüm sırasında kaynak hash'leri sabit kalmalıdır. Henüz ölçülmemiş operation dolu-store/recovery/job performansı bu adımın kanıtı diye anlatılmaz.

### İlk migration kaynak kabulü

[Ham 24 koşu](evidence.md#p01-4-step-1-migration): Apple M5 Max, macOS 27.0.1 arm64, CPython 3.11.18, SQLite sürümü ham kayıtta, SSD/APFS. Kaynak c3dbfe7 üzerindeki adım 1 çalışma ağacının dosya SHA-256'larıdır; ölçüm öncesi/sonrası aynıdır. Başka ağır test çalışmadan ölçüldü. Bütün koşular gerçek şema 6'ya, sıfır operation ile ve mevcut 5 s deadline açıkken ulaştı; eski payload satır SHA'ları eşit kaldı. VM progress sayımı deadline callback'ini korudu. Bu tablo her üç örneğin **en yavaşıdır**, p95 veya genel donanım garantisi değildir.

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

[Ham 27 işlem](evidence.md#p01-4-step-3-operation-budget): Apple M5 Max, macOS 27.0.1 arm64, CPython 3.11.18, SQLite sürümü ham kayıtta, doğrulanmış SSD/APFS; repo frozen .venv/editable import kökeni açıkça denetlendi. Her layout için üç yeni store ve her işlem için ayrı worker; hazırlık/hash maliyeti kullanım senaryosu süresine dahil değil, OS/disk cache'i boşaltılmadı. Test/build/başka profiler eşzamanlı çalıştırılmadı. İlk kaynak çalışma ağacı tabanı 0b8c2cf; runtime/seeder/probe SHA-256'ları ölçüm boyunca sabit. Commit hash'i yerine bu tam kaynak haritası ölçülen içeriği tanımlar.

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

Bütün reviewer/test süreçleri bittikten sonra, kaynak sabitken [yeni ham 27 işlem](evidence.md#p01-4-step-3-reviewed-operation-budget) aynı doğrulanmış SSD/APFS/M5 Max/editable .venv ortamında çalıştırıldı. Kaynak haritası 0092d40'a aittir ve ölçüm boyunca değişmedi; önceki kayıt ezilmedi. **27/27** işlem özgün 5 s deadline ve n=1.000 callback delegasyonuyla pozitif tamamlandı. Plan/onay/event/outcome hash ve hacimleri, satır sayıları ve reset etkileri korundu; örnek atılmadı. Aşağıdaki değerler üç örneğin maksimumudur:

| Fixture | Full ms | Preview ms | Reset ms | Tepe RSS MiB |
|---|---:|---:|---:|---:|
| Normal | 471,95 | 560,53 | 1.101,16 | 57,98 |
| Terminal yoğun | 3.719,60 | 3.734,19 | 4.646,95 | 73,59 |
| Karma yoğun | 3.705,52 | 3.778,71 | 4.936,65 | 83,44 |

Hacimler önceki kaynak kabulündekiyle aynı kotalardadır; gerçek her örneğin byte/row bilgisi ham kayıttadır. Karma reset'in **63,35 ms** marjı hâlâ dardır; bu kayıt diğer host/işletim sistemi veya her olası payload için kesin süre garantisi değildir. Eşik gevşetilmedi, timeout başarı sayılmadı.

Ardından aynı sabit 0092d40 runtime kaynağıyla [24 yeni migration örneği](evidence.md#p01-4-step-3-reviewed-migration-budget), özgün 5 s deadline/callback açıkken eski şema 2/3/4/5'ten şema 6'ya ulaştı; **24/24 geçti**. Her şema/hacim için üç fresh store/worker; normal maksimumları sırasıyla 1.112,27 / 1.356,27 / 1.407,47 / 957,51 ms, yoğun maksimumları **2.468,95 / 4.337,37 / 4.336,78 / 3.270,34 ms** oldu. Kaynak payload/satırları korundu, yeni operation tabloları boş kaldı ve son full validation geçti. CPU/OS/Python/SSD/APFS, kaynak hash'leri, VM/faz kayıtları ham dosyadadır. Bu yeni kabul ilk adımın tarihsel a73608a ölçümü yerine güncel kodu bağlar; eski kayıt silinmedi.

**P01-4b bu dalda verified:** adım 1–3 uygulama, her adımda iki fresh review turu ve doğrulanmış fix'ler, 1.594 test, 27 operation + 24 migration pozitif kaynak kabulü tamamlandı. Public jobs/kurulu artefakt/200 ms kabulü adım 4'te tamamlanacak; paket PR'ı henüz açılmadı.

## Adım 4 — Public yerel jobs ve ilk bütünleşik doğrulama

`api.list_jobs/show_job` ve `jobs list/show` Accepted exact sözleşmeyle eklendi. Query Result v1 completed/null + local_history_only döner; iş durumu data'dadır. CLI text execution/delivery'yi ayrı gösterir ve kaydın stale olabileceğini söyler. Public run/backend/reconcile/watch/stop açılmadı; normal prepare job yaratmaz. Stateful query state'i açıkça açar; config/env/girdi/provider çözümü yapmaz.

Liste sayfada en çok 101 operation/plan satırı, 1.601 attempt satırı, sayfa başına bounded outcome/son event alır. Beş SELECT ve BEGIN/ROLLBACK ile sayfa başına yedi statement; 1 ve 7 kayıtta aynı query sayısı gerçek SQLite trace ile doğrulandı. History count/min/max indeks üzerinden, yalnız son payload toplu join'le okunur; bütün geçmiş payload zinciri show/full doğrulamadadır. Strict ortak plan/approval/attempt/outcome/clock/projection kuralları saf yardımcıya ayrıldı; current clock snapshot'ı listede bir kez okunur, execution/full consumer'ları canlı ilişkileri ve bütün history zincirini doğrulamayı sürdürür. Immutable migration 1–5/handler/şema 6 manifesti değiştirilmedi.

Kapalı cursor store/filtre ve artan immutable created_at/ID anahtarına bağlıdır; bool/float/duplicate/non-finite/UTF-8/extra/padding/oversize ve yanlış store/filtre reddedilir. İki sayfa arasında durum değişirse ilan edilen yeni snapshot sınırı korunur. Gerçek ikinci SQLite bağlantısında atomik sahiplik/attempt değişimi hazırken açık reader snapshot'ı commit'i bekletir; list/show eski tutarlı kaydı, sonraki sorgu yeni kaydı görür. İlk test düzeni coordinator'ın daha erken clock transaction'ında bloklandığından, doğrudan geçerli ownership transaction'ıyla interleaving sınırı düzeltildi; ürün kusuru sayılmadı.

İlk ürün kaynağında **1.686 passed / 274,40 s**, Ruff ve strict mypy (51 src/script kaynağı), 114 Markdown ve 6 skill/9 kart kontrolleri geçti. Sonrasında kayıp ID'nin CLI hata eşliği ve liste metninin cursor/boş durum kabulü ayrıca genişletildi; son hedefli jobs/fixture/probe takımı **93 passed / 21,14 s** verdi; bunlar yeni full koşu diye sunulmaz. Ölçüm helper'ındaki göreli executable yolu ön kontrolde hata verdi ve hiç örnek üretmedi; venv symlink'i korunarak mutlak yol kullanımı düzeltildi, altı helper testi yeniden geçti. İlk ham ölçümler aşağıdadır; iki fresh review turu henüz tamamlanmadı.

### Kurulu jobs performansı ve veri hacmi

[İlk jobs ham kaydı](evidence.md#p01-4-step-4-initial-jobs-budget), M5 Max/macOS 27.0.1/CPython 3.11.18/SSD/APFS üzerinde, geliştirme araçları içermeyen ayrı frozen runtime venv'e kurulu wheel'i kullanır. Her modda ilk süreç ayrı, üç warmup ve **30 yeni süreç**; nearest-rank p95, tüm örnekler ve tam kaynak hash haritası korunur. Kaynak ölçüm boyunca değişmedi, kurulu tüm Python kaynak baytları checkout adayıyla eşleşti. Setup/hash/ek tanısal worker süreleri komut ölçümüne katılmadı; OS cache'i boşaltılmadı ve fiziksel soğuk başlangıç iddiası yoktur. Yeni jobs için önceki sürüm karşılaştırması uydurulmadı; mutlak 200 ms hedefidir.

| Yol | p95 ms | Sınır ms | Ayrı tanısal worker tepe RSS MiB |
|---|---:|---:|---:|
| Normal list | 111,119 | 200 | 46,11 |
| Normal show | 104,767 | 200 | 45,25 |
| Yoğun list | 165,678 | 200 | 53,61 |
| Yoğun show | 104,372 | 200 | 45,98 |

Normal fixture bir operation/plan/onay/cache, bir attempt ve üç event; yoğun fixture 1.024 operation/plan/onay/cache, **16.384 attempt / 262.144 event / 1.024 outcome** taşır. Yoğun plan payload'ı **67.108.864 byte**, cache 33.554.432 byte, attempt 4.854.784 byte, event 85.798.912 byte, outcome 169.984 byte'dır. Her plan 65.536 byte; current provider ID/status 256/128 karakter sınırındadır. Kapalı historical attempt/outcome nesneleri serbest padding alanı taşımadığından teorik bütün byte kotalarının aynı anda doldurulduğu iddia edilmez; gerçek maksimum payload'lar ham kayıttadır. Yoğun show dış Result 71.063 byte'dır; JobView'un 256 KiB sınırı ayrıca decoder'da korunur.

Ek tanısal worker bütün interpreter/import yaşamının RSS tepesini ölçer; timed CLI süreçlerinin tek tek RSS'i diye sunulmaz. Açılış dahil list/show 44/46 SQLite statement üretir; saf sayfa sorgusunun yedisi bunun alt kümesidir. Özgün n=1.000 deadline callback'i korunur; yoğun list/show örneklenmiş VM quanta 203.000/2.000'dir ve bütün callback'ler orijinale delege edilir. Normal örnekte callback sıfır olması gerçek VM adımının sıfır olduğu anlamına gelmez. Bütün jobs sorgularından sonra kaydedilen logical hacimler, immutable history/plan/outcome hash'leri, epoch, lease sayısı ve durum sayıları aynı kaldı. Bu snapshot bütün mutable payload baytlarının hash'ini kaydetmez.

### Artefakt, yardım ve mevcut başlangıç kapıları

[İlk iki temiz kurulum](evidence.md#p01-4-step-4-initial-installations): wheel **50**, sdist **310** izinli üye. İkisinde de konsol/import kökeni ve eski v1/cache/execution + yeni boş olmayan jobs CLI/API/text smoke geçti. Kurulu ölçüm wheel SHA-256'sı ve temiz kurulum wheel'i aynıdır: `03829c63cd3e0b2c0206ddcb92a8456489c7c5a4711566be000201ac200398b3`. Fixture kaynak geliştirme ortamında hazırlanır; temiz runtime'a pytest veya fixture backend kurulmaz. Bu ilk build kanıtıdır, yayın veya son review head artefaktı değildir.

[30 yardım çıktısı](evidence.md#p01-4-initial-help-parity) adım 3 sonuyla karşılaştırıldı: 29'u bayt düzeyinde aynı, kökte yalnız beklenen jobs seçeneği/açıklaması değişti. Yeni jobs/aile/fiil yardımının metadata guard'ı da geçti.

[İlk eşli startup kabulü](evidence.md#p01-4-step-4-initial-startup), development a9f1f2e detached checkout'u ile bu adayın ayrı frozen wheel/runtime ortamlarını aynı host'ta AB/BA sırasıyla ölçer. Üç warmup + 30 çift, eşit 1.024 cache/1.212.625 payload byte ve bütün örnekler korunur; kaynak sabittir. Aday p95 help **24,766**, version **23,005**, context **72,323**, cache **112,890 ms** ile mevcut 500/200 ms kapılarını geçti. Bu yerel kabul Linux PR/merge çıktısı değildir; kullanıcının açık tercihiyle o dış takip paket PR'ında değerlendirilecektir.

### Adım 4 — Birinci review turu

5c7ad8c commit'i üzerinde üç fresh salt-okunur reviewer (GPT-6 Astra xhigh query/state, GPT-6.1 Sol high public sözleşme, GPT-6 Astra high kaynak/artefakt) çalıştı. Public sözleşme reviewer 50 + 21 hedefli testte yeni kusur bulmadı. Kaynak reviewer altı helper testini çalıştırıp bütün jobs/startup p95'lerini ham 30 örnekten tekrar hesapladı; source/installed Python baytları, iki wheel ve sdist SHA'ları, a9f1f2e baseline Git blob'ları, frozen ortam ve yardım eşliği doğrulandı. Yeni kaynak/artefakt kusuru bulunmadı.

State reviewer **bir P2 kök nedenin beş varyantını** doğruladı: liste son event'in attempt fence/zaman/dispatch bağını ve latch-null normal event sayısını eksik denetliyordu. Root aynı gerçek SQLite bozulmalarını yeniden üretti: beşinin her birinde show state_invalid verirken list kabul etti; beş negatif önce başarısız oldu. Tam geçmiş taraması gerektirmeyen düzeltmede full ve son-event kontrolü ortak candidate yardımcısını kullanır; dispatched event aynı latch'e bağlı kalır. Latch-null admitted için normal event sayısı bir, yerel terminal için ikidir; ownership/recovery kontrolü yeni normal event üretemez. Query sayısı ve batch sınırı değişmedi. Geçersiz olduğu için atlanan bulgu yoktur; varyantlar aynı kök nedende kapandı.

Düzeltme sonrası jobs + operation full/warm/relationship/reconciliation hedefli takım **147 passed / 49,46 s**; Ruff ve strict mypy 51 kaynakta geçti. İlk ölçüm/kurulum dosyaları 5c7ad8c kaynak kanıtı olarak korunur; değişen decoder kaynağı için son kabul sayılmaz. İkinci fresh review ve ardından güncel kaynakla full/build/kurulu jobs/startup/operation bütçe kapanışı sıradadır; kart/paket henüz verified değildir.

### Adım 4 — İkinci review turu

4941bf3 üzerinde farklı üç fresh salt-okunur reviewer (GPT-6 Astra xhigh state/query, GPT-6.1 Sol high public sözleşme, GPT-6 Astra high kaynak/paket/kanıt) çalıştı. Public sözleşme 92, kaynak reviewer 35 ve state reviewer 31 hedefli test çalıştırdı; bu sayılar full takım diye toplanmaz. Kaynak reviewer dört jobs/dört aday/dört baseline p95'ini yeniden hesapladı, kaynak/installed bytes ve arşiv üye/hash bağlarını doğruladı; yeni public/artefakt kusuru bulunmadı.

State incelemesinde **üç P2** doğrulandı: son normal event revision'ı sequence'den küçük olabiliyordu; iki event'li dispatched işin zorunlu ilk intent'inde admission clock/approved interval/submitted kontrolü listede eksikti; ayrıca eski adım 3 kalıcı relationship consumer'ı succeeded execution ile beraber değiştirilmiş nonzero attempt/outcome exit'i kabul ediyordu. Sonuncu konu yeni list regresyonu değildir; root ek sözleşme kontrolü ve reviewer'ın bağımsız gerçek-store deneyiyle list/show/full için doğrulandı. Port reducer aynı çelişkiyi zaten reddediyordu.

Root dört first-intent varyantı (revision/epoch/generation/status), üç terminal list/show/full exit ve bir delivery-pending exit negatifini mevcut kodda çalıştırdı; **sekizinin hepsi önce başarısız oldu**. Düzeltmede full/son intent ortak tarihsel dispatch authority kontrolünü kullanır; candidate kontrolü revision≥sequence şartını taşır; ortak relationship execution succeeded için exit null/0 ister. Yeni history scan, alan, execution yetkisi veya ADR kararı eklenmedi. Geçersiz diye atlanan bulgu yoktur.

Düzeltme sonrası geniş jobs/store/warm-full/reconciliation takımı **155 passed / 52,34 s**; Ruff ve strict mypy 51 kaynakta geçti. İki fresh tur tamamlandı; son ürün kaynağında bütünleşik full/build/kurulu jobs/startup ve yoğun operation kabulü yapılmadan kart/paket verified değildir. İlk kaynak dosyaları tarihsel kanıt olarak korunur.

## Son kaynakla bütünleşik yerel kabul

Son ürün head'i **17de965** üzerinde iki turdaki bütün doğrulanmış bulgular kapandı. Ek bağımsız GPT-6.1 Sol high statik fix kontrolü yeni kusur bulmadı; strict intent authority, revision, success/exit ve memo key bağlarını doğruladı. Bu son kontrol yeni bir full test koşusu diye sayılmaz.

Kapanış belge/kanıt audit'inde GPT-6 Astra high son metrikleri ve kaynak haritalarını bağımsız karşılaştırdı. Yerel state referansında kalan bir P3 eski “adım 3 sürüyor/jobs henüz yok” paragrafı doğrulandı; yinelenen durum metni kaldırılıp son kabul kaydına bağlandı. Diğer sayı/hash/durum uyuşmazlığı bulunmadı; belge/ajan/diff denetimleri tekrar geçti.

**Tam takım 1.700 passed / 279,59 s.** Ruff format 106 dosya, lint, strict mypy 51 src/script kaynağı, 114 Markdown, 6 skill/9 kart ve diff kontrolü geçti. Golden migration 1–5/handler ve şema 6 checksum'u korundu. Ürün/seed/probe kaynakları bütün son ölçümler boyunca sabitti; Git tabanı ve dosya SHA-256 haritaları her ham kayıtta tutulur. İlk başarısız tanılar ve daha önceki kaynak kabul dosyaları ezilmedi.

### Son operation ve migration kabulü

[Son 27 operation işlemi](evidence.md#p01-4-final-operation-budget), normal/terminal yoğun/karma yoğun fixture başına üç yeni store ve fresh worker ile **27/27** geçti. Özgün 5 s deadline, n=1.000 progress quantum ve her callback'in asıl deadline'a delegasyonu korundu; timeout kabul sayılmadı, örnek atılmadı. Üç örneğin maksimumları:

| Fixture | Full ms | Preview ms | Reset ms | Tepe worker RSS MiB |
|---|---:|---:|---:|---:|
| Normal | 487,54 | 551,92 | 1.158,85 | 58,36 |
| Terminal yoğun | 3.690,50 | 3.745,32 | 4.647,56 | 73,72 |
| Karma yoğun | 3.748,36 | 3.765,06 | 4.931,33 | 83,77 |

Azami 1.024 operation/16.384 attempt/262.144 normal event, karma fixture'da 512 terminal + 512 adet 255 normal geçişli iş ve maksimum eski cache/plan payload hacmi korundu. Reset immutable history/plan/onay/outcome'u koruyup current owner/cache'i invalid etti; ham kayıt logical row/hash/hacim ve reset etkisini ayrı doğrular. **En yavaş karma reset 4.931,328083 ms; marj 68,671917 ms'dir.** Bu dar marj yalnız kayıtlı M5 Max/macOS/SSD/APFS referans kabulüdür; farklı host veya engellenemeyen sistem I/O'su için mutlak süre garantisi değildir. Eşik/kapasite/validation gevşetilmedi.

[Son 24 migration](evidence.md#p01-4-final-migration-budget), şema 2/3/4/5 normal ve yoğun kaynakları üçer yeni store/worker'da şema 6'ya yükseltti: **24/24** pozitif, kaynak payload/satırları aynı, yeni operation tabloları boş, son full validation başarılı. Normal maksimumları 1.087,95 / 1.375,90 / 1.412,69 / 954,26 ms; yoğun maksimumları 2.455,23 / 4.316,42 / 4.241,66 / 3.151,94 ms. Kaynak/ortam, VM ve faz kayıtları ham dosyadadır.

### Son kurulu jobs, startup ve artefakt kabulü

[Son jobs ölçümü](evidence.md#p01-4-final-jobs-budget), iki review fix'i dahil aynı 17de965 Python kaynak baytlarını içeren ayrı frozen runtime-only wheel kurulumundadır. İlk süreç ayrı, üç warmup ve her yol için **30 ayrı süreç**, nearest-rank p95 ve bütün örnekler korunur. Normal/yoğun hacimler ve yöntemin sınırları ilk ölçümde açıklandığı gibidir; gerçek byte/row değerleri bu son ham dosyada da vardır.

| Yol | p95 ms | Sınır ms | Ayrı tanısal worker tepe RSS MiB |
|---|---:|---:|---:|
| Normal list | 120,621 | 200 | 46,03 |
| Normal show | 105,248 | 200 | 45,23 |
| Yoğun list | 166,939 | 200 | 53,86 |
| Yoğun show | 104,432 | 200 | 45,84 |

Diagnostic list/show toplam 44/46 SQLite statement; yoğun örneklenmiş VM quanta 203.000/2.000, bütün callback'ler delege edildi. Normal callback sıfır olması gerçek VM adımı sıfır demek değildir. Ayrı diagnostic RSS, timed CLI süreçlerinin bireysel RSS'i diye gösterilmez. Bu snapshot'ın mutable payload hash kapsamı sınırlıdır; source/read-only sözleşmesi ve gerçek snapshot/bozuk projection testleri ayrı kanıttır.

[Son eşli startup](evidence.md#p01-4-final-startup), a9f1f2e baseline ile aynı host'ta AB/BA, eşit 1.024 kayıtlı cache ve 30 çift kullanır. Aday p95 help **23,374**, version **21,446**, context **90,236**, cache **114,536 ms** ile mevcut 500/200 ms kapılarını geçti. Kaynak ölçüm boyunca değişmedi; aynı interpreter ve frozen runtime paketleriyle yapılan yerel ölçümdür. Linux PR/merge çıktısı yerine kullanılmaz.

[İki son ürün temiz kurulumu](evidence.md#p01-4-final-installations), wheel 50/sdist 314 izinli üye; konsol/import kökeni, eski v1/cache/execution ve yeni boş olmayan jobs CLI/API/text smoke geçti. Performans ölçümleri test/build/profiler ile çakıştırılmadı; performans dışındaki son test/build hazırlığı aynı anda çalıştı. Jobs, paired startup ve iki kurulumun wheel SHA-256'sı aynıdır: **d834ec89c0d415b92bb65f7916b42a9d6237d87e6bc75846671501884b6ac9ff**. Bu ürün-kaynak build kanıtı son kanıt/durum belgeleri eklenmeden alınmıştır; PR CI tam teslim tree'sinden yeniden paket üretir. Yardım source'u 5c7ad8c'den sonra değişmedi; [30 çıktı kabulü](evidence.md#p01-4-initial-help-parity) geçerlidir.

**P01-4 yerel paket kabulü tamamlandı:** P01-4a önceki PR #6'da, P01-4b ve P01-4c bu dalda verified. Genel P01 devam eder; sıradaki paket P01-5a HTTP/SDK ve ortak taşıma, ardından P01-5b sonuç/akış/iptal hattıdır. PR development'a kullanıcı incelemesi için açılır; bu kayıt development merge'i, Master aktarımı, release veya canlı EVREN kabulü değildir.

## Sonraki adımlar

Adım 1–4, ikişer fresh review ve bütünleşik son kaynak kabulü tamamlandı. Development PR'ında dış CI/kalite sonuçları ayrıca izlenir; kullanıcı incelemesi ve merge'i beklenir. Fiziksel güç kesintisi, gerçek EVREN/ForgeLM, Windows veya yayımlanmış paket kanıtı yoktur. Master/release aktarımı kullanıcıdadır.

## PR #10 kalite incelemesi — takip

410c29e PR head'inde SonarCloud iki güvenlik ve 45 bakım/test uyarısı yayımladı. Üç bağımsız salt-okunur reviewer güvenlik sınırını, doğrulama dallarını ve test iddialarını inceledi. Bakım düzenlemeleri kontrol sırasını, SQL CAS/transaction sınırını ve bütün kapalı doğrulama kurallarını korur; yoğun normal event döngüsüne ek genel helper çağrısı eklenmedi. `pytest.raises` hazırlıkları/dal seçimi blok dışına taşındı. Sabit dalların önceki halinde yanlış başarı yeniden üretilmedi; bunlar assertion kapsamı ve okunabilirlik düzenlemeleridir.

Doğrudan `benchmark-startup.py --output` girişinin mevcut dosya veya symlink hedefini ezebildiği ayrı bir **P2 kanıt kaybı kusuru** doğrulandı. Erken yeni-dosya kontrolü ve son exclusive-create ile düzeltildi; mevcut dosya, mevcut/dangling symlink, eksik parent ve ölçüm sırasında oluşan dosya regresyonları eklendi. Kısıtlı bir kökten kaçış olmadığı için bu kusur path traversal olarak adlandırılmaz. Çıktı yolu çağıranın açık geliştirici rapor hedefidir.

`check-startup.py` S8705 akışı HTTP/ürün isteği almaz; açık CLI metadata'sı sabit yapılı argv listesinde `shell=False` ile taşınır. Offline literal argv deneyi ve kaynak incelemesi komut enjeksiyonunu doğrulamadı. Issue `AaGFhdKHvoIUrs5RY6NC`, gerekçesiyle SonarCloud'da **False positive** olarak değerlendirildi; genel kural/quality gate değiştirilmedi. Benchmark S8707 için de yetki sınırı aşımı doğrulanmadı; issue bazlı dış değerlendirme ve güncel tarama ayrıca izlenir.

CodeRabbit'teki beş güncel durum ifadesi kaynak/kartlarla karşılaştırılıp düzeltildi; indeks kart durumunu tekrar etmez. Fork testinin kilit/PID regresyonunda süresiz bekleyebilmesi ve beklenmeyen child istisnasında pytest'e dönebilmesi doğrulandı; child alarm ve zorunlu `finally` çıkışı eklendi. PR Lens'in delivery-required olmayan succeeded işte takeover iddiası uygulanabilir bulunmadı: bu kombinasyon reducer gereği terminal `succeeded` olur ve takeover terminal dalı mutasyondan önce döner. Bu nedenle varsayımsal guard değişikliği yapılmadı.

Düzenlemeler sonrası hedefli takım **312 passed / 79,99 s**; ayrıca güncellenen permit testi geçti. Ruff, strict mypy 51 kaynak, 114 Markdown, 6 skill/9 kart ve diff denetimleri geçti. Yeni kaynak refaktörünün fresh review ve bütünleşik performans/build kabulü henüz bu takip kaydına eklenmedi; yukarıdaki 17de965 ölçümleri tarihsel kaynak kanıtı olarak korunur.

### Linux CI gözlemi

Aynı 410c29e head ve aynı `d834ec89…` wheel ile [40807762132](https://github.com/HodeTech/Yorunge/actions/runs/40807762132) başarılı; [40808159684](https://github.com/HodeTech/Yorunge/actions/runs/40808159684) startup cache kapısında başarısızdır. Başarılı AMD EPYC 9V45 host'ta aday/taban cache p95 **116,575 / 119,019 ms**; AMD EPYC 9V74 başarısız koşuda **392,389 / 355,920 ms**. İki taraf da etkilenmiştir. Wall–child CPU farkı medyanı adayda yaklaşık **2,021 → 55,746 ms** artar; bu fark I/O ile scheduler nedenini ayırmaz. Disk türü `unknown`; setup image ile benchmark ortam metadata'sı farklı değerler taşıdığından image değişimi neden olarak ileri sürülmez.

İlk koşunun iptali PR açıklama güncellemesiyle açılan `edited` koşusunun concurrency davranışıdır. Sonraki başarısız startup gerçek bir kapı başarısızlığıdır; iptal ile karıştırılmaz. Eşik artırılmadı, başarısız örnek atılmadı ve aynı head'i yeşil göstermek için manuel rerun yapılmadı.

### Kalite takibi — yoğun bütçe reddi ve hedefli azaltım

227e800 ürün kaynaklarını içeren e638194 üzerinde tam takım **1.705 passed / 275,60 s**, iki temiz kurulum ve 30 kurulu yardım çıktısının ilk P01-4 çıktılarıyla byte eşliği geçti. Ek ölçüm betiğinin CPU yardımcısı değişikliği altı sözleşme testiyle ayrıca doğrulandı. İki bağımsız statik inceleme turunda yeni kusur bulunmadı. Sonar e638194 taraması başarılı ve **0 annotation**; S8705 `RESOLVED / FALSE-POSITIVE`, S8707 kod düzeltmesi sonrası `CLOSED / FIXED` durumundadır.

Buna rağmen [aynı kaynaktaki 27 yoğun işlem](evidence.md#p01-4-quality-operation-budget) **yerel kabulü geçmedi**: 21 pozitif, iki terminal reset, üç karma reset ve bir karma full işlemi `state_busy` ile reddedildi. Kaynak sabit, 5 s/n=1.000 kapıları değişmedi; immutable history/hacim ve satır sayıları korundu. Bu dosya başarısız tanı olarak tutulur, son kabul yerine sunulmaz. Güncel dış Linux CI'ın başarılı olması bu yerel başarısızlığı kapatmaz.

Orijinal 5 s deadline ile alınan ayrı cProfile tanısı max-karma full kontrolde süreyle kesildi; bütün resetin veya başarıyla tamamlanmış işlemin profili değildir. Kesilene kadar 765.411 genel metin kontrolü yaklaşık 0,729 s, satır fingerprint'leri 0,425 s; metadata/operation-clock okuması yaklaşık 0,005 s idi. Bu nedenle metadata için değişiklik yapılmadı. Gerçek event satırları üzerinde AB/BA mikro karşılaştırmada hash update birleştirmesi daha yavaştı ve uygulanmadı; duplicate hook'un `dict(pairs)` + uzunluk kontrolü eşdeğer veriyle yaklaşık 0,707 yeni/eski medyan oranı verdi. Mikro kazanç paket kabulü sayılmaz.

Dar azaltım: operation'ın ilk 12 SQL indeks alanı payload serileştirmesinden ayrılır; read karşılaştırması artık üretip atacağı JSON'u oluşturmaz, write payload'ı aynı canonical biçimde üretir. Duplicate JSON anahtarı, escaped/nested anahtar ve nonfinite reddi korunur. Metin kontrolünde yalnız başarılı, exact built-in `str`, en çok **128 ASCII karakter** için **4.096** girişli saf LRU kullanılır; uzun/non-ASCII metin aynı uncached Unicode/UTF-8/2.048-byte kontrolünden geçer. Başarısız kontrol tutulmaz. Bu cache yalnız sözdizimi sonucudur; model/yetki/credential/saat/DB ilişkisi veya güncellik kararı tutulmaz. Anahtar metni en çok 524.288 ASCII byte ve Python/LRU overhead'i kadar tutulur; büyük opaque path/Unicode değerler bu cache'e girmez.

Plan boyutu için sabit digest-ek-maliyeti formülü gibi daha kırılgan bir optimizasyon eklenmedi. Yeni kaynak fresh review ve son full/performance/build ölçümü tamamlanmadan bütçe kapanmış sayılmaz.

### Sonraki tanı — tekrar parse ve aynı key baytları

[ad6cb92 üzerindeki ikinci 27 işlem](evidence.md#p01-4-hotpath-operation-budget) kaynak sabitken yine **21 pozitif / 6 reset state_busy** üretti; bütün örnekler tutuldu. [Kurulu önce/sonra A/B tanısı](evidence.md#p01-4-hotpaths-ab-full), aynı max-karma salt-okunur fixture'da üç AB/BA çiftinin tümünü özgün 5 s full kontrolünde tamamladı. Önce/sonra medyan CPU **4.066,555 / 4.101,192 ms**, wall **4.084,400 / 4.140,554 ms**; bu küçük tanı toplam bir kazanç göstermedi ve reset kabulü değildir. Kaynak Git baytları/wheel hash'leri ayrıca doğrulandı. Tekil LRU etkisini diğer iki değişiklikten ayıran bir iddia kurulmaz. Ek global metin cache'i kaldırıldı; uzunluk/Unicode kontrolü önceki doğrudan uygulamasına döndü.

İkinci dar azaltım, `decode_record` içindeki yinelenen tam JSON parse'ını kaldırır. Kanonik `CapabilityRecord.model_validate_json` hâlâ duplicate/nested/escaped key, nonfinite, strict UTF-8 ve tipleri doğrular. Başarılı modelde `schema_version` alanının `model_fields_set` içinde bulunması ayrıca zorunludur; default 2, açık sürümün yerine geçemez. Verilmiş sürümün tam integer olması mevcut before-validator ile korunur. Geçerli gerçek önbellek kaydının kök `schema_version` alanını silen; bu alanı bool, float, string, null veya yanlış integer yapan; eşit ya da kaçışla yazılmış yinelenen anahtar içeren varyantlar ayrı ayrı oluşturulur. Her varyant doğrudan kayıt çözücüsünde, ilk tam kontrolde ve sıcak önbellek sorgusunda `state_invalid` bekleyen testlerle denetlenir.

Aynı immutable satırın key baytları bir kez üretilip hem SHA-256 hem ASCII key karşılaştırmasında kullanılır; projection/group/time/revision kontrolü atlanmaz. `CacheValidation.key`, yalnız `decode_entry` aynı satırın digest'ini doğruladıktan sonra doğrulanmış `row[0]` değerini kullanır. Frozen migration handler, public wire/digest biçimi, kota, transaction, current clock/credential/approval kontrolü ve hata kodu değişmez. Yeni paket kabulü yine fresh review ve gerçek son kaynak ölçümlerine bağlıdır.

### Kota hesabının tekrarlanan serileştirme maliyeti

[5d0b3a4 kaynak ölçümü](evidence.md#p01-4-cache-parse-operation-budget), 27 işlemin 24'ünü tamamladı; üç karma reset yine özgün 5 s kapısında `state_busy` verdi. Kaynak sabitti ve bütün sonuçlar korunur. [Ayrı tam reset tanısı](evidence.md#p01-4-reset-diagnostic) cProfile overhead'ini görmek için yalnız disposable fixture/test sürecinde 60 s pencere kullandı; **kabul değildir ve ürünün 5 s bütçesini değiştirmez**. Tanıda iki full validation, snapshot ve mutation/commit birlikte görüldü; byte kotası için model dump + Python canonical JSON tekrarları ölçüldü. JSON tabanlı yeni fingerprint önerisi de mevcut akıştan daha yavaş bulundu ve uygulanmadı.

[ASCII boyut mikro tanısı](evidence.md#p01-4-wire-size-micro), doğrulanmış plan **65.536**, capability **1.424** ve operation **1.984 byte** örneklerinde iki yöntem arasında eşit boyutla yaklaşık **0,642 / 0,504 / 0,455** yeni/eski medyan oranı gösterdi; bu yalnız yöntem tanısıdır. Desteklenen Pydantic alt sınırı 2.14.1'dir. Kısa metin LRU'su geri eklenmedi.

Yedi sık kota kontrolü, yalnız doğrulanmış integer/bool sayıları ve strict-text alanları olan ScopeV2, Evidence, CapabilityRecord, OperationAdmission, AttemptView, OperationRecord ve OperationOutcome için doğrudan compact ASCII JSON uzunluğunu kullanır. Alan sırası byte sayısını değiştirmez; canonical hash/digest/key üretimi aynı kalır. Bu korumalı helper genel float veya model-copy ile bozulmuş keyfi model boyut fonksiyonu değildir. Legacy nested Context taşıyan **JobView eski canonical hesabında kalır**.

ExecutionPlan büyük gövdesini canonical olarak bir kez üretir; aynı baytlardan SHA-256 ve boyut türetilir. Nonempty canonical gövde + gerçek digest-field nesnesi birleştirildiğinde iki brace kaldırılır ve bir comma eklenir; tam boyut iki uzunluğun toplamından bir eksiktir. Sabit 76-byte varsayımı kullanılmaz. Plan/JobView için legacy nested Unicode/surrogate farkı yaratacak doğrudan serializer yolu kullanılmaz. Bağımsız testler Unicode/escape, signed integer uçları, **65.536 kabul / doğru digest'li 65.537 ret** ve mevcut legacy nested canonical metin davranışını doğrular.

Hedefli takım 201 test, ek sınır takımı ayrıca geçti; Ruff ve strict mypy geçti. Yeni kaynak fresh review ve son pozitif bütçe/full/build kapanışı olmadan paket kabulünün güncel kaynağı sayılmaz.

### Ölçüm aracı dış runtime yolu

PR yorumundaki checkout dışı runtime yolu kusuru yeniden üretildi: kaynak/kurulum guard'ları geçen kontrollü fixture, rapor `prefix_relative` alanını oluştururken `Path.relative_to` hatası veriyordu. Regresyon önce bu noktada başarısız oldu. Artık prefix çözümlenmiş mutlak yola normalize edilir; checkout içindeyse `prefix_relative`, dışındaysa `prefix_absolute` doldurulur, diğeri null'dır. Kurulum/kaynak hash ve geliştirme paketi ret kontrolleri değişmez. Bu test yol metadata'sı içindir; kurulu süreç performansı diye sayılmaz. Dil/açıklama ve örnek boyutu yorumları da gerçek kayıtla hizalandı.

## Kullanıcı PR incelemesi — aynı gözlemin geçmiş kotası

Kullanıcının e638194 üzerinde bildirdiği iki P2 ve bir P3 bulgusu güncel kodla karşılaştırıldı. Aynı başarılı sağlayıcı gözleminin her reconcile'da normal event üretmesi güncel kaynakta doğrulandı. Dört nonterminal örnek, 255 dolu geçmiş ve reset onayı/zaman kararlılığı için altı negatif mevcut kodda **6/6 başarısız** oldu. Mevcut ADR-0016 normal **business geçişini** kotaya bağladığından yeni ADR/karar değişikliği gerekmedi; aynı gözlem bir iş değişikliği değildir. Timestamp referansı son kalıcı değişikliği anlatacak biçimde netleştirildi.

Düzeltme bütün correlation/hedef/yetki, run ID ve reducer kontrollerinden sonra, kapasite kontrolünden önce uygulanır. Recovery marker yoksa ve tüm kalıcı durum/sağlayıcı alanları aynıysa mevcut JobView döner; yeni event/revision/updated_at/lease üretmez. Ortak clock transaction'ı ve son owner/credential/lease/ReadAccess kapıları atlanmaz. Yeni provider status/exit ve marker temizleyen gerçek recovery hâlâ anlamlı değişikliktir. Geçmiş doluyken yeni nonterminal kanıtın capacity_exceeded davranışı ve 256. terminal slotu korunur.

Düzeltme sonrası uzlaştırma takımı 71 test geçti; aynı gözleme benzer credential yarışına ilişkin ek örnek ayrıca sınandı. Uzun sorgulama testi her çağrıya ayrı kullanım senaryosu bütçesi verir; 260 adet 5 s UTC adımı ve explicit renew ile 21 dakikadan uzun sentetik süreyi sınar, gerçek süre beklemez. Salt gözlemin kalıcı iş payload'ını değiştirmemesi, yeni kanıtın yazılması, aynı unknown eksenlerinde recovery marker temizliği, yanlış correlation/account/run/gerileme reddi ve son lease/read yetkisi expiry'si ayrı örneklerdir.

Diğer P2, incelenen e638194 için geçerliydi: başarısız 27 örnek korunmuştur. Sonraki 552d3e3 ürün kaynağında [27/27 operation](evidence.md#p01-4-quota-operation-budget) ve [24/24 migration](evidence.md#p01-4-quota-migration-budget) pozitif kabul sağlandı; en yavaş karma reset **4.965,896083 ms**, marj **34,103917 ms** ile dardır. [9600416 yardımcı kaynağıyla kurulu jobs](evidence.md#p01-4-closing-jobs-budget) normal list/show **124,486/121,779**, yoğun **178,063/120,208 ms** ile geçti. Bunlar yeni aynı-gözlem düzeltmesinden önceki kaynak kanıtlarıdır; son kaynak kabulü yeniden alınacak. GitHub startup yeşili operation bütçesi yerine sunulmaz.

P3 checkout dışı runtime kusuru 9600416'da başarısız-önce/geçen-sonra regresyonu ve iki bağımsız incelemeyle kapandı; tekrar kod değişikliği yapılmadı. Önceki PR Lens takeover iddiası, terminal reducer/erken dönüş nedeniyle uygulanabilir olmadığı için açık bulgu değildir.

## PR #10 son kaynak kapanışı

Ürün kaynağı **182f695f656c374530d9a496a59d9e7ee714932f**'dir. Yeni ham ölçümlerde checkout HEAD'i **bc0d3c9** görünür; bu aradaki commit yalnız `current.md` açıklamasını düzeltir. Bütün kaydedilmiş kaynak SHA-256'ları güncel dosyalarla eşleşir; ölçüm boyunca kaynak sabittir. Bu bölümün ve son kanıtların eklenmesi ürün/fixture/ölçüm kodunu değiştirmez. Eski 17de965/552d3e3 başarıları son kaynak kabulü yerine kullanılmadı.

**Doğrulama ve inceleme:** Tam yerel takım **1.779 passed / 304,60 s**. Ruff format/lint, strict mypy 51 kaynak, 114 Markdown, 6 skill/9 kart ve diff kontrolü geçti. Aynı-gözlem düzeltmesi iki farklı fresh turda state/dayanıklılık ve sözleşme/test reviewer'larıyla incelendi (GPT-6 Astra xhigh ve GPT-6.1 Terra high). Ürün kusuru kalmadı; ikinci turdaki tarihsel ölçümün güncel kabul gibi okunabilmesi bulgusu bc0d3c9 ile düzeltildi ve reviewer tarafından kapatıldı. Son kaynak/artefakt/bütçe kanıtı ayrıca salt okunur denetlendi.

Uzlaştırma regresyonları, dört nonterminal biçimde 260 ayrı gözlem/5 s sentetik adım ve explicit renew ile geçmişin değişmediğini gösterir. Her poll yeni kullanım senaryosu bütçesidir; gerçek 21 dakika beklenmez. Dolu 255 normal slotta aynı gözlem kabul edilir, gerçek yeni nonterminal kanıt kota denetimine girer, ayrılmış 256. terminal slot korunur. Provider status/exit/run bağı, recovery marker temizliği, reset consent/timestamp ve son lease/read expiry ayrı kontrol edilir. Ayrı süreç credential yarışı, semantik no-op görünse de son credential değişiminin `state_changed` vermesini doğrular. Hedefli uzlaştırma takımı 72 örnektir; tam takım bunları içerir.

### Özgün bütçeyle son operation ve migration ölçümleri

Ölçümler test/build/profiler ile çakıştırılmadan sıralı alındı. Ortam **Apple M5 Max / macOS 27.0.1 arm64 / SSD–APFS / Python 3.11.18 / SQLite 3.54.1**; operation/migration editable frozen `.venv`, jobs/startup ayrı frozen runtime-only wheel ortamıdır. OS/disk cache'i boşaltılmadı; farklı host/sistem I/O'su için mutlak süre garantisi verilmez.

[Operation ham kaydı](evidence.md#p01-4-noop-operation-budget): normal/azami terminal/azami karma fixture × full/preview/reset × üç yeni worker, **27/27 başarılı**. Her çağrı özgün **5 s**, n=1.000 progress callback ve gerçek deadline kontrolünü korur; timeout başarı sayılmaz. En yüksek wall süreleri:

| Fixture | Full (ms) | Preview (ms) | Reset (ms) |
|---|---:|---:|---:|
| Normal | 428,479 | 471,501 | 970,245 |
| Azami terminal | 3.638,258 | 3.705,219 | 4.549,715 |
| Azami karma | 3.630,003 | 3.641,685 | **4.851,708** |

En dar referans marjı **148,292 ms**'dir. Azami terminal fixture 1.024 operation/16.384 attempt/262.144 event; karma fixture 512 terminal + 512 running ve 261.632 event içerir. Azami cache 33.554.432, plan 67.108.864 payload byte'tır. Plan/onay ve immutable event/outcome hash'leri korunur; reset cache/kimliği ve aktif sahipliği değiştirirken geçmişi silmez. En yüksek RSS yaklaşık **84,33 MiB**. VM quanta özgün callback×1.000 örneklemesidir, tam instruction sayısı değildir.

[Migration ham kaydı](evidence.md#p01-4-noop-migration-budget): şema 2/3/4/5 × normal/azami × üç yeni store, **24/24 başarılı**. Bütün örnekler özgün 5 s içinde şema 6'ya ulaştı; en yavaş **4.456,741 ms**. Kaynak cache/plan/onay payload satırları byte olarak aynı kaldı, operation sayısı sıfır ve çağrı sonrası tam doğrulama geçti. Backup/sync/DDL/handler/validation/commit fazları ve VM sayımı ham dosyada ayrıdır; özgün deadline callback devrededir. Migration 1–5 kimlikleri ve frozen handler değişmedi.

e638194/ad6cb92/5d0b3a4 kaynaklarında başarısız ara ölçümlerin **6/6/3** kontrollü ret örnekleri önceki bölümlerde ve ham dosyalarda korunur. Başarısızlıklar atılmadı; bu son kaynak kabulünde kota, güvenlik kontrolü veya deadline gevşetilmedi. 60 s cProfile tanısı ve mikro A/B ölçümleri kabul yerine kullanılmadı.

### Kurulu ürün ve başlangıç

[Wheel/sdist iki temiz kurulum](evidence.md#p01-4-noop-installations): 50/330 izinli üye, doğru import/konsol kökeni, v1/cache/execution ve boş olmayan jobs CLI/API/text smoke geçti. Wheel SHA-256 **54d371d61c6eb5dc4b021c1ad989ed37ce447179ad1f30c89e1880ec18b45851**; sdist **19f7640dfaab36e55e77708ba6f50c4ed817661f188e8ebdd6bcfe9c5d65c607**. Bu build son kanıt/belge kapanışından önceki ürün kaynağıdır; kendi sonradan üretilmiş kanıtlarını içerdiği iddia edilmez. PR CI tam teslim ağacından yeniden paket üretir.

[Kurulu jobs ham kaydı](evidence.md#p01-4-noop-jobs-budget), aynı wheel'de dört yolun her birinde 30 yeni süreç/sıcak p95:

| Fixture | List (ms) | Show (ms) | Kapı |
|---|---:|---:|---|
| Normal | 133,522 | 118,806 | ≤200 ms, geçti |
| Yoğun | 175,712 | 122,114 | ≤200 ms, geçti |

İlk süreç ve warmup örnekleri ayrı tutulur; sıcak p95 yerine kullanılmaz. Salt-okunur sorgu/snapshot/RSS/byte/VM tanısı ayrı kayıttır; metadata için checkout içi/dışı runtime yolu desteği performans sonucu gibi sayılmaz.

[Eşli startup ham kaydı](evidence.md#p01-4-noop-startup), aynı host'ta development a9f1f2e tabanı ve aday arasında 30 AB/BA süreç çifti kullanır. Aday p95 help/version/context/cache **26,897 / 25,323 / 82,742 / 123,185 ms**; karşılık gelen taban **27,707 / 27,390 / 84,495 / 123,790 ms**. Mevcut 500/200 ms kapıları iki tarafta da geçti. Aday wheel hash'i jobs/kurulum kaydıyla aynıdır; runtime no-dev/frozen ve kaynak kökeni doğrulanır. Bir host'un sonucu sabit GitHub runner performansı veya fiziksel soğuk başlangıç kanıtı değildir.

Ürün head'i 182f695 için [GitHub offline-core](https://github.com/HodeTech/Yorunge/actions/runs/40826046460) ve [branch-policy](https://github.com/HodeTech/Yorunge/actions/runs/40826046139) başarılı; SonarCloud başarılı/0 annotation, CodeRabbit ve Sourcery bu head'de skipped. Son belge tesliminin CI'ı ayrıca izlenir; önceki head sonucu yeni head'e yazılmaz. Sonar S8705 gerekçeli false positive, S8707 kod düzeltmesiyle fixed durumundadır; genel kural/eşik değiştirilmedi.

**P01-4b/4c yerel kabulü verified; PR #10 kullanıcı incelemesine açıktır.** Sıradaki paket P01-5a/5b, ardından P01-6b faz kapanışıdır. Bu çalışma P01-5 uygulamasını başlatmaz. Development merge'i, Master/release, gerçek EVREN/ForgeLM, Windows veya fiziksel güç kesintisi kabulü değildir.

## PR #10 ham kanıtların ayrılması

Kullanıcı review yükünü azaltma önerisini uygulamaya yetkilendirdi. f186d27 head'inin 226.702 eklemesinin 214.340'ı, bu PR'ın eklediği 33 ham JSON raporuydu. Bu raporların özgün Git blob baytları okunup mevcut dosyayla karşılaştırıldı, gzip açılımı aynı baytlarla tekrar eşitlendi ve yalnız bundan sonra açılmış kopyalar kaldırıldı. Kaynak ve arşiv SHA-256/boyutları [manifesttedir](evidence-manifest.json); başarısız 6/6/3 ara koşular dahil bütün kayıtlar korunur. 5.677.252 byte özgün veri, 417.447 byte arşiv olarak saklanır. Eski Git geçmişi yeniden yazılmadı.

[Kanıt indeksi](evidence.md), raporlar, ölçüm betikleri ve sabit test vektörleri review'de kalır; yalnız raw gzip dizini CodeRabbit/GitHub normal diff'inden ayrılır. Diğer ajanların hedefli akışı kanonik rehbere ve review/verify skill'lerine eklendi. CI strict JSON, bounded gzip, iki hash/boyut, p95/kapı/özet ve indeks eşliğini denetler; bu mekanik kontrol gerçek ölçümün yeniden çalışması veya kaynağın bağımsız doğrulanması değildir.

İlk arşiv/paket/probe hedefli takım **93 passed**, ayrıca bağımsız migration/credential vektörlerini kullanan mevcut integration takımı **63 passed**. Belge/ajan/strict mypy ve Ruff kontrolleri geçti. Yerel hazırlık wheel/sdist build'i ve ayrı temiz kurulumlar doğru köken/v1/cache/execution/jobs smoke'u geçti; wheel 50, sdist 307 üyedir ve ikisinde de raw arşiv yoktur. İki bağımsız test vektörü sdist'te kalır. Bu kapanış metninden önceki build son teslim CI'ı yerine sunulmaz; son head ayrıca sınanır. Ürün kaynağı 182f695 ve wheel Python baytları değişmedi; mevcut 27/24/30-process bütçeler yeniden koşulmadı veya gevşetilmedi.
