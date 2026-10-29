---
id: P01-4c
phase: P01
status: in_progress
size: M
depends_on: [P01-4b, P01-3b]
capabilities: [C12, C13]
---
# P01-4c — Yerel jobs list/show

**Güncellendi:** 2026-10-29. **Paket:** [P01-4](../p01-4-delivery-plan.md). P01-4b bu dalda verified; adım 4 kod/ilk test/build/kurulu jobs ve startup kabulü tamamlandı. İki fresh review turu ve paket kapanışı sıradadır.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı restart sonrasında kayıtlı işin planını, attempt'lerini ve son yerel sonucunu CLI/Python'dan bulabilmeli. Bugün yalnız execution planı list/show vardır; operation işiyle karıştırılmamalıdır.

## Giren ve girmeyen kapsam

Tek ortak kullanım senaryosuyla jobs list/show, bounded status/plan filtresi, keyset cursor, tipli summary/plan/attempt/outcome ve metin/JSON sonuçları girer. Provider refresh/watch/stop/reconcile, public run, demo görev veya ürün fixture seed komutu yoktur. Uzak sonuç/artefakt doğrulandığı iddia edilmez.

## Bağımlılıklar ve kararlar

P01-3b verified (PR #8/#9); P01-4b bu pakette adım 1–3 test/commit/iki review ve son kaynak kabulüyle verified oldu. [ADR-0016](../../decisions/0016-operation-admission-and-ownership.md) ve [operations wire](../../reference/operations.md) Accepted; uygulama yetkisi vardır. Ayrı merge zorunlu değildir.

## Sözleşme ve uygulama sınırı

Exact CLI/Python/Result/cursor/limits/hatalar operations referansındadır. CLI/domain/application/repository ortak kuralları kullanır; read güncel config/env/input/provider erişimine dönüşmez. Public producer draft/blocked, normal prepare jobs yaratmaz. CLI ve README uygulandığı adımda güncellenir; örnekler şimdiden çalışan komut diye yayımlanmaz.

## Kabul

1. Boş gerçek store boş liste; yalnız plan/approval prepare sonrası da sıfır job. İç portla üretilmiş kalıcı iş restart sonrası aynı plan/digest/attempt/outcome ile list/show'da görünür. Unknown/failed/cancelled okuması dış Result completed/null ve exit 0'dır; kayıtlı durum data içinde korunur.
2. Closed wire/strict API, UUID/status/limit/cursor/store/filtre eşliği; 1–100 limit, çok sayfalı artan immutable sıra, değiştirilmiş status filtresinin ilan edilmiş snapshot sınırı. Repeat/bool/float/extra/non-finite/duplicate/oversize ve bozuk cursor kontrollü hatadır. Liste N+1 ve tüm payload taraması yapmaz; show tek read snapshot'ıdır.
3. Operation-plan/attempt/outcome/projection bozukluğu state_invalid; geçerli eksik ID operation_not_found; filtrede geçerli eksik plan boş liste. SQLite disk/busy/platform/intent hatası boş sonuç olmaz. JSON stdout/stderr saflığı, secret/path/traceback yokluğu ve CLI/Python/text eşliği sınanır.
4. Jobs context değiştiren üst/aile/fiil seçeneklerini reddeder. Env/config/manifest/network/keychain/ML/araç keşfi yapılmaz; explicit state açılışının mevcut recovery/migration davranışı doğru belgelenir. Root/jobs help mevcut lazy metadata sınırını korur; --help/--version ve mevcut 30 yardım çıktısı regresyonu kontrol edilir.
5. Kaynak fixture iki hacimde: normal iş ve 1.024 operation + her birinde 16 attempt + sınıra yakın geçerli metadata/plan/outcome; ayrıca 256 geçişli tek iş. Liste limit+1 ve bounded bellek/query sayısı; show 256 KiB tavanı. Aynı host/disk/kurulu wheel'de en az 30 ayrı süreç; **yeni P01-4 jobs kabul hedefi** sıcak p95≤200 ms'dir; profil/cache ölçümü jobs kanıtı sayılmaz. Ulaşılan gerçek byte/row/VM/query ve RSS kaydedilir; hedef başarısızsa sessiz gevşetilmez.
6. Tam test/lint/type/belge/ajan, wheel/sdist ve iki temiz kurulum; temiz kurulumlarda sentetik iç fixture DB'sini okuyan gerçek jobs CLI/API, mevcut v1/cache/execution smoke ve lazy guard. Önceden hazırlanmış startup bakımının paired ölçümü korunur; Linux CI çıktısı bu P01-4 PR'ında incelenir, daha önceki merge CI reddi yeni ürün önkoşulu değildir.

## Doğrulama

Contract CLI/Python/wire, integration gerçek SQLite ve ayrı süreç/restart/snapshot/bozuk kayıt, kurulu artefakt ve normal/yoğun performans. [CONTRIBUTING matrisi](../../../CONTRIBUTING.md#doğrulama-seçimi) ve performans standardı geçerlidir. Sentetik test dış hesabın veya gerçek yürütme backend'inin kanıtı değildir.

## Teslim kaydı

İlk uygulama CLI/Python/strict cursor/bounded snapshot ve kullanıcı belgelerini içerir. 1.686 full test, son hedefli 93 test, iki temiz kurulum, 30-process normal/yoğun jobs ve eşli mevcut startup kapıları geçti; [ilk kabul kaydı](../../research/p01-4-implementation-validation.md#adım-4--public-yerel-jobs-ve-ilk-bütünleşik-doğrulama). Commit sonrası iki fresh review turu ve son kaynak/bütünleşik kapanış sıradadır; PR henüz açılmadı, kart in_progress kalır.
