---
id: P02-2m
phase: P02
status: in_progress
size: M
depends_on: [P02-2l, P02-2f]
capabilities: [C03, C12, C13]
---
# P02-2m — Platform proxy upload codec'leri

**Tarih:** 2026-11-02. b üst kartının ilk gerçek provider codec birimi; aynı branch ve tek nihai P02-2 PR'ı.

## Kullanıcı sonucu ve mevcut eksik

Her dosyanın presign/PUT/confirm sonucu ad, boyut ve hash kimliğini korur. Mevcut storage portu gerçek provider descriptor veya confirm/items gövdesini henüz tüketmez.

## Giren ve girmeyen kapsam

Tek dosya request/descriptor codec'i, authenticated proxy exact target, ephemeral provider key ve bağımsız yerel file binding, unique descriptor seti, PUT/confirm acknowledgement ve bounded item projection girer. Ağ/koordinatör/public CLI, yeni authority/fiyat, direct provider wire ve live kabul girmez.

## Bağımlılıklar ve kararlar

L ve f verified; Accepted ADR-0025/0026 sınırı korunur. [Platform tüketici referansı](../../reference/platform-upload-consumer.md#proxy-upload-codec-sınırı) exact oracle'dır. Generic direct port hazır olsa da gerçek provider direct şeması kapanmadan seçilemez; kullanıcı seçimi proxy'ye çevrilmez.

## Sözleşme ve uygulama sınırı

Application codec, private ephemeral descriptor/StorageTarget ve closed item modelleri; signed URL serialize edilmez. Ham provider key kalıcılaştırılmaz; mevcut private receipt slotu yeni producer'da bağımsız yerel UUID file binding taşır. Provider key non-authorizing kanıtı kapanmış sayılmaz. Fixture grant veya SDK backend'i yoktur.

## Kabul

Filename/hash/UID/size/cardinality, duplicate/shared key, exact proxy path/query ve kısa/uzun literal; raw metadata/JSON/URL/MIME/header/handle sınırları. Same-hash farklı ad ayrı descriptor; strict created/actual_count/batch_duplicates ve nullable metadata SHA. Boyut/boolean/duplicate/cursor/path/type negatifleri. Saf decoder/request modeli doğru input olmadan etki başlatamaz.

## Doğrulama

Bağımsız contract negatifleri, Ruff/mypy/doc/rehber/diff; commit ve fresh R1/fix + farklı fresh R2/fix. Gerçek HTTP/server byte oracle, native/kurulum/live c'dedir; bu kartta hesap çağrısı yoktur.

## Teslim kaydı

L verified; wire hazırlık incelemesinde raw-key kalıcılık kanıtı eksikliği doğrulandı. ADR-0025 mevcut file-binding seçeneğiyle raw key tamamen ephemeral tutulacak; kod başlamadan referans düzeltildi. Uygulama başladı; in_progress, kabul/review henüz yok.
