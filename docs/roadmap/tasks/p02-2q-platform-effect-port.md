---
id: P02-2q
phase: P02
status: ready
size: M
depends_on: [P02-2p, P02-2n, P02-2o]
capabilities: [C03, C12, C13]
---
# P02-2q — Bütçeli gerçek Platform effect portu

**Tarih:** 2026-11-03. Aynı dal, a/b/c üst teslimi, tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Strict codec/quota/receipt tek başına gerçek request producer değildir. Port exact current source ve tek committed intent/permit ile gerçek HTTP'yi bir kez yapar; fake grant/cost/başarı üretmez. DB/controller/public yüzey ayrı kalır.

## Giren ve girmeyen kapsam

1. Intent öncesi private effect-call hazırlığı/quota/semantic bağ; actual TLS create/link/presign/confirm ve typed receipt/descriptor.
2. Aynı pool bounded descriptor PUT/byte hash, items pagination ve exact ordered metadata.

Her dilim commit ve iki fresh tur/fix ile kapanır. Controller/current memo/worker sırası, public API/CLI/summary sentinel, native/kurulum/source CI/live q kabulü değildir; r/public/c sonraki somut adımlardır. Provider direct wire açılmaz, generic direct mekanizması değişmez.

## Bağımlılıklar ve kararlar

P/n/o verified; Accepted ADR-0024/0025/0026/0027. [Port referansı](../../reference/dataset-upload-port.md) code öncesi exact internal sınırı tanımlar; [provider](../../reference/platform-upload-consumer.md) ve [v2 receipt/current](../../reference/dataset-upload-v2.md) değişmez. Yeni temel karar/ADR yoktur.

## Sözleşme ve uygulama sınırı

Adapter aynı UploadHttpxTransport/UploadBudget üstünde gerçek I/O yapar; application/domain semantic kuralı ortak kullanılır. Port DB/lease/permit üretmez; caller raw proof/client/secret header dict'i alamaz. Private raw key/URL ephemeral ve output/receipt dışında kalır.

## Kabul

Pre-intent typed validation/quota; exact intent operation/kind/index/request digest, permit/call/budget/credential bağları ve zero-wire ret; tek physical effect/no retry; actual TLS receipt/descriptor/byte/source/status/raw/literal/encoding sınırı; cancel/partial/cleanup. Metadata total/cursor/item/path/size/hash bijeksiyonu/null/duplicate ve bounded pages; local binding ağda yok; raw key/URL serialization/receipt/log/exception'da yok. V1 golden semantic digest aynı kalır.

## Doğrulama

Dar codec/semantic/actual TLS port/source/HTTP quota testleri ve gerekli önceki regresyon; Ruff/strict mypy/doc/rehber/diff. Her dilim iki fresh tur. Controller/native/live sonucu burada iddia edilmez.

## Teslim kaydı

Kart ready; port code henüz başlamadı. P02-2p yerel kalıcılık temeli verified, actual remote/public üst teslimi açık. Uygulama gerçek commit/review/test sonuçlarıyla güncellenir.
