# Veri sürümü ve bölme referansı

**Durum:** Taslak sözleşme — [ADR-0033](../decisions/0033-dataset-version-references.md) Accepted (2026-11-06); uygulama ve canlı kabul yok. **Tarih:** 2026-11-06. Aşağıdaki komut ve DTO adları onay sonrası uygulama kartlarında kesinleşir; bu belge çalışan örnek veya sağlayıcı garantisi değildir. Sürüm oluşturma/freeze bu sözleşmenin dışındadır ([P02-R4](../roadmap/tasks/p02-r4-dataset-version-creation.md)). Bu belge sürüm hata kodlarının **kanonik** tablosudur; [CLI sözleşmesi](cli-contract.md) buraya bağlanır, kopyasını tutmaz.

## Planlanan yüzey

```text
yorunge datasets versions list  --dataset-id UUID [--page N] [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets versions show  --dataset-id UUID --version-tag TAG [--config FILE] [--profile NAME] [--state-dir PATH]
yorunge datasets versions bind  --dataset-id UUID --version-tag TAG --binding-out FILE [--manifest FILE] [...bağlam]
yorunge datasets versions check --binding FILE [...bağlam]
```

Python karşılıkları aynı kullanım senaryolarına bağlı dört API’dir. Hepsi Platform hizmetine bağlı, salt okunur ve tek credential snapshot’ıyla çalışır; yazma, onay veya operation kaydı üretmez. `--manifest` yalnız yerel Manifest v1 dosyasını okur. Dataset kimliği açıkça verilir; ilk dataset otomatik seçilmez. Genel `--output text|json|ndjson` yalnız çıktı biçimidir; hedef dosya `--binding-out`tur. `--page` 1–10 000 kesin tamsayıdır.

## Tüketilen sağlayıcı yüzeyi

Hepsi `GET`’tir ve ADR-0017 salt okuma politikasına (en çok iki attempt, tek deadline) tabidir. Detay ve bölme okumaları **atomik bir anlık görüntü değildir** (aşağıda). Tanınmayan sorgu parametresi sağlayıcıda sessizce yok sayıldığından (4 Kasım 2026 tek hesap gözlemi; garanti değildir) `meta.page` gönderilen sayfayla eşleşmezse sonuç ret edilir; yalnız `page` gönderilir, `page_size` gönderilmez.

| Çağrı | Tüketilen alanlar |
|---|---|
| `datasets/{id}/versions?page=N` | Çağrı başına tek sayfa: `data[]` (1 MiB yanıt ve en çok 100 kayıt), `meta.{page,page_size,total,has_next}`; her kayıt `id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_config.{train,val,test,unassigned}`, `annotated_item_count`, `total_annotation_count`, `created_at` |
| `datasets/{id}/versions/{tag}` | Yukarıdakilere ek `dataset_id`, `class_labels_snapshot[]` (`id`, `name`, `sort_order`, `annotation_count`); `description`, `created_by`, `export_zip_url`, renk/kısayol alanları atılır |
| `datasets/{id}/versions/{tag}/splits` | `data.{train,val,test,unassigned}` |

Yanıt zarfı `success=true` ve `data` ister; mantıksal başarısızlık, eksik/yanlış tipli alan, bool≠int, kopya anahtar, 1 MiB aşımı, literal-secret eşleşmesi ve dataset/etiket uyuşmazlığı `invalid_response` olur. Tanınmayan ek alanlar yapısal ve sır denetiminden sonra atılır. `version_tag` kapalı `[A-Za-z0-9._-]{1,128}` kümesindedir (`.` ve `..` hariç) ve tek yol bileşenidir. `list` yalnız istenen sayfayı gösterir (`--page` varsayılan 1, `has_next` ve toplam görünür); kopyalanan sürüm kimliği veya `meta.total` çelişkisi sonucu tamamlanmış diye sunmaz.

## Gözlem, bağ ve digest

