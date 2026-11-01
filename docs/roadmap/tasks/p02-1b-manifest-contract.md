---
id: P02-1b
phase: P02
status: draft
size: M
depends_on: [P01-1a]
capabilities: [C03, C04, C13]
---
# P02-1b — Yerel manifest biçimi ve bağımsız bütünlük oracle’ı

**Tarih:** 2026-11-01. [Paket/adım 2](../p02-1-delivery-plan.md). ADR onayına bağlı taslak; ürün kodu yoktur.

## Kullanıcı sonucu ve mevcut eksik

Veri sorumlusu dosya adları/boyut/hash kümesini kökten bağımsız sürümlü bir dosyada saklar; bozuk veya yanıltıcı bir manifest doğrulanmış sayılmaz. Mevcut recipe’nin `data.manifest` string’i veri manifesti parser’ı değildir.

## Giren ve girmeyen kapsam

Strict/frozen Manifest v1 domain modeli, bounded strict JSON parser/encoder, canonical digest, isim/ancestor/collision kuralları ve golden test vektörleri. Tarama, dosya yayını, yeni CLI, upload veya execution desteği bu adımın sonucu değildir; aynı paketin sonraki kartlarındadır.

## Bağımlılıklar ve kararlar

P01-1a [PR #4](https://github.com/HodeTech/Yorunge/pull/4) ile verified. [ADR-0023](../../decisions/0023-local-dataset-manifests.md) Proposed ve kullanıcı onayı zorunludur; Accepted olmadan ready/kod geçişi yapılmaz. Kapanmış P01 wire/digest biçimleri değişmez.

## Sözleşme ve uygulama sınırı

Tek kaynak [dataset-manifest](../../reference/dataset-manifest.md); modeller domain’de, JSON/file I/O dış katmanda. Parse/model hatası public API’de güvenli `manifest_invalid` olur; raw input/ValidationError/path taşınmaz. Canonical JSON ve bağımsız vektörler üretici algoritmasına karşı sabittir. Lazy import ile help/context yolları yeni feature modelini yüklemez.

## Kabul

1. Elle seçilmiş boş/normal/Unicode dosya byte’ları için bağımsız SHA-256, canonical manifest byte ve digest beklenir; farklı girdi sırası veya root digest’i değiştirmez. Root, inode ve saat manifestte bulunmaz.
2. Hardlink/same-hash farklı adlar ayrı kayıt/sayı olarak temsil edilir. Path sıralı/tekrarsızdır; boyut/adet toplamları tamdır. Boş ağaç/dosya kabul edilir; boş dizinler içerik kimliğinde yoktur.
3. Extra/missing/duplicate key, sürüm bool/float/unknown, yanlış field tipi, malformed/nonfinite/UTF-8/depth/node/byte sınırı, yanlış hash/aggregate/digest/sıra reddedilir. Her raises yalnız tek hedef çağrıyı kapsar; fixture kurulumu dışında yapılır.
4. Traversal, mutlak yol, separator/control/surrogate, sınır üstü UTF-8 ad/path/depth; `A/x`–`a/y`, Unicode canonical/case ve dosya-ancestor çakışmaları reddedilir. Geçerli orijinal Unicode adlar değiştirilmez. Linux/macOS ve Python Unicode sürüm sınırı açık kalır.
5. Her sayısal tavan sınır−1/sınır/sınır+1 ile doğrulanır; dosya listesi/JSON boyutu için sınırsız allocation iddiası veya sessiz kırpma yoktur. Bütün eski model/plan parser sözleşmeleri korunur.

## Doğrulama

Domain/parser contract, golden byte/digest vektörleri, lazy-import/core boundary, format/lint ve strict mypy; belge/ajan kontrolü. Gerçek dosya/root/atomic çıktı sonraki kartın kabulüdür. Commit ardından iki fresh çok boyutlu tur; gerçek sonuç [kayıtta](../../research/p02-1-implementation-validation.md).

## Teslim kaydı

Henüz uygulanmadı veya doğrulanmadı. ADR-0023 onayı bekleniyor.
