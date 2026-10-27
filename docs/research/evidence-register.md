# Kanıt ve referans kaydı

**Güncellendi:** 2026-10-27. **Kapsam:** Başlangıç tasarımı için kaynaklar; güncel canlı hesap sertifikası değildir.

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