`DatasetVersionObservation v1` (`show`/`list` öğesi) alanları: `schema_version=1`, `kind=dataset_version_observation`, `dataset_id`, `version_id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_counts{train,val,test,unassigned}`, `split_total_matches_item_count`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`, `created_at`, `observed_at`. Hepsi strict/frozen/extra-forbid, zorunlu (nullable yok), sayılar `bool` olmayan nonnegative int64; kimlikler canonical UUID; zaman canonical altı haneli UTC. `list` sınıf-etiketi bilgisini taşımayan listeden geldiğinden ayrı bir `DatasetVersionListItem v1` (aynı alanlardan `class_count` ve `class_labels_sha256` hariç) döndürür; `show`/`bind`/`check` tam gözlemi kullanır. Sınıf adları hiçbir çıktıya girmez, yalnız hash’lenir.

`class_labels_sha256`: `class_labels_snapshot` öğelerinin `{annotation_count,id,name,sort_order}` nesneleri `id`’ye göre sıralanıp Manifest v1 ile aynı kanonik kodlayıcının UTF-8 baytlarının SHA-256’sıdır; renk/kısayol dışarıdadır. `id` sağlayıcı JSON’undaki türüyle (tam sayı veya dize) olduğu gibi kodlanır ve sıralanır; bir sürümde türler karışıksa veya `id` tekrarlanıyorsa sonuç `invalid_response`dur (sıralama belirsizliği digest’i bağımsız uygulamalarda farklılaştırırdı).

`DatasetVersionBinding v1` alanları: `schema_version=1`, `policy_version=1`, `kind=dataset_version_binding`, `service` (`origin`, `api_base_path`), `dataset_id`, `version_id`, `version_tag`, `created_at`, `is_frozen=true`, `is_partial`, `item_count`, `split_counts`, `split_total_matches_item_count`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`, nullable `local_manifest` (`digest`, `file_count`, `relation=count_matches|count_differs`), `observed_at`, `digest`. Digest, `digest` ve `observed_at` hariç bütün alanların Manifest v1 kodlayıcısıyla (UTF-8, `sort_keys`, ayraçsız, `allow_nan=False`) SHA-256’sıdır; artifact dosyası aynı kodlamayı digest ve `observed_at` dahil üretir ve tek LF ile biter. Aynı sağlayıcı durumunu **aynı `--manifest` seçimiyle** yeniden bağlamak aynı digest’i verir (`local_manifest` digest’in parçasıdır). Digest kendi kendine hash’tir (imza değildir): kazara bozulmayı yakalar, kurcalamayı değil; tüketici (P03-1) referansı kullanmadan önce `check` etmelidir. `is_export_ready` gözlemde görünür ama bağa girmez: export hazırlığıyla değişen, sürümün içeriğini tanımlamayan bir bayraktır ve bağlansaydı `check` gereksiz `changed` verirdi. Detay `split_config` ile `splits` rotası aynı dört sayıyı vermelidir; aksi `invalid_response`dur. `is_partial=true` sürüm de bağlanır (anlamı bilinmiyor): alan kaydedilir ve tüketici (P03-1) isterse reddeder; Yörünge anlamını bilmediği bir bayrağı kendi başına engel saymaz. `item_count`≠dört sayının toplamı bağı engellemez: `split_total_matches_item_count=false` kaydedilir ve text çıktıda uyarı olarak görünür.

## Karşılaştırma ve hata sınıfları

`check` önce bağdaki `service` hedefini etkin profilin hedefiyle karşılaştırır; eşleşmiyorsa alan karşılaştırması yapmadan `state_changed`/2 verir. Sonra bağdaki değişmez alanları yeniden gözlenenle alan alan karşılaştırır (`observed_at` ve manifest ilişkisi hariç). **Yalnız `unchanged` başarıdır** ve exit 0 ile `DatasetVersionCheck v1` döndürür (`schema_version=1`, `kind=dataset_version_check`, `result="unchanged"`, `dataset_id`, `version_id`, `version_tag`, `binding_digest`, `observed_at`); diğer sonuçlar hata zarfıdır (JSON/NDJSON’da `status=error`, kod ve kapalı ayrıntı):

