# Veri sürümü ve bölme referansı

**Durum:** Taslak sözleşme — [ADR-0033](../decisions/0033-dataset-version-references.md) Proposed; uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Aşağıdaki komut ve DTO adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek veya sağlayıcı garantisi değildir. Sürüm oluşturma/freeze bu sözleşmenin dışındadır ([P02-R4](../roadmap/tasks/p02-r4-dataset-version-creation.md)). Bu belge sürüm hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

## Planlanan yüzey

```text
yorunge datasets versions list  --dataset-id UUID [--page N] [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets versions show  --dataset-id UUID --version-tag TAG [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets versions bind  --dataset-id UUID --version-tag TAG --binding-out FILE [--manifest FILE] [...bağlam]
yorunge datasets versions check --binding FILE [...bağlam]
```

Python karşılıkları aynı kullanım senaryolarına bağlı dört API’dir. Hepsi Platform hizmetine bağlı, salt okunur ve tek credential snapshot’ıyla çalışır; yazma, onay veya operation kaydı üretmez. `--manifest` yalnız yerel Manifest v1 dosyasını okur. Dataset kimliği açıkça verilir; ilk dataset otomatik seçilmez. Genel `--output text|json|ndjson` yalnız çıktı biçimidir; hedef dosya `--binding-out`tur.

## Tüketilen sağlayıcı yüzeyi

Hepsi `GET`’tir ve ADR-0017 salt okuma politikasına (en çok iki attempt, tek deadline) tabidir. Tanınmayan sorgu parametresi sağlayıcıda sessizce yok sayıldığından `meta.page` gönderilen sayfayla eşleşmezse sonuç ret edilir; yalnız `page` gönderilir, `page_size` gönderilmez.

| Çağrı | Tüketilen alanlar |
|---|---|
| `datasets/{id}/versions?page=N` | Çağrı başına tek sayfa: `data[]` (≤20), `meta.{page,page_size,total,has_next}`; her kayıt `id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_config.{train,val,test,unassigned}`, `annotated_item_count`, `total_annotation_count`, `created_at` |
| `datasets/{id}/versions/{tag}` | Yukarıdakilere ek `dataset_id`, `class_labels_snapshot[]` (`id`, `name`, `sort_order`, `annotation_count`); `description`, `created_by`, `export_zip_url`, renk/kısayol alanları atılır |
| `datasets/{id}/versions/{tag}/splits` | `data.{train,val,test,unassigned}` |

Yanıt zarfı `success=true` ve `data` ister; mantıksal başarısızlık, eksik/yanlış tipli alan, bool≠int, kopya anahtar, 1 MiB aşımı, literal-secret eşleşmesi ve dataset/etiket uyuşmazlığı `invalid_response` olur. Tanınmayan ek alanlar yapısal ve sır denetiminden sonra atılır. `version_tag` kapalı `[A-Za-z0-9._-]{1,128}` kümesindedir (`.` ve `..` hariç) ve tek yol bileşenidir. `list` yalnız istenen sayfayı gösterir (`--page` varsayılan 1, `has_next` ve toplam görünür); kopyalanan sürüm kimliği veya `meta.total` çelişkisi sonucu tamamlanmış diye sunmaz.

## Gözlem, bağ ve digest

