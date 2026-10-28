---
id: P01-4b
phase: P01
status: in_progress
size: M
depends_on: [P01-4a, P01-3b]
capabilities: [C12, C13]
---
# P01-4b — Kalıcı operation ve güvenli sahiplik

**Güncellendi:** 2026-10-29. **Paket:** [P01-4](../p01-4-delivery-plan.md). Kullanıcı review düzeltmeleri ve iki fresh revizyon turu tamamlandı, ADR-0016 Accepted; adım 1 uygulaması başlıyor. Bu kart paket adım 1–3'ü kapsar; her adım ayrı commit ve iki fresh review turudur.

## Kullanıcı sonucu ve mevcut eksik

Çökme veya sahip değişiminde aynı planın sessizce ikinci yan etki üretmesini önleyen kalıcı koordinasyon gerekir. Mevcut şema 5'te yalnız identity/cache/plan/onay vardır; operation/attempt/lease/sonuç ve bunların reset tüketicisi yoktur.

## Giren ve girmeyen kapsam

Yeni gerçek SQLite tüketicisi, atomik kabul/approval snapshot, tek gönderim bağı, sahiplik/lease/fencing, trusted salt uzlaştırma, bounded tarihçe/sonuç ve bakım uyumu girer. Native domain/application kuralları; porttan önce kalıcılık ve aynı plan tekliği esastır. Public run/backend/fixture komutu, HTTP taşıması, gerçek EVREN/ForgeLM, iptal isteği, artefakt toplama ve uzak rezervasyon/faturalama girmez. Pozitif dış etki yalnız test alanındaki sentetik ayrı süreçtedir.

## Bağımlılıklar ve kararlar

P01-4a PR #6 ile verified; P01-3b PR #8 ile verified, global expiry/V2 takip PR #9 ile development `a9f1f2e` tabanında. [ADR-0016](../../decisions/0016-operation-admission-and-ownership.md) Accepted; kullanıcı yetkisi ve iki fresh belge review'u hazır olma kapısını kapattı. SQLite/DELETE/EXTRA, mevcut 5 s store/30 s execution ve restore/recover ret kararları yeniden açılmaz. [Ön inceleme](../../research/p01-4-readiness-review.md).

## Sözleşme ve uygulama sınırı

Yaşam döngüsü/ownership/kotalar ADR-0016; wire [operations](../../reference/operations.md), state/migration [local-state](../../reference/local-state.md). Yeni domain/application/repository modülleri somut ihtiyaçla yazılır; CLI içine coordination kopyalanmaz. Composition dış etki/observation portlarını seçer; product composition blocked producer'ı desteklenmişe yükseltmez. Exact DDL ve golden checksum adım 1'de sabitlenir.

## Kabul

