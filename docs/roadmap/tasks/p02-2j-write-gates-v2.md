---
id: P02-2j
phase: P02
status: verified
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

Kanonik [Upload v2](../../reference/dataset-upload-v2.md) tek ayrıntı kaynağıdır. Kalıcı etki adedi rezervi, port izninden önce commit edilen tekil stage intent slotudur. Gerçek HTTP body/read/response byte sayaçları exact producer/codec ile P02-2a/b bütünleşmesinde bağlanır; bu kart public port açmaz veya bu ölçümü yapılmış saymaz. V2 verified_read tarihçesi ortak writer geçişinin parçasıdır; null-grant explicit read/takeover ve read hata kaydı P02-2k kapsamıdır. Domain/application/adapter sınırları, eski wire ve quota korunur; fixture producer ürün backend'i yapılmaz.

## Kabul

Sıfır permitli v1 ret ve v2 draft/ack retleri; aynı plan/namespace/race/PID/fork/revoke/reset/credential/clock/lease fencing; partial/current proof expiry/semantic change; port deadline/null min; control/read kapsama geçmeden terminal invariants ve kapasite. Her kod dilimi commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Doğrulanmış açık bulgu bırakılmaz.

## Doğrulama

İlgili contract/integration/process regresyonları, Ruff format/lint, strict mypy, belge/rehber/diff. Yeni kaynak old source-bound M5 başarısı diye sunulmaz; bütünleşik native/build/CI/live P02-2c sahibidir.

## Teslim kaydı

- PR/commit: [f88a6e7](https://github.com/HodeTech/Yorunge/commit/f88a6e7) v2 writer/v1 kapanışı; [32950be](https://github.com/HodeTech/Yorunge/commit/32950be) current süre/freshness COMMIT ve kalıcı son gözlem düzeltmesi; ayrı PR yok.
- Sonuç: 529 ortak upload testi; fix sonrası 78 journal, 11 odaklı zaman/reopen testi; 99 kaynak strict mypy/Ruff. İki farklı fresh tur ve doğrulanmış P2 kapanışı; [kabul](../../research/p02-2-implementation-validation.md#p02-2j--v2-durable-write-kapıları).
- Kalan sınır: Yerel durable writer; null-grant explicit read/recovery k, exact provider/read/body byte sayaçları ve public kullanım a/b, native/build/CI/live c'dedir.

