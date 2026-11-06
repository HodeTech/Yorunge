---
id: P02-3r
phase: P02
status: draft
size: M
depends_on: [P02-3g]
capabilities: [C03, C12]
---
# P02-3r — Continuation yazma kapıları, soy bağı ve M=0 geçişleri

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 5. Yaşam döngüsü ve yazma kapıları; HTTP/koordinatör P02-3h’dedir. Kimlik sırası: bu kart P02-3g’den ayrıştırıldığı için alfabetik olarak sondadır, yürütme sırası planda gösterilir.

## Kullanıcı sonucu ve mevcut eksik

v3 geçmişi okunabilse bile continuation’ı güvenle başlatan kapılar yoktur: kaydetme, onay/iptal, admission (soy bağı, kaynak donma, dataset tekilliği), arm, makbuz, read lease, proof ve yerel durdurma/temizlik v1/v2’yi tanır.

## Giren ve girmeyen kapsam

Girer: save/approve/revoke/admit/arm/renew/receipt/stop_local/acquire_read/read_failed/prepare_initial_read/verified/cleanup kapılarının v3 için uygulanması; soy bağı ve kaynak donma (`cleanup_expired`), zincir dışı ve kaynağın torunlarında non-terminal operation yokluğu (admission transaction’ı içinde), `_namespace_available` atlaması ve kökün `intent_digest`i; durum yolu: latch ilk intent’te (v2 ile aynı; ilk intent öncesi kesinti/süre dolumu/yerel iptal → `cancelled`, kaynak değişmez), `read_failed`te v3 için açık `read_unavailable` dalı (mevcut kod yalnız v2 için bunu seçer); `verification_only` (M=0) kayıt için admission → okuma → proof → `succeeded` ve okuma hatası/kesinti/süre dolumunda `unknown`/`operation_uncertain` olmayan, kaynağın kendi kodunu taşıyan hata ve `cancelled/local_cancelled` (ADR-0031 §5 uç-durum tablosu) — bunun için mevcut kodun şu dalları v3 için açık yazılır: `prepare_initial_read` (`admitted` kabul edilir ⇔ `verification_only`), `read_failed` ve `_uncertain_verification` (latch’siz kayıtta `unknown` yazılmaz, yerel iptale gider), `stop_local` nedeni (`local_cancelled`); `--prepare` donma yolunun yalnız `running` kaynağa uygulanması (zaten `unknown` kaynağa dokunmaz, ikinci eşzamanlı `--prepare` fence/revision’ı yeniden artırmaz, `read_unavailable`/`identity_reset` nedenini ezmez) ve lease’i dolmuş unlatched `admitted` torunları `cancelled` yapması; admission’da `source_superseded` (kaynağın intent’li torunu) denetimi; arm’ın create/link ve `file_indices` dışını reddetmesi; presign’ın öncülsüzlüğü; confirm sayacı tabanı için `N−M` değerinin kayıttan sağlanması. Girmez: HTTP, producer/koordinatör, public yüzey, DDL.

## Bağımlılıklar ve kararlar

P02-3g verified olmalıdır. [ADR-0031](../../decisions/0031-upload-continuation.md)’in Accepted olması gerekir (bugün Proposed). Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §2/§5 ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md); yeni replay, politika veya TTL yoktur.

## Sözleşme ve uygulama sınırı

Mevcut clock, SQL transaction, lease/fence/CAS, kota ve hata öncelikleri yeniden kullanılır; v1/v2 yolları davranışsal olarak aynı kalır. v3 kaydı v2 gibi ilk intent’te latch’lenir (admission’da latch yoktur); `verification_only` kayıt hiç latch’lenmez; intent ve makbuz kuralları 3M ile sınırlıdır. Başarı: 3M accepted makbuz, N dosyalık ordered metadata (`TransferVerification v3`) ve kök baseline eşliği.

## Kabul

1. Gerçek SQLite ile her geçiş ve ret: draft/expired/revoked, ack kuralları, kaynak donmamış (etkin lease) → `operation_conflict`, aynı dataset’te zincir dışı veya kaynağın torununda non-terminal operation, kaynak terminal/`admitted`, kök baseline yok; admission’da kaynağın hâlâ non-terminal ve lease’siz olması (`--prepare` ile admission arasında `reconcile` kaynağı `succeeded` yaparsa admission reddedilir); iki süreç eşzamanlı admit → tam bir kazanan; zincirde ikinci hop admission.
2. `M=0` (`verification_only`) uç-durum tablosunun her satırı: admission → proof → `succeeded`; admission → okuma hatası → kaynağın kendi kodu (exit 1/3; `operation_uncertain`/5 değil) ve kayıt `cancelled/local_cancelled`, hiçbir zaman `unknown`; admission → SIGINT/Task iptali → `request_cancelled`/6 ve `cancelled/local_cancelled`; admission → lease kaybı/SIGKILL → `cleanup_expired` ile `cancelled/lease_expired`; hiçbirinde intent yok; aynı plan yeniden başlatılamaz (yeni `resume --prepare` gerekir). `M>0`: ilk intent öncesi SIGKILL → lease dolunca `cancelled`, kaynak değişmeden kalır ve aynı kaynaktan yeniden plan M’yi aynı bulur; ilk intent sonrası → `unknown/request_uncertain`; `read_failed` v3’te `unknown/read_unavailable` (v1 dalı değişmez).
3. Arm create/link ve `file_indices` dışı indeksi reddeder; presign öncülsüz; PUT/confirm sırası, kronoloji ve tazelik v2 kuralıyla aynı; başarı eksik/fazla makbuz, eksik baseline veya N-dosya proof uyuşmazlığında yazılmaz.
4. Namespace: continuation save/admit `operation_conflict` almaz, ikinci create hakkı doğmaz; hot/full invariant kök operation’a bağlıdır.
5. Gerçek SIGKILL: admission, arm ve makbuz commit sınırlarında v3 geçmişi okunabilir kalır ve ikinci etki yoktur.
6. v1/v2 yaşam döngüsü ve golden’lar değişmeden geçer; reset (latched → unknown/identity_reset) ve revoke v3’te de tutarlıdır.
7. Donma ve dal: `--prepare` freeze yalnız `running` kaynağa uygulanır; zaten `unknown` kaynakta (neden `read_unavailable`/`identity_reset` dahil) no-op’tur ve iki süreç eşzamanlı `--prepare`’da fence/revision tek kez artar; kaynağın intent’li torunu varsa admission `source_superseded` ile reddedilir, intent’siz `cancelled` torun kaynağı bloke etmez; lease’i dolmuş `admitted` torun `--prepare`’da temizlenir.

## Doğrulama

Gerçek SQLite/süreç/fork testleri, mevcut kota/maintenance regresyonları, Ruff ve strict mypy. Ağ ve public yüzey iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
