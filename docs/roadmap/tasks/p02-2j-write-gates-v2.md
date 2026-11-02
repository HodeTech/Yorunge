---
id: P02-2j
phase: P02
status: draft
size: M
depends_on: [P02-2i, P02-2f]
capabilities: [C03, C12, C13]
---
# P02-2j — V2 admission, current check ve tek yazma kapıları

**Tarih:** 2026-11-02. [P02-2 planı](../p02-2-delivery-plan.md); ADR-0026 kullanıcı revizyonunun dar uygulama birimi, aynı branch/tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı uygun onayın yeni veya ikinci gönderime dönüşmesini engelleyen v2 durable write temelini alır.

## Giren ve girmeyen kapsam

Repository save/approve/admit/arm/receipt/revoke v2, exact baseline/supplemental current gate, nullable deadline terimleri ve request quota rezervi. V1 yeni approve/admit/arm kapanır; existing lookup/inflight history korunur. Gerçek provider/public CLI yoktur. Canlı hesap, ücretli write, terms accept, DELETE veya ileri resume bu kart değildir.

## Bağımlılıklar ve kararlar

[ADR-0026](../../decisions/0026-explicit-unverified-transfer-attempts.md) kullanıcının koşullu onayı ve iki fresh revizyon turuyla Accepted oldu. Bu kart ancak o karar ve metadata bağımlılıkları verified iken ready olur; tarihsel d/e/f v1 kabulü v2 teslimi sayılmaz.

## Sözleşme ve uygulama sınırı

Kanonik [Upload v2](../../reference/dataset-upload-v2.md) tek ayrıntı kaynağıdır. Domain/application/adapter sınırları, eski wire ve quota korunur; fixture producer ürün backend'i yapılmaz.

## Kabul

Sıfır permitli v1 ret ve v2 draft/ack retleri; aynı plan/namespace/race/PID/fork/revoke/reset/credential/clock/lease fencing; partial/current proof expiry/semantic change; port deadline/null min; control/read kapsama geçmeden terminal invariants ve kapasite. Her kod dilimi commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Doğrulanmış açık bulgu bırakılmaz.

## Doğrulama

İlgili contract/integration/process regresyonları, Ruff format/lint, strict mypy, belge/rehber/diff. Yeni kaynak old source-bound M5 başarısı diye sunulmaz; bütünleşik native/build/CI/live P02-2c sahibidir.

## Teslim kaydı

Uygulama başlamadı; draft. Gerçek commit/review/test ve kalan sınır oluşunca kaydedilir.

