# Mühendislik standartları

**Güncellendi:** 2026-10-27. İlk dilimin etkin sınırları [kabul kaydında](../research/p01-core-validation.md); diğer maddeler ilgili uygulama fazını yönlendirir. CI tanımı bulunması uzakta koştuğu anlamına gelmez.

| Belge | Kapsam | Durum |
|---|---|---|
| [İlkeler](principles.md) | Kullanıcı değeri ve ortak öncelikler | Benimsenmiş |
| [Mimari](architecture.md) | Sınırlar ve bağımlılık yönü | Benimsenmiş |
| [Python](python.md) | Tip, kaynak yönetimi ve bağımlılıklar | Etkin — yerel şema, lint/type/import; uzak kaynaklar planlandı |
| [Kullanım deneyimi](ux.md) | Rehberli/doğrudan/CI davranışı | Benimsenmiş |
| [Performans](performance.md) | Bütçeler, ölçüm ve optimizasyon | Etkin — başlangıç/profil; aktarım/ağ planlandı |
| [Test](testing.md) | Sözleşme ve dayanıklılık kanıtı | Etkin — offline/yerel state kesinti kabulü; uzak yürütme planlandı |
| [Güvenlik](security.md) | Sır, dosya, ağ ve çalıştırma sınırları | Benimsenmiş |
| [Hata ve gözlemlenebilirlik](error-handling-observability.md) | Sonuç, log, metrik ve belirsizlik | Benimsenmiş |
| [Belgeleme](documentation.md) | Kanonik kaynak, dil ve durum | Benimsenmiş; bu belge temeline uygulanır |
| [Git ve yayın](git-release.md) | Değişiklik, inceleme ve sürüm | Etkin — dal/PR korumaları ve gerçek CI; yayın kapısı ayrıca geçerli |

`Taslak` açık öneri; `Benimsenmiş` uygulama değişikliklerini bağlayan karar; `Etkin` ilgili davranışın kod/CI veya kayıtlı işletim denetimiyle uygulandığı durumdur. Etkinleşen standardın kanıtı ve kapsamı aynı değişiklikte bu indekse eklenir. “Benimsenmiş” daha düşük kalite hedefi değildir; bugünkü kanıt sınırını doğru anlatır.
