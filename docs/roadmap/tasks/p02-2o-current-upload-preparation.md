---
id: P02-2o
phase: P02
status: in_progress
size: M
depends_on: [P02-2n, P02-2m, P02-2k]
capabilities: [C03, C12, C13]
---
# P02-2o — Güncel upload girdisi ve gerçek hazırlık

**Tarih:** 2026-11-03. a üst kartının gerçek provider hazırlığı; aynı branch ve tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Plan/approve/start yalnız güncel tam dosya kümesi ve doğru bildirilen owner/project ile ilerler. Gözlenmiş profil grant/fiyat üretmez; default draft, explicit risk/onay ayrımı korunur. Mevcut saf codec/journal/meter tek başına gerçek current producer değildir.

## Giren ve girmeyen kapsam

1. Tam yerel hash snapshot'ı ve sonraki descriptor metadata/üyelik recheck; request model revalidation'ın warning/exception girdi sızıntısı sınırı.
2. Aynı bütçeli session'da zorunlu provider okumaları, exact context/dataset/my-role ve typed not_exposed/current/read sonuçları.
3. Bu gerçek input/producer ile private prepare/approve/revoke kompozisyonu; her kısa SQLite fazı ayrı açılır, ağ/hash sırasında store tutulmaz.

Her dilim commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Start/etkili workflow/reconcile controller ve public API/CLI sonraki dar kartlardır; native/kurulum/CI/live kabulü c'dedir. Yeni maliyet/grant kaynağı veya SDK yoktur.

## Bağımlılıklar ve kararlar

N/m/k çalışma dalında verified; ADR-0024/0025/0026 Accepted. [Hazırlık referansı](../../reference/dataset-upload-preparation.md) mevcut tam hash/current sözleşmesini somutlaştırır. Global plan/approval/storage wire ve eski golden değişmez; yeni ADR gerektiren politika seçimi yoktur.

## Sözleşme ve uygulama sınırı

Adapter no-follow filesystem observation; application typed producer/proof; composition state/env/session sahipliği. Kullanıcı raw producer, bool verified, grant/cost veya private snapshot enjekte edemez. Snapshot read-only gözlemdir; write permit değildir.

## Kabul

Tüm dosya hash/isim/boyut/root eşliği; symlink/ancestor/metadata/üyelik değişimi; sabit mtime ile değişen içerik ilk hash'te ret; hardlink/aynı hash farklı ad korunur. Recheck yalnız metadata okur, atomik snapshot iddiası yoktur; gönderimde byte hash ayrıca doğrulanır. Warning-as-error, nested bozuk model/canary ve exception chain negatifleri. Gerçek TLS context/role/status/raw JSON ve credential/epoch/clock yarışları; prepare/approve no effect, eksik girdi/yanlış owner/private ile store/HTTP etkisi sıfır. Default draft, explicit unpriced exact acknowledgement; null grant/cost honest kalır.

## Doğrulama

Dar local input/codec testleri, ilgili eski dataset regresyonları, gerçek TLS producer, state/current yarışları; Ruff/mypy/doc/rehber/diff. Her dilimin iki fresh turu ve anlamlı kabulleri bitmeden o verified olmaz. Public/native/live gelecekteki kabul diye açık tutulur.

## Teslim kaydı

O.1 input/revalidation kodlandı, 481 ilgili test geçti; ilk commit/iki fresh tur bekliyor. O.2/o.3 ve gerçek public workflow/c kabulü henüz yoktur. D–n temeli bu bütünleşik teslimin yerine geçmez.
