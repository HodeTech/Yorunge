---
id: P02-R1
phase: P02
status: draft
size: L
depends_on: [P02-0a, P02-0d]
capabilities: [C01, C02, C13]
---
# P02-R1 — Doğrulanmış hizmet kimliği ve seçili context bağı

**Tarih:** 2026-11-01. **Durum:** Draft araştırma/tasarım takip işi; uygulama yetkisi veya ready iddiası değildir. **Sahip:** P02 / identity-context modülü. Bu kart özgün doğrulanmış kimlik/proje bağı ihtiyacının kanonik sahibidir; [B14](../backlog.md) yalnız bu karta işaret eder. [ADR-0022](../../decisions/0022-observed-platform-consumer-contract.md) 2026-11-01 kullanıcı onayıyla P02-0b/d’nin dar gözlem tesliminden ayrılan ihtiyaç burada takip edilir. Mevcut gözlem teslimi bu doğrulanmış kimlik ihtiyacını tamamlamaz.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı seçtiği hizmet hedefi/credential ile hangi provider principal’ın doğrulandığını, seçili account/organizasyon/projenin bu principal ile ilişkisinin hangi kanıtla kurulduğunu ve varsa göreve özgü iznin neyi kapsadığını görür. Mevcut PlatformContextDiscovery v1 yalnız reported ID ve unverified/unknown gözlemdir; yerel credential UUID/revision uzak principal değildir. LLM introspection alanı sunulmuyorsa kullanıcı hesabı uydurulmaz.

## Giren ve girmeyen kapsam

Hizmet/hedef/endpoint/parametre kapsamlı auth/principal/account/project ilişki kanıtı araştırması; public doğrulama sonucunun compatibility tasarımı; bağımsız otorite portunun gerçek tüketicide nasıl kullanılacağının belirlenmesi girer. Gerekli permission çözümlemesi yalnız ilgili görev/endpoint kapsamıyla ele alınır. Araştırma/tasarım, kod ve kabul alt işleri ready öncesi dar kartlara bölünür; bu L kart tek uygulama adımı değildir.

Gözlem verisini yetkiye çevirmek, browser JWT fallback, hesap/key yaratmak, inference/upload/ücretli işlem veya bütün P02 tüketicilerini bu karta otomatik bağlamak girmez. Yan etkili her tüketici kendi güncel otorite/onay/credential kapısını ayrıca kapatır. P02-R1, Accepted ADR-0022 kapsamında mevcut tek P02-0 PR’ının verified önkoşulu değildir; özgün ihtiyacın açık takip sahibidir.

## Bağımlılıklar ve kararlar

P02-0a kaynak kaydı ve P02-0d kapalı gözlem ayrımı girdidir. Hazırlık araştırması bugün yapılabilir; üretim uygulaması için provider’ın yetkili auth/principal/ilişki sözleşmesi veya aynı anlamı kapatan doğrulanabilir kaynak gerekir. Yalnız key 200/no-key 401 veya aynı ID’lerin görünmesi yeterli değildir. Key grameri bilinmeden iyi biçimli invalid-key kontrolü iddiası yoktur. Kanıt gelmezse draft/blocked neden ve sonraki adım burada kalır; ihtiyaç tamamlanmış sayılmaz.

ADR-0013 bağımsız otorite, ADR-0014/0016 son transaction karşılaştırması korunur. Mevcut v1 unverified sabitlerini yerinde verified yapan değişiklik yapılmaz. Yeni public kayıt/API sürümü veya başka temel karar gerekiyorsa ayrı ADR kullanıcı onayına sunulur; bu kart şimdiden bir yeni biçim/endpoint benimsemez.

## Sözleşme ve uygulama sınırı

Kanonik kullanım alanı identity-context; tipli domain/application, gerçek hizmet adaptörü ve ortak CLI/Python kullanımı. Kaynak kaydı normalized service/origin/API kökü/method/endpoint/parametre kapsamı, tarih/sürüm ve kanıt türünü taşır. Gözlem, doğrulanmış principal/bağ ve göreve özgü permission ayrı iddialardır. Cache/yerel kimlik/istemci rol adı kendi başına authority değildir.

## Kabul

1. Principal/account/organizasyon/project alanlarının anlamları, seçili bağ ve key-auth kapsamı kaynakla kapatılır; yok/unknown desteklenmiş gibi sunulmaz. Her iddia için gözlem ile bağımsız otorite ayrılır.
2. Provider’ın sunmadığı kimlik null/not_exposed/unknown kalır. Salt read gözlemi veya header yokken 401 doğrulanmış key/principal değildir; iyi biçimli kontrol gereken yerde gramer ve yetki/bütçe önce kapanır.
3. Gerçek read-only kabulde doğru bağ ve yanlış/erişilemeyen seçim, cross-service/target/credential farkı, eski kanıt ve scope değişimi sınanır. Başka host/projeye kanıt miras verilmez.
4. Credential ID/revision, store/epoch/clock generation ve toplam deadline finalde yeniden karşılaştırılır; yarışta state_changed, sıfır yan etki ve otomatik yeni çözümleme yoktur.
5. Yeni doğrulama yüzeyi için anlamlı bağımsız fixture, gerçek TLS/subprocess, ortak API/CLI, secret kapsamı ve gerekiyorsa kaynak bağlı test/paket/performans kabulü tamamlanır. Kullanıcı uyumluluğu ve yeni ADR onayı kaydedilir.
6. Hazır alt iş, iki fresh review turu ve gerçek kabul kanıtı olmadan bu kart verified olmaz. P02-0b/d’nin observed teslimi bu kartı kapatmaz.

## Doğrulama

Ready öncesi kaynak/iddia/otorite matrisi ve dar alt kartlar hazırlanır. Çalışan davranışa uygun [doğrulama matrisi](../../../CONTRIBUTING.md#doğrulama-seçimi) kullanılır. Hesap deneyi ayrı scoped read planı ve gerçek kullanıcı yetkisi ister; key/ID/PII/ham yanıt repoya girmez. Tarihli kaynak, sentetik test ve gerçek hesap deneyi ayrı kaydedilir.

## Teslim kaydı

Uygulama veya kabul yapılmadı. Bu kart P02-0b’nin özgün doğrulanmış kimlik/bağ ihtiyacını görünür ve sahipli tutar. Dış kanıt/ayrı tasarım kapısı açık; ready değildir. ADR-0022 Accepted; dar gözlem kabulünün tamamlanması bu kartı kapatmaz.
