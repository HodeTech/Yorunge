# Değişiklik günlüğü

Yayımlanan değişiklikler sürüm bazında kaydedilir. Bu dosyadaki `Unreleased` kaydı ürün yayını değildir.

## Unreleased

### Added — 2026-11-04

- ADR-0028: ilk Platform upload yolu aynı SHA-256’lı farklı adları ağ/create öncesinde açık `upload_duplicate_content`/exit 2 ile reddeder. Yerel Manifest/inspect/verify ve geçmiş kayıtlar korunur; tekrarlı adları bulmak için salt yerel rehber örneği eklendi. Özgün çoklu-ad upload desteği P02-R2’de açık kalır.
- Çalışma dalında `datasets upload` plan/review/approve/start/list/show/revoke/reconcile ve ortak Python API: private create/proje bağlantısı, bounded presign/PUT/confirm, kalıcı tekil intent/receipt, aynı operation üzerinde salt okuma toparlanması ve text/JSON/NDJSON. Varsayılan verified-only; yalnız açık risk/onayla explicit/unpriced deneme. Metadata sonucu yetki, fiyat veya uzaktan indirilmiş byte doğrulaması değildir. Otomatik replay, etkili resume ve indirme yoktur. [Kullanım rehberi](docs/reference/upload-workflows.md); nihai native/kurulum/CI/ayrı canlı kabul durumu [current](docs/roadmap/current.md) ve [kabul kaydında](docs/research/p02-2-implementation-validation.md) izlenir.

### Fixed — 2026-11-03

- Ortak `approval_required` mesajı işlemin gerektirdiği onay seçimine yönlendirir; plan digest’i dışındaki açık kabul yolları için yanlış toparlanma önermez. Kod ve exit 4 değişmez.

### Changed — 2026-11-02

- README genel EVREN kapsamı, mevcut/planlanan yetenek ayrımı, özgün kapak, isteğe bağlı erişilebilir CLI GIF’i, kısa başlangıç ve katkı bağlantılarıyla yenilendi; ayrıntılı mevcut CLI/Python örnekleri yerel kullanım rehberine taşındı.

### Fixed — 2026-11-02

- `--` sonrasındaki `--output=json/ndjson` biçimli dosya adları kullanım hatasının çıktı biçimini değiştirmez; makine biçimi yalnız gerçek seçeneklerden belirlenir. Var olan text/JSON/NDJSON hata zarfı ve exit kodları korunur.

### Fixed — 2026-11-01

- PR metadata edit’inde required check’in native merge kutusunda Expected kalmasına karşı sabit `offline-core` ve her olayda gerçek üç ortam doğrulaması; source/metadata concurrency ayrımı korunur. Platform raw/DTO doğrulaması küçük eşdeğer yordamlarla sadeleştirildi; raises hazırlıkları hedef assertion dışına taşındı.

- Discovery, credential ile karıştırılan yerel profil/hesap/proje tercihlerini ilk ağ isteğinden önce kontrollü reddeder; kısa sır proje URL’sine eklenmeden karşılaştırılır. LLM/Platform nihai dinamik sonuç alanları da seçili literal denetiminden geçer.
- Hesap hazırlığında dolu Platform tercihleri normal config profiline aktarılır; yalnız seçili anahtarı çocuk sürece veren çalıştırılabilir discovery örneği ve önceki hazırlıklar için geçiş yolu eklendi.

