# ADR-0026: Doğrulanmamış transfer denemesinde açık politika ve onay

**Durum:** Proposed — kullanıcı review bulguları kapandıktan sonra Accepted yapıp uygulamayı sürdürmeyi koşullu yetkilendirdi; revizyonun iki fresh turu henüz kapanmadı. **Tarih:** 2026-11-02. **İş:** P02-2a/b/c. [ADR-0024](0024-durable-dataset-transfers.md), [ADR-0025](0025-isolated-storage-streaming.md), [v2 kanonik sözleşme](../reference/dataset-upload-v2.md), [paket planı](../roadmap/p02-2-delivery-plan.md).

## Bağlam

[Canlı gözlemler](../research/p02-2-private-create-observations.md) bir private create 201, yanlış ID-detail GET 405 ve ayrı username/slug detail/my-role okumalarında 200/upload etiketi gösterdi. Link/presign/PUT/confirm yapılmadı. Bunlar genel yetki, principal veya fiyat garantisi değildir. Küçük deneme/200 CR aşımı izni varsayılan ürün politikası onayı sayılmaz.

Verified-only yol complete pre-authority/cost oracle yoksa draft kalır. Fixture/role→grant veya unknown→0 çözüm değildir. Kullanıcı review'si v1 cost'un aynı scope'ta farklı manifest/boyut/storage/ücret dönemini ayıramadığını doğruladı. Yeni karar explicit alternatif yanında bu maliyet kapsamını da kapatır.

## Karar

### ADR-0024 kısmi değişiklik eşlemesi

| Hüküm | Değişiklik ve korunan sınır |
|---|---|
| Default authority/cost | verified_only korunur; complete gerçek kanıt ve prepared gerekir |
| Explicit alternatif | yalnız explicit_attempt, digest-bound insan ack ve attempt_ready ile null proof denemesi; prepared/authority garantisi değildir |
| Numeric maliyet | exact-work complete UploadCostBound v2 gerekir; v1 scope-only tutar yeni write izni vermez |
| Current/deadline | v2 ayrı baseline/supplemental check; mevcut gerçek süreler korunur, null expiry min'e girmez |
| Read | yalnız v2 explicit için scoped read-attempt; v1/default read grant korunur |
| Başarı | tam 2+3N stage grafiği, accepted receipt ve metadata proof; authority veya indirilmiş byte iddiası değildir |
| Diğerleri | Capability/P02-R1, known negative, PID/owner/fence/lease/clock, namespace/intent/permit/replay, storage/secret/kota, ayrı live/nihai kabul değişmez |

### Açık seçim, maliyet ve insan onayı

Default verified_only kalır. Explicit_attempt yalnız insanın exact owner/proje/hedef/manifest/private etkilerini onayladığı tek denemedir; provider son kararı verir. Unknown authority grant veya capability supported olmaz. Bilinen exact-action 401/403/izin reddi, wrong-owner/project/private, input/hedef değişimi hiçbir ack ile aşılamaz.

