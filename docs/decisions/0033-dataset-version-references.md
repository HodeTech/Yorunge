# ADR-0033: Veri sürümü ve bölme sayımlarının salt okunur, değişmez referansı

**Durum:** Proposed — kullanıcı onayı bekleniyor; onaylanmadan bağımlı ürün kodu başlamaz. **Tarih:** 2026-11-06. **İş:** P02-3c. [Hazırlık incelemesi](../research/p02-3-readiness-review.md), [teslim planı](../roadmap/p02-3-delivery-plan.md), [önerilen sözleşme](../reference/dataset-versions.md). Uygulanmış sürüm desteği, sürüm oluşturma/freeze yetkisi veya eğitim planı bağı değildir.

## Bağlam

Faz satırı P02-3c’yi “veri sürümü/bölme metadata’sı ve değişmez plan bağı; gerekirse açık sürüm oluşturma/freeze kararı” olarak tanımlar; [P03-1](../roadmap/phase-03-training-and-tools.md) yönetilen eğitimi bu sürüm bağına dayandırır. Bugün Yörünge yalnız yerel Manifest v1 ve upload metadata kanıtı üretir; uzak veri sürümü, bölme sayısı ve bir eğitim planının hangi sürümü kullandığı kayıtsızdır.

Sağlayıcı gözlemi (4 Kasım 2026, tek hesap, API anahtarı; kalıcı sözleşme değildir, ham kayıtlar repoda tutulmaz): `GET datasets/{id}/versions` sayfalı liste, `GET datasets/{id}/versions/{version_tag}` tek sürüm ve `GET …/{version_tag}/splits` dört sayı döndürdü. Sürüm `version_tag` ile adreslenir (kimlikle 404); etiketi istemci seçer. Sürüm gövdesi `id`, `version_tag`, `is_frozen`, `is_partial`, `is_export_ready`, `item_count`, `split_config` (train/val/test/unassigned sayıları), `annotated_item_count`, `total_annotation_count`, `class_labels_snapshot` ve zaman alanlarını taşır; üye dosya listesi yoktur. Aynı etiketle silinmiş sürümün yeniden oluşturulması farklı `id` üretebilir. Sürüm oluşturma `POST datasets/{id}/versions` ile görünür bir sağlayıcı durum değişimidir; aynı etiket ve bazı `versions/diff` çağrıları sunucu 500’ü gözlendi. Bu bilgiler [sağlayıcı bundle’ı](https://evren.ssyz.org.tr/assets/datasetApi-DZyifXpy.js) (7.005 byte, SHA-256 `79387e65f48caa5aa9fea9e4e583e2bb781c1ff44aab32cb0ed5c1cfeda0a16b`) ve yetkili salt okuma/yazma keşfinden gelir; kaynak kodu yürütülmedi ve içerik izni, değişmezlik veya fiyat garantisi değildir.

## Karar

### 1. Yalnız salt okuma, üye listesi iddiası yok

P02-3c, sürüm listesi, tek sürüm ve bölme sayımlarını okuyan dört ortak komut/API üretir (`list`, `show`, `bind`, `check`). Hiçbiri sağlayıcıda durum değiştirmez: sürüm oluşturma/freeze, silme, rollback, export, otomatik bölme ve öğe bölme ataması bu kararın dışındadır. Sağlayıcı üye listesi sunmadığından referans **üyeliği kanıtlamaz**; `is_frozen` sağlayıcı iddiasıdır, bağımsız değişmezlik kanıtı değildir.

Sürüm oluşturma/freeze (**açık karar**): önerilen seçim bu fazda **uygulamamaktır**. Gerekçe: etki sözleşmesi bilinmiyor (etiket çakışmasında 500, idempotency, silme/rollback etkisi, maliyet), güvenle tekrarlanabilir bir niyet/uzlaştırma modeli yok ve kullanıcı Platform arayüzünde freeze edebilir. Kullanıcı bunun yerine uygulanmasını isterse ayrı Proposed ADR, plan/onay/tek gönderim ve kayıp cevap uzlaştırması gerekir; bu karar onu önceden onaylamaz. Eksiklik [P02-R4 kartında](../roadmap/tasks/p02-r4-dataset-version-creation.md) görünür kalır.

### 2. Değişmez referans: DatasetVersionBinding v1

`bind` tek bir `is_frozen=true` sürümü gözler ve kapalı, strict, extra-forbid `DatasetVersionBinding v1` üretir. Sağlayıcı hedefi (normalize origin/API kökü), `dataset_id`, `version_id`, `version_tag`, sağlayıcı `created_at`, `is_partial`, `item_count`, dört bölme sayısı, `annotated_item_count`, `total_annotation_count`, `class_count` ve kanonik sınıf-etiketi özetinin SHA-256’sı bağlanır; isteğe bağlı `--manifest` verildiğinde yerel Manifest v1 digest’i ve dosya sayısı eşliği (`count_matches|count_differs`) da bağlanır. Etiket **ve** sürüm kimliği birlikte bağlanır: aynı etiketle yeniden oluşturulmuş farklı sürüm değişmiş sayılır. `observed_at` ve sağlayıcıdan gelen serbest metin (`description`, `created_by`, URL alanları) digest’e girmez ve artifact’a yazılmaz; description yalnız bounded ekran özetidir. Digest, `digest` hariç bütün alanların kanonik JSON’unun SHA-256’sıdır. Referans sır, ham sağlayıcı gövdesi veya kişi kimliği taşımaz.

`is_frozen=false` sürüm bağlanamaz (`dataset_version_not_frozen`, exit 2). Bölme sayıları iki kaynağın (detay `split_config` ve `splits` rotası) birbirine eşit olmasını ister; çelişki `invalid_response` olur. `item_count`, dört bölme sayısının toplamına eşit değilse (provider çelişkisi) bağ üretilmez. Sayı eşitliği veya `count_matches` üyelik, içerik veya model uygunluğu kanıtı değildir.

### 3. Sapma denetimi ve hata sınıfları

`check` bir bağı yeniden gözler ve yalnız değişmez alanları karşılaştırır. Sonuçlar kapalıdır: `unchanged`, `changed` (alan adları sayısı/listesi), `missing` (sürüm bulunamadı), `unavailable` (taşıma/5xx/429/401/403). Değişim ve yokluk exit 7 `dataset_version_changed` (ayrıntı kapalı sayaçlar), yetki ve taşıma hataları mevcut `remote_*`/`transport_*` kodlarıdır. Yokluk içerik değişimi sayılmaz ve “yeniden oluştur” önerisi üretilmez. Başarılı `check` bağın hâlâ aynı sağlayıcı metadata’sına işaret ettiğini söyler; eğitimde kullanılacak byte’ların aynı olduğunu söylemez.

### 4. Sınırlar ve yerel dosya

Her komut tek hizmet/credential snapshot’ı ve ortak HTTP taşıması kullanır; ağda kapalı DB transaction’ı tutulmaz. `list` en çok 5 sayfa × 20 kayıt, `show/bind/check` en çok 2 GET (sürüm detayı + bölme sayımı); her yanıt 1 MiB, toplam 30 s, salt okuma retry’si ADR-0017 politikasıdır. `version_tag` kapalı bir ASCII güvenli kümeyle (1–128, `[A-Za-z0-9._-]`) doğrulanır; yol parçası olarak yeniden kodlanmaz. Referans artifact’ı Manifest v1 ile aynı root-dışı, no-follow, 0600, O_EXCL stage ve exclusive hardlink politikasıyla yayımlanır; mevcut hedef ezilmez. SQLite şeması, migration ve operation kayıtları bu karardan etkilenmez.

## Alternatifler

- **Sürüm oluşturmayı da eklemek:** Görünür, geri alması belirsiz bir etki; sağlayıcı sözleşmesi (idempotency, çakışma, maliyet) bilinmiyor. Seçilmedi, P02-R4’te açık.
- **Yalnız `version_tag` ile bağ:** Silinip yeniden oluşturulan etiketi ayırt edemez. Seçilmedi.
- **Güncel dataset item listesini sürüm üyeliği saymak:** Sağlayıcı sürüm anlık görüntüsünü sunmaz; sonradan değişen dataset’i yanlış doğrular. Seçilmedi.
- **Bağı SQLite’ta saklamak:** Yeni migration/yedek/reset yüzeyi ve plan bağı tüketicisi (P03-1) olmadan erken kalıcılık. Seçilmedi; dosya artifact’ı bağımsız ve taşınabilir.

## Sonuçlar ve kabul

Onay yalnız salt okunur sürüm/bölme gözlemi ve değişmez referans biçimini açar; freeze, eğitim bağı, canlı yazma veya sağlayıcı değişmezlik garantisi üretmez. Kabul; strict codec negatifleri (eksik/yanlış tip alan, bool≠int, kopya anahtar, 2xx mantıksal hata), sayı çelişkileri (toplam≠item_count, detay≠splits), tag çakışması/silinip yeniden oluşturulma, 404/401/403/429/5xx, sayfa döngüsü/tekrarlı ID, literal-secret ve PII (created_by, description) sızıntısı, aynı sürüm için aynı digest, no-clobber yayın ve kısmi yayın sonrası belirsizlik, JSON/NDJSON/text ve BrokenPipe/iptal eşliğini içerir. Gerçek hesapta salt okuma kabulü ayrı yetkiyle, bounded GET sayısıyla ve rapor/receipt’le yapılır; offline fixture yeşili canlı destek diye sunulmaz.
