# Mühendislik standartları

**Güncellendi:** 2026-10-29. İlk dilimin etkin sınırları [ilk kabulde](../research/p01-core-validation.md), yeni taşıma/stream/kurulum ve kaynak kabulü [P01 kapanış kaydında](../research/p01-remaining-implementation-validation.md) tutulur. Gerçek CI ortamları ayrıca kaydedilir; tanım bulunması uzakta koştuğu anlamına gelmez.

| Belge | Kapsam | Durum |
|---|---|---|
| [İlkeler](principles.md) | Kullanıcı değeri ve ortak öncelikler | Benimsenmiş |
| [Mimari](architecture.md) | Sınırlar ve bağımlılık yönü | Benimsenmiş |
| [Python](python.md) | Tip, kaynak yönetimi ve bağımlılıklar | Etkin — yerel şema, lint/type/import; uzak kaynaklar planlandı |
| [Kullanım deneyimi](ux.md) | Rehberli/doğrudan/CI davranışı | Benimsenmiş |
| [Performans](performance.md) | Bütçeler, ölçüm ve optimizasyon | Etkin — başlangıç/profil/jobs ve raw TLS stream; hizmet/araç aktarımı ayrı |
| [Test](testing.md) | Sözleşme ve dayanıklılık kanıtı | Etkin — yerel state, gerçek TLS/stream/process yolculuğu; canlı yürütme planlandı |
| [Güvenlik](security.md) | Sır, dosya, ağ ve çalıştırma sınırları | Benimsenmiş |
| [Hata ve gözlemlenebilirlik](error-handling-observability.md) | Sonuç, log, metrik ve belirsizlik | Benimsenmiş |
| [Belgeleme](documentation.md) | Kanonik kaynak, dil ve durum | Benimsenmiş; bu belge temeline uygulanır |
| [Araştırma kanıtı](research-evidence.md) | Ham arşiv, manifest, test vektörü ve review ayrımı | Etkin — PR #10 kayıpsız arşiv ve CI denetimi |
| [Git ve yayın](git-release.md) | Değişiklik, inceleme ve sürüm | Etkin — dal/PR korumaları ve gerçek CI; yayın kapısı ayrıca geçerli |

`Taslak` açık öneri; `Benimsenmiş` uygulama değişikliklerini bağlayan karar; `Etkin` ilgili davranışın kod/CI veya kayıtlı işletim denetimiyle uygulandığı durumdur. Etkinleşen standardın kanıtı ve kapsamı aynı değişiklikte bu indekse eklenir. “Benimsenmiş” daha düşük kalite hedefi değildir; bugünkü kanıt sınırını doğru anlatır.