1. Gerçek 5→6 V2 migration; eski 1–5 SQL/checksum/handler değişmeden yeni boş tablolar, tam schema/FK/index/payload validation. Eski schema 2/3/4/5 yoğun fixture zincirleri mevcut toplam 5 s içinde başarıyla hedefe ulaşır; timeout pozitif kabul değildir. Snapshot/validation/commit süreleri ve VM adımları raw kayıtta ayrılır.
2. Güncel trusted input/credential/approval validation ile atomik kabul; admission, predispatch takeover ve arm transaction'larının her birinde **her credential'ın ID/revision/epoch/hedefi** tekrar okunur. A snapshot r1→B r2 commit→A final transaction ayrı süreç bariyerleriyle state_changed/sıfır start/tek env çözümü verir. Approval replace/revoke tarihsel snapshot'ı değiştirmez; aynı approval ID/gövde gereklidir. Revoke→reapprove işi canlandırmaz, idempotent approve sorun yaratmaz. İki süreç aynı planla tek operation'a yakınsar. Sahibi ölmüş/latch boş işte revoke/expiry/credential değişimi cleanup takeover ile failed olur; yeni izin/attempt/start yoktur, geçici hata terminal kanıt sayılmaz.
3. Plan forget FK/restrict ve eşzamanlı admission/forget güvenlidir; plan_in_use kontrollüdür. Full ve warm decode bozuk FK/digest/projection/owner/attempt/outcome/tarihçeyi state_invalid ile reddeder, boş sonuç saymaz.
4. Gerçek ayrı süreçte: admission, intent commit öncesi/sonrası, port çağrısı öncesi, gözlenebilir yan etki sonrası/yanıt öncesi, outcome commit öncesi/sonrası SIGKILL. Restart son atomik kaydı korur; dış etki sayısı **en fazla bir**, yeniden gönderim sıfır. Intent commit sonrası ama port öncesi kesintide konservatif unknown kabul edilir.
5. **Predispatch:** A latch boşken ölür/durur→lease dolar→B geçerli aynı onayla eski attempt'i abandoned yapıp yeni attempt ile en fazla bir start yapabilir; A'nın geç arm/yazısı reddedilir. **Postdispatch:** A latch doluyken ölür/durur→B aynı attempt'i yalnız reconcile eder, start sayısı artmaz. Intent COMMIT gecikmesi/son kontrol lease/generation kaybında port sıfır; eski owner unknown bile yazamaz. Tam expiry, renew/takeover, fence taşması, dört frontier indeksi/13.313 kontrol, 1.024 lease'in başka stateful çağrıda gözlenmesi ve saat geri dönüşü testlenir. Anomaly rollback/restart ile kaybolmaz. PID/fork ve iki thread permit tüketimi tek start verir. Port min(call_remaining,lease_remaining)−5 s deadline'ına uyunca maksimum cooperative çağrı sonrasında sonuç yazımı başarıyla tamamlanır; scheduler/I/O gecikmesi ayrı controlled unknown kabulüdür.
6. Unknown'a yeni approval/reset/epoch/current credential uygulanması ikinci gönderim üretmez. Trusted reconciliation target/account/project/run ID/correlation ve güncel read izni ister; not_found/401/timeout/cancel-accepted/wrong-target/çelişkili observation başarı/iptal sayılmaz. Plan expiry geçmiş read'e tek başına engel değildir. Execution succeeded + delivery pending başarı değildir; doğru teslim/terminal kanıtı gerekir.
7. Runtime restore/recover: sıfır operation, eski/boş snapshot, eksik hedef, backup sonrası unknown, eski intent/stage/live ve backup kaybında I/O/migration öncesi state_restore_unsupported. Dosyalar/intent korunur. Tam preview v3 root/snapshot/fingerprint ve strict sayılar sınanır. Heartbeat-only onayı bozmaz, owner/semantic/sonuç değişimi bozar. Reset atomik history koruma + ownership invalidation; predispatch cancelled/armed recovery unknown; eski owner yazamaz. **+1 yıl UTC→iş→saati düzelt→credential reset→reconcile** akışı hemen tamamlanabilir: geçmiş event timestamp'i değişmez, yeni gerçek UTC/epoch ve sıra kaydedilir, clock_anomaly görünür, yeni start yoktur.
8. 1.024 operation, 16 attempt/256 normal geçiş ve byte kotaları; admission/dispatch öncesi slot ayrımı, recovery ownership/renew/reset normal slot tüketmez. **255 dolu + sahibi ölü** iş takeover/read-reconcile yapabilir ve yeni yetkili sahip 256. terminal slotunu yazabilir; dolu predispatch iş cleanup/reset ile terminalleşebilir. History silinmez. İki ayrı yoğun pozitif fixture: tümü terminal 262.144 normal geçişte full validation; en yakın üst hacimli terminal/nonterminal karışımında reset. Mevcut 5 s kontrol deadline'ı açıkken referans ortamında pozitif tamamlanma, raw hacim/RSS/VM/wall/CPU/disk kaydı gerekir; timeout başarı değildir. Kota/fence/busy/disk-full/IOERR/commit gecikmesinde port başlamaz veya latch unknown kalır, ID ve kapasite türü korunur. State/transaction/lock/descriptor her yolda kapanır.

## Doğrulama

Unit durum/strict model/oracle; contract trusted port ve mevcut execution/CLI zarfı; integration gerçek SQLite/dosya ve ayrı süreç, yarış/kesinti, bakım ve sızıntı. Her adımda değişikliğe uygun hedefli test/Ruff/mypy/belge; kapanışta [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) tam takım/build/iki temiz kurulum ve mevcut 30-process startup bütçeleri. Tam dolu operation store ile stateful normal/yoğun jobs ölçümü P01-4c'de tamamlanır. Raw fixture hacmi/ortam/disk kaydedilir; referans donanımda pozitif kabul gerekir. Fiziksel güç kesintisi/Windows/canlı EVREN iddiası yoktur.

## Teslim kaydı

Uygulanmadı; PR/ürün commit'i ve test/ölçüm kanıtı yok. ADR onayı sonrası adımların commit/review/fix/kanıtı [paket planına](../p01-4-delivery-plan.md) bağlanacak. Mevcut startup bakım kanıtı bu kartın operation kabulü sayılmaz.
