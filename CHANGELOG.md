# Değişiklik günlüğü

Yayımlanan değişiklikler sürüm bazında kaydedilir. Bu dosyadaki `Unreleased` kaydı ürün yayını değildir.

## Unreleased

### Added — 2026-10-28

- Ayrı ScopeV2/kanıt, tam credential/hedef kapsamı, kalıcı cache/clock generation, bounded TTL/kota ve açık cached/refresh CLI/Python sorgusu.
- Değişmez execution v2 planı, descriptor üzerinden yerel input hash/root kimliği, kayıt/list/show ve güncel validity.
- Güncel validation sonrası tam digest onayı, idempotent onay/revoke ve seçili plan/current approval için atomik forget.
- Cache/plan/onay runtime restore/recover, eski intent yükseltmeleri ve plan/onay fingerprint bağlı maintenance preview v2.
- Kurulu wheel/sdist üzerinde stateful komut kontrolleri, 1.024 kayıt başlangıç ve ayrı süreçlerde büyük input bellek/hash kanıtı.

Eski stateless offline v1 değişmedi. Public execution producer araç/uzak yetki/tam girdi kapanışı eksiklerini açık blocked gösterir; run, operation/lease ve gerçek EVREN yoktur. [P01-3 kabul/review kanıtı](docs/research/p01-3-implementation-validation.md).

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

Yayımlanmış paket yoktur. HTTP/EVREN, gerçek araç adaptörü, eğitim, SQLite operasyon kaydı ve artefakt teslimi henüz uygulanmadı. [İlk dilim kabulü](docs/research/p01-core-validation.md).

### Changed — 2026-10-27

- Roadmap epikleri dar teslim, bağımlılık ve dış kapılarla netleştirildi; ilk hazır P01-2a kartı ve ajan çalışma rehberi eklendi. Ürün capability'si eklenmedi.
- Ortak repo skill kütüphanesi ve Claude alias'ları, metadata/bağımlılık kontrolleri ve ilgili CI kapısı oluşturuldu.
- `development` hedefli zorunlu PR, merge commit ve kullanıcı kontrollü `Master` release akışı benimsendi; CI dal filtreleri ve güvenilen metadata kontrolü eklendi.
- Yerel analiz arşivi `docs/analysis/private/` altına taşınıp Git ve yayın kapsamından dışlandı.
- Paylaşılabilir kaynak kaydı resmî platform/araç belgeleri ve proje kararlarıyla sınırlandırıldı.
- Özel analizlerin kod, doküman ve commit/PR içeriklerinde referans verilmemesi kuralı eklendi.