| Sonuç | Zarf | Çıkış |
|---|---|---|
| `unchanged` | `DatasetVersionCheck v1` (başarı) | 0 |
| `changed` | Hata `dataset_version_changed`; kapalı ayrıntı `changed_field_count`, sıralı `changed_fields`, `annotation_only` | 7 |
| `missing` | Hata `dataset_version_missing`; **yalnız sürüm detay rotasındaki 404**. İçerik değişimi sayılmaz; exit 7 bilinçli: referans geçerliliğini yitirdi | 7 |
| `unavailable` | Mevcut `remote_*`/`transport_*` kodları: 401/403/429/5xx/zaman aşımı/taşıma; ayrıca detay başarılıyken bölme rotasında 404 (`remote_failed`: sürüm bulundu ama bölme sayımı okunamadı; `missing` değildir) | mevcut |
| hedef uyuşmazlığı | Hata `state_changed` | 2 |

`changed_fields` kapalı kümesi — kimlik/üyelik alanları: `version_id`, `version_tag`, `created_at`, `is_frozen`, `item_count`, `split_counts`, `split_total_matches_item_count`; açıklama alanları: `is_partial`, `annotated_item_count`, `total_annotation_count`, `class_count`, `class_labels_sha256`. `annotation_only=true` değişen bütün alanların açıklama alanları olduğunu söyler. `service` farkı bu kümede değildir (`state_changed`/2). Sonradan çözülmüş (`is_frozen=false`) bir sürüm `unchanged` olamaz: `changed` olur ve `is_frozen` ayrıntıda görünür. **Bilinçli seçim:** açıklama alanları dahil her fark exit 7’dir (referans yeniden üretilebilir eğitim için kullanılacağından yanlış güvence yanlış alarmdan daha pahalıdır); bu alanlar sağlayıcıda dondurulmuş sürümde bile oynayabilir (anlamları bilinmiyor) ve üyelik değişmemiş olabilir, `annotation_only` tüketiciye ayrımı yapma imkânı verir ve gevşetme, canlı gözlem bu alanların gerçekten oynadığını gösterirse ayrı bir ADR kararıdır.

Detay ve bölme okumaları **atomik bir anlık görüntü değildir**: iki okuma arasında sağlayıcı durumu değişirse detay↔bölme çelişkisi `invalid_response` olarak görünebilir (kullanıcı yeniden dener); başarılı `bind`/`check` iki okumanın tutarlı olduğunu söyler, aynı anda okunduğunu söylemez.

| Kod | Exit | Tetik |
|---|---:|---|
| `dataset_version_not_found` | 2 | `show`/`bind` etiketi yok (detay rotası 404) |
| `dataset_version_not_frozen` | 2 | Sürüm `is_frozen=false`; bağ üretilmez |
| `dataset_version_changed` | 7 | `check` değişmez alan farkı; `ManifestMismatch` emsali kapalı ayrıntı tipi (`YorungeError` alt sınıfı; düz `YorungeError("dataset_version_changed")` `details={}` korur) |
| `dataset_version_missing` | 7 | `check`: sürüm detay rotası 404 |
| `state_changed` | 2 | `check`: bağdaki `service` hedefi etkin profille eşleşmiyor (mevcut kod) |
| `binding_invalid` | 2 | Yerel dosya katı ayrıştırma/digest doğrulamasını geçmiyor |
| `binding_output_exists` | 2 | Hedef var veya yarışta oluştu; dokunulmaz |
| `binding_write_failed` | 2 | Yayın öncesi yazma/sync hatası |
| `binding_write_uncertain` | 5 | Link çağrısı başladıktan sonra sonuç kesinleşmedi |

Başarılı `check` yalnız sağlayıcı metadata’sının değişmediğini söyler; byte eşliği, üyelik veya model uygunluğu söylemez.

## Dosya yayını ve kabul sınırı

`bind --binding-out` hedefi [P02-3s](../roadmap/tasks/p02-3s-common-artifact-publisher.md)’in ortak no-clobber artifact yayıncısıyla (rastgele adlı stage) yayımlanır: parent mevcut ve no-follow, 0600, O_EXCL stage ve exclusive hardlink; mevcut hedef ezilmez. Artifact sır, ham gövde, `created_by`, `description` veya URL taşımaz. Kabul listesi [ADR-0033](../decisions/0033-dataset-version-references.md#sonuçlar-ve-kabul)’tedir; çevrimdışı fixture yeşili canlı destek sayılmaz.
