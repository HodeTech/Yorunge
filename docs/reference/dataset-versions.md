# Veri sürümü ve bölme referansı

**Durum:** Taslak sözleşme — [ADR-0033](../decisions/0033-dataset-version-references.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Aşağıdaki komut ve DTO adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek veya sağlayıcı garantisi değildir. Sürüm oluşturma/freeze bu sözleşmenin dışındadır ([P02-R4](../roadmap/tasks/p02-r4-dataset-version-creation.md)).

## Planlanan yüzey

```text
yorunge datasets versions list  --dataset-id UUID [--page N] [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets versions show  --dataset-id UUID --version-tag TAG [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets versions bind  --dataset-id UUID --version-tag TAG --binding-out FILE [--manifest FILE] [...bağlam]
yorunge datasets versions check --binding FILE [...bağlam]
```

Python karşılıkları aynı kullanım senaryolarına bağlı dört API’dir. Hepsi Platform hizmetine bağlı, salt okunur ve tek credential snapshot’ıyla çalışır; yazma, onay veya operation kaydı üretmez. `--manifest` yalnız yerel Manifest v1 dosyasını okur. Dataset kimliği açıkça verilir; ilk dataset otomatik seçilmez.

## Tüketilen sağlayıcı yüzeyi

Hepsi `GET`’tir ve ADR-0017 salt okuma politikasına (en çok iki attempt, tek deadline) tabidir. Tanınmayan sorgu parametresi sağlayıcıda sessizce yok sayıldığından `meta.page` gönderilen sayfayla eşleşmezse sonuç ret edilir; yalnız `page` gönderilir, `page_size` gönderilmez.

| Çağrı | Tüketilen alanlar |
|---|---|
| `datasets/{id}/versions?page=N` | `data[]` (≤20), `meta.{page,page_size,total,has_next}`; her kayıt `id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_config.{train,val,test,unassigned}`, `annotated_item_count`, `total_annotation_count`, `created_at` |
| `datasets/{id}/versions/{tag}` | Yukarıdakilere ek `dataset_id`, `class_labels_snapshot[]` (`id`, `name`, `sort_order`, `annotation_count`); `description`, `created_by`, `export_zip_url`, renk/kısayol alanları atılır |
| `datasets/{id}/versions/{tag}/splits` | `data.{train,val,test,unassigned}` |

Yanıt zarfı `success=true` ve `data` ister; mantıksal başarısızlık, eksik/yanlış tipli alan, bool≠int, kopya anahtar, 1 MiB aşımı, literal-secret eşleşmesi ve dataset/etiket uyuşmazlığı `invalid_response` olur. Tanınmayan ek alanlar yapısal ve sır denetiminden sonra atılır. `version_tag` kapalı `[A-Za-z0-9._-]{1,128}` kümesindedir ve tek yol bileşenidir. `list` en çok 5 sayfa okur; kopyalanan sürüm kimliği, sayfa döngüsü veya `meta.total` çelişkisi sonucu tamamlanmış diye sunmaz.

## Gözlem, bağ ve digest

`DatasetVersionObservation v1` (`show`/`list` öğesi) alanları: `schema_version=1`, `kind=dataset_version_observation`, `dataset_id`, `version_id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_counts{train,val,test,unassigned}`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`, `created_at`, `observed_at`. Hepsi strict/frozen/extra-forbid, zorunlu (nullable yok), sayılar `bool` olmayan nonnegative int64; kimlikler canonical UUID; zaman canonical altı haneli UTC.

`class_labels_sha256`: `class_labels_snapshot` öğelerinin `{annotation_count,id,name,sort_order}` nesneleri `id`’ye göre sıralanıp `json.dumps(ensure_ascii=True, sort_keys=True, separators=(",",":"), allow_nan=False)` UTF-8 baytlarının SHA-256’sıdır; renk/kısayol dışarıdadır.

`DatasetVersionBinding v1` alanları: `schema_version=1`, `policy_version=1`, `kind=dataset_version_binding`, `service` (`origin`, `api_base_path`), `dataset_id`, `version_id`, `version_tag`, `created_at`, `is_frozen=true`, `is_partial`, `item_count`, `split_counts`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`, nullable `local_manifest` (`digest`, `file_count`, `relation=count_matches|count_differs`), `observed_at`, `digest`. Digest, yalnız `digest` ve `observed_at` hariç bütün alanların aynı kanonik JSON biçiminin SHA-256’sıdır; artifact dosyası aynı kodlamayı digest ve `observed_at` dahil üretir ve tek LF ile biter. Aynı sağlayıcı durumunu yeniden bağlamak aynı digest’i verir. `item_count` dört bölme sayısının toplamına eşit olmalı ve detay `split_config` ile `splits` rotası aynı olmalıdır; aksi `invalid_response`dur, bağ üretilmez.

## Karşılaştırma ve hata sınıfları

`check` bağdaki değişmez alanları yeniden gözlenenle alan alan karşılaştırır (`observed_at` ve manifest ilişkisi hariç; manifest bağlıysa yerel dosya sayısı ayrıca denetlenmez, yalnız bağdaki ilişki korunur). Sonuçlar:

| Sonuç | Anlam | Çıkış |
|---|---|---|
| `unchanged` | Değişmez alanlar eşit | 0 |
| `changed` | Bir veya daha fazla alan farklı; yalnız alan sayısı ve kapalı ad listesi döner | 7 `dataset_version_changed` |
| `missing` | Etiket bulunamadı (404) | 7 `dataset_version_changed` |
| `unavailable` | 401/403/429/5xx/zaman aşımı/taşıma | mevcut `remote_*`/`transport_*` kodları |

Yerel hata kodları (taslak): `dataset_version_not_found` (exit 2, `show`/`bind` etiketi yok), `dataset_version_not_frozen` (2), `binding_invalid` (2, yerel dosya katı ayrıştırmayı geçmiyor), `binding_output_exists` (2), `binding_write_failed` (2), `binding_write_uncertain` (5). Başarılı `check` yalnız sağlayıcı metadata’sının değişmediğini söyler; byte eşliği, üyelik veya model uygunluğu söylemez.

## Dosya yayını ve kabul sınırı

`bind --binding-out` hedefi root-dışı, parent’ı mevcut, no-follow, 0600, O_EXCL stage ve exclusive hardlink politikasıyla yayımlanır; mevcut hedef ezilmez. Artifact sır, ham gövde, `created_by`, `description` veya URL taşımaz. Kabul listesi [ADR-0033](../decisions/0033-dataset-version-references.md#sonuçlar-ve-kabul)’tedir; çevrimdışı fixture yeşili canlı destek sayılmaz.
