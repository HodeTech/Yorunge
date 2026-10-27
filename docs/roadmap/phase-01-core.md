# P01 — Hafif çekirdek ve gerçek sözleşmeler

**Durum:** Uygulanıyor; ilk çevrimdışı dilim yerelde doğrulandı. **Bağımlılık:** P00. **Yetenekler:** C01/C02/C12/C13 temeli.

## İş sırası

| İş | Kapsam | Kabul |
|---|---|---|
| P01-1 | Paket/CLI/HTTP/şema spike'ı, kaynak yerleşimi | Gerçek lock/build; hafif `--help`; CLI/HTTP/şema kütüphanelerinin seçimi ve ilk ölçüm |
| P01-2 | Config/context/secret ref | Profil önceliği, açık proje seçimi, yanlış hizmet ve sır yansıması testleri |
| P01-3 | Capability ve plan modeli | Hedef/yetki/digest bağları, kapsam/tazelik, unknown/access ayrımı; default/override çözümleme |
| P01-4 | SQLite operation/attempt, migration, sahiplik | Çökme, kilit, bozuk kayıt, lease devri ve tekrar gönderim kontrolü |
| P01-5 | Ortak HTTP/sonuç/hata ve CLI/Python hattı | Loopback, deadline/retry, JSON/NDJSON ve iptal sözleşmesi |
| P01-6 | CI ve geliştirici kurulumunu bağlamak | Gerçek unit/contract/integration ve performans kontrolleri; doküman komutları güncel |

## İlk teslim durumu — 2026-10-27

| İş | Tamamlanan alt küme | Kalan |
|---|---|---|
| P01-1 | Paket, `src` yerleşimi, konsol, lock/build, CLI/şema/YAML deneyi, başlangıç ölçümü | HTTP seçimi bu ağsız teslimde gerekmiyor; P01-5'e taşındı |
| P01-2 | Strict TOML, yerel context, açık proje tercihi, env referansı şeması | Secret erişimi, credential kimliği/nesli, güncel hizmet/yetki bağları |
| P01-3 | Dört destek durumu, seçim önceliği, sabit seçimli offline draft ve digest | Hesaba bağlı kanıt/tazelik/cache; yürütme geçerliliği |
| P01-4 | Yok | SQLite/operation/attempt/migration/lease bütünü |
| P01-5 | Ortak CLI/Python yerel kullanım senaryoları, tipli sonuç ve JSON hata sınırı | HTTP, retry/deadline, streaming ve iptal |
| P01-6 | Test/lint/type/build/perf ve PR #1 üzerinde gerçek Ubuntu CI kanıtı | İlerideki P01 özelliklerine ait kontroller |

[Kabul kanıtı](../research/p01-core-validation.md). Tam faz tamamlandı diye işaretlenmez.

## Uçtan uca dilim

Bu teslimin sınırı: küçük offline görev → context → capability → seçim → şeması doğrulanmış plan taslağı → tipli planlama sonucu. Yürütme, veri/model dosyası doğrulaması, operation ve artefakt yoktur. İleride P01-1–P01-5 birikince test double'ı yalnız test/fixture içinde tutularak kalıcı durum ve teslim sınırı da sınanır. Üründe sahte execution veya eğitim başarısı bulunmaz. Uzak işler ve gerçek araçlar ayrıca kendi entegrasyon kapılarından geçer.

## Çıkış kapısı

Yardım/sürüm için ağ/DB/keychain/ML import yoktur. Kritik kayıt hatasında yan etki başlamaz. Varsayılan ForgeLM çözümü ile açık tool tercihi plan düzeyinde sınanır; adaptör henüz yoksa açık unsupported/unavailable sonucu verir. Makine çıktısı ve çıkış kodları contract testleriyle korunur. Başlangıç ve kaynak bütçeleri ölçülür.

Çoklu OS/Python hedefi gerçek matriste tanımlanır; destek sözü yalnız koşulan/kanıtlanan kapsamı taşır. Büyük UI, live GPU işi ve genel plugin yükleyici bu fazın işi değildir.
