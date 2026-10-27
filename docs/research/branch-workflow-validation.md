# Dal, PR ve koruma doğrulama kaydı

**Tarih:** 2026-10-27. **Kapsam:** Development PR / Master release kurulumunun canlı kanıtı. Ürün veya paket yayını değildir.

## Başlangıç ve ilk PR

- Canlı depoda başlangıçta yalnız korumasız `Master` (`6ec4b16`) vardı; açık PR ve Actions koşusu yoktu.
- `development` tam olarak bu Master commit'inden oluşturuldu. Yerel `bb67b3a` uygulaması ve `35f1115` politika/CI değişikliği [PR #1](https://github.com/HodeTech/Yorunge/pull/1) üzerinden development'a alındı.
- [İlk PR CI koşusu](https://github.com/HodeTech/Yorunge/actions/runs/40462730153) başarılı: 100 test, format/lint/strict type, 71 genel belge kontrolü, wheel/sdist ve ayrı temiz kurulum/import kökeni doğrulaması geçti.
- `offline-core` check'i GitHub Actions uygulaması (`app_id=15368`) olarak gözlendi; development korumasında zorunlu yapıldıktan sonra PR `d9f4ae7` merge commit'iyle alındı. İlk uygulama commit'i korundu.

## İlk koşunun performans kanıtı

GitHub Ubuntu koşucusu, Linux x86_64, CPython 3.11.15; kilitli ortam, editable geliştirme kurulumu. Her komut için üç ısınma ve 30 ayrı süreç:

| Yol | İlk süreç (ms) | Sıcak p95 (ms) | Hedef | Sonuç |
|---|---:|---:|---:|---|
| Yardım | 22,808 | 23,770 | ≤ 500 ms | Geçti |
| Sürüm | 23,695 | 31,365 | ≤ 500 ms | Geçti |
| Profil | 101,278 | 128,808 | ≤ 200 ms | Geçti |

OS/disk cache'i boşaltılmadı; fiziksel soğuk açılış kanıtı değildir. Bu ölçüm ilk dilimin ayrı wheel ortamı/macOS ölçümünü değiştirmez. Ham süreç örnekleri ve build arşiv SHA-256 değerleri bağlı CI koşusunun logunda bulunur.

## Canlı ayarlar ve ikinci kapı

Repo ayarı API'den geri okundu: varsayılan `development`, merge commit açık, squash/rebase merge kapalı. İki dalda PR, `offline-core`, yönetici denetimi ve konuşma çözümleme zorunlu; force push ve silme kapalı. `Master` yazma listesi yalnız `cemililik`; zorunlu review sayısı tek yazma yetkilisi nedeniyle 0. Development strict, Master loose check kullanır.

Güvenilen metadata kontrolü artık varsayılan dalda mevcut. Bu kaydı taşıyan takip PR'ında `branch-policy` gerçek check'i doğrulanıp iki dalda ikinci zorunlu kontrol olarak eklenecek; bu satır henüz tamamlanmış doğrulama iddiası değildir. Sonuç güncellendiğinde gerçek koşu bağlantısı ve API geri okuma kanıtı burada korunur.

Kanonik ayar sözleşmesi [Git/yayın standardındadır](../standards/git-release.md); bu dosya aynı sözleşmenin ikinci kopyası değildir. `Master` içeriği kuruluma dahil edilmez; release aktarımı ve yayımlama kullanıcıya aittir.
