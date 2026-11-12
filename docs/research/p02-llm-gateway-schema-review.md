# LLM geçidi şema yeniden okuması ve dış inceleme doğrulaması

**Tarih:** 2026-11-08. **Durum:** Karar girdisi ve roadmap/belge gerekçesi; ürün kodu, sözleşme değişikliği veya canlı hesap kabulü değildir. Üç bağımsız ajan incelemesinin iddiaları kaynakla yeniden doğrulandı; doğrulanamayan veya yanlış çıkan iddialar ayrıldı.

## Yöntem ve sınır

- Dış istekler yalnız anahtarsız HTTPS GET'tir: LLM geçidinde `openapi.json`, `/healthz`, `/readyz`, `/health`, `/v1/health` (5 GET) ve Yörünge'nin taşımalarının kullandığı TLS bağlamı oluşturucusuyla (`httpx.create_ssl_context(trust_env=False)`, certifi 2026.10.23) kurulan ad hoc istemciyle iki hostta `/healthz` (2 GET; kayıtlı betik yok, taşıma kabulü değildir). Anahtar, hesap, token harcayan veya durum değiştiren çağrı yoktur.
- İddia durumları: **Doğrulandı** (kendi okuma/ölçümüm), **Düzeltildi** (kısmen veya yanlış), **Doğrulanamadı** (anahtar/canlı hesap gerekir). Anahtarlı çağrı yapılmadığından hesap davranışı hakkında yeni kanıt yoktur.

## Resmî şemada doğrulananlar (O)

