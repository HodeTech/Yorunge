# P01 — Hafif çekirdek ve gerçek sözleşmeler

**Durum:** Planlandı. **Bağımlılık:** P00. **Yetenekler:** C01/C02/C12/C13 temeli.

## İş sırası

| İş | Kapsam | Kabul |
|---|---|---|
| P01-1 | Paket/CLI/HTTP/şema spike'ı, kaynak yerleşimi | Gerçek lock/build; hafif `--help`; CLI/HTTP/şema kütüphanelerinin seçimi ve ilk ölçüm |
| P01-2 | Config/context/secret ref | Profil önceliği, açık proje seçimi, yanlış hizmet ve sır yansıması testleri |
| P01-3 | Capability ve plan modeli | Hedef/yetki/digest bağları, kapsam/tazelik, unknown/access ayrımı; default/override çözümleme |
| P01-4 | SQLite operation/attempt, migration, sahiplik | Çökme, kilit, bozuk kayıt, lease devri ve tekrar gönderim kontrolü |
| P01-5 | Ortak HTTP/sonuç/hata ve CLI/Python hattı | Loopback, deadline/retry, JSON/NDJSON ve iptal sözleşmesi |
| P01-6 | CI ve geliştirici kurulumunu bağlamak | Gerçek unit/contract/integration ve performans kontrolleri; doküman komutları güncel |

## Uçtan uca dilim

P01-1–P01-5 işleri birikerek ilk uçtan uca dilimi tamamlar: küçük offline görev → context → capability → plan → sahte execution → kalıcı durum/artefakt sonucu, hem CLI hem Python'dan aynı kurallarla çalışır. P01-1'in kabulü paket/kütüphane seçimi ve ilk ölçümdür; context/capability/plan P01-2/P01-3'e, kalıcı yürütüm ve uçtan uca sonuç P01-4/P01-5'e bağlıdır. Bu dilim gerçek EVREN eğitimi diye sunulmaz; çekirdek sözleşmesini sınar.

## Çıkış kapısı

Yardım/sürüm için ağ/DB/keychain/ML import yoktur. Kritik kayıt hatasında yan etki başlamaz. Varsayılan ForgeLM çözümü ile açık tool tercihi plan düzeyinde sınanır; adaptör henüz yoksa açık unsupported/unavailable sonucu verir. Makine çıktısı ve çıkış kodları contract testleriyle korunur. Başlangıç ve kaynak bütçeleri ölçülür.

Çoklu OS/Python hedefi gerçek matriste tanımlanır; destek sözü yalnız koşulan/kanıtlanan kapsamı taşır. Büyük UI, live GPU işi ve genel plugin yükleyici bu fazın işi değildir.
