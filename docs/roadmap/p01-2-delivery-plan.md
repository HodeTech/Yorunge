# P01-2 — Kimlik ve bağlam paketi teslim planı

**Tarih:** 2026-10-27. **Durum:** B02/B13 kararları kullanıcı onayıyla Accepted; sıradaki uygulama P01-2a. **Dal:** `feat/p01-2-identity-context`, taban `development@83bcd83`. Bu plan uygulama veya bütün paketin `ready` olduğu iddiası değildir.

## Teslim sınırı

Kullanıcının tercihiyle P01 işleri epik başına tek development PR'ında teslim edilir: P01-2 → P01-3 → P01-4 → P01-5 → P01-6. Alt ID'ler uygulama, test, commit ve review birimleridir; ayrı PR zorunluluğu değildir. Ortak önkoşul, gerekli olduğu pakette açıkça teslim edilir ve özgün ID'sinde kanıtlanır.

Bu paketin kullanıcı sonucu: doğru yerel profil/hizmet/proje seçimi, açık çağrıda sır çözümleme, süreçler arasında credential kimliği/nesli ve güvenli yerel kurulum/tanılama. P01-4a kalıcılık temeli bu PR'a dahildir. Operation/lease/jobs P01-4'te; capability cache/execution geçerliliği P01-3'te; HTTP tanılaması/taşıma P01-5'te; gerçek hesap/proje keşfi P02-0b'dedir. Yerel doctor bu sonraki özellikleri çalışıyor diye göstermez.

## Paket içi sıra

| Adım | İş | Başlama kapısı | Kanonik kabul |
|---|---|---|---|
| 0 | B02/B13 araştırması ve karar belgeleri — tamamlandı | Kullanıcının mevcut hazırlık yetkisi | [Karar raporu](../research/p01-2-state-identity-decision-review.md), ADR-0011/0012 için 2026-10-27 kullanıcı onayı |
| 1 | P01-2a — hizmete bağlı env çözümleme | P01-1 doğrulandı; ürün uygulama yetkisi | [Mevcut kart](tasks/p01-2a-secret-resolution.md) |
| 2 | P01-4a — store/migration ve kayıt temeli | Adım 1 kanıtı; B02/B13 kabulü | [Store kartı](tasks/p01-4a-state-foundation.md) |
| 3 | P01-2b — opak kimlik/nesil ve hedef bağı | Adım 1/2 kanıtı; B13 kabulü | [Credential kartı](tasks/p01-2b-credential-identity.md) |
| 4 | P01-2c — yerel init/context/doctor | Adım 1/2/3 kanıtı | [Yerel yönetim kartı](tasks/p01-2c-local-context-management.md) |
| 5 | Bütünleşik kabul ve tek PR | Dört alt işin kendi kabulü | Aşağıdaki paket kapanışı |

Adım 0'ın karar onayı tamamlandı; kullanıcı P01-2 uygulamasını yetkilendirdi. Sonraki kartlar kendi uygulama/bağımlılık kanıtlarını bekler. P01-2b büyük olduğu için iki uygulama/review adımına ayrılır: önce kimlik gözlemi, sonra reset/restore. Ayrı kart/PR üretilmez; kart iki adımın kabulü tamamlandığında kapanır.

Uygulama/review adımları: **1** P01-2a env çözümleme ve hedef kapısı; **2** P01-4a güvenli store/migration/backup ve key temeli; **3** P01-2b kimlik/nesil gözlemi; **4** P01-2b reset/identity-only restore; **5** P01-2c init/profil/proje/doctor. Bütünleşik kapanış ve tek PR bu beş adımın iki review turundan sonra gelir. [Gerçek ilerleme ve kabul kaydı](../research/p01-2-implementation-validation.md).

## Uygulama ve review

Her uygulama adımı için: kod/test/belge → anlamlı doğrulama → commit → yeni bağımsız review ajanlarıyla birinci tur → doğrulanmış bulguları düzelt ve commit → başka yeni ajanlarla ikinci tur → doğrulanmış bulguları düzelt ve commit. Yeni risk çıkarsa ilgili doğrulama/odak review tamamlanır. Review yetkisi kullanıcının o uygulama görevindeki talimatına bağlıdır; bu plan tek başına delegasyon başlatmaz.

Alt işin `verified` kanıtı aynı çalışma dalındaki gerçek commit/test/review ile oluşabilir; ayrı merge beklemek zorunlu değildir. Hazır olmayan doğrudan bağımlılık hazır gösterilmez. Epik ancak bütün alt işler ve paket kabulü kanıtlandığında tamamlanır; PR/merge/yayın ayrı kayıt edilir. Kullanıcının son review'si için tek PR açılır; merge commit politikası sürer.

## Paket kapanışı

- Gerçek env adaptörü ve geçici gerçek DB ile profil → hizmet → sır çözümleme → kimlik/nesil → süreç yeniden açma akışı kanıtlıdır; sır plan/JSON/hata/loga çıkmaz.
- Farklı context/hedefe ait bağlar birbirinin yerine kullanılamaz; gözlenen A→B→A anahtar değişimi eski nesli yeniden geçerli yapmaz. Eşzamanlı süreç davranışı ve eksik/bozuk yerel kayıt hatası açıktır.
- Init/context yönetimi no-clobber, yedek ve kontrollü hata sağlar; yerel doctor uzak kimlik doğrulaması veya capability desteği ilan etmez.
- Yardım/sürüm ile mevcut offline komutlar ağ, credential okuma ve istemsiz DB/key oluşturma guard'larını geçer. Store ve secret erişimi açık kullanım senaryosunda lazy açılır.
- Kart kabulü, CLI/Python sözleşme uyumu, tam test/lint/type/belge, build/iki temiz kurulum ve değişen import yolları için başlangıç bütçeleri kanıtlıdır. Son head'in zorunlu CI'ı geçer.

## Hazırlık ve kabul edilen kararlar

[ADR-0011](../decisions/0011-state-foundation-and-migrations.md) ve [ADR-0012](../decisions/0012-credential-identity-and-change-detection.md), bağlı binding v1 ile 2026-10-27 kullanıcı onayıyla benimsenmiştir. Araştırma sonuçları resmî kaynak, yerel deney ve mühendislik kararı olarak ayrılır. Karar kapısı kapanmıştır; bu pakete ait ürün commit/PR veya kabul kanıtı henüz yoktur.