| Gözlem | Yörünge etkisi |
|---|---|
| Şema 53.649 bayt, SHA-256 `e2254a302d6108dcd715151f8f2310195b86439ac7f1686959df908a0f2a700e`, OpenAPI 3.1.0, info 0.1.0, 33 path. 31 Ekim kaydı 52.240 bayt / `5ba9b1b…` idi: +1.409 bayt, path sayısı aynı. Eski gövde repoda saklanmadığından yapısal fark ayrıştırılamaz | Kayıtlı hash güncel değil; [yeniden sabitlendi](evidence-register.md#8-kasım-llm-şeması-yeniden-okuma). Karşılaştırılan tüketici satırları [P02-0a kaydındaki](p02-contract-sdk-pilot.md) `ModelInfo` alanları (id, created, task, modalities, pricing, context_length, default_max_output_tokens, capabilities, precision), `QuotaStatus` (zorunlu `held_cr`/`remaining_cr`; nullable token, pencere, günlük, eşzamanlılık, model ve fair-share alanları), `TermsStatus` (dört zorunlu alan) ve ilgili yollardır; bunlarda çelişki çıkmadı. Diğer yollar ve açıklama metinleri karşılaştırılmadı. [Yapısal özet](probes/llm-openapi-structure-20261108/README.md) bir sonraki okumada diff alınmasını sağlar; P02-4a/5/6b hazırlığında şema yine karşılaştırılır |
| `/healthz` liveness (bağımlılık kontrolü yok), `/readyz` readiness (yalnız evet/hayır, iç teşhis yok). İkisi anahtarsız 200 (`{"status":"ok"}`, `{"status":"ready"}`); `/health` ve `/v1/health` 404. Şemada hiçbir operasyonda `security` yoktur (kimlik isteyenlerde de); anahtarsız erişim şemadan değil gözlemden çıkar | Yörünge sağlık ucunu bugün çağırmaz. Sağlayıcı tarafı sinyalidir, kullanıcının anahtar/hesap durumunu kanıtlamaz. Doctor'ın varsayılan (yerel, ağsız) kontrolüne eklenmez; ağ tanısı kararında ([P02-R9](../roadmap/tasks/p02-r9-network-diagnosis-and-trust-paths.md)) isteğe bağlı girdi adayıdır |
| `TermsStatus` dört zorunlu alan taşır: `accepted`, `current_version`, `is_material`, `doc_path` | P02-0c'nin [strict raw decoder'ıyla](../reference/context-discovery.md#raw-terms-adaptörü-ve-hata) uyumlu |
| `GET /v1/terms/text` `version`, `doc_path`, `content` (ham Markdown) döner. Açıklama okumanın kabul gerektirmediğini söyler; canlı doğrulanmadı. Şemada `terms_not_accepted` hata kodu geçmez | Salt okuma bir `terms show` teknik olarak mümkün görünür; karar kullanıcıdadır ([B17](../roadmap/backlog.md)). Sağlayıcı Markdown'ı güvenilmez metindir: boyut sınırı, terminal kaçış dizisi temizliği ve URL/`doc_path` takip etmeme ([ADR-0020](../decisions/0020-service-bound-context-discovery.md)) gerekir |
| `/v1/models` anahtarın kullanabildiği modelleri döner; `/v1/models/{model_id}` göremediği model için, kayıt defterinde olsa bile, 404 verir ("varlık bilgisi sızmaz"). `task` değerleri açıklama metnindedir (chat, vision_chat, embedding, rerank, ocr, audio_transcription, tts); kapalı enum yoktur | P02-4a "katalogda yok" ile "bu anahtar göremiyor" ayrımını yapamaz ve denememelidir: bulunamama yalnız "bu anahtara görünür değil" demektir, "yok" veya "kaldırıldı" denmez. `task` açık dizedir; bilinmeyen görev ayrı gösterilir |
| Şemada deprecation/sunset/retire/removal/replacement alanı yok (arama sıfır eşleşme) | Statik "kaldırılacak model" tablosu eklenmez. Sağlayıcı alan yayımlarsa okunur; o güne kadar kaldırılma bilgisi gösterilmez |
| `ModelPricing.free_until` nullable dizedir ("ISO date until which usage is billed at zero", null = standart fiyat); `pricing` de null olabilir. Biçim, saat dilimi ve dahil/hariç sınırı belirtilmemiş | P02-4a salt bilgi olarak okur ve strict parse eder; `free_until` maliyet kapısını gevşetmez ([ADR-0026](../decisions/0026-explicit-unverified-transfer-attempts.md) fiyatsız işlem kuralı aynen) |
| `QuotaStatus`: kayan pencere (`used_tokens`, `cap`, `window_minutes`, `reset_at`, `usage_ratio`, `level`), kredi (`held_cr`, `remaining_cr` zorunlu ondalık dize), UTC günü ve bütün anahtarlarla ortak günlük sayaç (`daily_*`; `daily_limit_tokens` "hesapta günlük sınır yoksa null"), eşzamanlılık ve `fair_share_active`; `?model=` model payını ekler. `level` (ok / warn ≥%75 / critical ≥%90 / unknown) hangi sınıra bağlı olduğunu söylemez | P02-6b: `daily_limit_tokens` null "günlük sınır yok", diğer null alanlar "bilinmiyor"; hiçbiri sıfır veya varsayılan sayı değildir ([compute](../modules/compute.md): sabit kota sayısı yerine güncel cevap). `level` sağlayıcı bildirimi olarak taşınır; Yörünge kendi eşiğini türetmez ve günlük sınıra bağlamaz |
| Şemada yok: `x-ratelimit-*`, `Retry-After`, SSE keep-alive, `stream_options.include_usage`. Belgelenen tek yanıt başlığı `X-Evren-Images-Dropped` (görsel sınırı aşılınca en eski görseller metin notuyla değiştirilir, sayıyı bu başlık bildirir) | Belgesiz davranışlar Yörünge sözleşmesi sayılmaz; P02-5b/6b'de canlı doğrulama adayıdır. Gelecekteki vision_chat tüketicisi görsellerin düşürülebildiğini sonuçta göstermelidir |

## Yörünge tarafında doğrulananlar

- Ortam proxy/CA/netrc kapalıdır: [`trust_env=False`](../../src/yorunge/adapters/http_transport.py), [ADR-0017](../decisions/0017-bounded-http-transport.md); `HTTPS_PROXY`, `ALL_PROXY`, `SSL_CERT_FILE`, `SSL_CERT_DIR` ve `NETRC` değerlerinin servis taşımasında yok sayıldığı [testle](../../tests/integration/test_http_transport.py) korunur. Bu kararın kullanıcı rehberlerinde görünür bir karşılığı yoktu; [taşıma referansına](../reference/http-transport.md#kurumsal-ağ-ve-ortam-proxysi) ve [upload rehberine](../reference/upload-workflows.md) eklendi.
- Hata kataloğunda `transport_timeout` ayrıdır; DNS, bağlantı reddi, TLS doğrulama ve protokol hataları tek `transport_failed` altındadır ([katalog](../reference/cli-contract.md#p01-5-hata-kataloğu)).
- Upload oturumunun tek bağlantı havuzu (Platform API ve depolama bağlantıları) çözülen adresleri kendisi denetler: biri bile genel değilse (loopback, private, link-local, CGNAT, ayrılmış aralıklar, karma küme) bağlanmadan `invalid_service_target` verir ([guarded_network.py](../../src/yorunge/adapters/guarded_network.py), [ADR-0025](../decisions/0025-isolated-storage-streaming.md)); kodun mesajı yapılandırılan HTTPS adresini suçlar, adres politikasını söylemez. `context discover` çözülen adrese bakmaz. Split-horizon DNS veya adres çeviren ağ geçidi olan kurumsal ağlarda upload bu kodla düşebilir ([P02-R9](../roadmap/tasks/p02-r9-network-diagnosis-and-trust-paths.md) kapsamına alındı).
- `yorunge doctor` uzak erişimi `not_checked` bırakır ([api.py](../../src/yorunge/api.py)); sağlık ucu hiçbir yerde kullanılmaz.
- `context discover --service evren-llm` terms kabul edilmemişse yalnız "kabul edilmemiş (sürüm N)" yazar ([cli/__init__.py](../../src/yorunge/cli/__init__.py)); sonraki adımı söylemez ([P02-R10](../roadmap/tasks/p02-r10-llm-terms-guidance.md)).
- 2026-11-08'de aynı TLS bağlamı oluşturucusuyla (`httpx.create_ssl_context(trust_env=False)`, certifi) kurulan ad hoc istemci `evren-llmapi.ssyz.org.tr` (`/healthz` → 200) ve `api.ssyz.org.tr` (`/healthz` → 404, el sıkışma başarılı) için sertifikayı doğruladı. Bu, Yörünge taşımasının kendisiyle yapılmış bir kabul değildir ve betiği kaydedilmedi. Bir inceleme Windows/stdlib ortamına özgü eksik zincir bulgusunu bildirmişti; bu macOS ortamında Yörünge'yi etkileyen bir sorun görülmedi. Gerçek Windows kabulü yoktur.

## Şemada olmayan, dışarıdan anılan davranışlar

Dış incelemelerde SSE keep-alive, boş `choices`'lı usage paketi, `stream_options.include_usage`, reasoning için `max_tokens` payı, hız sınırı başlıkları ve 500K/dk, 10M/gün gibi sayılar anıldı. Hiçbiri şemada yoktur; kaynakları portal veya topluluk notu olarak bildirildi ve doğrulanamadı. Yörünge için sözleşme kanıtı değildir; [canlı doğrulama adayları](#kararlar) arasındadır. Aynı incelemelerdeki iki tasarım kalıbı şemayla örtüşmediği için [kabul edilmeyenler](#kararlar) arasındadır: sağlık için `/health` varsaymak (gerçek uçlar `/healthz` ve `/readyz`) ve sabit kota sayısı varsaymak (şema `null` = sınır yok der).

## Gelen incelemelerin düzeltmeleri

1. "DNS/TLS/zaman aşımı ayrımı yok, hepsi tek `transport_failed`" kısmen yanlıştır: zaman aşımı ayrı koddur. Gerçek boşluk DNS / bağlantı reddi / TLS doğrulama / protokol ayrımıdır.
2. "Katalogda yok" ile "bu anahtar göremiyor" ayrılmalı önerisi uygulanamaz; API bunu bilerek gizler. Kural tersine çevrildi (yukarıdaki model satırı).
3. Anahtar önek uyarısını P02-0c'ye küçük ek yapma önerisi kabul edilmedi (aşağıda).
4. [Roadmap README](../roadmap/README.md)'deki "HTTP tanılaması P01-5" ifadesi yanıltıcıydı: P01-5 yalnız ortak taşımayı teslim etti, kullanıcıya dönük ağ tanısı yoktur. Düzeltildi.
5. `level` için "hazır eşik" varsayımı şemayla desteklenmez.
6. Sağlık için `/healthz` önerisi: readiness için `/readyz` daha uygun; ikisi de sağlayıcı sinyalidir.

## Kararlar

**Bu çalışmada uygulananlar (yalnız belge/roadmap):** [kanıt kaydında](evidence-register.md#8-kasım-llm-şeması-yeniden-okuma) şemanın yeniden sabitlenmesi; [HTTP taşıma referansına](../reference/http-transport.md#kurumsal-ağ-ve-ortam-proxysi) ve [upload rehberine](../reference/upload-workflows.md) kurumsal ağ sınırı (proxy/CA yok sayma ve upload adres politikası); yukarıdaki P02-4a/5/6b girdileri [faz risk matrisine](../roadmap/phase-02-data-and-inference.md); [P02-R9](../roadmap/tasks/p02-r9-network-diagnosis-and-trust-paths.md) (draft) ve [P02-R10](../roadmap/tasks/p02-r10-llm-terms-guidance.md) (ready) kartları; B16/B17 karar kayıtları.

**Kullanıcı kararı bekleyenler:** B16 (kurumsal ağ yolu ve ağ tanısı; alt kararlar ve önerilen sıra tek yerde, [P02-R9](../roadmap/tasks/p02-r9-network-diagnosis-and-trust-paths.md) kartında) ve B17 (salt okuma şart metni; [backlog](../roadmap/backlog.md)). İkisi de sözleşme değiştirir; bu kayıt karar vermez.

**Kabul edilmeyenler:**

| Öneri | Gerekçe |
|---|---|
| `terms accept` / CI'dan `--yes --version` ile kabul | [AGENTS.md](../../AGENTS.md) ve [ürün kapsamı](../product-scope.md): hesap şartları kullanıcı adına kabul edilmez |
| Anahtar önek/biçim sezgisi (`evren_llm_` vb.), tırnak/`Bearer` temizliği | [ADR-0021](../decisions/0021-platform-discovery-observations.md)/[0022](../decisions/0022-observed-platform-consumer-contract.md): sağlayıcı biçim sözleşmesi yok, sözdizimi uydurulmaz; credential değeri değiştirilmez; doctor değeri okumaz. Sağlayıcı yayımlı biçim sözleşmesi verirse yeniden açılır |
| TLS hatasında başka güven kaynağı deneme, doğrulamasız el sıkışmayla zincir okuma | [ADR-0017](../decisions/0017-bounded-http-transport.md) güven sınırı; teşhis amacıyla bile doğrulamasız bağlantı yok |
| `trust_env=True` / ortam proxy-CA'sını sessizce açma | Ortam bağımlılığı sır ve hedef sınırını bozar; ancak açık kullanıcı seçimi olarak B16'da değerlendirilir |
| Sabit 10M kota varsayımı | Şema `null` = sınır yok der; güncel cevap kullanılır |
| Statik "kaldırılacak model" tablosu | Şemada alan yok; tablo bayatlar |
| Sağlık ucunu doctor'ın varsayılan kontrolüne ekleme | Doctor yerel ve ağsızdır ([kullanıcı yolculuğu 1](../user-journeys.md) kabulü: salt yerel komut ağ yapmaz) |

**Canlı doğrulama adayları (unknown; anahtarlı çağrı ve token gerektirir, kullanıcı onayı olmadan yapılmaz):** `terms_not_accepted` 403 gövdesi ve kabul edilmemiş anahtarın hangi uçlara erişebildiği (P02-4a/5a); SSE keep-alive, boş `choices`'lı usage paketi, `include_usage` ve reasoning/`max_tokens` payı (P02-5b); hız sınırı başlıkları, `level` bağı, `free_until` sınırı ve sayısal limitler (P02-4a/6b); `X-Evren-Images-Dropped` (vision_chat tüketicisi).

## Sınırlar

Anahtar kullanılmadı: kimlik doğrulama, terms kapısı, kota ve model görünürlüğü hesap davranışı olarak doğrulanmadı. Eski şema gövdesi saklanmadığından yapısal fark çıkarılamadı. Yörünge taraması metin araması ve hedefli okumaya dayanır; tüm kodda kapsam garantisi vermez. Bu kayıt ürün sözleşmesi değildir; kabul edilen kararlar kendi kanonik belgelerinde ve ADR'lerinde yaşar.
