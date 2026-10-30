# P02-0a — Sözleşme, SDK ve pilot araştırması

**Tarih:** 2026-10-31 Europe/Istanbul. **Taban:** `9c4db010d60fef39f5e5971a617535e8f6a56b6c`, development `bc9532c`; dal `feat/p02-0a-sdk-pilot`. **Durum:** P02-0a araştırma kabulü iki fresh review ve düzeltmelerle verified; ürün uygulaması ve canlı hesap kabulü değildir. [Paket planı](../roadmap/p02-0-delivery-plan.md), [araştırma kartı](../roadmap/tasks/p02-0a-contract-sdk-pilot.md) ve [Accepted ADR-0020](../decisions/0020-service-bound-context-discovery.md) birlikte okunur.

## Yöntem ve kaynak sınırı

Ana inceleme mevcut domain/application/HTTP/session/credential/cache/CLI yüzeyini ve bağlı belgeleri karşılaştırdı. İki bağımsız araştırma ajanı sırasıyla sabit SDK kaynağını ve resmî Platform/LLM yayınlarını inceledi; sonuçlar ana incelemede kaynakla tekrar karşılaştırıldı. Bunlar commit sonrası iki fresh review turunun yerine geçmez; o turlar [teslim kaydına](p02-0-implementation-validation.md) yazılır.

