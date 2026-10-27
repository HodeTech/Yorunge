# Değişiklik günlüğü

Yayımlanan değişiklikler sürüm bazında kaydedilir. Bu dosyadaki `Unreleased` kaydı ürün yayını değildir.

## Unreleased

### Fixed — 2026-10-27

- Bozuk YAML scalar ve collection tag'leri güvenli `invalid_recipe` hatasına dönüştürüldü; ham parser istisnası ve girdi yansıması kapatıldı.
- Manifest/hizmet URL'sinde C0/DEL/C1 kontrol karakterleri ve boş URL userinfo reddedildi; YAML scalar/mapping düğüm türleri doğrulandı.
- Capability sorgusunun destek kaydı ile plan hazırlamanın hata çıkışı belgede ayrıldı.
- Wheel/sdist ham üye yolu, kök, dosya türü ve çakışma denetimi güçlendirildi; iki dağıtımın sürüm eşleşmesi ve JSONL kurulum kanıtı akışı netleştirildi.

### Added — 2026-10-27

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
