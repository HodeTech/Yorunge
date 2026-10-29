# Değişiklik günlüğü

Yayımlanan değişiklikler sürüm bazında kaydedilir. Bu dosyadaki `Unreleased` kaydı ürün yayını değildir.

## Unreleased

P01-4, [PR #10](https://github.com/HodeTech/Yorunge/pull/10) ile development’a alındı; [merge/CI kanıtı](docs/research/p01-4-implementation-validation.md#development-merge-kapanışı). Bu kayıt paket yayını veya Master/release aktarımı değildir.

### Changed — 2026-10-29

- PR #10'un büyük ölçüm çıktıları özgün baytları korunarak gzip arşivine ayrıldı; küçük manifest/indeks ve CI bütünlük kontrolü eklendi. CodeRabbit yalnız raw arşivleri dışlar, ajan rehberi hedefli kanıt incelemesini tanımlar. Arşivler sdist'e girmez; sabit test vektörleri ve ölçüm kodu normal incelemede kalır.

### Fixed — 2026-10-29

- Provider run ID/status, HTTP ile aynı kısa-secret tam eşitlik ve ≥8 UTF-8 byte alt dize kuralını kullanır; meşru kısa-secret yanıtları gereksiz unknown olmaz.
- Arm commit’i sonrası bütçe dolduğunda kalıcı dispatch niyeti/operation ID belirsizlik zarfında korunur; ikinci gönderim açılmaz.
- Raw stream kabulü anlık RSS baseline, aynı Linux kernel sayaç ailesi ve bağımsız 64/8 MiB kapılarıyla doğrulanır; tarihsel HWM büyüme/ek bellek kullanımını maskeleyemez.

### Added — 2026-10-29

- Session-owned async HTTPX taşıması ve sync Runner; canonical hedef/credential, bounded deadline/retry, TLS/cookie/log/yanıt doğrulama sınırları. Doğrudan SDK bağımlılığı veya EVREN endpoint adaptörü eklenmedi.
- Tipli StreamEvent v1, bounded NDJSON codec, HTTP message EOF’a kadar tutulan terminal ve mevcut normal CLI komutlarında tek-result NDJSON. Eski Result/JSON v1, plan digest’i ve yerel komutların lazy import sınırı korunur.
- UTF-8 byte çıktı, kontrollü SIGINT/pipe/I/O ve kritik config yayınında korunmuş uncertainty 5. Altı adım ve ikişer fresh review ile P01 altyapısı uygulandı; kullanıcı review sonrası native raw v2, Accepted ADR-0019 kaynak bağlı M5 startup/jobs ve strict Linux tanısı, Sonar/fresh referans ve gerçek üç ortam kabulü tamamlandı; [kapanış kaydı](docs/research/p01-remaining-implementation-validation.md#kullanıcı-review-kapanışı). Development PR review/merge ve yayın ayrıdır.
- Linux/Python 3.11/3.14 ve macOS/Python 3.11 tam uyumluluk, build ve iki temiz kurulum; son kaynakla startup, zorunlu kaynak-bağlı 200 ms jobs referansı, raw stream RSS ve yoğun 5 s state/migration kapıları. Başarısız ortam ölçümleri ve referansın donanım sınırı açıkça saklanır.
- Jobs okumasında gereksiz composition import maliyeti ve eşdeğer ASCII kontrol taraması azaltıldı; SQL/digest/tam validation/FK kuralları korundu. Python 3.14 platform taklidi ve izole fixture interpreter/TLS tanılama sorunları düzeltildi.
- Şema 6 operation/attempt/terminal outcome, aynı plan tekliği ve kalıcı dispatch bağı; current credential/onay transaction kontrolü, lease/fencing ve tek kullanımlık süreç izni.
- Trusted salt gözlem, execution/delivery ayrımı, bounded recovery ve tarihçeyi koruyan kimlik reset preview v3.
- Yerel `jobs list/show` ve ortak Python API; store/filtre bağlı keyset cursor, bounded toplu liste sorgusu ve son yerel kayıt uyarısı.
- Ayrı süreç/SIGKILL/yarış ve azami hacim kaynak kabulü; [adım ve review kaydı](docs/research/p01-4-implementation-validation.md). Dört adım/ikişer fresh review ve son 182f695 ürün kaynağında 1.779 test/iki temiz kurulum/son kaynak bütçeleriyle yerel paket kabulü tamamlandı; canlı EVREN ve public run teslimi değildir.
- Değişmeyen geçerli sağlayıcı gözlemi operation geçmiş kotasını tüketmez; yeni kanıt ve gerçek recovery geçişi kaydedilir. Son owner/credential/lease/read yetkisi kontrolleri korunur.

### Added — 2026-10-28

- Ayrı ScopeV2/kanıt, tam credential/hedef kapsamı, kalıcı cache/clock generation, bounded TTL/kota ve açık cached/refresh CLI/Python sorgusu.
- Değişmez execution v2 planı, descriptor üzerinden yerel input hash/root kimliği, kayıt/list/show ve güncel validity.
- Güncel validation sonrası tam digest onayı, idempotent onay/revoke ve seçili plan/current approval için atomik forget.
- Cache/plan/onay runtime restore/recover, eski intent yükseltmeleri ve plan/onay fingerprint bağlı maintenance preview v2.
- Kurulu wheel/sdist üzerinde stateful komut kontrolleri, 1.024 kayıt başlangıç ve ayrı süreçlerde büyük input bellek/hash kanıtı.

Eski stateless offline v1 değişmedi. Public execution producer araç/uzak yetki/tam girdi kapanışı eksiklerini açık blocked gösterir; run, operation/lease ve gerçek EVREN yoktur. [P01-3 kabul/review kanıtı](docs/research/p01-3-implementation-validation.md).

### Fixed — 2026-10-28

- CLI yalnız seçilen komut ailesinin seçeneklerini parse/help sırasında oluşturur; mevcut yardım, seçenek önceliği ve hata sözleşmesi korunur.
- Başlangıç CI ölçümü ayrı frozen runtime wheel/venv ortamlarında aynı host'ta AB/BA taban-aday karşılaştırması yapar; tam örnekler, kaynak/paket hash'leri ve runner bilgisi saklanır. Mutlak 500/200 ms kapıları korunur; [yerel kabul ve dış CI sınırı](docs/research/startup-ci-reliability.md) kayıtlıdır.

- Store genelindeki cache/proof/conflict ve plan/onay expiry sınırlarını aynı terminal snapshot’ta denetleyen şema 5; restart/saat geri dönüşünde başka bir kaydın yeniden etkinleşmesi önlendi.
- Eski migration 1–4 kimliklerini koruyan V2 manifest ve aynı hash-doğrulanmış kaynak baytlarıyla yürütülen veri dönüşümü.
- Yinelenen clock yazması ve kullanılmayan şema kurulum maliyeti azaltıldı; yoğun migration’da sınırlı kullanım senaryosu içi doğrulama özeti kullanıldı. Başarılı ölçümler ile açık merge-CI başlangıç bütçe reddi [kapanış kaydında](docs/research/p01-3-implementation-validation.md#pr-9-development-merge-kapanışı) ayrı tutulur.

### Fixed — 2026-10-27

- Yerel context yolunda kullanılmayan kimlik/bakım modellerinin eager import maliyeti kaldırıldı; Linux başlangıç bütçesi korundu.
- Araştırma probe çıktıları belgelenmiş sabit no-clobber hedeflere sınırlandı.

- Bozuk YAML scalar ve collection tag'leri güvenli `invalid_recipe` hatasına dönüştürüldü; ham parser istisnası ve girdi yansıması kapatıldı.
- Manifest/hizmet URL'sinde C0/DEL/C1 kontrol karakterleri ve boş URL userinfo reddedildi; YAML scalar/mapping düğüm türleri doğrulandı.
- Capability sorgusunun destek kaydı ile plan hazırlamanın hata çıkışı belgede ayrıldı.
- Wheel/sdist ham üye yolu, kök, dosya türü ve çakışma denetimi güçlendirildi; iki dağıtımın sürüm eşleşmesi ve JSONL kurulum kanıtı akışı netleştirildi.

### Added — 2026-10-27

- Hizmete bağlı tek env çözümleme, korumalı secret taşıyıcısı ve kanonik hedef kapısı.
- SQLite store/migration, özel kalıcı credential kimliği/nesli ve güvenli no-clobber snapshot temeli.
- Önizleme/digest onaylı identity reset, identity-only restore ve kesintiden açık recover.
- Atomik config init/profil/proje yönetimi, özgün backup ve sır/K içeriği okumayan yerel doctor.

- EVREN platformunun kapsamlı yardımcı aracı olarak ürün kapsamı ve yetenek matrisi.
- ForgeLM varsayılanı ve kullanıcı tarafından seçilebilen muadil araçlar için sağlayıcı sözleşmesi.
- Mimari, modül sınırları, standartlar, ADR'ler, yol haritası ve araştırma kanıt rehberi.
- MIT lisansı ve temel katkı/ajan yönergeleri.
- `0.1.0.dev0` geliştirme paketi, gerçek `yorunge` konsol girişi ve ortak Python kullanım senaryoları.
- Strict TOML/dar YAML, yerel context, capability durumları ve sabit seçim/digest içeren yürütülemez offline plan.
- Offline sözleşme/CLI testleri, format/lint/type, build/temiz kurulum, belge ve başlangıç kontrolleri; CI tanımı.

27 Ekim ilk diliminde yayımlanmış paket, HTTP/EVREN, gerçek araç adaptörü, eğitim, SQLite operasyon kaydı ve artefakt teslimi yoktu. [İlk dilim kabulü](docs/research/p01-core-validation.md).

### Changed — 2026-10-27

- Roadmap epikleri dar teslim, bağımlılık ve dış kapılarla netleştirildi; ilk hazır P01-2a kartı ve ajan çalışma rehberi eklendi. Ürün capability'si eklenmedi.
- Ortak repo skill kütüphanesi ve Claude alias'ları, metadata/bağımlılık kontrolleri ve ilgili CI kapısı oluşturuldu.
- `development` hedefli zorunlu PR, merge commit ve kullanıcı kontrollü `Master` release akışı benimsendi; CI dal filtreleri ve güvenilen metadata kontrolü eklendi.
- Yerel analiz arşivi `docs/analysis/private/` altına taşınıp Git ve yayın kapsamından dışlandı.
- Paylaşılabilir kaynak kaydı resmî platform/araç belgeleri ve proje kararlarıyla sınırlandırıldı.
- Özel analizlerin kod, doküman ve commit/PR içeriklerinde referans verilmemesi kuralı eklendi.
