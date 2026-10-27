# Varsayılan ve seçilebilir araç sağlayıcıları

**Durum:** Benimsenmiş tasarım. **Tarih:** 2026-10-27.

## Dört bağımsız eksen

| Eksen | Örnek | Sahip olduğu karar |
|---|---|---|
| Görev | `llm.train`, `llm.evaluate`, `dataset.upload` | Kullanıcının sonucu |
| Araç sağlayıcısı | `forgelm`, doğrulanmış muadil | Haricî araçla uygulama ve parametre çevirisi |
| Execution | `local`, `evren-managed`, koşullu `evren-workspace` | Kaynak ve çalışma ortamı |
| EVREN hizmeti | Platform API veya LLM gateway | Uzak hedef ve hizmete özel kimlik/yetki |

İlk offline modelde `dataset.upload` ve `llm.chat` yerel istemci (`local`) + ayrı uzak Platform/LLM hizmet scope'u taşır. `vision.train.managed`, `evren-managed` seçer. Yerel istemci yürütme ortamı ile bağlandığı uzak hizmet tek kimlikte birleştirilmez. Hiçbiri bu aşamada yürütülmez.

`evren-managed` görsel eğitim hizmetini kullanır; bu hizmetin motorunu `--tool forgelm` ile değiştirmek mümkün kabul edilmez. `llm.train` ise uygun tool ve execution birleşimi gerektirir. ForgeLM veya Axolotl adı tek başına EVREN GPU erişimi sağlamaz.

## Çözümleme önceliği

Yeni plan için açık CLI/Python isteği → reçete seçimi → profil göreve özel tercihi → ürün varsayılanı. Ürün kapsamına alınan ve ForgeLM yeteneğiyle örtüşen `llm.data.ingest`, `llm.data.audit`, `llm.data.generate`, `llm.fit.check`, `llm.train`, `llm.evaluate`, `llm.merge`, `llm.export` görevlerinde ürün varsayılanı ForgeLM'dir. Görev aracın gerçekten desteklediği alt yeteneğe uymalıdır; örneğin her model export biçimi otomatik desteklenmez. Bu görev adlarının tanımlanması hepsinin aynı sürümde teslim edildiği anlamına gelmez.

Kaydedilmiş plan tekrar yürütülürken mevcut profile göre yeniden araç seçilmez; planın sabit seçimi denetlenir. Araç yok/uyumsuzsa plan başlamaz. Alternatifler açıklanabilir; açık seçim olmadan fallback yapılmaz. `dataset.upload` ve native inference gibi görevler tool default zincirine sokulmaz. Yerel yol/hash/aktarım denetimi ile LLM veri içeriği denetimi farklı görevlerdir; ikinci görevde seçilen araç kullanılabilir.

## Adaptör sorumluluğu

Adaptör doğrulanmış sürüm aralığı/görev listesi, parametre eşleme ve kayıp raporu, veri/artefakt biçimleri, çalıştırılacak executable/argümanlar, gerekli erişimler, iptal ve sonuç normalizasyonu sağlar. Sağlayıcıya özgü ileri parametreler kendi namespace'inde doğrulanır; bütün araçlara geçerliymiş gibi ortak alana doldurulmaz.

Ortak sözleşme **ortak sonuçları** temsil eder; araçların bütün ayarlarını en küçük ortak paydaya indirgemek zorunda değildir. Desteklenmeyen ayar hata veya açık kayıp raporudur; sessizce düşürülmez. Veri dönüşümü orijinal veriyi ezmeden kendi manifestini ve kaynak bağını üretir.

## İlk sağlayıcı hedefi

ForgeLM varsayılan adaptörü + aynı LLM eğitim görevi için en az bir muadil, P03 kabul koşuludur. Axolotl ilk değerlendirme adayı; LlamaFactory başka bir adaydır. Unsloth'un ForgeLM içindeki backend rolü ile bağımsız Yörünge sağlayıcısı rolü farklı kaydedilir. Bugün hiçbir Yörünge araç adaptörü yoktur; aday listesi destek ilanı değildir.

Üçüncü parti Python kodunu otomatik keşfedip import eden açık plugin sistemi ilk sürümde kurulmaz. Adaptörler gözden geçirilmiş kayıt ve açık sürüm kanıtıyla gelir. [Araç portu](../reference/tool-provider-contract.md), [ADR-0002](../decisions/0002-forgelm-default-open-tools.md).
