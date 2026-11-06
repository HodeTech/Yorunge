---
id: P02-3p
phase: P02
status: draft
size: M
depends_on: [P02-0d]
capabilities: [C04]
---
# P02-3p — Veri sürümü tipleri, strict codec ve salt okuma okuyucusu

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 13. [ADR-0033](../../decisions/0033-dataset-version-references.md); durum değiştirmeyen okuma.

## Kullanıcı sonucu ve mevcut eksik

Uzak veri sürümü, bölme sayıları ve bir sürüme değişmez referans bugün tipli olarak yoktur; eğitim planı (P03-1) sürüm bağına dayanacaktır.

## Giren ve girmeyen kapsam

`DatasetVersionObservation v1`, `DatasetVersionBinding v1`, bölme sayıları, sınıf-etiketi özeti, canonical kodlama/digest; sürüm listesi/detay/bölme için strict Platform codec’leri ve bütçeli salt okuma okuyucusu; sapma karşılaştırması (`unchanged|changed|missing|unavailable`); yeni hata kodları girer. API/CLI, dosya yayını ve sürüm oluşturma girmez.

## Bağımlılıklar ve kararlar

Platform bağlamı P02-0d’dedir; [ADR-0033](../../decisions/0033-dataset-version-references.md) onayı gerekir. Teknik olarak P02-3a/b’ye bağlı değildir; plan sırası gereği sonra yapılır.

## Sözleşme ve uygulama sınırı

[sürüm referansı sözleşmesi](../../reference/dataset-versions.md) taslağındaki alanlar burada kesinleşir. Hepsi strict/frozen/extra-forbid, bool≠int, kimlikler canonical UUID, zaman canonical UTC. `created_by`, `description`, URL alanları atılır ve çıktıya girmez. Okuyucu ADR-0017 salt okuma politikasıyla (en çok iki attempt), 1 MiB yanıt, 5 sayfa ve 30 s bütçesiyle çalışır; yalnız `page` gönderilir ve `meta.page` doğrulanır.

## Kabul

1. Binding için bağımsız elle hesaplanmış canonical byte/SHA-256 golden’ı; aynı sürüm aynı digest’i verir, `observed_at` digest’e girmez, etiket/kimlik/sayı/sınıf özeti değişimi digest’i değiştirir.
2. Codec negatifleri: eksik/yanlış tip alan, bool-as-int, kopya anahtar, 2xx mantıksal hata, detay↔splits uyuşmazlığı, `item_count`≠bölme toplamı, `is_frozen=false` (bağ reddi), yanlış dataset/etiket, literal-secret.
3. Sayfalama: `meta.page` uyuşmazlığı, tekrarlı ID, döngü, >5 sayfa, `total` çelişkisi; tamlık iddiası yoktur.
4. 404 `missing`/`dataset_version_not_found`, 401/403/429/5xx/timeout kodları; etiket karakter kümesi ve yol kaçışı.
5. Gerçek loopback TLS okuyucu testleri; created_by/description canary’leri hiçbir çıktıda yoktur.

## Doğrulama

Contract/unit/integration testleri, Ruff, strict mypy. Gerçek hesap salt okuma kabulü üst kartta ve ayrı yetkiyle.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
