# Yetenek kaydı sözleşmesi

**Durum:** Offline v1 ve açık yerel cache v2 uygulandı; P01-3a yerel kabulü tamamlandı, canlı keşif yok. **Tarih:** 2026-10-28.

P01-3 için ayrı v2/cache ayrıntısı [Accepted ADR-0013](../decisions/0013-scoped-capability-cache.md) ve ona bağlı [CapabilityScopeV2 wire](capability-scope-v2.md) ile 2026-10-27 kullanıcı onayıyla benimsenmiştir. Tasarım onayı aşağıdaki uygulanmış v1'i veya henüz benimsenmemiş tasarımı değiştirmez; [hazırlık incelemesi](../research/p01-3-readiness-review.md).

## Uygulanan offline görünüm

`yorunge capabilities` / `yorunge.api.inspect_capabilities` seçilmiş context/task/tool/execution kapsamını döndürür. `planning.offline=supported` yalnız uygulanmış yerel şema/seçim politikasını anlatır; dış araç/EVREN desteği değildir. Eksik adaptör veya uyumsuz birleşim `unsupported`, doğrulanmamış hizmet/yetki/runtime `unknown`, açıkça eksik proje önkoşulu `requires_access` olur. `evren-workspace` genel kullanıcı sözleşmesi bilinmediği için erişim var/yok hükmü verilmez.

Kanıt `local_policy` veya `not_verified`; `checked_at`/`expires_at`, credential kimliği/nesli, yetki kapsamı ve araç sürümü null'dır. Bu bilinmeyen alanlar runtime/canlı kanıt gibi doldurulmaz. Aşağıdaki genel alanlardan `constraints` ve `provider_request_id` bu dar modelde henüz yoktur; bilinmeyen alanlar reddedilir. Offline v1 cache/tazelik eklemez; aşağıdaki ayrı v2 sorgusu bunları uygular. Plan yalnız bu kayıtları ve engelleri sabitler; yürütülemez.

| Alan | Anlam |
|---|---|
| `schema_version` | Kaydın biçim sürümü |
| `capability_id`, `task` | İncelenen işlem ve görev |
| `scope` | `service_id`, `service_origin`, `api_base_path`, `account_id`/`project_id`, `credential_id`/`credential_revision`, `authorization_scope`, model, tool/sürüm ve execution |
| `support` | `supported`, `unsupported`, `unknown`, `requires_access` |
| `reason_code`, `message` | Kararlı kod ve insan açıklaması |
| `constraints` | Model/format/parametre/boyut/süre gibi doğrulanmış sınırlar |
| `evidence` | Şema/kılavuz/istemci/sentetik test/canlı hesap kanıtı ve kaynak |
| `checked_at`, `expires_at` | UTC son doğrulama ve tazelik sınırı |
| `provider_request_id` | Varsa sınırlı tanılama kimliği; sır değildir |

`supported`: bu kapsamda yeterli kanıtla destek var. `unsupported`: bu kapsamda açık uyumsuzluk kanıtı var. `unknown`: yeterli/tutarlı kanıt yok. `requires_access`: işlem veya özellik biliniyor ama bu bağlamın yetkisi/erişim koşulu sağlanmadı.

