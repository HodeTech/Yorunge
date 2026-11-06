---
id: P02-3g
phase: P02
status: in_review
size: M
depends_on: [P02-3t]
capabilities: [C03, C12]
---
# P02-3g — Continuation sürüm donanımı: 3 tipli decode, birleşik tipler ve v3 graf belirtimi

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 5. Okuma yarısının ilk dilimi: v3 tiplerinin depoda **okunabilmesi** için gereken sürüm donanımı. Ölçülen büyüklük bu kartı L yaptığından büyüme kuralı gereği üçe bölündü: bu kart sürüm donanımını ve graf belirtimini, [P02-3u](p02-3u-continuation-graph-validation-and-chain.md) v3 graf doğrulamasını ve zincir/baseline çözümleyicisini, [P02-3v](p02-3v-continuation-capacity-and-projection.md) kapasite, bakım, reset önizlemesi ve projeksiyonları kapsar. Yazma kapıları [P02-3r](p02-3r-continuation-write-gates.md)’dedir.

## Kullanıcı sonucu ve mevcut eksik

v3 payload’ları depo katmanında bugün çözülemez: `decode_versioned` iki tip imzalıdır, `upload_versions` birleşik tipleri ve gönderim yardımcıları (`validate_versioned_approval`, `verification_scope`, `graph_of`) yalnız v1/v2’yi tanır ve `verification_scope` bir v3 kanıtını sessizce “v1” sayıp `grant.scope`a düşerdi; `StageGraphSpec` v3 grafiğini (create’siz, `file_indices` alt kümesi, 3M intent) bilmez. Bu yapılmadan hiçbir v3 satırı store genelinde okunamaz.

## Giren ve girmeyen kapsam

Girer: `StageGraphSpec`in v3 sürümü (`SUPPORTED_PLAN_VERSIONS`, alt küme `files`, `intent_count = 3M`, create/link’siz `required_stages`, öncülsüz presign, 3M ve N’e göre `operation_reservation`, create/link=0 `request_counts`, alt küme `put_batches`; `RequestCounts`ın create/link alanlarının 0’ı alabilmesi; v1/v2 davranışı ve `ORIGINAL_PLAN_VERSION` tüketicileri değişmez); `domain/upload_versions.py`nin v3 üyeleri (birleşik tipler, `validate_versioned_approval` v3 dalı, `verification_scope`un v3’ü açıkça tanıması, `graph_of` v3, `validate_create_receipt`ın v3’ü reddetmesi; v3 hiçbir yerde “v1’in kalanı” sayılmaz); `decode_versioned`in üçüncü sürümü (mevcut iki tipli çağrılar v3 payload’ını `state_invalid` ile reddetmeye devam eder; v3’ü okuyan çağrı noktaları: `read_plan`, `read_approval`, `read_any_record`, denetim ve kanıt okumaları, `write_record`ın doğrulaması) ve `read_plan`/`read_any_record`ın v3 satırı (namespace payload eşitliği, `operation_reservation` formülü); **v2’ye özgü gönderim noktalarının kontrol listesi** (`isinstance`/`schema_version`/`TransferRecordV2` kullanan ve iki tipli `decode_versioned` çağıran her nokta, hangi dilime ait olduğuyla: P02-3u, P02-3v, P02-3r veya P02-3h) bu kartın çıktısı olarak belgelenir ve testle kilitlenir. Girmez: v3 graf doğrulaması, zincir/baseline çözümleyicisi, kapasite/bakım/projeksiyon, yazma kapıları, HTTP, public yüzey, DDL.

## Bağımlılıklar ve kararlar

P02-3f ve P02-3t tipleri verified olmalıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir. DDL gerekirse koddan önce kullanıcı kararı alınır. Eski binary uyumu ADR-0031 §6’daki kontrollü `state_invalid` retidir.

## Sözleşme ve uygulama sınırı

Mevcut ortak primitive’ler yeniden kullanılır; v1/v2 yolları davranışsal olarak aynı kalır. v3 tipleri v2 sınıflarının alt sınıfı değildir; bu yüzden her `isinstance(…, V2)` gönderimi v3 için açık bir dal ister ve atlanan dal sessiz yanlış davranış değil test edilmiş bir ret olmalıdır. Doğrulama doğrudan SQLite satırlarına yazılmış sentetik v3 satırlarıyla sınanır (yazma kapısı bu dilimde yoktur). Restore/recover yasağı değişmez.

