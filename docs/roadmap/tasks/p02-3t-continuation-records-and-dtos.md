---
id: P02-3t
phase: P02
status: in_review
size: M
depends_on: [P02-3f]
capabilities: [C03, C12]
---
# P02-3t — Continuation v3 kayıt, kontrol, doğrulama ve kullanıcı DTO tipleri

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 3 (ikinci yarı); [P02-3f](p02-3f-continuation-domain-v3.md)’nin ölçülen büyüklük nedeniyle bölünen yarısıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) ve [continuation sözleşmesi](../../reference/dataset-upload-continuation.md) tipleri; kalıcılık ve HTTP yok.

## Kullanıcı sonucu ve mevcut eksik

Continuation operasyonunun kayıt, kontrol ve doğrulama tipleri ile kullanıcıya dönen özet ve rapor tipleri bugün yoktur; v2 tipleri kapalıdır. Bu kart, v1/v2’yi değiştirmeden strict v3 kayıt/kontrol/doğrulama tiplerini ve gizli alan taşımayan kullanıcı DTO’larını sabitler; P02-3g bunları depoda okur, P02-3i bunları yüzeyde gösterir.

## Giren ve girmeyen kapsam

`TransferRecord v3` (plandan dolu `dataset_id`, latch ilk intent’te, `verification_only` bayrağı ve kuralları: intent üretmez, latch’lenmez, yalnız `admitted`, `succeeded` veya `cancelled` olabilir, unlatched `succeeded` yalnız `verification_only`), `TransferControl v3`, `TransferVerification v3` (v2 ile aynı alanlar, N dosyalık sıralı kanıt), kaydın ve kanıtın planla eşleşmesini denetleyen `validate_record_binding_v3` ve `validate_verification_binding_v3`, `DatasetUploadSummary v3` (`continuation_of`, `continuation_files` (M), `remote_present_files` (= N−M) ve `uncertain_files`; plan yalnız `remote_present_count` taşıdığından `confirmed`/`observed` ayrımı özette yoktur; yol/baseline/makbuz alanı yok), `DatasetUploadResumeReport v1` (kapalı `blockers`, önerilen eylem, nullable `related_operation_id`, N; gözlenmeyen kaynaklar için nullable `observation` — sınıf sayıları, M, M için toplam bayt, `unconfirmed_ack_required`, iki özet ve sorunlu sınıf başına ≤8 örnek göreli yol; kota kullanımı ve ekleneni, nullable `plan_id`/`plan_digest`) ve onu gerçek `classify` çıktısından kuran saf `resume_report` üreticisi, canonical kodlama ve byte sınırları ile kayıt/kontrol/doğrulama sürüm eşitliği girer. `len(intents) ≤ 3M` ve intent/makbuz grafiği kuralları, kanıt girdilerinin Manifest’le eşitliği ve kayıt/kanıt sürüm ve saat eşleşmesi kayıt tiplerinde değil depo okumasında (P02-3g), rapor örnek yollarının literal-secret taraması üreticide (P02-3i) doğrulanır. Repository/DDL, HTTP, koordinatör, CLI/API yüzeyi ve mevcut v2 kullanıcı kapsayıcıları (`UploadIntentReview`, `DatasetUploadsPage`, `Result[DatasetUploadSummary]` dönüşleri ve CLI’deki `isinstance` noktaları) girmez; bunların v3’ü taşıması P02-3i’nin açık işidir.

## Bağımlılıklar ve kararlar

P02-3f plan ve onay tiplerine bağlıdır. [ADR-0031](../../decisions/0031-upload-continuation.md) Accepted’dir (2026-11-06). Tip alanları sözleşmedeki tablodan kesinleşir; golden vektörler bağımsız hesaplanır.

## Sözleşme ve uygulama sınırı

Hepsi strict/frozen/extra-forbid, zorunlu alanlı (nullable dahil), bool≠int; canonical ASCII JSON ve byte sınırları v1/v2 ile aynı. Kayıt/kontrol/doğrulama sürümü eşleşir; v3 `decode` yalnız kendi tür/sürüm çiftlerini kabul eder (üç tipli decode’un depoya bağlanması P02-3g’dedir). Raporun M, M-bayt ve `unconfirmed_ack_required` alanları engel varken sınıf vektöründen türetilen bilgi amaçlı değerlerdir; plan alanları yalnız engelsiz `selection()`dandır.

## Kabul

