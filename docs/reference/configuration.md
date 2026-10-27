# Profil ve reçete sözleşmesi

**Durum:** v1 yerel config/context, env ve kalıcı kimlik uygulandı; config yönetimi/doctor iki review turuyla doğrulandı; uzak yürütme bağları planlandı. **Tarih:** 2026-10-27.

## Uygulanan dosya ve şema sınırı

Config açık `--config PATH` / Python `config=Path(...)` ile seçilir. Verilmezse `~/.config/yorunge/config.toml` okunur; dosya yoksa sır/hesap/proje içermeyen yerleşik `default` profili kullanılır. Açık dosya yoksa hata döner. Env davranış override'ı taranmaz. `platform_key_env` ve `llm_key_env` adları şemayla doğrulanır, context/plan/çıktıya dahil edilmez. Değer açık `context credential` / `api.check_credential` veya `context identity` / `api.observe_credential` çağrısında seçilen hizmet için bir kez okunur. Stateless context, varsayılan capability ve offline v1 plan okumaz. Açık remote cache sorgusu ile execution prepare/validate/approve, gerekli seçili hizmet referansı varsa aynı çağrıda tek private env snapshot'ı kullanır; [cache](capability-record.md#açık-cache-v2-sorgusu) ve [execution](execution-plan.md) sözleşmeleri geçerlidir. Keychain henüz yoktur.

TOML root alanları: `schema_version=1` (bool/string değil int), `active_profile`, `profiles`. Her profil: `platform_url`, `llm_url`, `platform_key_env`, `llm_key_env`, `account_id`, `project_id`, `tools.defaults`. Bilinmeyen/nested alan ve yinelenen anahtar reddedilir. Proje önceliği açık çağrı → reçete `project` → profil `project_id` → null; liste başından proje alınmaz. Eksik proje yerel okumayı/plan hazırlığını engellemez; gerektiğinde remote plan engeli olur.

`platform_key_env`/`llm_key_env` verilirse ad 1–128 ASCII karakter ve `^[A-Z_][A-Z0-9_]*$` biçimindedir (`EnvName` modelinin mevcut v1 sınırı). Açık çözümlemede secret strict UTF-8 ile 1–16.384 bayt olmalıdır; trim/case/Unicode normalizasyonu yapılmaz. Secret'ın veya referansın eksikliği başka hizmete fallback üretmez. Credential hedef kapısı [binding v1](credential-binding-v1.md) kuralını uygular; kalıcı HMAC/kimlik açık gözlem API'sinde tutulur. Mevcut Plan dosyaları yeniden yazılmaz; config yalnız açık yönetim çağrısında güncellenir.

Hizmet URL'leri HTTPS olmalı; userinfo, dolu query/fragment, beklenmeyen port, kontrol karakteri ve karışmış bilinen Platform/LLM host'ları reddedilir. Mevcut offline parser boş `?`/`#` ayıraçlarını kabul eder; yeni credential hedef kapısı bunları [binding v1](credential-binding-v1.md) gereği reddeder. Eski offline Plan uyumu için genel parser bu kapıyla sessizce değiştirilmez. Özel host'u yerel şemaya kabul etmek o host'un güvenilirliğini veya API uyumunu doğrulamaz. IPv6 kapsamı köşeli parantezle korunur. Uzak hedef politikası sonraki HTTP işinde doğrulanmalıdır.

Kontrol karakteri sınırı C0 (`U+0000–U+001F`), DEL (`U+007F`) ve C1 (`U+0080–U+009F`) aralıklarıdır; hem hizmet URL'sine hem veri yolu referansına uygulanır. Boş userinfo (`https://@host/...`) de reddedilir. Önceden yanlışlıkla kabul edilen bu girdiler artık config/reçete/kayıtlı Plan hatasıdır; geçerli Unicode dosya adları ve v1 dosyaları korunur.

YAML alanları: `schema_version`, `task`, isteğe bağlı `profile`, `project`, `tool: {id}`, `execution: {backend}`, `model: {source, id, revision}`, `data: {manifest}`, `training: {method, epochs}`, `provider_options`. `schema_version` ve `task` zorunlu; model/veri bu taslakta isteğe bağlı referanstır. İlk model biçimi `source=huggingface`, `id=owner/model`, açık revision; eğitim yalnız `llm.train`, `method=sft`, int `epochs` 1–1000. Native görevlerin model/veri parametreleri henüz uygulanmadığı için reddedilir. `provider_options` yalnız boş nesne kabul eder; adaptör yokken doğrulanamayan seçenek geçirilmez. Veri yolu URL/kontrol karakteri içeremez; YAML parser ve offline v1 dosya varlığı, çalışma kökü, symlink veya içerik doğrulaması yapmaz. Açık execution hazırlığı manifest dosyasını descriptor/root/hash bağıyla doğrular; tam veri/model kapanışını veya adaptör desteğini bundan çıkarmaz.

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

## Yerel config yazma ve tanılama

Config oluşturma/güncelleme ve yerel doctor bu sürümde macOS/Linux dosya ve kilit desteği gerektirir. Windows veya eksik `fcntl` desteğinde config yazımları I/O öncesi `config_unsupported` (çıkış 2), doctor `state_unsupported` (çıkış 2) verir; traceback veya kısmi yazma üretilmez. Bu sınır SQLite state desteğiyle aynı yerel platform hedefini kullanır; Windows desteği eklendiği iddia edilmez. Metadata komutları bu altyapıyı yüklemez.

P01-2c yüzeyi: `init [--config PATH] [--profile NAME] [--project ID]` ilk dosyayı no-clobber oluşturur. Varsayılan yol `~/.config/yorunge/config.toml`, açık profil yoksa `default`'tur. Yeni config iki hizmet için yalnız geleneksel `EVREN_PLATFORM_API_KEY` / `EVREN_LLM_API_KEY` env adlarını yazar; değerleri okumaz. Mevcut implicit default davranışı değişmez.

`context profiles` profilleri/aktif seçimi listeler; `context use-profile NAME` kalıcı aktif profili değiştirir. `context set-project ID` / `context clear-project` seçili (`--profile` veya aktif) profilin proje tercihini değiştirir. Diğer profiller, hizmet alanları ve araç varsayılanları anlamsal olarak korunur; TOML yorum/biçimi korunmaz, özgün byte'lar özel backup'ta saklanır. Liste ve use-profile çağrılarında `--profile/--project`; proje değişiminde ayrıca `--project` kabul edilmez. Init/profile/proje yönetimi credential veya state açmaz.

Python karşılıkları `initialize_config(*, config=None, profile=None, project=None)`, `list_profiles(*, config=None)`, `activate_profile(name, *, config=None)`, `set_project(project, *, config=None, profile=None)` ve `clear_project(*, config=None, profile=None)`'dır. Yazma no-follow/owner/regular/no-hardlink güvenliği ve ortak kalıcı config lock'u kullanır. Başlangıç snapshot'ı lock altında yeniden karşılaştırılır; değişmiş içerik/inode `config_conflict` olur. Yeni TOML parse/şema/boyut sınırlarını geçmeden yazılmaz. Mevcut dosyanın özel no-clobber backup'ı ve yeni dosyanın file/dizin sync'i atomik publish'ten önce yapılır. Yeni yayın 0600'dür; mevcut dosya sessiz chmod ile sahiplenilmez. Yayın öncesi hata çalışan eski config'i değiştirmez. Yayın sonrası bariyer hatası `config_write_uncertain` ile açıkça ayrılır, otomatik tekrar yapılmaz. Backup ve yarım çıktı otomatik silinmez.

`doctor [--config PATH] [--profile NAME] [--project ID] [--state-dir PATH]` / `api.diagnose_local` yerel config/profil, hizmet env referanslarının tanımı, state ve key dosyasının metadata'sını denetler. Env değerini veya K içeriğini okumaz; key-check ve uzak erişim `not_checked` kalır. Eksik state/key yaratmaz, migration veya hot-journal recovery başlatmaz. Mevcut store salt okunur/immutable açılmadan önce ortak exclusive bakım kilidi alınır; journal/intent onarım gereği olarak raporlanır. Başarılı tanılama toplaması çıkış 0'dır; her `checks` kaydının `ok/missing/invalid/busy/not_checked` durumu ve `issue_count` değerlendirilmelidir. Çıkış 0 uzak auth, tam K doğrulaması veya her kontrolün geçtiği anlamına gelmez. Geçersiz çağrı kontrollü hata zarfıdır; non-TTY prompt yoktur.

Config lock'u bu protokole katılan yazıcıları sıralar. Geçici dosya ve backup hazırlandıktan sonra, publish'ten hemen önce inode/byte snapshot tekrar kontrol edilir; staging I/O'su sırasında değişen dosya ezilmez. Kilide katılmayan haricî editörün bu son kontrol ile atomik replace arasındaki değişimi için POSIX dosya API'si compare-and-swap garantisi vermez. Uygulama bu sınırı gizlemez veya sınırsız retry ile geçmez.
