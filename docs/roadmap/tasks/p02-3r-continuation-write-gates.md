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

Girer: save/approve/revoke/admit/arm/renew/receipt/stop_local/acquire_read/read_failed/prepare_initial_read/verified/cleanup kapılarının v3 için uygulanması; soy bağı ve kaynak donma (`cleanup_expired`), zincir dışı ve kaynağın torunlarında non-terminal operation yokluğu (admission transaction’ı içinde), `_namespace_available` atlaması ve kökün `intent_digest`i; `M=0` durum yolu (admission → proof → `succeeded`; admission → okuma hatası → `unknown/read_unavailable`; süre/lease kaybı → `unknown/request_uncertain`); arm’ın create/link ve `file_indices` dışını reddetmesi; presign’ın öncülsüzlüğü; confirm sayacı tabanı için `N−M` değerinin kayıttan sağlanması. Girmez: HTTP, producer/koordinatör, public yüzey, DDL.

## Bağımlılıklar ve kararlar

P02-3g verified olmalıdır. [ADR-0031](../../decisions/0031-upload-continuation.md)’in Accepted olması gerekir (bugün Proposed). Davranış [ADR-0031](../../decisions/0031-upload-continuation.md) §2/§5 ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md); yeni replay, politika veya TTL yoktur.

## Sözleşme ve uygulama sınırı

Mevcut clock, SQL transaction, lease/fence/CAS, kota ve hata öncelikleri yeniden kullanılır; v1/v2 yolları davranışsal olarak aynı kalır. v3 kaydı admission’da latched’tır; intent ve makbuz kuralları 3M ile sınırlıdır. Başarı: 3M accepted makbuz, N dosyalık ordered metadata (`TransferVerification v3`) ve kök baseline eşliği.

## Kabul

1. Gerçek SQLite ile her geçiş ve ret: draft/expired/revoked, ack kuralları, kaynak donmamış (etkin lease) → `operation_conflict`, aynı dataset’te zincir dışı veya kaynağın torununda non-terminal operation, kaynak terminal/`admitted`, kök baseline yok; iki süreç eşzamanlı admit → tam bir kazanan; zincirde ikinci hop admission.
2. `M=0`: admission → proof → `succeeded`; admission → okuma hatası → `unknown/read_unavailable`; admission → lease kaybı → `unknown/request_uncertain`; hiçbirinde intent yok ve cancelled’a düşme yok.
3. Arm create/link ve `file_indices` dışı indeksi reddeder; presign öncülsüz; PUT/confirm sırası, kronoloji ve tazelik v2 kuralıyla aynı; başarı eksik/fazla makbuz, eksik baseline veya N-dosya proof uyuşmazlığında yazılmaz.
4. Namespace: continuation save/admit `operation_conflict` almaz, ikinci create hakkı doğmaz; hot/full invariant kök operation’a bağlıdır.
5. Gerçek SIGKILL: admission, arm ve makbuz commit sınırlarında v3 geçmişi okunabilir kalır ve ikinci etki yoktur.
6. v1/v2 yaşam döngüsü ve golden’lar değişmeden geçer; reset (latched → unknown/identity_reset) ve revoke v3’te de tutarlıdır.

## Doğrulama

Gerçek SQLite/süreç/fork testleri, mevcut kota/maintenance regresyonları, Ruff ve strict mypy. Ağ ve public yüzey iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
