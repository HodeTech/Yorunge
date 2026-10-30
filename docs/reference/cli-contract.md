# CLI sözleşmesi

**Durum:** Yerel CLI/Python alt kümesi uygulandı; sonuç zarfı v1, ayrı capability/execution kayıtları v2. Yerel jobs list/show ve normal komutlarda NDJSON uygulandı; P01-5b ve P01-6b/ADR-0019/Sonar [son kaynak kabulü](../research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı) çalışma dalında verified. Önceki bf652f6 kaydı tarihseldir; development PR review/merge ayrı. Public run/watch ve EVREN adaptörü planlandı. **Tarih:** 2026-10-30.

## Uygulanan alt küme

| Komut | Gerçek davranış |
|---|---|
| `yorunge --help`, `--version` | Yalnız metadata; config/DB/sır/ağ/araç keşfi ve ML import yok |
| `yorunge context show` | Yerel profil, hesap/proje tercihi; uzak doğrulama yok |
| `yorunge context credential --service evren-platform\|evren-llm` | Yalnız seçilen hizmetin env değerini bir kez çözer; sırrı göstermeden UTF-8/boyut ve hedef kontrolü; DB/ağ yok |
| `yorunge init`, `context profiles/use-profile/set-project/clear-project` | Güvenli yerel config oluşturma/güncelleme; [seçenekler](configuration.md#yerel-config-yazma-ve-tanılama) |
| `yorunge doctor [--state-dir PATH]` | Yerel config/referans/store/key metadata tanısı; env/K içeriği ve ağ yok |
| `yorunge context identity --service SERVICE [--state-dir PATH]` | Tek seçili env snapshot'ının kalıcı yerel kimlik/nesil gözlemi |
| `yorunge state reset/restore/recover` | Varsayılan etki önizlemesi; açık `--confirm DIGEST` ile bakım |
| `yorunge state init [--state-dir PATH]` | Açık yerel store/key oluşturma veya mevcut store'u doğrulama; env/ağ yok |
| `yorunge capabilities --task TASK` | Yerel seçim politikası ve doğrulanmamış/eksik yürütme durumları |
| `yorunge capabilities --task TASK --cached\|--refresh [--state-dir PATH]` | Açık private cache/clock kullanımı; yalnız mevcut yerel kanıt, uzak discovery yok |
| `yorunge plan prepare --task TASK` | Şema/seçim doğrulanmış offline draft; görev reçeteden de gelebilir |
| `yorunge plan execution prepare/list/show/validate/approve/revoke/forget` | Ayrı kalıcı hazırlık, güncel validation ve digest onayı/yerel yönetim; [exact sözleşme](execution-plan.md) |
| `yorunge jobs list/show` | Son yerel summary/plan/attempt/terminal outcome; current validation veya provider sorgusu yok; [exact sözleşme](operations.md) |
| `yorunge train plan` | `plan prepare --task llm.train` ile aynı kullanım senaryosu |
| `yorunge plan show --plan FILE` | Kaydedilmiş **Plan nesnesini** doğrular; güncel config okunmaz |

İlk sürüm `--config PATH`, `--profile NAME`, `--project ID`, `--output text|json|ndjson`, `--non-interactive` seçeneklerini uygular. Ortak seçenekler komuttan önce veya sonra verilebilir; kısaltmalar kabul edilmez. Plan/capability için `--recipe PATH`, `--tool ID`, `--execution BACKEND`; genel plan/capability için ayrıca `--task TASK` vardır. `--cached`/`--refresh` yalnız capability sorgusunda birbirini dışlayarak desteklenir; bu ailede `--state-dir` ancak bu açık modlardan biriyle geçerlidir. Normal NDJSON tek result event’i üretir; metadata help/version insan çıktısı kalır. Rehberli mod ve bütün `run` komutları henüz yoktur. `plan show` context değiştiren seçenekleri reddeder; profil değişimiyle seçim yenilemez.

Yeni plan seçim önceliği [config sözleşmesindedir](configuration.md#öncelik-ve-sabitleme). `train plan` görevi açık `llm.train` çağrısı sayılır. Açık görev override'ı reçetedeki parametreyi geçersiz kılarsa hata olur; parametre düşürülmez.

Offline v1 planlama sonucu `status=completed`, `operation_id=null`; `data` içinde `mode=offline`, `state=draft`, `executable=false`, `inputs_verified=false`, context, seçim/kaynağı, reçete, capability kayıtları, engeller ve SHA-256 digest bulunur. Bu başarı yalnız **plan hazırlığına** aittir. Araç sürümü bilinmiyor; model/veri referanslarının içeriği, yetki veya maliyet doğrulanmaz. Plan yürütülemez ve onay/operation kimliği oluşturulmaz.

Uygulanan çıkış kodları **0**, **2**, açık credential kontrolünde **3**, execution/forget digest onayında **4** ve config yayın belirsizliğinde **5**’tir; çıktı I/O hatası **1**, yerel SIGINT/kapalı pipe **6** döner. Bilinen ama adaptörü olmayan araç, seçimi koruyan ve engeli gösteren draft üretebilir; bu okuma/planlama başarıyla tamamlanır. **Offline v1 plan hazırlamada** tanınmayan araç `tool_unavailable`, uyumsuz görev/araç/ortam `unsupported_combination` ile 2 döner. Geçerli bir `capabilities` sorgusu aynı seçim için çıkış 0 ve ilgili reason code ile `unsupported` kayıt döndürür; sorgunun tamamlanması yürütme desteği değildir. Sorgunun kendisi geçersizse (örneğin bilinmeyen görev veya bozuk dosya) yine 2 döner. Diğer kararlı kodlar: `invalid_request`, `invalid_config`, `invalid_recipe`, `invalid_plan`, `file_unreadable`, `profile_not_found`. `credential_unavailable` (referans/değer yok veya boş) ve `invalid_credential` (UTF-8/16.384 bayt sınırı) çıkış 3; `invalid_service_target` çıkış 2'dir. Credential kontrolü hesap/izin doğrulaması değildir; `available=true`, `remote_verified=false` ve sır içermeyen hedef/context metadata'sı döndürür. Ham parser hatası/girdi/traceback kullanıcıya basılmaz; bozuk standart YAML scalar tag'leri de güvenli `invalid_recipe` olur. JSON hatası tek nesne stderr, stdout boştur. 7 çıkışı aşağıda gelecekteki içerik/artefakt sözleşmesidir; 1/6 için [P01-5 kataloğu](#p01-5-hata-kataloğu) uygulanır.

Çalışan örnekler [README](../../README.md#çalışan-başlangıç); Python API `yorunge.api.show_context`, `inspect_capabilities`, `prepare_plan`, `load_plan` ve `check_credential(service_id, *, config=None, profile=None, project=None)` aynı tipli zarfı döndürür. Secret taşıyıcısı public sonuca girmez. Kamuya açık kontrollü hata `yorunge.domain.errors.YorungeError`'dır.

`api.initialize_state(*, state_dir: Path | None = None)` / `state init`, [yerel state sözleşmesini](local-state.md) uygular. `--state-dir` state ailesinde, `doctor`, açık `context identity`, cache sorgusu, execution planı ve jobs ailesinde desteklenir; config/profil/proje seçenekleri bu komutta reddedilir. `state_invalid`, `state_busy`, `state_repair_required`, `state_write_failed`, `state_unsupported` kontrollü çıkış 2'dir; dosya/SQL/key ayrıntısı hata zarfına girmez. Reset/restore/recover önizleme ve açık uygulama akışları aşağıda tanımlıdır.

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
- `ndjson`: Uygulandı; P01-5b kabul/review kapandı. Bütün normal komutlarda opt-in (`--output ndjson`/`--output=ndjson`), tek başarılı sonuç tek result olayıdır. Çok olaylı gerçek taşıma fixture composition'ındadır; public watch/stream açılmaz. İlk publish öncesi hata stderr JSON, sonrası tek terminal error stdout; ikinci başarılı özet yoktur. Makine çıktı UTF-8 byte olarak yazılır, locale/PYTHONIOENCODING bunu değiştirmez.

Sonuç zarfı `schema_version`, `operation_id` (yoksa null), `status`, `data`, `warnings` taşır. Hata zarfında kararlı `code`, yerelleştirilebilir `message`, `operation_id`, `retryable` ve sınırlı `details` vardır. Tekil istek JSON çıktısı ile streaming NDJSON birbirine karışmaz. `--help`/`--version` insan odaklı meta işlemlerdir, operation oluşturmaz.

## Çıkış kodları

| Kod | Anlam |
|---:|---|
| 0 | İstenen iş/okuma tamamlandı |
| 1 | Kesin operasyon/uzak servis başarısızlığı veya sonuç çıktısı teslim edilemedi; kalıcı iş başarısı çıktı hatasıyla değişmez |
| 2 | Kullanım, config/şema veya yerel önkoşul hatası |
| 3 | Kimlik/erişim eksik veya reddedilmiş |
| 4 | Gerekli onay sağlanmadı |
| 5 | Yan etkili işlemin sonucu belirsiz; uzlaştırma gerekli |
| 6 | Yerel çağrı/izleme bırakıldı veya stdout alıcısı kapandı; uzak işin iptali kanıtı değildir |
| 7 | İçerik/artefakt bütünlüğü uyuşmazlığı |

Salt okunur capability sorgusu başarıyla bilinmiyor sonucu döndürürse kod 0 olabilir; belirsiz **yan etki** kod 5'tir. Haricî aracın ham kodu `provider_exit_code` olarak ayrıca saklanır. Örneğin ForgeLM'in kod 6'sı Yörünge'de otomatik iptal sayılmaz; adaptör anlamını eşler.

## Açık yerel kimlik gözlemi

`context identity --service evren-platform|evren-llm [--state-dir PATH]` ortak config/profile/project seçiminden sonra tek env snapshot'ını kalıcı yerel kimlikle bağlar. Python karşılığı `api.observe_credential`'dır. `identity` nesnesi opak UUID, pozitif nesil, epoch ve gözlem zamanı taşır; uzak doğrulama false kalır. Eksik/geçersiz secret çıkış 3; state/taşma/bağ değişimi çıkış 2'dir. Aynı değer yeniden gözlendiğinde yazma/zaman güncellemesi yapılmaz. Eski offline komutlar ve Plan biçimi değişmez; ayrıntı [binding v1](credential-binding-v1.md).

## Açık capability cache sorgusu

Python `query_capabilities(*, task=None, config=None, recipe=None, profile=None, project=None, tool=None, execution=None, refresh=False, state_dir=None)` ortak tipli `Result[CachedCapabilityView]` döndürür. `refresh` strict bool, dosya/dizin argümanları Path'tir. CLI `--cached` aynı default refresh=False yoludur; bu yeni API'nin çağrılması başlı başına stateful niyettir. Eski `inspect_capabilities`/CLI varsayılanı aynı stateless v1'i üretir.

Sonuçtaki hit/freshness, etkin destek ve tarihsel kayıt [cache v2 sözleşmesinde](capability-record.md#açık-cache-v2-sorgusu) tanımlıdır. Miss/stale/clock anomaly/unknown başarılı sorgu olabilir ve çıkış 0'dır; stored supported etkin karar yerine gösterilmez. `--refresh` bu sürümde ağ değil yerel politika yenilemesidir. Kapasite dolu ve pinlenmiş çelişkiler korunuyorsa `capability_capacity_exceeded`, refresh sırasında süre/bütçe dolmuşsa `capability_expired`, bağ değişmişse `state_changed` çıkış 2 olur; otomatik retry yoktur. Uzak seçili env referansı varsa eksik/geçersiz değeri mevcut credential çıkış 3 sözleşmesine uyar. Fcntl/platform kapısı bütün I/O ve env gözleminden öncedir.

## Kimlik bakımı

`state reset`, `state restore --backup PATH`, `state recover` varsayılan önizleme; `--confirm DIGEST` açık uygulamadır. `--state-dir PATH` desteklenir, diğer context seçenekleri reddedilir. Python karşılıkları, önizleme alanları, kesinti/onarım sınırları ve kayıt kaybı [local-state](local-state.md#açık-reset-restore-ve-kesilmiş-restore-kurtarması) içinde kanoniktir. `state_changed`, `credential_revision_exhausted`, `state_restore_unsupported` kontrollü çıkış 2'dir; onay otomatik tekrar veya uzak yürütme izni vermez.

## Yerel config yönetimi ve doctor

Uygulanan `init`, `context profiles`, `context use-profile NAME`, `context set-project ID`, `context clear-project` ve `doctor` seçenekleri/API sonuçları [config sözleşmesinde](configuration.md#yerel-config-yazma-ve-tanılama) tanımlıdır. Init/update no-clobber/backup/optimistic conflict ve atomik publish kullanır. `config_unsupported`, `config_exists`, `config_conflict`, `config_busy`, `config_write_failed` çıkış 2; yayın sonrası `config_write_uncertain` çıkış 5'tir. Çıkış 5'te güncel dosya ve backup incelenir, otomatik tekrar yoktur. Doctor desteklenmeyen yerel platformda I/O öncesi `state_unsupported` ile 2 döner; desteklenen ortamda tanıların toplanmasında 0 döner; `checks`/`issue_count` değerlendirilir, `not_checked` başarıya çevrilmez. Varsayılan doctor sır/K içeriği okumaz veya state/lock/key yaratmaz.


## Kalıcı execution hazırlığı

`plan execution prepare|list|show|validate|approve|revoke|forget` ve Python karşılıkları uygulandı; exact seçenekler, gövde, validity/hata ve dosya/süre sınırları [execution planı v2](execution-plan.md) içindedir. Eski `plan prepare/show` v1 kalır. Digest onayı açık ve güncel validation gerektirir; eksik/yanlış onay çıkış 4, blocked plan çıkış 2. Run/dispatch yoktur.


## Yerel iş sorguları

`jobs list/show` ve `api.list_jobs/show_job` aynı salt kullanım senaryosudur. [Exact filtre, cursor, wire ve snapshot sınırı](operations.md) kanoniktir. Dış Result completed/null, warnings local_history_only; failed/unknown/cancelled işi okumak exit 0'dır. Text son kaydın uzak güncel durum olmayabileceğini belirtir. Jobs config/profil/proje/görev/araç seçmez; tekrar edilen tekil seçenekleri reddeder. Public run/watch/stop/reconcile yoktur.

## Operation hata kataloğu

Jobs yalnız operation_not_found ve mevcut request/state hatalarını üretir; plan_in_use seçili plan forget yüzeyindedir. Diğer coordination kodları trusted iç portlara aittir, yeni public yürütme komutu anlamına gelmez. OperationError zarfı ve kalıcı neden ayrımı [operations referansındadır](operations.md#coordination-hata-sınırı).

| Kod | Exit | Kesin tetik |
|---|---:|---|
| operation_not_found | 2 | Canonical ID ile istenen operation yok |
| operation_conflict | 2 | Dispatch latch doluyken yeniden arm, yanlış lifecycle mutasyonu veya değişmez terminal sonucu değiştirme girişimi; repeated admission değildir |
| operation_lease_lost | 2 | Business/renew/result çağrısındaki owner/fence/ownership epoch/generation uyuşmuyor, lease null/expired veya clock anomaly var |
| operation_fence_exhausted | 2 | Yeni acquire signed-64 fence taşır; reset buna bağlı değildir |
| operation_capacity_exceeded | 2 | Yeni admission/attempt/normal business event kotası dolu; capacity_kind ilgili sınırdır; recovery/terminal reserve istisnası korunur |
| plan_in_use | 2 | Forget'in kendi transaction'ında doğrulanan operation FK bağı; başka IntegrityError state_invalid |
| operation_uncertain | 5 | Arm sonrası dış çağrı/sonuç commit'i belirsiz; alttaki kontrollü ErrorCode reason_code olur; retry yok |
| state_changed | 2 | Admission/arm'ın final credential ID/revision/hedefi, plan/approval snapshot veya beklenen store clock bağları değişmiş; güncel owner token uyuşmazlığı yukarıdaki lease_lost'tur |

## P01-5 hata kataloğu

Bu bölüm **uygulanan kapalı kod/mesaj/exit kataloğudur; P01-5b review ve kabulü kapandı**; 2026-10-29 kullanıcı yetkisiyle [ADR-0017](../decisions/0017-bounded-http-transport.md) ve [ADR-0018](../decisions/0018-stream-results-and-cancellation.md) review düzeltmeleri sonrası benimsendi. Yerel çıktı/iptal tüketicisi uygulanmıştır; public uzak komut eklenmez. Yeni normal CLI output seçeneği ve wire [stream referansında](stream-results.md), taşıma politikası [HTTP referansında](http-transport.md) tanımlıdır. Eski Result v1 ve text/JSON anlamı korunur.

| Kod | Exit | Kesin tetik |
|---|---:|---|
| transport_timeout | 1 | Shared total veya HTTP phase/pool timeout; arm sonrası aşağıdaki unknown öncelikli |
| transport_failed | 1 | TLS/bağlantı/protokol taşıma hatası; ham URL/exception yok |
| remote_access_denied | 3 | HTTP 401/403; retry yok, hesabın hangi yetkisinin eksik olduğu uydurulmaz |
| remote_rate_limited | 1 | 429 ve izinli retry/bütçe sonrası ret; sınırsız bekleme yok |
| remote_failed | 1 | Redirect dahil kabul edilmeyen diğer HTTP status veya endpoint'in doğrulanmış mantıksal başarısızlığı |
| invalid_response | 1 | Encoding/content/size/strict domain schema veya stream sequence/ID/terminalsonrası veri bozukluğu; 2xx başarıya yetmez |
| stream_interrupted | 1 | Terminal yokken clean EOF veya kabul edilmiş record/terminal adayı sonrası reset/truncated body; yarım line invalid_response, timeout transport_timeout; exact öncelik stream referansında |
| request_cancelled | 6 | Yerel çağrı/izleme SIGINT ile bırakıldı; rollback veya uzak iş cancellation başarısı değildir |
| output_closed | 6 | Stdout alıcısı kapandı; retry/ikinci write yok, stderr best-effort |
| output_write_failed | 1 | BrokenPipe dışı stdout I/O hatası; başarılı kalıcı iş değişmez |

Dispatch sırasında API sınırından taşan yerel `OSError` veya `UnicodeError`, mevcut `file_unreadable`/2 ile kontrollü raporlanır; stdout susturulmaz ve bu hata çıktı teslim hatası sayılmaz. `output_closed`/`output_write_failed` eşlemesi renderer yazım/serileştirme sınırına aittir. API’nin daha özel kontrollü hataları ve yan etki belirsizliği önceliği korunur.

Operation bağlamı olmayan yeni genel hatalar mevcut envelope şekli, `retryable=false`, `operation_id=null`, `details={}` kullanır. **Bağlanmış operation ID'li stream istisnası:** invalid_response/stream_interrupted ve diğer genel stream/çıktı hataları `OperationError(code, bound_operation_id)` ile taşınır; envelope ID bağlamla aynıdır, details tam `{reason_code: code, capacity_kind: null}` olur. Genel hata kodu/exit değişmez; yalnız ID taşımak hatayı operation_uncertain/5 veya job durum mutasyonu yapmaz. Gelen upstream hata mesajı/details doğrudan kopyalanmaz; kod yerel katalogdan güvenli zarfı yeniden kurar. Gerçek coordination hatası kendi mevcut OperationError/ID/kapalı details sözleşmesini kullanır. Sync ağ bridge active-loop/reentry/thread/PID uygunsuzluğu mevcut invalid_request/2'dir; state/env/arm/ağ öncesinde reddedilir. Effectful coordinator start sınırında timeout/iptal/yanıt belirsizliği **operation_uncertain/5** ve ilgili reason_code olarak kalır; config yayın belirsizliğinde mevcut config_write_uncertain/5 genel iptal/çıktı hatasından önceliklidir. Async kütüphane iptali CancelledError olarak cleanup sonrası yükselir; yeni hata kodları bunu global yutma izni değildir.
