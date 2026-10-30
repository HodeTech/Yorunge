# Kanıt ve referans kaydı

**Güncellendi:** 2026-10-31. **Kapsam:** Başlangıç tasarımı ve tarihli kaynak kontrolleri; güncel canlı hesap sertifikası değildir.

## Kanıt türleri

Resmî şema/kılavuz, yayımlanmış web istemcisi, araç sözleşmesi, offline deney ve gerçek hesap deneyi farklı seviyelerdir. Bu çalışma yeni hesap/GPU deneyi yapmadı. Kaynak okuma tarihi ile kaynakta yazan geçmiş ölçüm tarihi karıştırılmaz.

## EVREN başlangıç kanıtları — 26 Ekim 2026

| Kaynak | Çıkarılan bilgi | Sınır |
|---|---|---|
| [Kullanım kılavuzu](https://evren.ssyz.org.tr/guide) | Veri/sürüm, presign/PUT/confirm, ZIP import, yönetilen görsel eğitim ve API yüzeyleri | Metin ve sunucunun güncel davranışı aynı olmak zorunda değil |
| [LLM OpenAPI](https://evren-llmapi.ssyz.org.tr/openapi.json) | Çıkarım/görev/kota yüzeyi; başlangıç snapshot'ında 30 path | Model erişimi, sayısal kota veya canlı çalışma ölçülmedi |
| [GPU rezervasyonu](https://evren.ssyz.org.tr/gpu-reservations) | İncelenen istemci, rezervasyonun doğrudan SSH/sunucu erişimi vermediğini açıklıyor | Runtime erişimi ayrı |
| [Workspace](https://evren.ssyz.org.tr/workspace) | Yayımlanmış istemcide notebook/runtime ve admin preview/execution kapıları görüldü | Standart kullanıcı ve API key erişimi doğrulanmadı |
| [Altyapı](https://evren.ssyz.org.tr/infrastructure) | GPU envanteri görünürlüğü | Kullanıcı tahsisi ve serbest kapasite garantisi değil |
| [evren-sdk](https://pypi.org/project/evren-sdk/) | Kılavuzda referans verilen mevcut SDK; 26 Ekim metadata'sında 0.11.0 | Bütün kodu bu çalışmada denetlenmedi; uygun bölümler adaptör adayı |

Başlangıç LLM şeması SHA-256: `200e493ec31662bbb8f20c72f7d934ca10c4c623c1c03cd71b72f0ec50f6602d`, OpenAPI 3.1.0. Fine-tuning/adapter oluşturma yolu o şemada görülmedi; bu bütün özel/gelecek Platform yeteneklerinin yokluğunu kanıtlamaz. Platform API için denenen `/docs`, `/api/v1/docs`, `/api/v1/openapi.json` adresleri 404 verdi; başka bir doküman adresi bulunamayacağı sonucu çıkarılmadı.

## P02 hazırlığında dar güncellik kontrolü — 30 Ekim 2026

[P02 hazırlık incelemesinde](p02-readiness-review.md#dış-kaynak-kontrolü) yalnız kamuya açık belgelere credentialsız GET yapıldı. Bu kontrol P02-0a’nın tam endpoint/SDK araştırması değildir; 26 Ekim kaydı tarihsel olarak korunur.

| Kaynak | Bu turda gözlenen | Sınır |
|---|---|---|
| [LLM OpenAPI](https://evren-llmapi.ssyz.org.tr/openapi.json) | HTTP 200; 52.240 byte; OpenAPI 3.1.0, info.version 0.1.0, 33 path; SHA-256 `5ba9b1b79f0f4ff7cf288ee0e9e7d7ce10eb860bfaf0fbbef9b33680cf6ac8d5` | Başlangıçtaki 30 path/hash değişmiştir; bütün farkların ve auth/limitlerin kabulü henüz yapılmadı |
| [Kılavuz](https://evren.ssyz.org.tr/guide) | HTTP 200; 10.407 byte HTML; SHA-256 `24c6e8cd52acb9236862d9e54f917bd42b92cc326ccf6dafe3b9d5d90c8117c8` | İstemci script’i yükleyen HTML kabuğu; tam kılavuz/API sözleşmesi olarak doğrulanmadı |
| [SDK dağıtım metadata’sı](https://pypi.org/pypi/evren-sdk/json) | 0.11.0; wheel SHA-256 `a3f0e191819c27c9df2047fdeeceb15d86140066c3f59e1efb6cb8c150416d92`; sdist SHA-256 `af1332a5d9a2067a8c39f9b82b5128ab6af1cff62e1d6475708abdef8e94aa8e` | Bu turda paket indirilmedi/kurulmadı veya kaynak denetimi yapılmadı; sürüm numarasının aynı kalması endpoint uyumu kanıtı değildir |

Hash’ler bu GET gövdelerine/metadata’da bildirilen dağıtımlara aittir; sağlayıcı attestasyonu veya canlı hesap kanıtı değildir. Büyük kaynak kopyaları repoya alınmadı. Ayrıntılı tüketici endpoint’i ve sürüm/hash sabitlemesi P02-0a’da tekrarlanır; tarihsel bu kontrol onun yerine geçmez.

## P02-0a kaynak sabitlemesi — 31 Ekim 2026

[P02-0a araştırması](p02-contract-sdk-pilot.md) için kamu kaynakları credentialsız GET ile tekrar okundu. Tarihler Europe/Istanbul’dur; UTC’de 30 Ekim’in son saatlerine karşılık gelir. SDK wheel’i indirildi ama kurulmadı/import edilmedi/çalıştırılmadı; JavaScript yalnız metin olarak incelendi. Aşağıdakiler kaynak kimliğidir, kullanıcı hesabı veya sunucu davranışı attestasyonu değildir. Önceki snapshot’lar korunur; guide shell/main asset’i değişmiş, LLM OpenAPI aynı kalmıştır.

| Kaynak / kanıt türü | Byte | SHA-256 |
|---|---:|---|
| [Guide HTML kabuğu](https://evren.ssyz.org.tr/guide) / W | 10407 | `2ca0c264de48e31149c72bc9d87b2b7dcf8bbc0ae1df6a467872b206b4d5f6b8` |
| [Main istemci](https://evren.ssyz.org.tr/assets/index-D_27Bp0m.js) / W | 729034 | `7905d40664f126133e531abc896a1c41b89583ed77fd6831048696553765e1ea` |
| [Guide içeriği](https://evren.ssyz.org.tr/assets/UserGuidePage-CbK-YjDp.js) / G | 96252 | `3a2115680efd8194f7d9c10615a4c33603f24cb213f59d1a42fbec7b36e1015a` |
| [LLM OpenAPI](https://evren-llmapi.ssyz.org.tr/openapi.json) / O; 3.1.0, info 0.1.0, 33 path | 52240 | `5ba9b1b79f0f4ff7cf288ee0e9e7d7ce10eb860bfaf0fbbef9b33680cf6ac8d5` |
| [Project istemcisi](https://evren.ssyz.org.tr/assets/useProject-C93_BqSs.js) / W | 2460 | `6e595ac57d07ceca2cd6bdee42388ede0e0199dcad021cafd98bce2cc460f4eb` |
| [Organization istemcisi](https://evren.ssyz.org.tr/assets/OrgPage-DXC03dG9.js) / W | 8239 | `15a443f32decfaf3d5fa51b4c12445fb39959e3c18aa8e0c73f24ab65aa8ac82` |
| [Dataset istemcisi](https://evren.ssyz.org.tr/assets/datasetApi-BcOh2J15.js) / W | 7005 | `f06fdd0f403013bbc5146c691cbceaa43111668102a248e330a125dc927e551f` |
| [Model istemcisi](https://evren.ssyz.org.tr/assets/useModels-1Ere5UwN.js) / W | 6662 | `91ce0593514efa7c2f1c104e11e3fa6901e42dee6a49e60cda3ddcd7b2e74a82` |
| [LLM katalog/açıklama](https://evren.ssyz.org.tr/assets/LlmModelCatalogPage-Bo9HCoSz.js) / W | 90529 | `d56013caf017f5189006ecef412f7df9fda0dd79ea0b7eb931753b66ddfaef68` |
| [Vision istemcisi](https://evren.ssyz.org.tr/assets/InferencePage-BkRPzcSv.js) / W | 118942 | `cdf250c1b2fa84c4fbf98eb7e4c39b6215ea7d1e5c84c2f5392df54b8f21606f` |
| [GPU istemcisi](https://evren.ssyz.org.tr/assets/useGpuStatus-DOhtiDOA.js) / W | 299 | `f40883460c65c2a2ba6ff31394fa13be01470c0ac2db7014dd5a38ea469a7218` |
| [Reservation istemcisi](https://evren.ssyz.org.tr/assets/useReservation-BHKj8xby.js) / W | 2003 | `a1ce4d0f4470556f1744f893a4afda72121a293f848922f772a290fd63a46ef6` |
| [SDK 0.11.0 wheel](https://files.pythonhosted.org/packages/68/a8/a2f5c8b2ea17ea9513f652c83fff52a9425eadfbb6ac95c2655ba3fcaa07/evren_sdk-0.11.0-py3-none-any.whl) / S | 55693 | `a3f0e191819c27c9df2047fdeeceb15d86140066c3f59e1efb6cb8c150416d92` |

[Sürüm metadata’sı](https://pypi.org/pypi/evren-sdk/0.11.0/json) sdist için `af1332a5d9a2067a8c39f9b82b5128ab6af1cff62e1d6475708abdef8e94aa8e` bildirir; sdist indirilmedi/build edilmedi. `v0.11.0` etiketi [f4eaa4a](https://github.com/speker/evren-sdk/tree/f4eaa4a71f324e61058f24fb90c0aec7a58ae24f) commit’ine çözüldü; client, llm_client, llm_async_client, llm_retry, llm_sse, llm_errors, llm_types, llm_tasks dosyaları sabit Git kaynağı ile wheel’de byte-byte eşleşti. Metadata Apache-2.0/Python≥3.10/httpx≥0.27 ve ayrı image/edge extra’ları bildirir; LICENSE wheel içinde okundu.

Türetilen endpoint/auth/envelope/limit/SDK ve eksik kimlik bulgularının kanonik yeri araştırma raporudur. W browser Bearer çağrısını API key doğrulaması diye sunmaz; O securitySchemes eksikliğini anonim erişim saymaz. Ham büyük kaynaklar repoya/pakete eklenmedi; asset URL’si kalıcı garanti olmadığı için hash/tarih tutuldu. Kaynak güncellenirse consumer sözleşmesi tekrar denetlenir.

## ForgeLM snapshot'ı

[ForgeLM development — 83e62f6](https://github.com/HodeTech/ForgeLM/tree/83e62f6fbd0d29900fd8efb35e326e6a9db380ae), metadata `0.11.2rc1`, 26 Ekim snapshot'ı. **27 Ekim 2026'da sabit resmî kaynak yeniden okundu:** [Synthetic API yolu](https://github.com/HodeTech/ForgeLM/blob/83e62f6fbd0d29900fd8efb35e326e6a9db380ae/forgelm/synthetic.py#L210-L250) `api_base` sonuna `/chat/completions` ekleyerek `safe_post` çağırıyor; [judge yolu](https://github.com/HodeTech/ForgeLM/blob/83e62f6fbd0d29900fd8efb35e326e6a9db380ae/forgelm/judge.py#L324-L368) ise verilen `api_base` değerini doğrudan istek URL'si olarak kullanıyor. Bu statik kaynak gözlemi adaptörün URL eşleme gereksinimini gösterir. Uçtan uca istemci/gateway uyumu, canlı model kalitesi veya EVREN GPU erişimi doğrulaması değildir; bunlar ayrıca sınanmalıdır.

ForgeLM'i özel yardımcı fonksiyonlara bağlamak kalıcı adaptör API'si sayılmaz; doğrulanmış public CLI/Python yüzeyi seçilmelidir. Varsayılan araç kararı teknik olarak bütün görevlerin ForgeLM'e dönüştürülebileceği anlamına gelmez.

## Muadil araç kaynakları — 27 Ekim 2026

[Axolotl resmî belgeleri](https://docs.axolotl.ai/), [LlamaFactory resmî belgeleri](https://llamafactory.readthedocs.io/en/latest/) ve [Unsloth resmî belgeleri](https://unsloth.ai/docs) inceleme adaylarıdır. Belgeler bu projelerin LLM eğitim/fine-tuning alanında çalıştığını gösterir. Yörünge adaptörü, sürüm/model eşdeğerliği veya EVREN çalışma uyumu bu kaynak ziyaretleriyle doğrulanmış değildir. İlk muadil kararı ortak P03 göreviyle sınanacaktır.

## Referans repo yapıları — 27 Ekim 2026

| Referans snapshot | Yörünge'ye uyarlanan yapısal ilke |
|---|---|
| [LearnStack — ea114d2](https://github.com/HodeTech/LearnStack/tree/ea114d25266d7db7729d276c07d0011a7ba180fd) | Alan modülü sahipliği; standart/karar/roadmap ayrımı; benimsenmiş ile etkin kuralı ayırma |
| [Relavium — 5a328bc](https://github.com/HodeTech/Relavium/tree/5a328bca302dcda1b69f826da46d45955bde02c0) | Ortak çekirdek/yüzey sınırı; tek kanonik sözleşme; faz bazlı kabul kapıları |
| [Leakwatch — 5755635](https://github.com/HodeTech/Leakwatch/tree/575563502227368bff93adf714a887113a15eae6) | CLI sonuç doğruluğu; sağlayıcı sözleşmesi ve dürüst feature statüsü; düzenli root belgeleri |

Bu referansların dilleri, teknoloji yığınları, lisansları, branch veya canlı CI kuralları Yörünge'ye devralınmadı. Kaynak yapısı ve ilkeler incelendi; bağımsız Yörünge metinleri yazıldı.
