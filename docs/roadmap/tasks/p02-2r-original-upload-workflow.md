---
id: P02-2r
phase: P02
status: in_progress
size: M
depends_on: [P02-2q]
capabilities: [C03, C12, C13]
---
# P02-2r — Tek original upload iş akışı

**Tarih:** 2026-11-03. Aynı P02-2 dalı ve tek nihai development PR’ı; public kullanıcı yüzeyi ayrı, epik kapsamı korunur.

## Kullanıcı sonucu ve mevcut eksik

Gerçek portlar tek başına bir işi tamamlamaz. Koordinatör bir original invocation içinde create → proje bağlantısı → bütün presign’lar → bounded PUT → seri confirm → metadata proof akışını kalıcı aynı operation ile birleştirir; durunca yeni yazma hakkı üretmez.

## Giren ve girmeyen kapsam

1. Private invocation/environment ve application algoritması: ağsız existing lookup, tek original toplam bütçe/credential snapshot, gerçek input/current producer, yeni admission ve create/link fazı. Ara faz private kalır, teslim başarısı döndürmez.
2. Bütün presign’lar/bijeksiyon, en çok iki PUT worker’ı, seri confirm ve her arm için metadata/current/final state kapıları. İlk hata yeni aşamaları durdurur, başlamış worker’lar kapanır; önceden commit edilmiş permit fiziksel olarak geri alınmış sayılmaz.
3. Initial-owner current read ve tam graph/immutable create-detail/items eşliğiyle yeni proof; application hata/iptal ve aynı-ID unknown marker, gerçek workflow/cevap kaybı/kill sınırları.

Her dilim commit + fresh R1/fix + farklı fresh R2/fix ile kapanır. Ayrı restart/reconcile controller, public summary/API/CLI ve bütünleşik native/kurulum/source CI/live sonraki s/public/c kabulleridir. Yeni canlı çağrı, grant veya fiyat kaynağı bu karttan çıkmaz.

## Bağımlılıklar ve kararlar

Q verified; p baseline/writer, o current/input/preparation, n meter/budget ve önceki v2 state/policy temeli verified. Accepted ADR-0024/0025/0026/0027 değişmez. [Koordinatör referansı](../../reference/dataset-upload-workflow.md) uygulama öncesi akışı daraltır; [v2](../../reference/dataset-upload-v2.md) tek state/policy/proof kaynağıdır. Yeni temel karar veya ADR yoktur; iki eksenli preflight ve katman açıklığı düzeltmesi tamamlandı.

## Sözleşme ve uygulama sınırı

Application algoritması adapter import etmez; private environment/typed port protokolü mevcut gerçek producer/DB/session composition’ına bağlanır. CLI/Python ileride aynı kullanım senaryosuna gider. Environment bütün SQLite fazlarını kısa tutar; dosya hash/recheck ve await sırasında store/transaction açık kalmaz. Public caller environment/client/proof/current flag enjekte etmez. Ara sonuç ve full receipt/provider DTO private kalır.

## Kabul

Existing operation lookup config/env/source/network/admission/lease/permit üretmeden aynı ID’yi bulur. Yeni işlemde exact saved scope, tek captured secret, full hash ve immutable plan/onay, current timestamp/memo ve pre-intent reservation geçer. Gerçek stateful TLS provider ile tek create/link, bütün distinct presign descriptor’ları ilk PUT öncesi; iki worker ve seri confirm sayısı; byte/hash ve metadata tam grafiğiyle metadata success, authority false. Bir mandatory read/schema/status/input/revoke/reset/clock/lease/cancel/cevap kaybı hatası ikinci write/re-presign/fallback üretmez. Marker owner/CAS kapısı başarısızsa yanlış unknown yazıldı iddiası yoktur; operation ID ve güvenli reason korunur. Task.cancel cleanup sonrası yeniden yayılır. Commit öncesi/sonrası ve ID çıktısı öncesi kill recovery aynı yerel kayıtla gözlenir; ayrı read-takeover burada açılmaz.

## Doğrulama

Application/gerçek composition testleri; stateful loopback TLS, SQLite/process kill ve ilgili eski port/current/journal/recovery testleri; kaynak/sır/worker/DB-lock sınırı, Ruff/strict mypy/doc/rehber/diff. Native/kurulum/source CI ve canlı ücretli upload burada tamamlanmış gösterilmez. Her dilimde iki fresh tur ve doğrulanmış bulgu kapanışı gerekir.

## Teslim kaydı

R.1 private original invocation/admission/create-link commit ve iki fresh kod review/fix turuyla yerel kapandı. R.2 dosya fazları doğrulanmış worker yarışı fix’i, bağımsız teyit ve farklı fresh R2 ile yerel kapandı. R.3 initial proof/full workflow açık; private ara record running’dır, teslim başarısı değildir. Q yerel verified temeli korunur.
