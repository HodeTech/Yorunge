---
id: P02-2i
phase: P02
status: draft
size: M
depends_on: [P02-2h, P02-2e]
capabilities: [C03, C12, C13]
---
# P02-2i — V1 ve V2 journal okuma ve tam graph doğrulaması

**Tarih:** 2026-11-02. [P02-2 planı](../p02-2-delivery-plan.md); ADR-0026 kullanıcı revizyonunun dar uygulama birimi, aynı branch/tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı eski geçmişini koruyan, yeni payload'ı kapalı doğrulayan kalıcı okuma temelini alır.

## Giren ve girmeyen kapsam

Kapalı union decoder ve v2 record/control/verification; DDL/checksum değişmeden history/list/show/full graph/rezerv doğrulaması. Yeni public writer bu kartta açılmaz. Canlı hesap, ücretli write, terms accept, DELETE veya ileri resume bu kart değildir.

## Bağımlılıklar ve kararlar

[ADR-0026](../../decisions/0026-explicit-unverified-transfer-attempts.md) kullanıcının koşullu onayı ve iki fresh revizyon turuyla Accepted oldu. Bu kart ancak o karar ve metadata bağımlılıkları verified iken ready olur; tarihsel d/e/f v1 kabulü v2 teslimi sayılmaz.

## Sözleşme ve uygulama sınırı

Kanonik [Upload v2](../../reference/dataset-upload-v2.md) tek ayrıntı kaynağıdır. Domain/application/adapter sınırları, eski wire ve quota korunur; fixture producer ürün backend'i yapılmaz.

## Kabul

Literal v2 graph/control/proof golden/digest; mixed version/slot/digest/chronology retleri; eksik intent ama mevcut accepted+metadata eş iken success yok; v1 history/checksum, max boyut/rezerv ve tarihi proof tazelik ayrımı. Her kod dilimi commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Doğrulanmış açık bulgu bırakılmaz.

## Doğrulama

İlgili contract/integration/process regresyonları, Ruff format/lint, strict mypy, belge/rehber/diff. Yeni kaynak old source-bound M5 başarısı diye sunulmaz; bütünleşik native/build/CI/live P02-2c sahibidir.

## Teslim kaydı

Uygulama başlamadı; draft. Gerçek commit/review/test ve kalan sınır oluşunca kaydedilir.

