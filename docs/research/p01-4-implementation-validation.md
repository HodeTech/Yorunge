# P01-4 uygulama ve kabul kaydı

**Güncellendi:** 2026-10-29. **Durum:** Adım 1 uygulanıyor; paket ve P01-4b/4c kabulü tamamlanmadı. **Dal:** feat/p01-4-operations, development tabanı a9f1f2e. [Teslim planı](../roadmap/p01-4-delivery-plan.md), [karar/review disposition](p01-4-readiness-review.md).

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

## Sonraki adımlar

Adım 1 commit ve iki fresh review turuyla kapandıktan sonra admission/lease/tek gönderim (adım 2), recovery/terminal/reset (adım 3), public jobs ve bütünleşik kabul (adım 4) otomatik ilerler. Fiziksel güç kesintisi, gerçek EVREN/ForgeLM, Windows veya yayımlanmış paket kanıtı yoktur. PR ancak bütün paket tamamlandıktan sonra development'a açılır ve kullanıcı incelemesine bırakılır.
