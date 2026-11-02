# ADR-0027 — Create cevabının kalıcı sahiplik bağı

**Durum:** Proposed; kullanıcı onayı bekleniyor. **Tarih:** 2026-11-03. **İş:** P02-2 create/reconcile bütünlüğü. [ADR-0026](0026-explicit-unverified-transfer-attempts.md) yalnız aşağıdaki receipt koruma hükmünde kısmen değişir; authority, cost, tek gönderim, reset ve live yetkisi korunur.

## Bağlam

[Provider sözleşmesi](../reference/platform-upload-consumer.md#context-create-ve-proje-bağlantısı), create ile sonraki exact-ID detail cevabının owner_id/org_id çiftinin de eşit olmasını ister. User-owned dataset'in org_id alanı null veya bir ID olabilir; organization-owned dataset'in owner_id alanı da seçilmiş organization ID'sinden türetilemez. Şimdiki accepted create StageReceipt v1 yalnız dataset_id saklar. Sonraki current owned/detail yanıtlarını birbirine eşlemek tarihsel create cevabını kanıtlamaz; immutable plan, request digest veya tam dosya grafiği bu eksik cevabı geri getirmez.

O.2 öncesi bağımsız salt-okunur hazırlık review'si bu boşluğu doğruladı. Original writer gerçek create DTO'sunu bellekte karşılaştırabilir; süreç ölünce aynı koşulsuz karşılaştırma için kalıcı kanıt eksiktir. Hâlen public writer yoktur; yeni canlı çağrı yapılmadı. Bu ADR, gözlenen API'nin genel auth veya sahiplik garantisini doğrulamaz.

## Karar

### Dar, sürümlü accepted-create receipt

Yeni `CreateReceiptV2`, yalnız v2 transfer operation'ın accepted create intent'i için kullanılır. V1 StageReceipt byte/digest/decoder ve tarihsel kayıtlar değişmez. Yeni kapalı modelin alanları:

| Alan | Tip / kural |
|---|---|
| schema_version | strict integer 2 |
| intent_id | canonical internal UUIDv4; mevcut create intent FK'si |
| recorded_at | mevcut canonical UTC; issuing intent zaman aralığı |
| result | literal accepted |
| dataset_id | canonical provider UUID |
| object_key, sent_bytes, sent_sha256 | zorunlu null; eski alanlar başka anlamla kullanılmaz |
| created_dataset | kapalı ProviderDataset: id, name, modality, visibility=private, contributions_enabled=false, owner_id, zorunlu nullable org_id |

created_dataset.id dataset_id ile eşittir. Scope/plan name/modality/private/false ve selected owner eşliği, mevcut strict create codec'inden sonra repository transaction'ında da doğrulanır. Bilinen yanlış owner/private/parent hiçbir onayla geçilmez. Bütün ham create cevabı veya metadata dict'i saklanmaz; name planın mevcut girdisidir, diğer alanlar dar bildirilen ID/politika alanlarıdır. Bu ID'ler kişiye bağlanabilir; yerel özel state dosyası sınırında tutulur, tüm PII'nin ayıklandığı iddia edilmez. Seçili credential literal kuralı typed payload'a kalıcılaştırmadan önce uygulanır.

Encoded receipt sınırı mevcut **2 KiB**'dır. Stage slotu, toplam canonical payload/reservation ve otomatik silmeme sınırları değişmez; daha büyük cevap veya typed payload kontrollü ret/unknown'dır. Strict UTF-8/JSON/depth/node, canonical encoding ve schema-version ayrımı mevcut upload wire kurallarıdır. Rejected create ve diğer bütün accepted/rejected stage receipt'leri v1 kalır; yalnız bu intent-kind'e bağlı karışım geçerlidir.

### Atomik bağ ve yeni başarı kapısı

CreateReceiptV2, accepted receipt insert'i ve operation.dataset_id güncellemesiyle **aynı SQLite transaction/savepoint** içinde kalıcılaşır. Commit yanıtı kaybolursa bilinmeyen create yine otomatik gönderilmez. Receipt veya baseline eksikliği owned/name/detail okumasıyla backfill edilmez. Yeni write/attempt/lease/permit üretilmez; raw URL/provider object key/caller auth kalıcılaştırılmaz.

Sonraki bütün orijinal-writer ve restart detail karşılaştırmaları, bu immutable created_dataset'i expected olarak kullanır. Exact ID/name/modality/private/contributions ve **iki sahiplik alanı** da eşit olmalıdır. Reset veya credential rotation baseline'ı yeniden yazmaz; yeni okuma scope'u eski kaynağı okur ve güncel yetki kuralını ayrıca sağlar. Metadata eşliği auth grant veya uzak byte hash'i değildir.

Yeni **nonterminal v2 metadata success commit'i**, mevcut tam 2+3N accepted graph ve v2 read/proof şartlarına ek olarak accepted create'in CreateReceiptV2 taşımasını ister. Bu kontrol yalnız yeni proof yazımı kapısıdır; önceki terminal kayıt full validation'da geriye dönük yeni kurala göre bozulmaz. TransferVerification v2/control v2 biçimleri ve digest'leri değişmez; trusted producer detail eşliğini receipt'teki baseline'a karşı yapar, repository de aynı graph baseline'ının varlığını ve scope/plan bağını doğrular. Public caller raw proof/producer/baseline sağlayamaz.

### Geçmiş ve decoder matrisi

| Kayıt | Okuma ve yeni işlem |
|---|---|
| V1 plan/operation + v1 receipts | Decode/history/local show/revoke ve mevcut grant'lı read-recovery kuralları korunur; yeni write yine kapalı |
| V1 plan/operation + CreateReceiptV2 | state_invalid; sürüm/kind sınırı ihlali |
| V2 operation + accepted create v2 + diğer receipts v1 | Yeni producer'ın normal graph'ı; tam mevcut success kapılarıyla metadata success mümkün |
| V2 operation + accepted create v1 | Tarihsel decode/show/list/revoke ve terminal history korunur. Nonterminal kaydın yeni metadata success'i baseline eksikliğiyle kapalıdır; HTTP'den önce unknown/request_uncertain + aynı operation ID/operation_uncertain exit 5, sıfır yeni etki |
| V2 receipt yanlış intent-kind, rejected/result veya ID/scope/plan bağı | state_invalid; geçerli yeni proof veya receipt değildir |

V2 legacy nonterminal için read-only local inspection ve mevcut cleanup/reset yolları korunur; baseline olmadan yeni success veya yeniden create önerilmez. Eski binary yeni receipt schema_version=2'yi kontrollü state_invalid ile reddeder; rewrite/downgrade/backfill yapılmaz. DDL/migration/checksum **1–7 değişmez**; mevcut JSON payload alanında kapalı union decode edilir. Reset/backup/capacity/hot/full doğrulama union'ı birlikte tanır.

## Değerlendirilen alternatifler

- **Restart'ta yalnız selected-owner eşliğini yeterli saymak:** Daha az kalıcılık değişir, fakat mevcut koşulsuz create–detail çift eşliği daralır. Seçilmedi.
- **Owned/detail'den tarihsel baseline üretmek:** Yalnız iki güncel gözlemi eşler; tarihsel create kanıtı değildir. Seçilmedi.
- **Eski receipt alanını veya request digest'ini baseline hash'iyle aşırı yüklemek:** Eski anlam/golden ve file-binding sınırını karıştırır. Seçilmedi.
- **Yeni ayrı tablo/migration:** Aynı transaction'ın yeni bounded receipt payload'ı yeterlidir; ilave tablo gerekmez. Seçilmedi.

## Sonuçlar ve onay sonrası geçiş

Dar typed sahiplik kanıtı, süreç öldürülse bile aynı kayıtta korunur. Yeni schema eski binary'lerle paylaşılan store'u açmayı engelleyebilir; eski binary kontrollü ret verir. Eski nonterminal v2 kayıt eksik baseline nedeniyle yeni metadata başarıya yükselmez; otomatik geçmiş düzeltmesi veya replay yoktur. Yetki/fiyat unknown ve ayrı live kabulü değişmez; bu ADR yeni canlı write yetkisi vermez.

Onay sonrası tek commit/review paketinde: ADR-0026 receipt cümlesine partial amendment forward link; dataset-transfer receipt/union/current success; dataset-upload-v2 tür/graph/gate tablosu; provider create/detail referansı; o hazırlık/current ve sonraki controller kart/plan/current/faz/karar indeksi güncellenir. Bu ön geçiş listesi Proposed metni uygulanmış göstermez; bağımlı receipt ürün kodu onaya bağlıdır. O.1 ve O.2/O.3'ün pre-create/current/prepare/approve işleri aynı dalda bağımsız ilerleyebilir; yeni receipt/restart success uygulanmaz.

Kabul: literal v1/v2 create JSON/canonical byte ve üst sınır golden'ı; diğer receipt'lerin v1 byte eşliği; type/kind/result/ID/scope/plan/selected literal negatifleri; name'in azami Unicode encoded sınırı; atomik accepted receipt + dataset ID commit/kill/cevap kaybı; create sonrasında owner_id veya org_id değişimi (seçilmiş owner değişmese bile) → ret/unknown, metadata success yok; original ve restart aynı predicate; reset/credential rotation baseline immutable; eksik baseline/all accepted+dosya metadata eş → yeni başarı yok ve HTTP sıfır; eski terminal history/full validation korunur; backup/quota/recovery/reset union; unknown version/old binary ret; sıfır yeniden gönderim. Her kod dilimi commit + iki fresh review turuyla kapanır; native/kurulum/CI/live epik kabulü ayrıca tamamlanır.