Kamu kaynaklarına credentialsız HTTPS GET yapıldı. Web okuyucusu EVREN guide/OpenAPI adreslerini açamadı; sınırlı Python HTTPS indirmesiyle kaynaklar alındı. JavaScript metin olarak incelendi; SDK wheel’i yalnız arşiv/metin olarak okundu, kurulmadı/import edilmedi/çalıştırılmadı. Kullanıcı env’si, tarayıcı oturumu, özel arşiv ve gerçek hesap kullanılmadı. Büyük HTML/JS/wheel kopyaları repoya eklenmedi. Kaynak kimlikleri [kanıt kaydındadır](evidence-register.md#p02-0a-kaynak-sabitlemesi--31-ekim-2026); hash imza veya sunucu garantisi değildir.

Kanıt etiketleri: **G** yayımlanmış kılavuz; **W** yayımlanmış web istemcisi; **O** OpenAPI; **S** sabit SDK kaynağı. Hepsi doküman/istemci kanıtıdır, `live_account` değildir. `unknown` alanı boş dizi, sıfır limit veya destek yokluğu diye yorumlanmaz. Platform’ın denenen `/docs`, `/api/v1/docs`, `/api/v1/openapi.json` adresleri 404 döndü; başka şema bulunamayacağı sonucu çıkarılmaz.

## P02-0 için belirleyici bulgular

1. Platform’ın `https://api.ssyz.org.tr/api/v1` kökü ve `X-API-Key` kullanımı G/S’de var. W’de `/auth/me`, `/organizations`, `/projects` çağrıları **tarayıcı Bearer oturumuyla** yapılıyor. Bu üç ucun API key kabulü, tam yanıt şeması ve izin semantiği doğrulanmış değil. Browser JWT’ye gizli fallback eklenemez.
2. LLM’nin `https://evren-llmapi.ssyz.org.tr/v1` kökünde O toplam 33 path içeriyor; hesap/me/organizasyon/proje introspection yolu yok. W hem X-API-Key hem Bearer örneği veriyor; S Bearer kullanıyor. Modelin `owned_by` alanı kullanıcının hesap ID’si değildir; quota ve terms sonucu da hesap ID’si üretmez. P02-0b LLM kolu bu eksikliği açık göstermeli.
3. `Context` v1 `remote_verified=false` ve tek account/project tercihi taşır. Onu yerinde “doğrulanmış context”e çevirmek eski JSON/Plan anlamını değiştirir. Yeni, hizmete bağlı gözlem sonucu gerekir; profil tercihi ile gözlenen kimlik ayrı tutulur. Karar kullanıcı review düzeltmeleri sonrası ADR-0020 ile benimsendi; uygulama/canlı kabulü ayrıdır.
4. SDK kimlik/org/proje keşfi sunmuyor; istemcileri P01 taşıma politikasını karşılamıyor. P02 için ortak HTTP üstünde bağımsız normalizasyon öneriliyor; bu araştırma SDK’yı core’a eklemiyor veya tüm olası kullanımlarını yasaklamıyor.

## İlk tüketici endpoint matrisi

Path’ler aşağıda **wire path**’tir. Uygulamada Platform hedef kökü `/api/v1`, LLM kökü `/v1` zaten vardır; `HttpRequest.endpoint` başında slash veya ikinci `/v1` bulunmaz. Her satırın seçimi gereken hizmetle sınırlıdır; bir hizmetin kapalı erişimi diğerini bekletmez.

### Kimlik, organizasyon ve proje

| İş / kaynak | Method + wire path | Girdi / yanıt gözlemi | Yetki, limit ve açılma koşulu |
|---|---|---|---|
| Platform kimlik / W main | GET `/api/v1/auth/me` | İstemci organization_id/personal_org_id/role ve kullanıcı sunum alanlarını tüketiyor; kapalı principal-ID şeması yok | Browser Bearer kanıtı; API key kabulü ve principal alanı `unknown`. Sağlayıcı sözleşmesi veya yetkili salt okuma pilotuyla kapatılmalı |
| Organizasyon / W OrgPage | GET `/api/v1/organizations` | Dizi veya items; id/name/slug ve üyelik görünümü | API key, pagination ve role→izin eşlemesi `unknown`; liste görünürlüğü yazma izni değildir |
| Proje / W useProject | GET `/api/v1/projects` | Dizi; UUID id/owner_id, nullable org_id, name/slug/visibility | API key/pagination/tamlık `unknown`; ilk UUID otomatik seçilmez |
| Seçilen proje / W useProject | GET `/api/v1/projects/{id}` | Yukarıdaki bağlar, ek settings/updated_at | Readability yalnız bu kaynağın okunabildiğini gösterir; upload yetkisi çıkarılmaz |
| LLM önkoşul / O + W catalog | GET `/v1/terms/status` | current_version:int, is_material:bool, doc_path:string, accepted:bool | Key sahibi için şart durumu; account/org/project alanı yok. POST accept çağrılmaz; doc_path takip edilmez |

Platform envelope adaptasyonu endpoint bazlı olmalıdır. Main helper `success/data` sarmalamasını açıyor; Yörünge `success=false` cevabını `error` alanı bulunmasa da başarı saymamalı. Direct/envelope alternatifleri ancak sabit fixture ve tanımlı anahtarlarla kabul edilir; bütün yanıtlarda sezgisel unwrap yapılmaz. 2xx veya boş liste kendi başına bağlam/izin kanıtı değildir. Kapalı raw kimlik şeması bulunmadan “provider identity verified” uygulaması ready olmaz.

### Normal dosya, sürüm, katalog ve kaynak okumaları

| İş / kaynak | Method + wire path | Minimum veri / pagination | Kalan sözleşme ve replay sınırı |
|---|---|---|---|
| Veri listesi / W datasetApi | GET `/api/v1/datasets` | page/page_size; X-Total-Count/X-Has-Next; istemcide uzunluk fallback’i | Snapshot, eksik header ve tamlık `unknown`; tahmin edilen son sayfa kesin tamlık değildir |
| Veri referansı / W datasetApi | GET `/api/v1/datasets/{owner}/{slug}` | id, owner_id, org_id, modality, visibility, item_count | Güncellenen metadata immutable revision değildir |
| Private create / G | POST `/api/v1/datasets` | name/modality/visibility/license/tags; private açık | Correlation/idempotency/search-by-request `unknown`; kayıp cevapta ikinci create yok |
| Dosya listesi / G + W | GET `/api/v1/datasets/{id}/items` | limit≤200, cursor; items/next_cursor/total; öğede id,filename,size,nullable sha256_hash | Sıra/snapshot/cursor ömrü ve hash anlamı `unknown` |
| Presign / G + S | POST `/api/v1/datasets/{id}/upload/presign` | files: filename/sha256_hash/file_size; presigned_urls/items/duplicates | Dedup aynı içerikte farklı adları düşürebilir; cardinality ayrıca doğrulanmalı; replay `unknown` |
| Upload / G + S | PUT dönen upload_url | Byte gövde; object_key ile confirm’e bağlanır | G MinIO anlatımı ile relative API-proxy + key örneği çelişiyor. Host/auth/expiry `unknown`; key rastgele URL’ye gönderilmez |
| Confirm / G + S | POST `/api/v1/datasets/{id}/upload/confirm` | items: object_key/sha256_hash/filename/file_size | Atomicity/replay/kalıcı öğe eşliği `unknown`; sadece 200/201 yeterli değil |
| Sürüm/split / G | GET `/api/v1/datasets/{id}/versions`, `/{version}`, `/{version}/splits` | Sürüm ve train/val/test metadata’sı | Create/freeze etkisi ayrı; byte/split değişmezliği ve freeze digest’i `unknown` |
| Tek öğe indirme / W | GET öğenin file_url hedefi | original_filename,file_size_bytes,nullable sha256_hash | Range/ETag/expiry/auth/byte doğrulama `unknown`; metadata eşliği içerik ispatı değil |
| Model list/detail/version / W + S | GET `/api/v1/models`, `/{owner}/{slug}`, `/{id}/versions` | Liste page/page_size/filtreler; sürüm id/tag, weights metadata | SDK list limit’i ve web pagination aynı garanti değil; sürüm byte hash’i/izinleri ayrıca |
| Ağırlık hedefi / S client | GET `/api/v1/models/versions/{vid}/download?format=...` | download_url, opsiyonel filename | Redirect/storage policy, lisans, boyut/hash/resume ayrı indirme kabulü |
| GPU / W useGpuStatus | GET `/api/v1/public/infrastructure/gpu-status` | Kamu envanter metadata’sı | Tahsis/hesap entitlement değil; TTL ve alanlar tüketici kartında |
| Takvim / W useReservation | GET `/api/v1/public/reservations/calendar?from=&to=` | Bounded tarih aralığı | Kamu görünürlüğü; rezervasyon yaratmaz |
| Hesap rezervasyonu / W | GET `/api/v1/reservations`, `/reservations/availability?from=&to=` | page/page_size veya tarih aralığı | Key auth ve hesap kapsamı `unknown`; POST/DELETE kapsam dışı |
| Bakiye/ledger / W main | GET `/api/v1/billing/balance?org_id=...`, `/billing/ledger` | org_id; limit/offset/tx_type | Key auth, decimal/bakiye kaynağı/paging `unknown`; finansal otorite uydurulmaz |

G’deki **500 MB/dosya** sağlayıcı UI bilgisidir; Yörünge kabul sınırı veya ölçülmüş limit değildir. Dataset **ZIP export** ayrı hazırlama ve belgelenen ücret içerir; normal dosya indirme yerine gizlice seçilmez. GET ismi maliyetsiz/saf okuma kanıtı değildir. Yeni salt okuma whitelist’ine export eklenmez. G’nin paralel upload önerisi P01’in 2 worker sınırını değiştirmez.

### Aşama bazında etki ve kayıp cevap

Aşağıdaki güvenli durma koşulları mevcut tek-gönderim sınırını korur; gelecekteki transfer tasarımının veya replay mekanizmasının onayı değildir. Sağlayıcının garanti etmediği korelasyon/gözlem yöntemi `unknown` kalır; dosya adı veya hash tek başına bu çağrının etkisini kanıtlamaz.

| Aşama / olası uzak etki | Cevap kaybında kalan kimlik | Salt okunur gözlem / bilinmeyen | Güvenli sınır ve açılma sahibi |
|---|---|---|---|
| Create / yeni private dataset oluşmuş olabilir | Yerel plan/operation/dispatch bağı; provider dataset ID cevap yoksa bilinmeyebilir | Request-correlation ile exact dataset bulma `unknown`; ada göre ilk eşleşme kabul değil | Yeni create yok; unknown + mevcut operation korunur. P02-2a correlation/read oracle, P02-2c ilk kesinti kabulü |
| Presign / upload yetkisi veya geçici nesne kaydı ayrılmış olabilir | Bilinen dataset ID ve gönderilen file identity/hash/size; URL/object_key cevap kaybında bilinmeyebilir | Bu istekten doğan yetki/nesneyi exact listeleme ve presign replay garantisi `unknown` | Kör presign/PUT yok; tek bir yeniden izin üretimi bile garantiye bağlı. P02-2a/b faz bağı; P02-2c güvenli durma |
| PUT / nesne hiç, kısmen veya tamamen yazılmış olabilir | Önceden alınmış dataset/object_key ve yerel file identity/hash/size; signed URL loga/payload’a yazılmaz | Yetkili status/HEAD/GET ve size/hash eşliği imkânı `unknown`; ETag=SHA varsayılmaz | Metadata veya 2xx yokluğundan yeni PUT/confirm çıkarılmaz. P02-2b exact doğrulama oracle’ı; P02-2c aynı ID ile read-only uzlaştırma |
| Confirm / üyelik oluşturulmuş veya dedup uygulanmış olabilir | Bilinen dataset/object_key/file identity/hash/size ve operation fazı | Items listesinden bütün ad/ID/adet/byte bağını doğrulama adaydır; atomiklik ve request-correlation `unknown` | Yeni confirm/create/PUT yok; eksik/çelişkili/çoklu eşleşme unknown kalır. P02-2c ilk uzlaştırma; P02-3a yalnız kanıtlı eksik aşama devamı |

Signed/proxy hedefin scheme/host/port/path/query, allowed header, expiry ve yenileme anlamları henüz kapalı değildir. Query yetki değeri sırdır; Platform/LLM credential’ı hedefe miras verilmez. P01 HTTPS/443 kuralının yeni storage hedeflerine nasıl uygulanacağı veya genişleyeceği yalnız ilgili güven sınırı ADR’sinde seçilir. Range/ETag/checksum/version sözleşmesi olmadan güvenli resume garantisi yoktur.

### Native çıkarım ve gözlem

| İş / kaynak | Method + wire path | Minimum alanlar ve yanıt | Belirsizlik / kabul sahibi |
|---|---|---|---|
| LLM katalog / O | GET `/v1/models`, `/v1/models/{model_id}` | ModelListResponse data; ModelInfo id/created/task, modalities/pricing/context_length/default_max_output_tokens/capabilities/precision | İzinli model görünümü inference başarısı değil; immutable revision yok, alias pin sayılmaz; P02-4a |
| Chat / O + S llm_types | POST `/v1/chat/completions` | model/messages; stream=false, açık max_tokens, evren_tools=false. S choices/message/content/reasoning/tool_calls/usage/id tüketiyor | O 200 response `{}`; kapalı çıktı/usage/request-ID oracle P02-5a’da. Gömülü hata/boş choices success değil; ücretli tek deneme |
| SSE / O + S llm_sse | POST aynı yol stream=true | data JSON delta.content/reasoning, finish_reason/usage; `[DONE]` istemci kanıtı | SSE framing, usage sonu, EOF/trailing kuralı tam sağlayıcı sözleşmesi değil; P02-5b. P01 NDJSON decoder’ı SSE değildir |
| Embedding / O + S | POST `/v1/embeddings` | model/input string veya string[]; S data[index,embedding] | O response `{}`; sayım/sıra/dimension/finite/model/usage bağımsız oracle P02-5c; SDK sort eksik indeksi doğrulamaz |
| Rerank / O + S | POST `/v1/rerank` | model/query/documents; top_n S’de opsiyonel; S results[index,relevance_score] | O top_n/closed response tanımlamıyor; index/top-n/finite/usage P02-5d; OpenAI chat biçimine zorlanmaz |
| Vision / G + S client | POST `/api/v1/inference/predict` multipart | file, model_version_id, confidence_threshold/iou_threshold/image_size; predictions ve task-specific alanlar | Bounded multipart, model görevi/yanıt/price/usage P02-5e; P01 bytes portu genel stream multipart değil |
| LLM kota / O | GET `/v1/quota?model=...` | held_cr/remaining_cr decimal string; nullable token/window/daily/concurrency/model/fair-share alanları | Account ID değil; null sıfır değildir; UTC daily ile sliding window ayrı, bütün key’ler ortak olabilir; P02-6b |
| Uzak istek durumu / O | GET `/v1/requests/{request_id}` | UUID request_id, execution_terminal, charge_terminal, is_billing_pending, decimal tahsilat, state_version | Yalnız metadata; response replay yok. Kimlik/operation bağı ve bilinen durum kataloğu ilk tüketicide; unknown durum success olmaz |

LLM OpenAPI’de securitySchemes yokluğu anonim erişim anlamına gelmez. 401/403 yetki/terms nedeni olabilir; Platform geneli unsupported olmaz. W katalogda 429 için concurrency/fair-share/request/token/daily-limit nedenleri ve 503 capacity örnekleri var; 402’nin kapalı şeması bulunmadı. Normalizer kapalı yerel hata kataloğunu kullanır; ham provider mesajını yansıtmaz. Provider önerse de inference POST/SSE otomatik tekrarlanmaz. Usage bilinmiyorsa sıfır ücret değildir; seçilen model/istek kimliği ve kullanımın doğruluk düzeyi korunur.

## Sabit SDK değerlendirmesi / B03

PyPI **0.11.0** wheel hash’i doğrulandı; sdist hash’i yalnız metadata’dan alındı, sdist indirilmedi/build edilmedi. Git `v0.11.0` etiketi `f4eaa4a71f324e61058f24fb90c0aec7a58ae24f` commit’ine gidiyor; incelenen sekiz Python dosyası wheel ile byte-byte aynı. Apache-2.0 lisans metni wheel’de var. Python≥3.10; temel bağımlılık `httpx>=0.27`, image/edge extra’ları ayrı. SDK’nın hafif oluşu politika uyumunu tek başına sağlamaz.

| Sınır / sabit kaynak | Doğrulanan davranış | P02 önerisi |
|---|---|---|
| [llm_client.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_client.py#L47) | Eksik key/base_url için implicit env fallback; kendi HTTPX client’ı; LLM timeout 600/connect 10; varsayılan 2 retry | Tek env snapshot/hedef/total deadline için ortak HTTP |
| [llm_retry.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_retry.py#L20) ve llm_client 115–182 | Retry loop/POST idempotency header ve stream pre-send retry var; sunucudaki kapsam/TTL/payload garantisi bu kodla kanıtlanmıyor | ADR-0017 read-only max2/effectful1 korunur; SDK retry sahibi olmaz |
| [client.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/client.py#L304) ve [llm_async_client.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_async_client.py#L48) | Bağımsız client/config; trust_env kapatma, cookie reddi, owned log filtresi ve P01 PID/task kapısı yok. Default redirect takip edilmiyor; normal context cleanup var | “SDK kesin leak yapar/redirect açar” denmedi; ortak session’dan bağımsız client kullanılmaz |
| client 307/619, 499/790; llm_client 106–113 / llm_async_client 48–55 | Platform sync/async `verify=True` parametresi False yapılabilir; ana ve dış download client’ına aktarılır. LLM verify belirtmez; [HTTPX varsayılanı](https://www.python-httpx.org/api/) TLS doğrulamasıdır | SDK varsayılanının TLS’i kapattığı iddia edilmez. Yörünge TLS doğrulamasını açık tutar; public verify=False yolu eklenmez, env CA/proxy davranışı da P01 policy’sinde kalır |
| [llm_sse.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_sse.py#L18) | Replace decode, sınırsız buffer/lax JSON, malformed kayıt atlama ve DONE ile EOF öncesi dönüş | Bağımsız bounded SSE codec; copied parser yok |
| client 115–120, 542–592 | Dosya tümden okunuyor; presign sonrası dönen URL aynı credentialed client ile PUT ediliyor | Stream upload/target policy/journal ayrıca; bu ağ adaptörü kullanılmaz |
| client 239–275, 479–501 | Download aynı host karşılaştırması yalnız hostname; hedef `wb` açılıyor, hash/no-clobber/Range oracle yok | Ortak güvenli indirme tüketicisi |
| [llm_types.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_types.py#L101) / [llm_tasks.py](https://github.com/speker/evren-sdk/blob/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f/evren_sdk/llm_tasks.py#L196) | Permissive normalizasyon; model limit/capability/precision ve kota concurrency alanları kaybolabiliyor; eksik credit 0’a dönebiliyor | Göreve özel strict bağımsız model; bilinmeyen veri korunur, sahte chat/0 varsayılmaz |

SDK’da account/org/project, private dataset create, dataset version/download/freeze veya Platform GPU/ledger public metodu bulunmadı. Chat/embed/rerank/vision/catalog/upload/download/kota için yukarıdaki wire bilgisinden yararlanılabilir; **bu P02 paketinde bütün seçilen endpoint’ler için öneri ortak taşıma + bağımsız codec/normalizer’dır**. Salt codec import’u bile SDK ağ/env bağımlılığını ve permissive sonuçlarını getireceği için önerilmiyor. Kod kopyalanmadı; gelecekte yeniden kullanım seçilirse lisans/NOTICE ayrı incelenir. B03 araştırma çıktısı hazır; bu tüketici önerisi kullanıcı review düzeltmeleri sonrası Accepted ADR-0020 kapsamında benimsendi; diğer P02 endpoint’leri kendi tüketici kabulüne bağlıdır.

## B04 ve sonraki kararların açılma koşulu

| Karar / sahip | Araştırma sonucu | Uygulama öncesi gereken |
|---|---|---|
| Hizmete bağlı discovery / P02-0b | İki ayrı auth/kimlik yüzeyi; principal/izin boşluğu var | Accepted ADR-0020 + [kapalı discovery referansı](../reference/context-discovery.md); Platform key endpoint/şema teyidi, yetkili canlı read kabulü |
| Depolama hedefi / P02-2b, 3b | Signed MinIO/proxy çelişkisi, expiry/host/Range/ETag unknown | Gerçek hedef sınıfları ve credential ayrımı için yeni Proposed ADR; bugünden key forwarding veya port gevşetme yok |
| Aşamalı operation / P02-2a | Create/presign/PUT/confirm çok aşamalı; idempotency/correlation unknown | Kalıcı faz/kimlik/lost-answer gözlem kararı, kapasite/plan/approval modeli; dispatch latch bypass yok |
| Veri boyutu/manifest / P02-1/2 | UI limiti mevcut P01 input/request bütçesiyle aynı kavram değil | Normal dosya sayısı/byte/manifest bağı ve job/request/validation deadline kartı; sınır değişiyorsa ADR |
| Native çıktı/SSE / P02-5 | Response şemaları kısmi, SDK parser’ı kabul oracle’ı değil | Bağımsız response fixture, request-ID/usage/terminal eşlemesi; gerekiyorsa yeni karar, SSE kabulü ayrı |
| Kota/price / P02-6b + pilot | Dinamik account/day/model kapsamı; sabit ücret uydurulamaz | Güncel hesap/model cevabı ve kullanıcı tavanı; eksik fiyatla ücretli pilot açılmaz |
| Eğitim durum/parametre / P03-1 | P02 araştırmasına dahil değil | B04’ün P03 kısmı açık kalır; P02’yi döngüsel bekletmez |

Bu listede sonraki epiklerin tasarımı benimsenmedi; gereksiz geniş ADR paketiyle P02-0b bekletilmiyor. Araştırmada unknown kalan alanın sahibi/açılma koşulu vardır; entegrasyon veya tüm B04 kapanmış sayılmaz.

## Küçük pilot planı — icra edilmedi

**Ortak kapı:** Pilot sahibi kullanıcı veya açıkça atadığı hesap sahibi; hesap/proje ve key **env adları** henüz bildirilmedi. Token değeri sohbet/rapor/komuta yazılmaz. Gerçek yetki ve tutar bilinmeden effectful pilot başlamaz. Aşağıdaki sayılar sağlayıcı limiti değil önerilen Yörünge pilot tavanıdır. Her satır ayrı yetkilendirilir; P02-0b yalnız ilk iki salt okuma satırının adayıdır.

| Görev / hesap ve yetki | Sentetik girdi / azami çağrı ve kaynak | Süre / maliyet kapısı | Kanıt, abort ve kalan kaynak |
|---|---|---|---|
| P02-0b Platform / seçili key sahibi; kimlik/org/proje okuma teyitli olmalı | En fazla 4 pozitif GET: me/orgs/projects/seçili project, ≤8 attempt; auth sözleşmesi eksik her endpoint/parametre kapsamında1 iyi biçimli invalid-key GET, retry0. Pilot toplam ≤8 GET/12 attempt/4 MiB | Pilot toplam30 s; istek kalan bütçe; ücretli endpoint yok, ayrıca 0 CR varsayımı yapılmaz | Strict auth/principal/ID/envelope/pagination; negatif kontrolde auth reddi yoksa bağ verified olmaz. Normal çağrıda401/403/429/redirect/unknown schema’da dur; negatif kontrolde401 veya anlamı doğrulanmış invalid-key403 kontrol oracle’ıdır; terms/permission403 yeterli değil. Uzak kaynak yok |
| P02-0b LLM / yalnız LLM key sahibi; terms status okuma | En fazla1 pozitif GET /terms/status, ≤2 attempt; explicit key-auth sözleşmesi yoksa aynı endpoint’te1 iyi biçimli invalid-key GET, retry0. Pilot toplam ≤2 GET/3 attempt/1 MiB | Pilot toplam30 s; terms accept/model warmup/inference yok | accepted/version ve exposed olmayan kimlik ayrımı; auth bağı kanıtlanamıyorsa unverified. Negatif kontrol principal ID üretmez; uzak kaynak yok |
| Katalog/kota / ilgili hizmet ve hesap okuma yetkisi | Hizmet başına ≤6 GET mantıksal, toplam ≤12 attempt/6 MiB, ≤100 satır; quota’da tek model | Toplam 30 s; export/download hazırlama yok, ücret teyidi ayrı | Model/task/price/null ve kaynak zamanı; page-loop/limit/schema değişiminde dur; uzak kaynak yok |
| Private normal dosya / kullanıcıca seçilen Platform proje sahibi ve create/upload/read izni | 2 farklı ad, aynı içerik; 1 farklı içerik; toplam 3 normal dosya ≤1 MiB. Create≤1, presign≤1, PUT≤3, confirm≤1, observe/list≤4, byte download≤3; effectful retry0 | Toplam ≤120 s önerisi, istek≤30 s; fiyat+azami CR **unknown**, teyit ve tavan olmadan kapalı | Kimlik/adet/byte SHA oracle; ilk belirsizlikte yeni effect yok. Private dataset kalır; kullanıcı sahibi. Silme ayrıca yetkili iş, otomatik cleanup yok |
| Chat/SSE/embed/rerank/vision / ilgili key ve izinli açık model | Görev başına 1 POST, retry0; chat+SSE her biri ≤256 input token hedefi/32 output token; embed2 kısa metin, rerank2 belge, vision1 sentetik görsel≤256 KiB | Görev başına≤30 s, toplam≤150 s önerisi; sayılabilir tokenizer, model, fiyat ve azami CR **unknown**, çözülmeden kapalı | Her görev typed çıktı/usage/ID, stream EOF; beklenmeyen ücret/terms/unknown’da dur. Faturalı istek metadata’sı kalabilir; uzak iptal/geri ödeme varsayılmaz |

Auth davranışı kanıtı normalize hizmet/origin/API kökü + method/endpoint + ilgili query/path parametre kapsamına bağlıdır; başka host/API kökü/endpoint/projeye taşınmaz. Yetkili auth sözleşmesi yoksa **her kullanılan endpoint** ayrı kontrol ister. Aynı doğrulanmış syntax/length/prefix içinde kriptografik rastgele üretilmiş, gerçek key’den farklı ve sağlayıcıdan alınmamış negatif kontrol kullanılır; biçim bilinmiyorsa malformed tahminiyle kapı kapanmaz. 401 tercih edilir; 403 yalnız kapalı şemada açık invalid-key nedeni ise kullanılabilir, terms/permission veya belirsiz403 auth kanıtı değildir. Pozitif strict yanıt ile iyi biçimli kontrol reddi yalnız o hedef/endpoint’in tarihli davranışını gösterir; principal ID, permission veya bütün hedeflerde kalıcı runtime otoritesi üretmez. İkisi de2xx ise auth unknown kalır. Normal discover yanlış key isteği üretmez; kontrol registry’ye yazılmaz. Pilot scope/biçim/iki status/neden/no-registry outcome kaydını tutar; secret/ham PII gövdesi tutmaz. Ayrı kontrol yetkisi/bütçesi yoksa bu uç unknown kalır. [Kanonik bütçe/kanıt kapsamı](../reference/context-discovery.md#bütçe-ve-pilot-kapsamı) ve [yerel hazırlık](../p02-account-setup.md) geçerlidir.

Süre/byte tavanına varmak pilot başarısı değildir. Geç çıktı ve iptal, kalıcı işin geri alındığını kanıtlamaz. Canlı raporda hesap ID’leri gerekiyorsa özel kanıtta kalır; repoda sentetik/maskelemiş kimlik, seçili kapsam, status ve tarih yeterlidir. Ham secret/header/signed URL/full kullanıcı cevabı arşivlenmez. Pilot ölçümü önce sahibi/erişim/fiyat/limit/abort/temizleme onayıyla somutlaştırılır; bu tablo canlı işlem yetkisi üretmez.

## Sonuç ve doğrulama sınırı

P02-0a kaynak, endpoint/SDK farkı, belirsizlik sahipleri, B03/B04 çıktıları ve pilot planını üretir; kapalı bir endpoint’in unknown kalması bu araştırmayı geçersiz kılmaz. P02-0b’nin gerçek hesap/kimlik/yetki kabulü bununla tamamlanmaz. ADR-0020 kullanıcı review bulgularının kapanması koşuluyla kabul/uygulama yetkisi aldı; Accepted kararın kapalı referansı ürün kodundan önce tamamlanır. LLM P02-0c bağımsız ilerler; Platform P02-0d raw/key sözleşmesi kapanmadan draft kalır. Belge, metadata, kaynak-hash ve iki fresh review sonuçları [uygulama kaydında](p02-0-implementation-validation.md) tutulur; runtime/build/performans veya canlı EVREN kabulü bu araştırma turunda yapılmadı.