**P02-3t devir notu.** Kayıt ve kanıt tipleri tek başlarına denetlemez, depo okuması (P02-3u) denetler: kanıt girdilerinin saklı Manifest’le eşitliği; kayıt ve kanıt sürüm eşitliği; kanıtın kimlik dönemi ve saat nesli ile kaydınki; `len(intents) ≤ 3M` ve intent başına tek makbuz; kayıt `operation_id`sinin zincirdeki kaynak ve kök operation’dan farklı olması ve zincirin döngüsüzlüğü.

**Hata eşlemesi.** Depo okumasında v3 plan, onay, kayıt ve doğrulayıcılarının `ValueError`ı `state_invalid` olur (üretici yolundaki `invalid_request`/`input_changed` eşlemesinden ayrıdır; tip katmanı düz `ValueError` verir).

**P02-3d devir notu.** `StageGraphSpec` bugün yalnız v1/v2 grafiğini bilir; plan sürümü taşımayan dört tüketici (`upload_preparation._limits`, `UploadCostWork.quantities`, `UploadIntentReview`, test dışında çağrılmayan `dataset_transfer.operation_reservation`; hepsi `ORIGINAL_PLAN_VERSION` adını verir) gözden geçirilir. Dataset kimliğinin kaynağı v3’te kabul edilmiş create makbuzu değil plan/baseline’dır: `files` ve `put_batches` demettir ve alt küme indekslerini ifade eder. Bu noktalar P02-3d R2 mutasyon incelemesinde testlerle kilitlidir (`tests/contracts/test_upload_graph_wiring.py`, journal testleri); v3 davranışı o testleri bilinçli olarak günceller, sessizce geçmez.

## Kabul

1. `StageGraphSpec` v3: alt küme `files`, `intent_count = 3M`, `required_stages` yalnız seçilen dosyaların presign/put/confirm’ü, presign’ın öncülü yok, put/confirm öncülleri v2 gibi, `operation_reservation` 3M intent ve N dosyalık proof için bağımsız formülle, create/link isteği 0, `put_batches` en çok iki dosyalı gruplar; M=0 geçerli ve boştur; geçersiz alt küme (sırasız, tekrarlı, aralık dışı) reddedilir; v1/v2 vektörleri ve golden’lar değişmez.
2. Birleşik tipler ve gönderim yardımcıları v3’ü açıkça tanır: yanlış sürüm eşleşmeleri (plan v3+onay v2 vb.) reddedilir; `verification_scope` v3 kanıtında kanıtın kendi kapsamını verir (v1’in `grant.scope`una düşmez); `validate_create_receipt` v3’te reddeder.
3. `decode_versioned` üç sürümü ayırır: v3 payload’ı mevcut iki tipli çağrılarda `state_invalid`, üç tipli çağrıda doğru tip; kapalı sürüm, bayt sınırı ve canonical payload kuralları v1/v2 ile aynıdır.
4. Sentetik v3 plan/onay/kayıt satırları `read_plan`, `read_approval`, `read_any_record` ile okunur; indeks/namespace/rezervasyon uyuşmazlığı `state_invalid`dir; `operation_reservation` v3 için kayıt yazımında ve okumasında aynı formüldür.
5. v2’ye özgü gönderim noktaları kontrol listesi eksiksizdir (kaynağın sözdizimi ağacından okunur, test listeyle kodu karşılaştırır) ve her nokta sahibine atanmıştır.
6. v1/v2 geçmişi, golden’lar ve mevcut regresyon ağı değiştirilmeden geçer.

## Doğrulama

Contract testleri (`StageGraphSpec` bağımsız formüller, birleşik tipler), gerçek SQLite integration testleri (sentetik v3 satırları), mevcut upload regresyonları, Ruff ve strict mypy. Ağ ve yazma kapısı iddiası yoktur.

## Teslim kaydı

