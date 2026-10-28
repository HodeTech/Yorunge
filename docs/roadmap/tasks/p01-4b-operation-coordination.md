---
id: P01-4b
phase: P01
status: draft
size: M
depends_on: [P01-4a, P01-3b]
capabilities: [C12, C13]
---
# P01-4b — Kalıcı operation ve güvenli sahiplik

**Güncellendi:** 2026-10-28. **Paket:** [P01-4](../p01-4-delivery-plan.md). Kod başlamadı; ADR-0016 onayı bekleniyor. Bu kart paket adım 1–3'ü kapsar; her adım ayrı commit ve iki fresh review turudur.

## Kullanıcı sonucu ve mevcut eksik

Çökme veya sahip değişiminde aynı planın sessizce ikinci yan etki üretmesini önleyen kalıcı koordinasyon gerekir. Mevcut şema 5'te yalnız identity/cache/plan/onay vardır; operation/attempt/lease/sonuç ve bunların reset tüketicisi yoktur.

## Giren ve girmeyen kapsam

Yeni gerçek SQLite tüketicisi, atomik kabul/approval snapshot, tek gönderim bağı, sahiplik/lease/fencing, trusted salt uzlaştırma, bounded tarihçe/sonuç ve bakım uyumu girer. Native domain/application kuralları; porttan önce kalıcılık ve aynı plan tekliği esastır. Public run/backend/fixture komutu, HTTP taşıması, gerçek EVREN/ForgeLM, iptal isteği, artefakt toplama ve uzak rezervasyon/faturalama girmez. Pozitif dış etki yalnız test alanındaki sentetik ayrı süreçtedir.

## Bağımlılıklar ve kararlar

P01-4a PR #6 ile verified; P01-3b PR #8 ile verified, global expiry/V2 takip PR #9 ile development `a9f1f2e` tabanında. [ADR-0016](../../decisions/0016-operation-admission-and-ownership.md) Proposed; onay ve kapalı sözleşme review'u sonrası ready olur. SQLite/DELETE/EXTRA, mevcut 5 s store/30 s execution ve restore/recover ret kararları yeniden açılmaz. [Ön inceleme](../../research/p01-4-readiness-review.md).

## Sözleşme ve uygulama sınırı

Yaşam döngüsü/ownership/kotalar ADR-0016; wire [operations](../../reference/operations.md), state/migration [local-state](../../reference/local-state.md). Yeni domain/application/repository modülleri somut ihtiyaçla yazılır; CLI içine coordination kopyalanmaz. Composition dış etki/observation portlarını seçer; product composition blocked producer'ı desteklenmişe yükseltmez. Exact DDL ve golden checksum adım 1'de sabitlenir.

## Kabul

