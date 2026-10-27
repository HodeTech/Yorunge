# Profil ve reçete sözleşmesi

**Durum:** v1 yerel alt küme uygulandı; secret erişimi/migration ve yürütme bağları planlandı. **Tarih:** 2026-10-27.

## Uygulanan dosya ve şema sınırı

Config açık `--config PATH` / Python `config=Path(...)` ile seçilir. Verilmezse `~/.config/yorunge/config.toml` okunur; dosya yoksa sır/hesap/proje içermeyen yerleşik `default` profili kullanılır. Açık dosya yoksa hata döner. Env davranış override'ı taranmaz; bu dilimde credential değeri de okunmaz. `platform_key_env` ve `llm_key_env` yalnız ad şemasıyla doğrulanır, context/plan/çıktıya dahil edilmez. Keychain henüz yoktur.

TOML root alanları: `schema_version=1` (bool/string değil int), `active_profile`, `profiles`. Her profil: `platform_url`, `llm_url`, `platform_key_env`, `llm_key_env`, `account_id`, `project_id`, `tools.defaults`. Bilinmeyen/nested alan ve yinelenen anahtar reddedilir. Proje önceliği açık çağrı → reçete `project` → profil `project_id` → null; liste başından proje alınmaz. Eksik proje yerel okumayı/plan hazırlığını engellemez; gerektiğinde remote plan engeli olur.

`platform_key_env`/`llm_key_env` verilirse ad 1–128 ASCII karakter ve `^[A-Z_][A-Z0-9_]*$` biçimindedir (`EnvName` modelinin mevcut v1 sınırı). Bu ad sınırı secret değerinin uzunluğu değildir; değer bugün çözülmez. Secret değerinin UTF-8 byte sınırı ve credential hedef eşlemesi [Proposed binding sözleşmesinde](credential-binding-v1.md) ADR-0012 onayına sunulur; mevcut config/Plan dosyaları bu hazırlıkla yeniden yazılmaz.

Hizmet URL'leri HTTPS olmalı; userinfo/query/fragment, beklenmeyen port, kontrol karakteri ve karışmış bilinen Platform/LLM host'ları reddedilir. Özel host'u yerel şemaya kabul etmek o host'un güvenilirliğini veya API uyumunu doğrulamaz. IPv6 kapsamı köşeli parantezle korunur. Uzak hedef politikası sonraki HTTP işinde doğrulanmalıdır.

Kontrol karakteri sınırı C0 (`U+0000–U+001F`), DEL (`U+007F`) ve C1 (`U+0080–U+009F`) aralıklarıdır; hem hizmet URL'sine hem veri yolu referansına uygulanır. Boş userinfo (`https://@host/...`) de reddedilir. Önceden yanlışlıkla kabul edilen bu girdiler artık config/reçete/kayıtlı Plan hatasıdır; geçerli Unicode dosya adları ve v1 dosyaları korunur.

YAML alanları: `schema_version`, `task`, isteğe bağlı `profile`, `project`, `tool: {id}`, `execution: {backend}`, `model: {source, id, revision}`, `data: {manifest}`, `training: {method, epochs}`, `provider_options`. `schema_version` ve `task` zorunlu; model/veri bu taslakta isteğe bağlı referanstır. İlk model biçimi `source=huggingface`, `id=owner/model`, açık revision; eğitim yalnız `llm.train`, `method=sft`, int `epochs` 1–1000. Native görevlerin model/veri parametreleri henüz uygulanmadığı için reddedilir. `provider_options` yalnız boş nesne kabul eder; adaptör yokken doğrulanamayan seçenek geçirilmez. Veri yolu URL/kontrol karakteri içeremez; dosya varlığı, çalışma kökü, symlink ve içerik doğrulaması bu dilimde yapılmaz. Görevin yürütme planına dönüşmesi bunları gerektirir.

Planlanabilir görev kimlikleri: sekiz araçlı LLM görevi (aşağıdaki defaults), `dataset.upload`, `vision.train.managed`, `llm.chat`. Araç adları seçim politikası kapsamında `forgelm`, `axolotl`, `llamafactory`, `unsloth`; **hiçbirinin adaptörü yoktur**. Native veri/LLM için `local` istemci, görsel yönetilen eğitim için `evren-managed`; araçlı LLM için `local` veya sözleşmesi henüz bilinmeyen `evren-workspace` taslakları gösterilebilir. Uyumsuz birleşimde fallback yoktur.

TOML/YAML en çok 65.536 bayt, JSON Plan 262.144 bayt; UTF-8 ve normal dosya gerekir (salt okunur config symlink'i izlenebilir). YAML en çok 32 collection derinliği ve 2.048 parse olayı; alias, anchor, merge/özel tag ve çoklu belge reddedilir. JSON'da yinelenen anahtar ve NaN/Infinity reddedilir. Kaydedilen dosya CLI zarfı değil `result.data.model_dump_json()` Plan nesnesidir. Digest anahtarları sıralı, kompakt UTF-8 JSON üzerinden `digest` alanı hariç hesaplanır. Yüklemede şema, digest ve yerel plan politikası denetlenir; mevcut profil kullanılarak araç yeniden çözülmez.

Standart YAML tag'i de doğru düğüm türünde olmalıdır: scalar tag'ine mapping veya mapping tag'ine sequence verilmez. PyYAML'ın `!!str {=: ...}` gibi mapping'i scalar'a dönüştüren uyumluluk kısayolu bu dar reçetede kabul edilmez; normal string veya `!!str "..."` kullanılır. Bozuk literal ve düğüm/tag birleşimleri ham parser istisnası yerine `invalid_recipe` üretir.

## Ayrım

Profil TOML'i hizmet/hesap tercihleri ve sır referanslarını taşır. Paylaşılabilir YAML reçetesi görev, veri, model, araç ve execution ayarını tanımlar. Geçici işlem durumu bu dosyalara geri yazılmaz; operation store'da kalır.

**Okunabilen profil örneği — URL'ler belge varsayılanıdır, canlı doğrulama değildir:**

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

**Okunabilen reçete örneği — model/sürüm/dosya referansları yer tutucudur; yürütme sağlamaz:**

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
