# ADR-0027 — Create cevabının kalıcı sahiplik bağı

**Durum:** Accepted — 3 Kasım kullanıcı review bulguları kapatıldı; iki farklı fresh belge turu temiz tamamlandı. Kullanıcının koşullu uygulama yetkisiyle benimsendi. **Tarih:** 2026-11-03. **İş:** P02-2 create/reconcile bütünlüğü. [ADR-0026](0026-explicit-unverified-transfer-attempts.md) aşağıdaki eşlemede kısmen değişir; authority, cost, tek gönderim, reset ve ayrı live kabulü korunur.

## Bağlam

[Provider sözleşmesi](../reference/platform-upload-consumer.md#context-create-ve-proje-bağlantısı), create ile sonraki exact-ID detail cevabının owner_id/org_id çiftinin de eşit olmasını ister. User-owned dataset'in org_id alanı null veya bir ID olabilir; organization-owned dataset'in owner_id alanı seçilmiş organization ID'sinden türetilemez. StageReceipt v1 yalnız dataset_id saklar. Güncel owned→detail eşliği tarihsel create cevabı değildir; plan/request digest veya dosya grafiği eksik cevabı geri getirmez.

Original writer gerçek create DTO'sunu bellekte karşılaştırabilir; restart için aynı predicate'in kalıcı kaynağı eksiktir. [O hazırlığı](../reference/dataset-upload-preparation.md) yerel verified oldu; public writer ve yeni canlı çağrı yoktur. Bu karar provider auth/sahiplik garantisi veya yeni bir write yetkisi üretmez.

## ADR-0026 kısmi değişiklik eşlemesi

| Değişen hüküm | Kabul sonrası normatif karşılık |
|---|---|
| ADR-0026 sürümleme: stage/receipt/lease v1 korunur | StageIntent/TransferLease v1 kalır. StageReceipt v1 rejected create ve diğer accepted/rejected stage'lerde; **yeni v2 accepted create insert'i yalnız CreateReceiptV2** |
| ADR-0026 tam graph/metadata success | Yeni nonterminal v2 success ayrıca accepted CreateReceiptV2 baseline ister. Tarihsel v2+v1 terminal kayıtlar geriye dönük bozulmaz |
| ADR-0026 V1 korunur | V1 byte/digest/golden/decode/history korunur; bütün yeni receipt'lerin v1 olacağı anlamına gelmez. V1 yeni write yasağı değişmez |
| dataset-upload-v2 tip/byte tablosu | UploadReceipt kapalı StageReceipt v1 veya CreateReceiptV2 union'ıdır. CreateReceiptV2 yalnız v2 accepted create; canonical sınırı 2 KiB, mevcut slot/reservation değişmez |
| Nonterminal tarihsel v2+v1 create | Yeni arm/renew/write/read-recovery lease/permit ve success kapalı; yalnız yerel inspection/revoke/cleanup/reset. HTTP sıfır; aşağıdaki owner/CAS marker kuralı uygulanır |
| Diğerleri | Capability/P02-R1, known negative, PID/fence/lease/clock, kalıcı intent/replay, literal-secret, storage/kota ve ayrı canlı kabul değişmez |

ADR-0026 ve kanonik v2 referansı bu eşlemeyle aynı doküman geçiş commit'inde güncellenir; yalnız genel forward link yeterli sayılmaz.

## Dar, sürümlü accepted-create receipt

CreateReceiptV2, StageReceipt v1'den ayrı strict/frozen/extra-forbid kapalı modeldir. Ayrım payload JSON schema_version ile yapılır; kapalı versioned union decode ardından operation sürümü ve intent-kind denetlenir.

| Alan | Tip / kural |
|---|---|
| schema_version | strict integer 2 |
| intent_id | canonical internal UUIDv4; mevcut create intent FK'si |
| recorded_at | canonical UTC; issuing intent zaman aralığı ve güncel commit kapısı |
| result | literal accepted |
| dataset_id | canonical provider UUID |
| object_key, sent_bytes, sent_sha256 | zorunlu null; başka anlam verilmez |
| created_dataset | mevcut kapalı ProviderDataset: id, name, modality, visibility=private, contributions_enabled=false, owner_id, zorunlu nullable org_id |

Operation.dataset_id, receipt.dataset_id ve created_dataset.id eşittir. Repository insert transaction'ında name/modality/private/false planla; **user owner'da owner_id**, **organization owner'da org_id** seçili scope owner ile eşleşir. Diğer owner alanı tahmin edilmez/null'a zorlanmaz. Name sınırı 256 UTF-8 byte, modality enum ve private/false mevcut tüketiciyle aynıdır. Full typed DTO original/restart predicate'ini birebir aynı tutmak için saklanır; ham metadata dict'i saklanmaz. Yanlış selected owner/project context hiçbir ack ile geçilmez.

Ham create HTTP gövdesi mevcut **1 MiB** kontrol yanıtı sınırındadır: strict UTF-8/JSON/depth/node ve seçili credential literal kuralı bütün raw-tree'ye uygulanır, sonra kullanılmayan metadata atılır. **2 KiB yalnız canonical encoded receipt'e uygulanır**, ham gövdeye değil. Receipt byte preflight'ı SQL insert'ten öncedir; DDL IntegrityError'a bırakılmaz. Büyük geçerli temiz raw cevap küçük receipt'e dönüşebilir. Typed receipt/bağlama geçersiz veya aşırıysa aşağıdaki post-dispatch belirsizlik kuralı uygulanır. Mevcut stage slotu/toplam payload/reservation/otomatik silmeme değişmez.

ID'ler kişiye bağlanabilir; baseline yerel özel state'te kalır, tam PII temizliği iddiası yoktur. Seçili credential literal kuralı typed payload'a da uygulanır. **Public prepare/approve/revoke/start/reconcile/show/list text/JSON/NDJSON ve hata/support çıktısı tam repository view veya receipt serialize etmez**; [DatasetUploadSummary v2](../reference/dataset-upload-v2.md#public-özet-ve-kabul) ayrı dar projeksiyondur. created_dataset ve bildirilen owner_id/org_id/name bu çıktılara girmez; mevcut public plan/resource ID'leri receipt'ten genişletilmez. Public/controller tesliminde sentinel çıktı testleri zorunludur.

## Atomiklik, yeni yazım ve geçişte alınan cevap

Accepted CreateReceiptV2 insert'i ile operation.dataset_id güncellemesi **aynı SQLite transaction/savepoint** içindedir. Yeni v2 accepted-create için v1 insert state_invalid ile reddedilir; receipt/operation business yazısı commit edilmez. Mevcut exact tarihsel satırla idempotent karşılaştırma yeni insert değildir; mevcut owner/time kapılarını aşmaz. DDL/migration/checksum 1–7 değişmez.

Upgrade öncesi arm edilmiş create cevabı yeni binary'ye ulaşırsa ancak gerçek strict create DTO'su eldeyse, aynı intent/original owner/PID erişimi ve **halen geçerli** lease/intent/credential/clock kapılarıyla CreateReceiptV2 kaydedilebilir. Kalan v1 nesne veya yalnız dataset ID full baseline'a çevrilemez; owned/name/detail ile backfill yoktur. Intent/lease bitmiş veya reset/owner değişmişse geç gelen cevap insert edilmez; yeni permit/lease/arm açılmaz. Eski çalışan binary'nin verilmiş permit'i fiziksel olarak geri çekilemez; sürümler arası eşzamanlı writer uyumluluğu iddia edilmez.

**Create denemesi başladıktan sonra** invalid/oversize receipt, sahiplik/ID uyuşmazlığı, kayıp cevap/commit veya create→detail owner_id/org_id değişimi write sonucunda operation_uncertain/5 + aynı ID üretir; yeni create/PUT yoktur. Marker yazılabilirse unknown/request_uncertain olur; owner/store kapısı engellerse unknown olduğu vaat edilmez. ADR-0026'nın ayrı readonly hata istisnası korunur; sahiplik çelişkisi success üretmez. Reddedilen receipt kalıcı intent'i kaldırmaz; invalid_response tek başına yeniden yazma önerisi olamaz.

**Commit edilmiş** accepted receipt süreç öldürülünce korunur. Provider201 ile receipt COMMIT arasındaki kill penceresinde create gerçekleşmiş olabilir; ID/baseline kaybolabilir. Bu unknown create'tir; aynı adla arama/ikinci gönderimle doldurulmaz. COMMIT cevabı kaybolunca da aynı kalıcı ID yerel show/list ile incelenir.

## Tarihsel okuma, eksik baseline ve owner/CAS

| Kayıt / işlem | Kural |
|---|---|
| V1 plan/operation + v1 receipts | Decode/history/local show/revoke ve mevcut grant'lı recovery korunur; yeni write kapalı |
| V1 plan/operation + herhangi CreateReceiptV2 | state_invalid; legacy view projeksiyonu da reddeder |
| V2 operation + accepted create v2 + diğer receipts v1 | Yeni normal graph; tam mevcut başarı kapıları geçerlidir |
| V2 operation'a **yeni** accepted create v1 insert'i | state_invalid; receipt/operation business commit'i yok |
| V2 operation + tarihsel accepted create v1 + terminal | Read/show/list/full validation tarihsel sonucu korur; yeni mutation/network terminal kapısında reddedilir |
| V2 operation + tarihsel accepted create v1 + nonterminal | **Her yeni arm/renew/write/read-recovery lease/permit ve success** HTTP öncesi kapanır; operation_uncertain/5 + aynı ID. Local inspection/revoke/cleanup/reset korunur |
| CreateReceiptV2 yanlış kind/result/ID/scope/plan | state_invalid; geçersiz yapısal kayıt |

Eksik baseline genel full validation hatası değildir. Nonterminal engelleme controller current/read GET'lerinden önce yerel inspection ile; repository arm/renew/acquire_read/yeni proof kapılarında tekrar yapılır. Henüz accepted create receipt'i bulunmayan **normal pre-create/missing-response** kayıtlar bu tarihsel-v1 özel durumuyla karıştırılmaz; mevcut predecessor/unknown/recovery kapıları korunur.

| Marker aktörü ve güncel durum | Kalıcı sonuç ve güvenli hata |
|---|---|
| Aynı geçerli owner/lease ve mevcut PID/write access (write owner ise) | Owner/fence/CAS/clock kapısıyla unknown/request_uncertain yazılabilir; lease yenilenmez, yeni hak yoktur |
| Lease yok/süresi bitmiş veya mevcut cleanup'ın izin verdiği epoch değişimi | Mevcut execution izni üretmeyen local cleanup CAS/fence yolu unknown/request_uncertain yazabilir; yeni read/write lease yoktur |
| Başka etkin owner veya marker owner/store/clock/busy/CAS reddi | Lease devralınmaz; business kayıt eski durumda kalabilir. operation_uncertain/5 + aynı ID/kapalı reason_code; unknown yazıldı iddiası yoktur |
| Yarışta terminal olmuş kayıt | Terminal geçmiş bozulmaz/düşürülmez; mutation/remote etki yoktur. Mevcut terminal giriş kapısı operation_conflict/2'dir |

Marker best-effort olsa da **HTTP/permit/attempt sıfır** zorunludur. Commit sonrası final gate hatasında marker zaten yazılmış olabilir. Aynı unknown marker coalesce edilir; reset/revoke yeni gönderim hakkı üretmez. Eski binary v2 receipt'i state_invalid ile reddeder; rewrite/downgrade yoktur.

## Karşılaştırma ve katman sorumluluğu

Original-writer/restart detail karşılaştırması aynı immutable created_dataset'i expected alır: ID/name/modality/private/contributions ve **iki owner alanı** eşittir. Reset/credential rotation baseline'ı değiştirmez; current read scope aynı eski kaynağı okur, historical admission scope'u mutate edilmez. Metadata auth grant veya indirilmiş byte hash'i değildir.

| Katman | Sorumluluk |
|---|---|
| Union decode/validate_graph/full validation | Yapısal kind/version/ID/plan eşliği; v1+v2 ret. Tarihsel v2+v1 create decode/terminal kabulü korunur; koşulsuz yeni success şartı buraya konmaz |
| Receipt insert transaction | Yeni v2 accepted create yalnız CreateReceiptV2; full DTO/selected owner/plan/ID/literal/2 KiB preflight, atomik dataset ID |
| Controller pre-read/pre-arm ve repository mutation girişleri | Legacy nonterminal+accepted v1'i HTTP/permit/yeni lease öncesi durdur; owner/CAS marker tablosu |
| Yeni proof commit | Tam 2+3N accepted graph'a ek CreateReceiptV2 varlığı ve plan/scope bağı; producer full detail-baseline eşliğini doğrular. Tarihsel terminal proof yeniden üretilmez |
| Public renderer/API projeksiyonu | Dar summary; internal receipt/view/created_dataset dışarı çıkmaz |

TransferVerification v2/control v2 byte/digest değişmez. Public caller raw proof/producer/baseline enjekte edemez. Hot/full/reset/backup/quota union'ı tanır; eski golden'lar ayrı tarihsel kalır.

## Alternatifler ve sonuçlar

Selected-owner-only eşliği, güncel owned/detail'den baseline, eski receipt/request digest alanının aşırı yüklenmesi ve yeni tablo/migration seçilmedi. İlk ikisi tarihsel predicate'i daraltır/üretmez; diğerleri wire/rezerv sınırını gereksiz değiştirir. Full dar DTO original/restart predicate'inin aynı kalması içindir. Yetki/fiyat unknown, ayrı native/kurulum/CI/live ve otomatik silmeme değişmez.

## Onay sonrası doküman geçişi ve kod planı

**Doküman geçişi** tek commit/review paketinde eşlemeyi ADR-0026'ya; dataset-upload-v2 tip/byte/graph/gate/public projeksiyona; dataset-transfer receipt/union ve provider create/detail sınırına işler. O preparation/current, sonraki controller kartı, plan/current/faz, karar/ref indeksleri ve research readiness/validation hizalanır. Karar Accepted'dır; uygulama durumu P02-2p kartındadır ve kararın benimsenmesi runtime/live kabulü değildir. Kullanıcının review yanıtı bu geçişi ve bağımlı uygulamayı yetkilendirir; yeni canlı write yetkisi değildir.

**Kod** iki ayrı commit/review dilimidir: (1) DTO/union/golden/yapısal geçmiş ve bakım/capacity; (2) yeni receipt writer, legacy baseline pre-arm/read/lease/proof gate'leri, atomik/yarış/kill kabulü. Her dilim iki fresh tur/fix ile kapanır. Controller/public projeksiyon ve native/kurulum/source CI/ayrı live kabulü sonraki bütünleşik teslimdir.

Kabul: literal v1/v2 canonical golden/diğer v1 byte eşliği; gerçek modelle Unicode/escape azami receipt/2 KiB; **2 KiB üstü ama 1 MiB içi geçerli temiz raw create → küçük receipt** ve aşırı/geçersiz typed receipt ayrı testi; new v2+new accepted v1 zero-business-commit; v1+v2 mixed-kind/version/result ret; operation/receipt/DTO ID üçlü eşliği; user-owned org_id null/non-null ve org-owned owner_id; name/modality/private/owner/literal negatifleri. Terminal v2+v1 golden/full validation korunur. Legacy nonterminal her arm/renew/acquire-read/proof öncesinde sıfır HTTP/permit/new lease; başka etkin owner, expired lease, reddedilen marker/CAS ve terminal yarışları. Receipt+ID atomikliği; provider201/COMMIT öncesi ve sonrası kill, commit cevabı kaybı, intent expiry sonrası geç cevap; replay yok. Original/restart detail'de selected owner sabitken diğer owner değişimi success'i engeller; reset/rotation baseline immutable. Public API/CLI/text/JSON/NDJSON/error sentinel'ları receipt alanlarını yayımlamaz. Backup/quota/reset/unknown-version/old-binary ve değişmeyen rezerv testleri zorunludur.
