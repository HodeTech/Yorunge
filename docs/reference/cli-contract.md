# CLI sözleşmesi

**Durum:** v1; aşağıdaki dar çevrimdışı alt küme uygulanmıştır, diğer komutlar tasarımdır. **Tarih:** 2026-10-27.

## Uygulanan alt küme

| Komut | Gerçek davranış |
|---|---|
| `yorunge --help`, `--version` | Yalnız metadata; config/DB/sır/ağ/araç keşfi ve ML import yok |
| `yorunge context show` | Yerel profil, hesap/proje tercihi; uzak doğrulama yok |
| `yorunge context credential --service evren-platform\|evren-llm` | Yalnız seçilen hizmetin env değerini bir kez çözer; sırrı göstermeden UTF-8/boyut ve hedef kontrolü; DB/ağ yok |
| `yorunge state init [--state-dir PATH]` | Açık yerel store/key oluşturma veya mevcut store'u doğrulama; env/ağ yok |
| `yorunge capabilities --task TASK` | Yerel seçim politikası ve doğrulanmamış/eksik yürütme durumları |
| `yorunge plan prepare --task TASK` | Şema/seçim doğrulanmış offline draft; görev reçeteden de gelebilir |
| `yorunge train plan` | `plan prepare --task llm.train` ile aynı kullanım senaryosu |
| `yorunge plan show --plan FILE` | Kaydedilmiş **Plan nesnesini** doğrular; güncel config okunmaz |

İlk sürüm `--config PATH`, `--profile NAME`, `--project ID`, `--output text|json`, `--non-interactive` seçeneklerini uygular. Ortak seçenekler komuttan önce veya sonra verilebilir; kısaltmalar kabul edilmez. Plan/capability için `--recipe PATH`, `--tool ID`, `--execution BACKEND`; genel plan/capability için ayrıca `--task TASK` vardır. `--refresh`, `ndjson`, rehberli mod ve bütün `run` komutları henüz yoktur. `plan show` context değiştiren seçenekleri reddeder; profil değişimiyle seçim yenilemez.

