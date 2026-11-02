---
id: P02-2h
phase: P02
status: draft
size: M
depends_on: [P02-2g]
capabilities: [C03, C12, C13]
---
# P02-2h — V2 politika, reducer ve onay bağı

**Tarih:** 2026-11-02. [P02-2 planı](../p02-2-delivery-plan.md); ADR-0026 kullanıcı revizyonunun dar uygulama birimi, aynı branch/tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı kanıt eksiğini, gerçek blocker'ı ve onay gereğini doğru ayıran v2 yerel plan temelini alır.

## Giren ve girmeyen kapsam

V2 plan/approval/current-check ve authorization/upload observation tipleri, policy-aware reducer ve snapshot factory. Default verified_only; explicit/unpriced acknowledgements, exact baseline/supplemental ve immutable binding. Henüz SQL/HTTP/public CLI dispatch yoktur. Canlı hesap, ücretli write, terms accept, DELETE veya ileri resume bu kart değildir.

## Bağımlılıklar ve kararlar

[ADR-0026](../../decisions/0026-explicit-unverified-transfer-attempts.md) kullanıcının koşullu onayı ve iki fresh revizyon turuyla Accepted oldu. Bu kart ancak o karar ve metadata bağımlılıkları verified iken ready olur; tarihsel d/e/f v1 kabulü v2 teslimi sayılmaz.

## Sözleşme ve uygulama sınırı

Kanonik [Upload v2](../../reference/dataset-upload-v2.md) tek ayrıntı kaynağıdır. Domain/application/adapter sınırları, eski wire ve quota korunur; fixture producer ürün backend'i yapılmaz.

## Kabul

96 bağımsız literal policy/proof/cost/input satırı; v2 plan/approval golden'ları; eksik/gereksiz bool/yanlış policy, full/partial/null ve current null→positive/partial→full/full→expired; draft onay ret; v1 golden korunumu. Her kod dilimi commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Doğrulanmış açık bulgu bırakılmaz.

## Doğrulama

İlgili contract/integration/process regresyonları, Ruff format/lint, strict mypy, belge/rehber/diff. Yeni kaynak old source-bound M5 başarısı diye sunulmaz; bütünleşik native/build/CI/live P02-2c sahibidir.

## Teslim kaydı

Uygulama başlamadı; draft. Gerçek commit/review/test ve kalan sınır oluşunca kaydedilir.