P01 tamamlandı; son P01-5a/b ve P01-6b paketi [PR #11](https://github.com/HodeTech/Yorunge/pull/11) ile development’a [bc9532c](https://github.com/HodeTech/Yorunge/commit/bc9532cd66c76dc4126162fabd4307c2fdaf4027) merge’ünde alındı. [Merge/CI kanıtı](docs/research/p01-remaining-implementation-validation.md#development-merge-kapanışı). Bu kayıt paket yayını veya Master/release aktarımı değildir.

### Added — 2026-11-01

- P02-1 ile yerel `datasets inspect/verify` ve ortak Python API: taşınabilir Manifest v1, descriptor ile yeniden hash, root dışında 0600/no-clobber yayın, küçük text/JSON/NDJSON özeti ve uyuşmazlık exit 7. Kod review’ları, üç temiz kurulum turu ve kaynak bağlı native/gerçek kanıt kabulü tamamlandı; üç ortam source/metadata CI ve kalıcı kanıt kabulü geçti. [PR #13](https://github.com/HodeTech/Yorunge/pull/13), 2 Kasım’da [50d68b1](https://github.com/HodeTech/Yorunge/commit/50d68b1deab80d6fe14749d556efde1f103b5759) ile development’a teslim edildi; paket yayını değildir. Upload ve veri formatı değerlendirmesi eklenmedi.

- `context discover --service evren-platform`: kapalı ID/liste/proje gözlemi, profil veya açık proje detail seçimi ve ortak Python API. ADR-0022 ile nihai dar consumer sonucu daima unverified/unknown; strict tüketilen alan ve seçili literal denetimi sonrası metadata atılır. Gerçek üç uç/seçili-detail kabulü geçti; son kaynak/review/kurulum/M5 ve üç ortam PR CI kabulü tamam; PR #12 development teslimi tamam, doğrulanmış kimlik/bağ P02-R1’de açık. Ham metadata ve kişisel profil alanları yayımlanmaz; bildirilen ID’ler kişiye bağlanabilir.

### Added — 2026-10-31

- P02 kapsamında açık `context discover --service evren-llm` ve ortak `api.discover_context`: mevcut store, tek credential snapshot’ı ve bounded GET terms/status; text/JSON/NDJSON. Auth ve uzak hesap/proje doğrulanmış sayılmaz; Platform’un nihai dar gözlem sınırı 1 Kasım ADR-0022 ile ayrıca benimsendi. LLM ilk canlı terms, Platform consumer/live ve bütünleşik kaynak/review/kurulum/M5/üç ortam PR CI kabulü tamamlandı; PR #12, 1 Kasım’da 9f30fd2 merge’üyle development’a teslim edildi; [merge/CI kapanışı](docs/research/p02-0-implementation-validation.md#development-merge-kapanışı) kayıtlıdır.

### Changed — 2026-10-29

- PR #10'un büyük ölçüm çıktıları özgün baytları korunarak gzip arşivine ayrıldı; küçük manifest/indeks ve CI bütünlük kontrolü eklendi. CodeRabbit yalnız raw arşivleri dışlar, ajan rehberi hedefli kanıt incelemesini tanımlar. Arşivler sdist'e girmez; sabit test vektörleri ve ölçüm kodu normal incelemede kalır.

### Fixed — 2026-10-29

- Provider run ID/status, HTTP ile aynı kısa-secret tam eşitlik ve ≥8 UTF-8 byte alt dize kuralını kullanır; meşru kısa-secret yanıtları gereksiz unknown olmaz.
- Arm commit’i sonrası bütçe dolduğunda kalıcı dispatch niyeti/operation ID belirsizlik zarfında korunur; ikinci gönderim açılmaz.
- Raw stream kabulü anlık RSS baseline, aynı Linux kernel sayaç ailesi ve bağımsız 64/8 MiB kapılarıyla doğrulanır; tarihsel HWM büyüme/ek bellek kullanımını maskeleyemez.

### Added — 2026-10-29

- Session-owned async HTTPX taşıması ve sync Runner; canonical hedef/credential, bounded deadline/retry, TLS/cookie/log/yanıt doğrulama sınırları. Doğrudan SDK bağımlılığı veya EVREN endpoint adaptörü eklenmedi.
- Tipli StreamEvent v1, bounded NDJSON codec, HTTP message EOF’a kadar tutulan terminal ve mevcut normal CLI komutlarında tek-result NDJSON. Eski Result/JSON v1, plan digest’i ve yerel komutların lazy import sınırı korunur.
- UTF-8 byte çıktı, kontrollü SIGINT/pipe/I/O ve kritik config yayınında korunmuş uncertainty 5. Altı adım ve ikişer fresh review ile P01 altyapısı uygulandı; kullanıcı review sonrası native raw v2, Accepted ADR-0019 kaynak bağlı M5 startup/jobs ve strict Linux tanısı, Sonar/fresh referans ve gerçek üç ortam kabulü tamamlandı; [kapanış kaydı](docs/research/p01-remaining-implementation-validation.md#ilk-runtime-release-ci-kapanışı). PR #11 development teslimi tamamlandı; Master/release ve yayın ayrıdır.
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