Numeric budget yalnız [complete v2 cost](../reference/dataset-upload-v2.md#işe-ve-döneme-bağlı-maliyet-kanıtı) ile açılır. Work digest scope/root/manifest/parameters/storage/request_limits/execution_window'u bağlar; producer gerçek quote kapsamını doğrulamalı veya sürümlü tarifeyi bu exact quantity/attempt/byte/period sınırlarına uygulamalıdır. Digest etiketi tek başına hesap kanıtı değildir. Bütün kategoriler+dönem ve post-period storage guarantee kapanmadıkça cost_unverified kalır. Süre bitimi silme/ücretsiz saklama değildir. Aynı scope başka manifest veya yalnız transfer için bound numeric hazırlığı geçemez.

Unpriced yalnız explicit_attempt'ta, budget_micros=null ve kullanıcı CR tavanı olmadan seçilir. Kısmi bound yalnız kapsadığı kategori/dönem için gösterilir; kalan ve süreğen storage unknown görünür. Complete bound varsa gerçek kapsamıyla gösterilir; kullanıcı sayısal tavan seçtiği iddia edilmez. **Her unpriced seçimde**, quote complete olsa bile, approval-time acknowledge_unpriced_cost=true zorunludur. İlk gözlenen profilde complete pricing source yoktur; fake bound üretilmez.

Budget/unpriced ikisi birlikte veya ikisi de yok, verified_only+unpriced ve gereksiz true approval flag invalid_request/2'dir. Gerekli ack eksikse approval_required/4. Config/env risk flag'i üretmez. V2 approval hem admission_policy hem cost_policy ve exact plan/binding digest'ine bağlıdır.

### Kesin reducer ve işlem kapıları

[V2 reducer ve 96 literal durum](../reference/dataset-upload-v2.md#kesin-v2-reducer-ve-tam-matris) normatiftir; V1 helper/invariant v2'ye uygulanmaz veya gevşetilmez. Risks kanıt boşluğu, blockers seçilmiş policy engelidir; değerler kesişebilir. Explicit_attempt'ta input/cost kapıları geçince authority_unverified yalnız risk kalır. Inputs_unverified her policy'de blocker'dır. Numeric cost eksik/kısmi/over-budget iken attempt_ready açılamaz. Blocker varsa draft; blockers boş+bounded+risks boş ise prepared; diğer legal explicit durumlar attempt_ready. Unpriced+tam kanıt risks/blockers boş olsa da attempt_ready'dir.

Approve/admit/arm prepared veya yalnız v2 explicit attempt_ready kabul eder; draft upload_plan_not_valid/2. [Gate tablosu](../reference/dataset-upload-v2.md#işlem-kapıları-ve-current-kanıt) ack/type/scope/expiry/owner ve hata/exit'i kesinleştirir. Existing admit yalnız aynı yerel kaydı döndürür; yeni check/lease/claim/attempt yoktur. V1'in eksik maliyet kanıtıyla yeni approve/admit/arm kapalıdır.

Fresh pozitif için **seçenek A**: saved plan/approval/status/risks/binding immutable; ayrı UploadCurrentCheck baseline ve supplemental kanıt taşır. Null/partial için yeni tam ek kanıt gate'i daraltabilir, historical özeti yükseltmez. Saved nonnull semantic değişimi/expiry veya current ret/failure kapanıştır. Port deadline yalnız var olan total/plan/approval/lease/grant/cost/request/URL terimlerini kullanır; null assert/sahte expiry yoktur. 5 s sonuç payı, 900/150/120 s ve intent COMMIT sonrası geri alınamayan pencere korunur.

### Profil, HTTP ve read/metadata sonucu

[Kayıtlı evren-platform-observed-upload-v2/policy_version=2](../reference/dataset-upload-v2.md#tüketici-profili-http-ve-my-role), AuthorizationCheck'in allowed/not_exposed/denied/unavailable/invalid sınıflarını, action/scope/tazelik ve tam HTTP/my-role şemasını tanımlar. Not_exposed yalnız önceden kayıtlı oracle yokluğudur; 404/405/429/5xx/timeout/malformed cevap buna dönüşmez. Zorunlu current context/my-role başarısızlığı sıfır yeni arm'dır; upload etiketi grant değildir. Profil P02-R1'in verified principal kapısı değildir.

[Read aktör/flag/grant matrisi](../reference/dataset-upload-v2.md#read-terminal-ve-başarı-grafiği) initial-owner ve restart ayrımını kapatır. Yalnız v2 explicit, uygun onay/current read fallback seçimiyle aynı kaydı okuyabilir; yeni write hakkı yoktur. Verification scope gözlem anındaki current scope'tur; historical admission/approval mutate edilmez. Terminal kayıt network/lease öncesi operation_conflict/2 ile reddedilir; read failure onu unknown'a düşürmez.

Ayrı readonly reconcile 401/403→remote_access_denied/3, 429/5xx/transport→ilgili mevcut kod/1, malformed/404/405→invalid_response/1; operation ID korunur. Latched nonterminal read failure unknown/read_unavailable'dır, execution failure değildir. Bu sıfır-write çağrı genel exit-5 önceliğinin açık istisnasıdır; aktif write coordinator teslimi kesinleştiremezse operation_uncertain/5 önceliği sürer.

Success **tam graph** ister: create+project_link ve her i=0..N−1 için presign/PUT/confirm, tam 2+3N intent, hepsinin tek accepted receipt'i, chronology ve tam ordered metadata. Eksik intent fakat mevcut bütün receipt'ler accepted+metadata eş ise sonuç unknown'dır. Kayıp create ID/receipt read ile yeniden üretilmez. Metadata/read authority'yi yükseltmez; remote_bytes_verified=false kalır.

### Sürümleme ve geçiş

[Kapalı tip kataloğu](../reference/dataset-upload-v2.md#kapalı-tipler-ve-sürümler) plan/cost/approval/record/control/verification ve [public summary](../reference/dataset-upload-v2.md#public-özet-ve-kabul) v2'yi tanımlar. V1 byte/digest/golden/decode/history/local show/revoke ve güvenli recovery korunur. **Maliyet P1 düzeltmesinin açık istisnası:** scope-only v1 cost yeni write vermez; historical prepared writable değildir. V1 quote/plan'a varsayılan v2 alanları eklenmez, belirsiz iş v2'ye çevrilip arm edilmez.

DDL/checksum 1–7 değişmez; ayrım payload JSON schema_version'ıdır, ayrı SQL version kolonu değildir. V2 operation/approval/control/proof eşleşir; stage/receipt/lease v1 biçimi korunur. Metadata_verified yalnız succeeded/terminal+nonnull v2 proof digest; read_unavailable yalnız unknown/recovery+null; diğer non-success digest null. İki slot/coalescing/reset/takeover ve byte/gerçek rezerv sınırları korunur. Eski binary kontrollü ret verir; rewrite/downgrade yoktur.

## Onay sonrası akış ve kabul

Bu review düzeltmesi iki fresh turla kapanınca kullanıcının koşullu talimatıyla Accepted yapılır; aynı karar yeniden onaya sorulmaz. Önce v2 domain/cost/reducer/golden, sonra union journal/current/arm/read/reset ve tam graph, sonra producer/codec ve ortak CLI/Python; her kod dilimi commit+iki fresh tur+doğrulanmış fix döngüsüdür.

Geçiş: ADR-0024 partial amendment; karar/ref indeksleri; dataset-transfer v1 status/onay/current/journal/verified bölümlerinin v2 karşılığı; phase-02/current/plan; P02-2a/b/c ve dar v2 kartlar; capability matrix. [Kabul listesi](../reference/dataset-upload-v2.md#public-özet-ve-kabul) 96 literal reducer satırı, exact-work/period/storage negatifleri, bütün v2 DTO/golden/digest, fresh positive matrix'i, gate/ack/error/read/terminal, eksik graph, control/slot/coalescing/mixed version/reset/takeover ve rezerv tavanlarını kapsar. Tarihsel başarı freshness nedeniyle ertesi gün bozulmaz.

Provider wire, aynı hash/farklı ad, secret/signed-target/byte ayrımı, son kaynak native/kurulum/CI ve ayrı somut live kabul kaldırılmaz. Durmuş research workflow'ı yeni write permit almaz. Bu karar yeni canlı write'a otomatik yetki değildir; sınırsız dataset/harcama çıkarılmaz. Tek nihai P02-2 PR'ı paket tamamlanınca açılır.

## Alternatifler ve sonuç

Yalnız verified_only güvenli mevcut seçenektir fakat provider oracle bekler. Fixture/role→grant/unknown→0 yanlış kanıttır; default unknown veya tek force flag bilinmeyen harcamayı gizler; hesap hardcode'u ortak sözleşmeyi bozar. Açık alternatif bunları seçmez. Sonuç insanın dar bir denemeye izin vermesidir; remote exactly-once, permission guarantee, spending cap veya etkili restart/resume değildir.
