---
id: P02-3p
phase: P02
status: draft
size: M
depends_on: [P02-0d]
capabilities: [C04]
---
# P02-3p — Veri sürümü tipleri, strict codec ve salt okuma okuyucusu

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 15. [ADR-0033](../../decisions/0033-dataset-version-references.md); durum değiştirmeyen okuma.

## Kullanıcı sonucu ve mevcut eksik

Uzak veri sürümü, bölme sayıları ve bir sürüme değişmez referans bugün tipli olarak yoktur; eğitim planı (P03-1) sürüm bağına dayanacaktır.

## Giren ve girmeyen kapsam

`DatasetVersionObservation v1`, `DatasetVersionListItem v1` (sınıf-etiketi alanları olmadan), `DatasetVersionBinding v1`, bölme sayıları, `split_total_matches_item_count`, sınıf-etiketi özeti, Manifest v1 kodlayıcısıyla canonical kodlama/digest; sürüm listesi (tek sayfa)/detay/bölme için strict Platform codec’leri ve bütçeli salt okuma okuyucusu; sapma karşılaştırması (`unchanged|changed|missing|unavailable`, kapalı `changed_fields` ayrıntısı; `YorungeError` alt sınıfı kapalı ayrıntı tipi, düz kod `details={}` korur); bağdaki `service` hedefi etkin profille eşleşmiyorsa `state_changed`/2; yeni hata kodları (`dataset_version_not_found`, `dataset_version_not_frozen`, `dataset_version_changed`, `dataset_version_missing`, `binding_*`) girer. API/CLI, dosya yayını ve sürüm oluşturma girmez.

## Bağımlılıklar ve kararlar

Platform bağlamı P02-0d’dedir; [ADR-0033](../../decisions/0033-dataset-version-references.md)’ün Accepted olması gerekir (bugün Proposed). Teknik olarak P02-3a/b’ye bağlı değildir; plan sırası gereği sonra yapılır.

## Sözleşme ve uygulama sınırı

[sürüm referansı sözleşmesi](../../reference/dataset-versions.md) taslağındaki alanlar burada kesinleşir. Hepsi strict/frozen/extra-forbid, bool≠int, kimlikler canonical UUID, zaman canonical UTC. `created_by`, `description`, `export_zip_url` ve URL alanları atılır ve çıktıya girmez. Okuyucu ADR-0017 salt okuma politikasıyla (en çok iki attempt), 1 MiB yanıt (ve en çok 100 kayıt) ve 30 s bütçesiyle çalışır; `list` çağrı başına tek sayfa, yalnız `page` (1–10 000) gönderilir ve `meta.page` doğrulanır. Sınıf adları hiçbir çıktıya girmez, yalnız hash’lenir. Hata kodlarının kanonik tablosu [sürüm referansı sözleşmesi](../../reference/dataset-versions.md) belgesindedir.

## Kabul

1. Binding için bağımsız elle hesaplanmış canonical byte/SHA-256 golden’ı; aynı sürüm ve aynı `--manifest` seçimi aynı digest’i verir, `observed_at` digest’e girmez, etiket/kimlik/sayı/sınıf özeti değişimi digest’i değiştirir.
2. Codec negatifleri: eksik/yanlış tip alan, bool-as-int, kopya anahtar, 2xx mantıksal hata, detay↔splits uyuşmazlığı, `is_frozen=false` (bağ reddi), yanlış dataset/etiket, literal-secret, karışık türlü veya yinelenen sınıf `id` (`invalid_response`); `is_partial=true` sürüm bağlanır ve alan kaydedilir. `item_count`≠bölme toplamı bağı engellemez ve `split_total_matches_item_count=false` kaydedilir.
3. Sayfalama: `meta.page` uyuşmazlığı, tekrarlı ID, `total` çelişkisi; tamlık iddiası ve çok sayfalı toplama yoktur.
4. 404 → `dataset_version_not_found` (`show`/`bind`) ve `dataset_version_missing` (`check`), 401/403/429/5xx/timeout kodları; etiket karakter kümesi (`.` ve `..` hariç) ve yol kaçışı.
5. `DatasetVersionChanged` bir `YorungeError` alt sınıfıdır ve kapalı ayrıntı taşır; düz `YorungeError("dataset_version_changed")` `details={}` korur (mevcut zarf testi yeşil kalır). `changed_fields` ayrımı: `version_id` (etiket yeniden oluşturulmuş), `is_frozen` (bağlı sürüm sonradan çözülmüş: `unchanged` değil `changed`) ve `annotated_item_count` (açıklamalar oynamış) ayrı alanlarla bildirilir; `service` bu kümede yoktur (hedef uyuşmazlığı `state_changed`/2).
6. Gerçek loopback TLS okuyucu testleri; created_by/description/URL canary’leri hiçbir çıktıda yoktur.

## Doğrulama

Contract/unit/integration testleri, Ruff, strict mypy. Gerçek hesap salt okuma kabulü üst kartta ve ayrı yetkiyle.

## Teslim kaydı

Draft; uygulama, commit veya review kanıtı yoktur.
