---
id: P02-2n
phase: P02
status: in_progress
size: M
depends_on: [P02-2g, P02-2f, P02-2k, P02-2l]
capabilities: [C03, C12, C13]
---
# P02-2n — Gerçek upload HTTP bütçe bağlantısı

**Tarih:** 2026-11-03. a/b üst kartlarının ortak HTTP bağımlılığı; üç dar kod dilimi, aynı branch ve tek nihai PR.

## Kullanıcı sonucu ve mevcut eksik

Saved work'teki request/attempt/body limitleri gerçek service/storage çağrılarında uygulanır; kullanıcı sayaçları metadata/byte/ücret garantisiyle karıştırmaz. Bugün domain limitleri ve stage intent slotları var; actual HTTP sayaçları bağlı değildir.

## Giren ve girmeyen kapsam

1. Kayıtlı service URI provenance ve default HTTP uyumu.
2. Pre-intent quota reservation ve owner/single-use metering modeli.
3. Aynı owned client/pool'a gerçek physical-attempt/request/response/storage byte bağlantısı, TLS/iptal/retry kabulü.

Her dilim geliştirme/test/commit, fresh R1/fix ve farklı fresh R2/fix ile kapanır. Producer/controller/public CLI, yeni fiyat/grant, native/live ve epik kabulü girmez.

## Bağımlılıklar ve kararlar

G/f/k/l yerel verified ve ADR-0024/0025/0026 Accepted. [HTTP quota referansı](../../reference/dataset-upload-http.md) koddan önce yazıldı; sabit work limitleri [v2 sözleşmesinde](../../reference/dataset-upload-v2.md) kalır. M provider codec'i ayrı tamamlandı; bu kart HTTP mekanizmasıdır.

## Sözleşme ve uygulama sınırı

Application registered URI/meter reservation; adapter shared HTTP transport sınırı. Default HttpRequest/discovery/legacy consumer değişmez. Budget token effect yetkisi veya durable DispatchPermit yerine geçmez. Private URL/body/key log veya sayaç DTO'suna girmez.

## Kabul

Exact registered method/target/path/query ve dynamic literal; default legacy regresyonu. Quota limit−1/limit/+1, yanlış scalar, reservation/owner/cancel/close ve iki worker aggregate kaynak sınırı. Gerçek read retry fiziksel sayaçları artırır; effectful retry yoktur. Red/timeout/partial/cancel yollarında sayaç düşürme/reset ile yeni hak açılmaz. TLS server oracle gerçek body/attempt eşliğini doğrular; sayaçlar provider kabulü veya billable CR değildir.

## Doğrulama

Contract + gerçek loopback TLS/source testleri; Ruff/strict mypy/doc/rehber/diff. Native/build/source CI yalnız son runtime/script değişikliği sonrasında c'de; burada çalışmış sayılmaz. Üç kod diliminin ayrı iki fresh turu kapanmadan n verified olmaz.

## Teslim kaydı

M iki fresh turla kapandı. N referansı/kartı hazırlandı; 1. URI dilimi uygulanıyor; rezervasyon modeli, wire bağlantısı ve kabul/review henüz yok. In_progress.