1. Gerçek 5→6 V2 migration; eski 1–5 SQL/checksum/handler değişmeden yeni boş tablolar, tam schema/FK/index/payload validation. Eski schema 2/3/4/5 yoğun fixture zincirleri mevcut toplam 5 s içinde başarıyla hedefe ulaşır; timeout pozitif kabul değildir. Snapshot/validation/commit süreleri ve VM adımları raw kayıtta ayrılır.
2. Güncel trusted input/credential/approval validation ile operation+attempt+lease atomik kabul; blocked/stale/değişmiş plan ve revoke/expiry yarışında port çağrısı sıfır. Approval replace/revoke tarihsel snapshot'ı değiştirmez; admission/takeover/arm aynı approval ID/gövdeyi ister. Revoke→reapprove mevcut operation'ı canlandırmaz, idempotent aynı approval sorun yaratmaz. İki ayrı süreç aynı planla tek operation'a yakınsar; repeated admission/terminal iş yeni izin üretmez.
3. Plan forget FK/restrict ve eşzamanlı admission/forget güvenlidir; plan_in_use kontrollüdür. Full ve warm decode bozuk FK/digest/projection/owner/attempt/outcome/tarihçeyi state_invalid ile reddeder, boş sonuç saymaz.
4. Gerçek ayrı süreçte: admission, intent commit öncesi/sonrası, port çağrısı öncesi, gözlenebilir yan etki sonrası/yanıt öncesi, outcome commit öncesi/sonrası SIGKILL. Restart son atomik kaydı korur; dış etki sayısı **en fazla bir**, yeniden gönderim sıfır. Intent commit sonrası ama port öncesi kesintide konservatif unknown kabul edilir.
5. A durur→lease dolar→B devralır→A geç döner; eski token'ın her mutasyonu ve sonucu reddedilir, B start yapmaz. Intent COMMIT gecikmesi/son kontrol öncesi lease veya generation kaybında port çağrısı sıfırdır; eski owner unknown dahi yazamaz, son atomik submitted takeover'a kadar korunur. Tam expiry, renew/release/takeover, fence taşması, ileri/geri saat, başka stateful çağrının lease expiry gözlemi ve reboot-benzeri monotonic referans değişimi ayrı sınanır. Anomaly rollback/restart ile kaybolmaz.
6. Unknown'a yeni approval/reset/epoch/current credential uygulanması ikinci gönderim üretmez. Trusted reconciliation target/account/project/run ID/correlation ve güncel read izni ister; not_found/401/timeout/cancel-accepted/wrong-target/çelişkili observation başarı/iptal sayılmaz. Plan expiry geçmiş read'e tek başına engel değildir. Execution succeeded + delivery pending başarı değildir; doğru teslim/terminal kanıtı gerekir.
7. Runtime restore/recover: sıfır operation, eski/boş snapshot, eksik hedef, backup sonrası unknown, eski intent/stage/live ve backup kaybında I/O/migration öncesi state_restore_unsupported. Dosyalar/intent korunur. Reset v3 operation/attempt/semantic değişimi onaya bağlar; heartbeat-only onayı bozmaz, takeover/sonuç değişimi bozar. Reset atomik history koruma + ownership invalidation; predispatch cancelled/armed unknown; geç eski sahibin yazısı reddedilir. İleri saatli operation + reset/yeni epoch + geri UTC birleşiminde geçmiş timestamp gerilemez, erken reconcile/reset state_changed olur; UTC yetişince aynı iş read/reconcile edilebilir, yeni start olmaz.
8. 1.024 operation, operation başına 16 attempt/256 geçiş ve byte sınırlarında kontrollü kapasite; port öncesi slot ayrımı, son terminal slotu, heartbeat no-history, otomatik silme yok. İki ayrı yoğun pozitif fixture: tümü terminal 1.024×256=262.144 geçişli maksimum tarihçede full validation; ayrıca nonterminal işte reset geçişi için normal slotu kalan, en yakın üst hacimli terminal/nonterminal karışımında reset. İkisi mevcut 5 s bütçesinde tamamlanır; kota dolu nonterminal resetinin ilan edilen kontrollü reddi ayrı negatiftir. Gerçek en yakın geçerli payload hacmi, RSS/VM/wall ve kaynak ortam raw kaydedilir; bütçe aşımı başarı sayılmaz. Kota/fence/busy/disk-full/IOERR/progress/commit gecikmesinde yan etki başlamaz veya mevcut intent unknown kalır; hata ID'yi korur. Bağlantı/descriptor/lock ve transaction her yolda kapanır.

## Doğrulama

Unit durum/strict model/oracle; contract trusted port ve mevcut execution/CLI zarfı; integration gerçek SQLite/dosya ve ayrı süreç, yarış/kesinti, bakım ve sızıntı. Her adımda değişikliğe uygun hedefli test/Ruff/mypy/belge; kapanışta [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) tam takım/build/iki temiz kurulum ve mevcut 30-process startup bütçeleri. Tam dolu operation store ile stateful normal/yoğun jobs ölçümü P01-4c'de tamamlanır. Raw fixture hacmi/ortam/disk kaydedilir; referans donanımda pozitif kabul gerekir. Fiziksel güç kesintisi/Windows/canlı EVREN iddiası yoktur.

## Teslim kaydı

Uygulanmadı; PR/ürün commit'i ve test/ölçüm kanıtı yok. ADR onayı sonrası adımların commit/review/fix/kanıtı [paket planına](../p01-4-delivery-plan.md) bağlanacak. Mevcut startup bakım kanıtı bu kartın operation kabulü sayılmaz.
