---
id: P02-2g
phase: P02
status: verified
size: M
depends_on: [P02-2d]
capabilities: [C03, C12, C13]
---
# P02-2g — Exact işe ve döneme bağlı v2 maliyet kanıtı

**Tarih:** 2026-11-02. [P02-2 planı](../p02-2-delivery-plan.md); ADR-0026 kullanıcı revizyonunun dar uygulama birimi, aynı branch/tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı sayısal bütçenin hangi exact işi ve dönem sonrası maliyeti kapsadığını ayırt eden yerel temeli alır; prod pricing source bu kartta yoktur.

## Giren ve girmeyen kapsam

UploadCostWork/RequestLimits/ExecutionWindow ve UploadCostBound v2; scope/root/manifest/storage/parametre/attempt/byte/window digest'i, charge kategori/dönem ve post-period storage completeness. V1 modelleri/golden'ları aynen kalır. Canlı hesap, ücretli write, terms accept, DELETE veya ileri resume bu kart değildir.

## Bağımlılıklar ve kararlar

[ADR-0026](../../decisions/0026-explicit-unverified-transfer-attempts.md) kullanıcının koşullu onayı ve iki fresh revizyon turuyla Accepted oldu. Bu kart ancak o karar ve metadata bağımlılıkları verified iken ready olur; tarihsel d/e/f v1 kabulü v2 teslimi sayılmaz.

## Sözleşme ve uygulama sınırı

Kanonik [Upload v2](../../reference/dataset-upload-v2.md) tek ayrıntı kaynağıdır. Domain/application/adapter sınırları, eski wire ve quota korunur; fixture producer ürün backend'i yapılmaz.

## Kabul

Aynı scope farklı manifest/N/byte/root/storage/parametre/window/request cap yeniden kullanımının reddi; transfer-only/unknown storage numeric completeness=false; quote expiry ile charge period ayrımı; literal digest/golden; bool/float/overflow/extra/duplicate/UTF-8/boyut retleri. 128 file max iş ve source v1 byte eşliği. Her kod dilimi commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Doğrulanmış açık bulgu bırakılmaz.

## Doğrulama

İlgili contract/integration/process regresyonları, Ruff format/lint, strict mypy, belge/rehber/diff. Yeni kaynak old source-bound M5 başarısı diye sunulmaz; bütünleşik native/build/CI/live P02-2c sahibidir.

## Teslim kaydı

- PR/commit: [a8fbd7c](https://github.com/HodeTech/Yorunge/commit/a8fbd7c) uygulama, [2c9aded](https://github.com/HodeTech/Yorunge/commit/2c9aded) R1 test güçlendirmesi; aynı dal/tek nihai PR.
- Sonuç: 241 hedefli contract testi; Ruff/strict mypy; iki farklı fresh R1/R2 turu, doğrulanmış açık bulgu yok. [Kabul](../../research/p02-2-implementation-validation.md#p02-2g--exact-work-maliyet-v2).
- Kalan sınır: Saf yerel maliyet modeli; gerçek pricing producer, public upload ve admission/arm kapıları henüz yoktur. Son kaynak native/build/CI/live P02-2c'dedir.

