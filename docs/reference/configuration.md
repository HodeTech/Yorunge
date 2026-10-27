# Profil ve reçete sözleşmesi

**Durum:** Tasarlanan v1 sözleşmesi. **Tarih:** 2026-10-27.

## Ayrım

Profil TOML'i hizmet/hesap tercihleri ve sır referanslarını taşır. Paylaşılabilir YAML reçetesi görev, veri, model, araç ve execution ayarını tanımlar. Geçici işlem durumu bu dosyalara geri yazılmaz; operation store'da kalır.

**Örnek profil — taslak; bugün okunabilir uygulama config'i değil:**

```toml
schema_version = 1
active_profile = "work"

[profiles.work]
platform_url = "https://api.ssyz.org.tr/api/v1"
llm_url = "https://evren-llmapi.ssyz.org.tr/v1"
platform_key_env = "EVREN_PLATFORM_API_KEY"
llm_key_env = "EVREN_LLM_API_KEY"

[profiles.work.tools.defaults]
"llm.data.ingest" = "forgelm"
"llm.data.audit" = "forgelm"
"llm.fit.check" = "forgelm"
"llm.train" = "forgelm"
"llm.data.generate" = "forgelm"
"llm.evaluate" = "forgelm"
"llm.merge" = "forgelm"
"llm.export" = "forgelm"
```

Proje verilmediyse gereken ilk uzak işlem öncesi açık seçim yapılır; liste başındaki UUID alınmaz. Keychain desteği env referansının alternatifi olabilir; sır değeri dosyaya yazılmaz. Platform ve LLM adres/anahtar eşleşmesi ayrı kontrol edilir.

**Örnek reçete — taslak; model/sürüm/dosya yer tutucuları gerçek girdiyle değişir:**

```yaml
schema_version: 1
task: llm.train
profile: work
model:
  source: huggingface
  id: owner/model
  revision: SELECTED_REVISION
data:
  manifest: ./data/manifest.json
training:
  method: sft
  epochs: 1
execution:
  backend: local
provider_options: {}
```

Araç atlanınca uygun görevin varsayılanı çözülür. Reçeteye `tool: {id: axolotl}` eklemek veya CLI'da `--tool axolotl` seçmek açık override'dır. Bu örnek o adaptörün hazır olduğunu göstermez.

## Öncelik ve sabitleme

Yeni plan: açık çağrı parametresi → reçete → profil göreve özel tercihi → ürün varsayılanı. Env davranış override'ı olarak taranmaz; yalnız belirtilmiş sır adı için okunur. Çözümlenmiş plan tüm önemli seçimleri sabitler; run sırasında profil değişimi planı sessizce değiştirmez. Aynı profil/env adı altında URL veya anahtar değişmesi de [plan geçerliliği denetimine](../architecture/execution-model.md#planın-içerdiği-bağlar) tabidir; sır referansı tek başına yetki kimliği değildir.

## Doğrulama

Bilinmeyen alan/sürüm, duplicate key, aşırı boyut/alias, yanlış tür, geçersiz yol ve sonlu olmayan sayılar kontrollü hata üretir. Sağlayıcı özel seçenekleri provider namespace'inde doğrulanır; `provider_options` keyfî kod/shell geçişi değildir. Geçerli YAML olması, seçilen araç/model/ortamda uygulanabilir olması demek değildir.

Config migration açık sürüm yükseltmesi ve yedek/önizleme ile tasarlanır. Eski dosya sessizce ezilmez; sır profile veya generated plan'a taşınmaz. [Araç çözümleme](../architecture/tool-providers.md).
