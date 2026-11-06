---
id: P02-3g
phase: P02
status: draft
size: M
depends_on: [P02-3f]
capabilities: [C03, C12]
---
# P02-3g — Continuation kalıcı journal, yaşam döngüsü kapıları ve kota

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 4. En ağır dilimdir; ölçülen büyüklük bölünmeyi gerektirirse bu karttan önce kayıt altına alınır.

## Kullanıcı sonucu ve mevcut eksik

v3 tipleri kalıcılaştırılıp güvenle kullanılamadan continuation çalışamaz: kaydetme, onay/iptal, admission, arm, makbuz, read lease, proof ve reset/yedek davranışı bugün yalnız v1/v2’yi tanır.

## Giren ve girmeyen kapsam

Repository/store’un v3 plan, onay, kayıt, kontrol ve doğrulamayı tanıması; save/approve/revoke/admit/arm/renew/stop/acquire_read/verified kapıları; soy bağı, kaynak donma ve dataset başına tek non-terminal operation kontrolü; namespace davranışı; aşama grafiği (3M), öncüller ve kronoloji; kota/rezervasyonun plan türüne göre sürümlenmesi; hot/full doğrulama, reset önizleme parmak izi ve yedek izin listesi girer. HTTP/producer/koordinatör, public API/CLI girmez. DDL/migration yoktur.

## Bağımlılıklar ve kararlar

P02-3f tipleri ve [ADR-0031](../../decisions/0031-upload-continuation.md) onayı gerekir. Eski binary uyumu [ADR-0031](../../decisions/0031-upload-continuation.md)#6 gereği kontrollü `state_invalid` retidir; DDL değişikliği gerekirse koddan önce kullanıcı kararı alınır.

## Sözleşme ve uygulama sınırı

Mevcut ortak primitive’ler (clock, SQL transaction, lease/fence/CAS, kota) yeniden kullanılır; v1/v2 yolları davranışsal olarak aynı kalır. Create/link intent’i v3 operation’da hiçbir koşulda oluşmaz; presign öncülsüzdür; PUT/confirm öncülleri v2’deki gibidir. Başarı: seçilen M dosyanın tam 3M accepted makbuzu, N dosyalık ordered metadata kanıtı ve kök operation’ın CreateReceiptV2 baseline eşliği. `operation_reservation` plan türüne göre sürümlüdür; mevcut satırların doğrulaması değişmez.

## Kabul

1. Gerçek SQLite ile her geçiş ve ret: draft/expired/revoked, ack kuralları, kaynak donmamış (etkin lease) → `operation_conflict`, aynı dataset’te başka non-terminal operation, kaynak terminal (succeeded/failed/cancelled), journal’da rejected makbuz, baseline yok; iki süreç eşzamanlı admit → tam bir kazanan.
2. Arm create/link ve `file_indices` dışı indeksi reddeder; presign öncülsüz; PUT/confirm sırası, kronoloji ve tazelik v2 kuralıyla aynı; başarı eksik/fazla makbuz, eksik baseline veya N-dosya proof uyuşmazlığında yazılmaz (unknown).
3. Kota: continuation plan/operation 128/128, dosya 4.096, 16 MiB sınırlarına yeniden sayılır; rezervasyon 3M için doğru; v1/v2 satırları yeniden doğrulanır.
4. Reset önizleme/uygulama, yedek (continuation tabloları allowlist’te), restore/recover yasağı, global expiry frontier ve hot/full doğrulama v3’ü kapsar.
5. Eski-binary benzeri decode, v3 satırını mutasyon olmadan `state_invalid` reddeder; v1/v2 geçmişi ve golden’ları değişmez.
6. Gerçek SIGKILL: admission, arm ve makbuz commit sınırlarında v3 geçmişi okunabilir kalır ve ikinci etki yoktur.

## Doğrulama

Gerçek SQLite/süreç/fork testleri, mevcut kota ve migration/maintenance regresyonları, Ruff, strict mypy. Ağ ve public yüzey iddiası yoktur.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