Yeni plan seçim önceliği [config sözleşmesindedir](configuration.md#öncelik-ve-sabitleme). `train plan` görevi açık `llm.train` çağrısı sayılır. Açık görev override'ı reçetedeki parametreyi geçersiz kılarsa hata olur; parametre düşürülmez.

Planlama sonucu `status=completed`, `operation_id=null`; `data` içinde `mode=offline`, `state=draft`, `executable=false`, `inputs_verified=false`, context, seçim/kaynağı, reçete, capability kayıtları, engeller ve SHA-256 digest bulunur. Bu başarı yalnız **plan hazırlığına** aittir. Araç sürümü bilinmiyor; model/veri referanslarının içeriği, yetki veya maliyet doğrulanmaz. Plan yürütülemez ve onay/operation kimliği oluşturulmaz.

Uygulanan çıkış kodları **0**, **2** ve açık credential kontrolünde **3**'tür. Bilinen ama adaptörü olmayan araç, seçimi koruyan ve engeli gösteren draft üretebilir; bu okuma/planlama başarıyla tamamlanır. **Plan hazırlamada** tanınmayan araç `tool_unavailable`, uyumsuz görev/araç/ortam `unsupported_combination` ile 2 döner. Geçerli bir `capabilities` sorgusu aynı seçim için çıkış 0 ve ilgili reason code ile `unsupported` kayıt döndürür; sorgunun tamamlanması yürütme desteği değildir. Sorgunun kendisi geçersizse (örneğin bilinmeyen görev veya bozuk dosya) yine 2 döner. Diğer kararlı kodlar: `invalid_request`, `invalid_config`, `invalid_recipe`, `invalid_plan`, `file_unreadable`, `profile_not_found`. `credential_unavailable` (referans/değer yok veya boş) ve `invalid_credential` (UTF-8/16.384 bayt sınırı) çıkış 3; `invalid_service_target` çıkış 2'dir. Credential kontrolü hesap/izin doğrulaması değildir; `available=true`, `remote_verified=false` ve sır içermeyen hedef/context metadata'sı döndürür. Ham parser hatası/girdi/traceback kullanıcıya basılmaz; bozuk standart YAML scalar tag'leri de güvenli `invalid_recipe` olur. JSON hatası tek nesne stderr, stdout boştur. Diğer çıkış kodları aşağıda gelecekteki yürütme sözleşmesidir.

Çalışan örnekler [README](../../README.md#çalışan-başlangıç); Python API `yorunge.api.show_context`, `inspect_capabilities`, `prepare_plan`, `load_plan` ve `check_credential(service_id, *, config=None, profile=None, project=None)` aynı tipli zarfı döndürür. Secret taşıyıcısı public sonuca girmez. Kamuya açık kontrollü hata `yorunge.domain.errors.YorungeError`'dır.

`api.initialize_state(*, state_dir: Path | None = None)` / `state init`, [yerel state sözleşmesini](local-state.md) uygular. `--state-dir` state ailesine özeldir; config/profil/proje seçenekleri bu komutta reddedilir. `state_invalid`, `state_busy`, `state_repair_required`, `state_write_failed`, `state_unsupported` kontrollü çıkış 2'dir; dosya/SQL/key ayrıntısı hata zarfına girmez. Reset/restore/repair komutları henüz yoktur.

## Komut alanları

| Aile | Planlanan işlemler | Aşama |
|---|---|---|
| `init`, `doctor`, `context`, `capabilities` | Başlangıç, profil/proje, tanılama, destek | P01 |
| `datasets` | inspect, upload, download, verify, versions | P02/P03 |
| `data` | LLM içeriği ingest, audit ve generate; görev bazlı tool seçimi | P03 |
| `catalog`, `models` | Arama, çözümleme ve sürüm/detail; araçlı fit, merge/export | P02 temel / P03 araç görevleri |
| `llm` | models, chat, embed, rerank, quota | P02 |
| `inference` | predict ve model/girdi uyumu | P02/P03 |
| `resources` | status, quota, reservations ve quote | P02/P03; yazma ayrıca kapılı |
| `train`, `evaluate` | plan ve run; task/tool/execution seçimi | P03 |
| `tools` | list ve açık check | P03 |
| `jobs` | list, show, watch, stop, reconcile | P01 temeli / P03 tam |
| `artifacts` | list, fetch, verify | P02/P03 |

İleri servis/MCP komutları P04 tasarımıyla eklenir. Yerel komutlar ağ veya sır okuma zorunluluğu taşımaz. Her ailede bütün fiillerin aynı fazda yayımlandığı varsayılmaz; kesin destek matrisi uygulama sürümünde daraltılabilir.

## Planlanan geniş ortak seçenekler

`--profile`, `--project`, `--output text|json|ndjson`, `--non-interactive` ve gerektiğinde `--refresh`. Araçlı planlamada `--tool` ve `--execution` bulunur. `--tool` native veri/çıkarım işlemine gereksiz zorunluluk getirmez. TTY yalnız etkileşimi belirler; çıktı biçimini kendiliğinden JSON'a dönüştürmez.

**Örnekler taslaktır:**

```text
yorunge datasets inspect ./veri
yorunge llm models --profile work --output json
yorunge train plan --recipe training.yaml
yorunge train plan --recipe training.yaml --tool axolotl --execution local
yorunge train run --plan PLAN_ID --approve-plan PLAN_DIGEST
yorunge jobs watch OPERATION_ID --output ndjson
```

Onay seçeneği açık yürütme niyetini planla bağlar; kendi başına kriptografik insan kimliği kanıtı değildir. Güvenilen UI/CI/MCP host'unun yetkilendirme politikası ayrıca tanımlanır. Non-interactive çağrıda onay yoksa sessiz “evet” veya asılı prompt olmaz.

## Çıktı

- `text`: İnsan sonucu stdout; ilerleme/diagnostic stderr. Renk ve TUI kapatılabilir.
- `json`: Tek sonuç nesnesi stdout. Başlamadan/sonuçta başarısız komut stdout'u boş tutar, tek yapılandırılmış hata stderr'e yazar; kısmi operation kimliği hata içinde taşınır. İnsan ilerleme metni çıkmaz.
- `ndjson`: Destekleyen watch/stream komutunda her satır sürümlü olaydır. Başlatma öncesi hata stderr JSON'dur; başlamış akışın terminal başarısızlığı olayda yer alır. Akış sonunda başarılıymış gibi ek özet üretilmez.

Sonuç zarfı `schema_version`, `operation_id` (yoksa null), `status`, `data`, `warnings` taşır. Hata zarfında kararlı `code`, yerelleştirilebilir `message`, `operation_id`, `retryable` ve sınırlı `details` vardır. Tekil istek JSON çıktısı ile streaming NDJSON birbirine karışmaz. `--help`/`--version` insan odaklı meta işlemlerdir, operation oluşturmaz.

## Çıkış kodları

| Kod | Anlam |
|---:|---|
| 0 | İstenen iş/okuma tamamlandı |
| 1 | Kesin operasyon/uzak servis başarısızlığı |
| 2 | Kullanım, config/şema veya yerel önkoşul hatası |
| 3 | Kimlik/erişim eksik veya reddedilmiş |
| 4 | Gerekli onay sağlanmadı |
| 5 | Yan etkili işlemin sonucu belirsiz; uzlaştırma gerekli |
| 6 | İşlem iptal edildi |
| 7 | İçerik/artefakt bütünlüğü uyuşmazlığı |

Salt okunur capability sorgusu başarıyla bilinmiyor sonucu döndürürse kod 0 olabilir; belirsiz **yan etki** kod 5'tir. Haricî aracın ham kodu `provider_exit_code` olarak ayrıca saklanır. Örneğin ForgeLM'in kod 6'sı Yörünge'de otomatik iptal sayılmaz; adaptör anlamını eşler.

## Açık yerel kimlik gözlemi

`context identity --service evren-platform|evren-llm [--state-dir PATH]` ortak config/profile/project seçiminden sonra tek env snapshot'ını kalıcı yerel kimlikle bağlar. Python karşılığı `api.observe_credential`'dır. `identity` nesnesi opak UUID, pozitif nesil, epoch ve gözlem zamanı taşır; uzak doğrulama false kalır. Eksik/geçersiz secret çıkış 3; state/taşma/bağ değişimi çıkış 2'dir. Aynı değer yeniden gözlendiğinde yazma/zaman güncellemesi yapılmaz. Eski offline komutlar ve Plan biçimi değişmez; ayrıntı [binding v1](credential-binding-v1.md).
