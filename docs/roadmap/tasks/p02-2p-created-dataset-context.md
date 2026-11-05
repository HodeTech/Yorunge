---
id: P02-2p
phase: P02
status: verified
size: M
depends_on: [P02-2o]
capabilities: [C03, C12, C13]
---
# P02-2p — Kalıcı create baseline ve legacy gate

**Tarih:** 2026-11-03. P02-2a/b/c üst teslimi, aynı dal ve tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Restart detail karşılaştırması ilk create'teki iki owner alanını da kanıtlayabilir. Tarihsel eksik baseline yeni etki/harcama üretmez; eski terminal geçmiş korunur. Bu kart public writer/controller veya live kabulü değildir.

## Giren ve girmeyen kapsam

1. Ayrı CreateReceiptV2, kapalı receipt union, canonical golden/sınırları, structural kind/version/ID/plan kontrolü; eski history/full/reset/backup/capacity uyumu. Yeni writer açmaz.
2. Yeni accepted-create insert'i yalnız v2; atomik receipt+dataset ID, late-response/time/owner kapısı; legacy nonterminal tüm yeni arm/renew/read lease/proof öncesi engel, koşullu owner/CAS marker. Eski yeni-writer fixture'ları v2'ye geçer; tarihsel v1 fixture'lar korunur.

Her dilim commit+fresh R1/fix+farklı fresh R2/fix. Public renderer/controller, gerçek ağ write/kill uçtan uca, native/kurulum/source CI ve live c'nin sonraki bütünleşik kabulleridir. Public summary'ye receipt veya created_dataset eklenmez; sentinel output kabulü controller/public dilimine zorunlu aktarılır.

## Bağımlılıklar ve kararlar

O ve bütün yerel temel verified. [ADR-0027](../../decisions/0027-durable-created-dataset-context.md) kullanıcı review düzeltmeleri ve iki fresh tur sonrası Accepted; [v2 receipt referansı](../../reference/dataset-upload-v2.md#kalıcı-create-receipt-ve-tarihsel-geçiş) kanoniktir. DDL/migration 1–7, eski byte/golden/terminal history ve 2 KiB slot/rezerv değişmez. Ham response 1 MiB, canonical receipt 2 KiB ayrı sınırlar.

## Sözleşme ve uygulama sınırı

Domain kapalı DTO/union ve owner/plan bağıdır; repository kısa SQLite fazlarında write/owner/CAS ve atomik kayıt uygular. Controller pre-read/pre-arm aynı yerel baseline gate'ini kullanır; public view yerine dar summary döner. Seçili credential literal ve raw/receipt byte sınırları mevcut canonical referanstadır. Yeni replay/grant/fiyat veya mixed-version dönüşümü yoktur.

## Kabul

Literal v1/v2 decode/byte, strict scalar/version/kind/result ve ID üçlü eşliği; owner kind ve nonselected owner; Unicode/escape worst-case, 2 KiB ve raw büyük temiz yanıt. New v2+new accepted create v1 → no-business-commit/state_invalid; v1+v2 ret. Legacy terminal full validation/golden ve diğer receipt v1 byte'ları korunur. Aynı nonterminal legacy için her arm/renew/acquire/read/proof → zero HTTP/permit/new lease; active other owner, expiry, marker ret ve terminal yarışında durum doğru anlatılır. Receipt+ID atomik rollback/commit/kill; geç intent response/reset/rotation; eksik baseline hiçbir owned/detail backfill veya replay üretmez. Full graph yeni success kapısı ayrı; bakım/reset/capacity/backup mixed family ve old binary kontrollü ret.

## Doğrulama

Domain/golden ve gerçek SQLite/process sınırları; önceki journal/recovery/history/maintenance regresyonları; format/lint/strict mypy/doc/rehber/diff. Controller/native/live bu yerel karttan ayrı gerçek sonuçla kapatılır. İki dilim ve tüm fresh turlar bitmeden verified değildir.

## Teslim kaydı

- PR/commit: [746ac36](https://github.com/HodeTech/Yorunge/commit/746ac36); tek nihai P02-2 PR'ı henüz açılmadı.
- Sonuç: P.1 DTO/union/history ve p.2 writer/legacy gate, ayrı commit ve ikişer fresh review/fix teyidiyle çalışma dalında yerel verified. Yeni V2 accepted-create, atomik receipt+ID, strict read/history/backup/reset, legacy no-new-rights ve gerçek SQLite kill/spawn kanıtı; [kabul kaydı](../../research/p02-2-implementation-validation.md#p02-2p2--atomik-writer-ve-legacy-mutation-kapısı).
- Kalan sınır: Gerçek HTTP effect portu/controller, public summary sentinel, API/CLI, native/kurulum/source CI ve ayrı canlı upload henüz kabul değildir. Üst a/b/c ve epik açık kalır; grant/fiyat kanıtı yoktur.
