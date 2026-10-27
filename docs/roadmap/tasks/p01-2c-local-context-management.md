---
id: P01-2c
phase: P01
status: in_progress
size: M
depends_on: [P01-2a, P01-4a, P01-2b]
capabilities: [C01, C02]
---
# P01-2c — Yerel init, context yönetimi ve doctor

**Tarih:** 2026-10-27. **Teslim paketi:** [P01-2](../p01-2-delivery-plan.md). Bu kart yerel tanılama içindir; HTTP/cache önkoşulu taşımaz.

## Kullanıcı sonucu ve mevcut eksik

Kullanıcı config oluşturabilmeli, profilleri görebilmeli, aktif profil/projeyi açıkça seçebilmeli ve yerel ayar sorununu tipli sonuçla anlayabilmelidir. Bugün yalnız context okuma vardır.

## Giren ve girmeyen kapsam

Güvenli ilk config oluşturma, profil listeleme/aktivasyonu, açık proje tercihi ve yerel config/referans/store tanılaması girer. Komut/API adları ve seçenekleri uygulama öncesi CLI/config referansında kesinleştirilir; burada çalışan komut örneği ilan edilmez. HTTP tanılaması P01-5, capability cache P01-3 ve gerçek hesap/proje keşfi P02-0b'dedir.

## Bağımlılıklar ve kararlar

P01-2a/4a/2b aynı dalda kendi kabulüyle tamamlanır. B02/B13'ün koruma/kurtarma sınırları doctor sonucuna uygulanır. Uzak kontrol yerine sahte başarılı tanılama konmaz; yerel kanıtın sınırı sonuçta görünür kalır.

## Sözleşme ve uygulama sınırı

CLI parse/render, Python aynı application kullanım senaryosunu çağırır. Config yazma dış dosya adaptöründedir; mevcut profil/reçete/çağrı önceliği korunur. Doctor varsayılanı credential değeri çözmez, ağ açmaz ve store/key yaratmaz; eksik kayıt eksik/henüz kurulmamış olarak raporlanır. Credential tanılaması gerekiyorsa ayrı açık istek ve yalnız seçilen hizmet kapsamı gerekir.

## Kabul

1. Init mevcut dosyayı ezmez; açık yazma akışında config doğrulanır, yedek ve atomik görünürlük sağlanır. Hata mevcut çalışan config'i kaybettirmez.
2. Profil listeleme, aktif profil ve açık proje tercihi CLI/Python'da aynı sonucu verir; diğer profil alanları korunur, liste başından hedef seçilmez.
3. Eşzamanlı/yazılırken değişmiş config için çatışma davranışı açık ve testlidir; sır veya geçici operation bilgisi config'e taşınmaz.
4. Yerel doctor config/referans/store/koruma eksikliğini tipli ve sır içermeyen sonuçla ayırır; unknown uzak desteği supported yapmaz. Non-TTY akışı prompt'ta kalmaz.
5. Saved plan profilden yeniden çözülmez; mevcut metadata/offline guard ve başlangıç bütçesi geçer. Yeni CLI/API sözleşmesi ve kullanıcı belgesi aynı değişikliktedir.

## Doğrulama

Gerçek tempfile/config yazma, izin/çatışma/bozuk dosya negatifleri ve gerçek konsol/API eşitliği. Ağ ve istenmeyen credential/DB/key yaratma guard'ları; ilgili lint/type/build/başlangıç kontrolleri [CONTRIBUTING](../../../CONTRIBUTING.md#doğrulama-seçimi) ile seçilir.

## Teslim kaydı

Ürün uygulaması, yeni komut/API veya teslim PR'sı henüz yoktur. Bu kartın hazırlanması runtime doctor veya canlı hesap desteği sağlamaz.