Hizmet ve yetki bağlarının anlamı [planın içerdiği bağlarla](../architecture/execution-model.md#planın-içerdiği-bağlar) aynıdır; kayıtta sır veya anahtarın ham hash'i tutulmaz. Cache anahtarı `capability_id`, `task` ve `scope` alanlarının tamamını kapsar. Aynı hesap/projede iki ayrı anahtarın `supported` sonucu paylaşılmaz; aynı env/keychain referansında anahtar değişirse yetki kimliği/nesli yenilenir. İzin kapsamı değişince eski kayıt kullanılmaz. Yetki kimliği veya kapsamı bilinmiyorsa hesap özelinde `supported` sonucu yeniden kullanılamaz; gerekli doğrulama yapılana kadar `unknown` veya erişim eksikliği kanıtlıysa `requires_access` kullanılır. Genel şema/kılavuz kanıtı hesap yetkisi doğrulaması sayılmaz.

Registry hedef karşılaştırması ve kalıcı kimlik/nesil için [credential binding v1](credential-binding-v1.md) P01-2 ile uygulandı; [PR #6](https://github.com/HodeTech/Yorunge/pull/6) development’a alındı. Mevcut v1 offline capability kaydı değişmedi; açık v2 cache aşağıdadır, execution plan tüketicisi P01-3b'dir. İki sürecin farklı credential snapshot'ı revision thrash'ine yol açabilir; revision anahtardan çıkarılmaz ve otomatik yeniden çözümleme döngüsü açılmaz.

## Açık cache v2 sorgusu

`capabilities --cached|--refresh [--state-dir PATH]` / `api.query_capabilities` stateless v1'den ayrıdır. Her iki yol private state oluşturabilir/migrate edebilir ve kalıcı clock metadata yazar. Uzak scope için seçilmiş env referansı varsa yalnız o değer bir kez gözlenir; referans yoksa credential bağı bilinmeyen kalır. `--cached` producer/discovery çağırmaz; `--refresh` yalnız bu sürümün yerel politika üreticisini çağırır, ağ/EVREN erişimi yoktur.

Sonuç `data.records[]` içinde `key`, `hit`, `freshness`, `effective_support`, `reason_code`, `message`, `checked_at`, `valid_until`, `record` ve `historical_candidates` taşır. `freshness`: `fresh`, `miss`, `stale`, `clock_anomaly`, `historical_only`. Etkin karar ile saklanan tarihsel `record.support` ayrıdır; eski supported yeni etkin destek sayılmaz. Hit olmayan scope unknown döner; gerekli doğrulama otomatik başlatılmaz.

`record` ayrı `schema_version=2`, `key={capability_id,task,scope}`, `support`, `reason_code`, `message`, `evidence[]`, `checked_at`, `expires_at`, `conflict_until` biçimidir. [Scope wire](capability-scope-v2.md) kapalıdır. Her evidence kind/producer kimliği+sürümü/policy sürümü/provenance/support/reason, tipli `constraints[{name,value}]` ve özgün checked/expiry taşır. Constraint value sınırlı string, boolean veya negatif olmayan signed-64 integer'dır; serbest provider dict'i yoktur. Dizi sırası aggregate çözümlemede kanonikleştirilir. Genel tablodaki gelecekteki `provider_request_id` bu v2 üreticisinde yoktur; bilinmeyen alan reddedilir.

Tam anahtar/binding ayrımı, 300/60/30 saniyelik TTL, son süre kapısı, kalıcı clock generation, tarihsel aday projection, concurrent producer merge ve çelişki/overflow saklaması [ADR-0013](../decisions/0013-scoped-capability-cache.md) uyarınca uygulanır. Kayıtların kaynak sürümü güncel composition manifestiyle eşleşmezse etkin karar unknown olur. Public API kanıt/izin/producer nesnesi kabul etmez.

SQLite şema 1→2 cache/clock tablolarını immutable migration ve doğrulanmış backup ile ekler. Reset yeni epoch/clock alanı kurar, cache temizlenir; kimlik geçmişi korunur. Eski runtime restore intent'inin sağlam stage/live çifti, kaynak backup artık yokken de yeni şemaya yükseltilebilir; otomatik yeni epoch üretilmez. Operation-capable runtime'da restore kapalıdır. [Kabul/review kaydı](../research/p01-3-implementation-validation.md) uygulamanın gerçek durumunu taşır.

Bir kaydın `supported` olması başka hedef/yetki/hesap/araç/sürüm/ortama yayılmaz. Eski kayıt, yenilenmesi gereken kritik planda otomatik geçerli sayılmaz. Her 403 access eksikliği de değildir; yanlış key/endpoint veya sözleşme hatası ayrıca ayrıştırılır.

## Store genelinde süre kapısı

**PR #9 prototipi:** Bu şema 5 uygulaması development'a merge edilmedi. Checksum kapsamındaki veri dönüşümü [ADR-0015](../decisions/0015-checksummed-data-migrations.md) onayını bekler; mevcut backfill manifest engeli kapanmadan teslim edilmiş sayılmaz.

Son süre kapısı yalnız sorgulanan kaydın expiry'sini kullanmaz. Kalıcı cache kayıtlarının aggregate/evidence/conflict süreleri ile bütün plan/onay expiry'lerinden sonraki global sınır aranır. Cache başına en çok 10 ayrı zaman, 1.024 cache + 1.024 plan + 1.024 onay için en çok 12.288 sınır vardır. Sıcak yol üç sıralı indeks araması yapar; bütün payload'ları taramaz. Kaydı okurken kendi en çok 10 türetilmiş zamanı da tam karşılaştırılır.

Clock, bağlar ve global sınır aynı SQL read snapshot'ında kalırken terminal UTC örneği alınır. Araya daha erken expiry içeren bir writer commit'i giremez. Yeni geçilen global veya kullanılan proof sınırı kalıcı watermark'a taşınır; son UTC/monotonic/bağ kapısı yeniden çalışır. Böylece uzun ömürlü bir kayıt sorgusu sırasında başka bir kaydın gözlenen expiry'si geçmişse restart sonrası saat geri dönüşü onu yeniden etkinleştirmez. Eşzamanlı writer'ların tarihleri değiştirmesi toplam deadline ve ayrıca 12.289 kontrol sınırıyla sınırlanır; tükenmede `state_busy` gelir. Producer/env/discovery otomatik tekrarlanmaz.

`checked_at` terminal geçerlilik noktasıdır; kalıcı watermark son başarılı clock transaction'ının noktasıdır. İki değerin her mikrosaniyede eşitliği garanti edilmez. Global expiry sınırı geçilmediyse yeni fsync gerekmez; hiçbir başarılı sonuç gözlenen bir kalıcı expiry'nin gerisinde kalmış watermark'a dayanmaz. Güvenilir dış saat, gözlenmeyen geri dönüş veya DB+K+clock'un birlikte eskiye alınmasını saptama garantisi verilmez; noktasal geçerlilik sonraki caller anı için süreyi durdurmaz.

Bu kayıt dış uyumu anlatır. Yörünge özelliğinin planlandı/uygulandı/yayımlandı durumu [yetenek matrisindedir](../capability-matrix.md); iki durum tek enum'da birleştirilmez.