1. Her tip için literal canonical byte ve SHA-256 golden’ları; v1/v2 golden’ları değişmez.
2. Doğrulayıcı negatifleri: v3 kaydında `dataset_id=null`, `verification_only` ile `file_indices` boşluğunun eşleşmemesi, `verification_only` olmayan unlatched `succeeded`, `verification_only` + intent/latch/`unknown`, etkisiz iptalin `request_uncertain`/`provider_rejected` taşıması, devamın kendi kaynağı olması, sürüm eşleşmeleri (kayıt v3+doğrulama v2 vb.), bilinmeyen/eksik alan, bool-as-int, sırasız/tekrarlı kanıt dosyası; N dosyadan az kanıt tipin kendi başına geçerlidir ama `validate_verification_binding_v3` ile plana ait değildir (kayıt–plan ve kanıt–plan eşleşmesi: başka plan/digest/`intent_digest`/dataset/onay/kip, başka dataset/proje/hedef).
3. v3 özet/rapor DTO’ları `created_dataset`, owner/org/ad, makbuz alanı, tam yol listesi ve literal-secret taşımaz (sentinel); rapor örnek yolları taşınabilir göreli Manifest yolu olmak, sıralı ve tekil olmak zorundadır, sorunlu sınıf başına en çok 8’dir ve sınıf sayısını aşamaz (literal-secret taraması üreticinindir, P02-3i).
4. Rapor alanları engel varken ve engelsizken tutarlıdır (plan kimlikleri yalnız `--prepare` sonrası dolu); gözlem yapılamayan kaynak (`create_unknown` vb.) `observation: null` ile gerçek bir rapordur ve uzak kanıt gerektiren engel taşıyamaz; rapor gerçek `classify` çıktısından (432 senaryo) hata vermeden kurulur, kota kullanımı ve ekleneni ile en kötü yasal (24 yol, ≈73 KB) rapor tel sınırı içindedir.

## Doğrulama

Contract/unit testleri, golden fixture’ları, Ruff ve strict mypy; belge kontrolleri. Kalıcılık ve ağ davranışı iddia edilmez.

## Teslim kaydı

Uygulandı, review bekliyor; `verified` değildir. Commit’ler `feat/p02-3-dataset-recovery` dalındadır: uygulama [0179462](https://github.com/HodeTech/Yorunge/commit/0179462d5e698a1ebc78678fedf18c99ddc59318), mutasyon özdenetimi [17e344f](https://github.com/HodeTech/Yorunge/commit/17e344f37f2b880f7323f455b209d32e48f68ba8); kontrol çıktıları ve review kaydı [uygulama kaydındadır](../../research/p02-3-implementation-validation.md#adım-4--p02-3t-continuation-v3-kayıt-kontrol-doğrulama-ve-kullanıcı-dto-tipleri). Seçilen adlar ve yerleşim:

- `yorunge.domain.dataset_transfer_v3`: `TransferRecordV3`, `TransferControlV3`, `TransferVerificationV3`, `validate_record_binding_v3` ve `validate_verification_binding_v3`.
- `yorunge.domain.dataset_transfer_v2`: v2 davranışı, iletisi ve baytı değişmeden ortak `validate_lease_binding`, `validate_control_facts` ve `validate_verification_facts` (v2 ve v3 kayıt/kontrol/kanıt aynı kuralları paylaşır; `LeaseFacts`, `ControlFacts`, `VerificationFacts` protokolleri).
- `yorunge.domain.upload_public`: `DatasetUploadSummaryV3` ve v2 ile ortak `validate_summary_approval`/`validate_summary_evidence` (`SummaryFacts`).
- `yorunge.domain.upload_resume_report`: `DatasetUploadResumeReport`, `ResumeClassCounts` ve `ResumeExamples` (`PROBLEM_CLASSES`, `MAX_EXAMPLES=8`, `MAX_QUOTA_PAYLOAD_BYTES=16 MiB`).
- Golden fixture’lar `tests/fixtures/dataset-continuation-{record-v3-admitted,record-v3-running,record-v3-verification-only-succeeded,control-v3,verification-v3,summary-v3,resume-report-v1-blocked,resume-report-v1-eligible,approval-v3-verification-only}.json` düz `hashlib`/`json` ile bağımsız üretildi; testler özetleri yeniden hesaplar.
- Uygulama sırasında belirlenen kararlar: özet v3 `confirmed`/`observed` yerine `remote_present_files` ve `uncertain_files` taşır (plan bu ayrımı bilmez); `verification_only` kayıt `running`/`unknown`/`failed` olamaz; `inventory_too_large` rapor tipinde `inventory_unreliable` gerektirir; rapor `recommended_action(blockers)` ile eşit olmak zorundadır.