Uygulandı, birinci tur review düzeltmeleri yapıldı, ikinci tur review bekliyor; `verified` değildir. Commit’ler `feat/p02-3-dataset-recovery` dalındadır: uygulama [3bf6f19](https://github.com/HodeTech/Yorunge/commit/3bf6f19), mutasyon özdenetimi [61af432](https://github.com/HodeTech/Yorunge/commit/61af432), R1 düzeltmeleri [38e0112](https://github.com/HodeTech/Yorunge/commit/38e0112); kontrol çıktıları ve review kaydı [uygulama kaydındadır](../../research/p02-3-implementation-validation.md#adım-5--p02-3g-continuation-sürüm-donanımı). Seçilen adlar ve yerleşim:

- `yorunge.domain.upload_graph`: `CONTINUATION_PLAN_VERSION`, `ORIGINAL_PLAN_VERSIONS` ve `StageGraphSpec(plan_version, file_count, selection)`; v3 için `continuation`, `dataset_from_plan`, alt küme `files`, `intent_count = 3M`, create/link’siz `required_stages`, öncülsüz presign (`predecessor` create/link’te `ValueError`), N dosyalık proof payını koruyan `operation_reservation`, create/link=0 `request_counts`; `RequestCounts.create/project_link` 0 veya 1 olabilir. v1/v2 vektörleri değişmez; v1/v2 seçim almaz.
- `yorunge.domain.upload_versions`: üç ailenin birleşik tipleri (plan, onay, kayıt, kontrol, kanıt), `validate_versioned_approval` v3 dalı, aileleri adıyla sayan ve tanımadığını reddeden `verification_scope` ve `graph_of` v3 (`StageGraphSpec`e planın `file_indices`ini verir). Makbuzlar `StageReceipt | CreateReceiptV2` kalır: devam create göndermez.
- `yorunge.adapters.upload_store`: `decode_versioned(v1, v2, payload, v3=None)` (üçüncü sürüm yalnız onu listeleyen çağıranda okunur, listelemeyen çağıran v3 payload’ını `state_invalid` ile reddeder); `read_plan`, `read_approval`, `read_any_record`, `read_any_view`in kontrol/kanıt okumaları ve `write_record` v3’ü okur/yazar. Saklı v3 kaydı okunurken ve eklenirken `bind_continuation_record` ile planına bağlanır (`validate_record_binding_v3`: kimlik, digest’ler, dataset, mod, onay; iki aile karışmaz); `write_record` dataset ve modu sabit tutar; `request_digest` v3’te dataset kimliğini plan bağından alır (create makbuzuna bakmaz); `namespace_owner` v3 için sahibi `baseline_operation_id` sayar (`read_any_view`in latch’li kayıt denetimi). **Kapalı başarısızlıklar (bilinçli):** `validate_graph` (P02-3u), `capacity()`, `upload_projection.summary` ve `invalidate_uploads` (P02-3v) bir devamı yanlış okumak yerine, değişiklik yapmadan `state_invalid` verir; depo yazıcıları (`save`, `revoke`, `_change`, `_control`, `_verified`) iki tipli decode ettiği için bir devamı reddeder ve P02-3r’ye atanmıştır.
- `tests/fixtures/version-dispatch-sites.json` ve `tests/contracts/test_version_dispatch_sites.py`: aileleri ayıran her nokta kaynağın **sözdizimi ağacından** okunur (`isinstance`/`issubclass`, `type(x)` ve `__class__` karşılaştırmaları, `match`, `schema_version` okumaları, `decode_versioned` aritesi, aile tipiyle doğrudan decode) ve anahtarı yerden ve biçimden bağımsızdır (dosya, fonksiyon, tür, ifade, sıra). 103 nokta sahipleriyle listelenir (done 36, P02-3r 25, P02-3v 10, v1-only 8, P02-3u 7, v2-only 7, P02-3h 6, unrelated 4: başka şemaların kendi sürümünü okuyan iki modül); yeni nokta atanana kadar test başarısız olur ve eklenecek satırı yazdırır. Her `schema_version` okuması modülün hangi tipleri içe aktardığından bağımsız listelenir. Bulucunun kendisi sentetik kaynaklarla sınanır (her tür görünüm, biçim değişikliği, tekrarlı ifade), her `decode_versioned` çağrısının tipleri tek bir ailenin sürüm sırasındaki üyeleri olmak zorundadır ve bir aile tipi ya da `decode_versioned` başka adla içe aktarılamaz. Bulucunun göremediği idiomlar (tip sabiti, değişken takma adı, `type(x).__name__`, alan varlığına göre ayırma) bugün kodda yoktur ve test modülünün belge metninde adlandırılmıştır.
- Bilinçli ayrım: v3 kontrol ve doğrulama kanıtı v2 ile aynı alanlara sahip olduğundan yalnız `schema_version` etiketiyle ayrılır; kayıtla sürüm eşitliği depo kuralıdır (P02-3u). `adapters/upload_preparation._limits` v2 sınır tipinin create/link=1 değerlerini sabit yazar (tip daraltması için ayrı bir koruma gerekmez). `ORIGINAL_PLAN_VERSION` kullanan diğer üç tüketici (`domain/upload_costs.py`, `domain/upload_public.py`, `domain/dataset_transfer.operation_reservation`) v2’ye özgü DTO’lara bağlıdır ve orijinal grafiği bilinçli olarak varsayar; devam bu yollardan geçmez (P02-3d devir notu böylece kapanır).