`DatasetVersionObservation v1` (`show`/`list` öğesi) alanları: `schema_version=1`, `kind=dataset_version_observation`, `dataset_id`, `version_id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_counts{train,val,test,unassigned}`, `split_total_matches_item_count`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`, `created_at`, `observed_at`. Hepsi strict/frozen/extra-forbid, zorunlu (nullable yok), sayılar `bool` olmayan nonnegative int64; kimlikler canonical UUID; zaman canonical altı haneli UTC. `list` öğeleri sınıf-etiketi bilgisini taşımayan listeden geldiğinden `class_count`/`class_labels_sha256` yalnız `show`/`bind`/`check` gözleminde bulunur.

`class_labels_sha256`: `class_labels_snapshot` öğelerinin `{annotation_count,id,name,sort_order}` nesneleri `id`’ye göre sıralanıp Manifest v1 ile aynı kanonik kodlayıcının UTF-8 baytlarının SHA-256’sıdır; renk/kısayol dışarıdadır.

`DatasetVersionBinding v1` alanları: `schema_version=1`, `policy_version=1`, `kind=dataset_version_binding`, `service` (`origin`, `api_base_path`), `dataset_id`, `version_id`, `version_tag`, `created_at`, `is_frozen=true`, `is_partial`, `item_count`, `split_counts`, `split_total_matches_item_count`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`, nullable `local_manifest` (`digest`, `file_count`, `relation=count_matches|count_differs`), `observed_at`, `digest`. Digest, `digest` ve `observed_at` hariç bütün alanların Manifest v1 kodlayıcısıyla (UTF-8, `sort_keys`, ayraçsız, `allow_nan=False`) SHA-256’sıdır; artifact dosyası aynı kodlamayı digest ve `observed_at` dahil üretir ve tek LF ile biter. Aynı sağlayıcı durumunu **aynı `--manifest` seçimiyle** yeniden bağlamak aynı digest’i verir (`local_manifest` digest’in parçasıdır). Detay `split_config` ile `splits` rotası aynı dört sayıyı vermelidir; aksi `invalid_response`dur. `item_count`≠dört sayının toplamı bağı engellemez: `split_total_matches_item_count=false` kaydedilir ve text çıktıda uyarı olarak görünür.

## Karşılaştırma ve hata sınıfları

`check` bağdaki değişmez alanları yeniden gözlenenle alan alan karşılaştırır (`observed_at` ve manifest ilişkisi hariç). Sonuçlar:

| Sonuç | Anlam | Çıkış |
|---|---|---|
| `unchanged` | Değişmez alanlar eşit | 0 |
| `changed` | Bir veya daha fazla alan farklı; kapalı ayrıntı `changed_field_count` ve sıralı `changed_fields` | 7 `dataset_version_changed` |
| `missing` | Etiket bulunamadı (404); içerik değişimi sayılmaz | 7 `dataset_version_missing` |
| `unavailable` | 401/403/429/5xx/zaman aşımı/taşıma | mevcut `remote_*`/`transport_*` kodları |

`changed_fields` kapalı kümesi: `service`, `version_id`, `version_tag`, `created_at`, `is_partial`, `item_count`, `split_counts`, `split_total_matches_item_count`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`. Bağlı alanların bir kısmı (`is_partial`, annotation sayıları) sağlayıcıda dondurulmuş sürümde bile oynayabilir; `check` bunları değişim diye bildirir ve üyelik değişmemiş olabilir.

| Kod | Exit | Tetik |
|---|---:|---|
| `dataset_version_not_found` | 2 | `show`/`bind` etiketi yok |
| `dataset_version_not_frozen` | 2 | Sürüm `is_frozen=false`; bağ üretilmez |
| `dataset_version_changed` | 7 | `check` değişmez alan farkı (kapalı ayrıntı) |
| `dataset_version_missing` | 7 | `check` etiket bulunamadı |
| `binding_invalid` | 2 | Yerel dosya katı ayrıştırma/digest doğrulamasını geçmiyor |
| `binding_output_exists` | 2 | Hedef var veya yarışta oluştu; dokunulmaz |
| `binding_write_failed` | 2 | Yayın öncesi yazma/sync hatası |
| `binding_write_uncertain` | 5 | Link çağrısı başladıktan sonra sonuç kesinleşmedi |

Başarılı `check` yalnız sağlayıcı metadata’sının değişmediğini söyler; byte eşliği, üyelik veya model uygunluğu söylemez.

## Dosya yayını ve kabul sınırı

`bind --binding-out` hedefi [P02-3l](../roadmap/tasks/p02-3l-download-sink-publisher.md)’in ortak no-clobber yayın ilkesiyle yayımlanır: parent mevcut ve no-follow, 0600, O_EXCL stage ve exclusive hardlink; mevcut hedef ezilmez. Artifact sır, ham gövde, `created_by`, `description` veya URL taşımaz. Kabul listesi [ADR-0033](../decisions/0033-dataset-version-references.md#sonuçlar-ve-kabul)’tedir; çevrimdışı fixture yeşili canlı destek sayılmaz.
