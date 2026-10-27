# Git, inceleme ve yayın standardı

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

Repo boş olarak `Master` varsayılanıyla klonlandı. Bu belge `main`/`development` dalı veya branch protection kurulduğunu iddia etmez. Mevcut varsayılan dal üzerinden kısa ömürlü çalışma dalları kullanılır; dal modelini değiştiren işlem ayrıca karara bağlanır.

Commit türleri `docs`, `feat`, `fix`, `test`, `refactor`, `perf`, `build`, `ci`, `chore` gibi açık amaç taşır. PR problemi, kullanıcı sonucunu, sözleşme/uyumluluk etkisini ve gerçek kontrolleri anlatır. Reviewer davranış doğruluğu, kullanıcı kolaylığı, kaynak bütçesi ve toparlanmaya öncelik verir.

## Yayın kapısı

İlk sürümden önce paket metadata'sı, MIT bildirimi, tekrar üretilebilir build, sır/veri dışlama, destek matrisi, kullanıcı komutları ve anlamlı test/performans sonuçları gerekir. `Unreleased` veya accepted ADR yayın değildir. Tag/build ile paket yayımlama ayrı işlemlerdir; bir dosya oluşturma görevi dış yayımlamayı otomatik kapsamaz.

[SECURITY.md](../../SECURITY.md) ana özel bildirim kanalını ve doğrudan özel yedek kanalı kullanılabilirlik doğrulama tarihiyle sunmalıdır. Kapalı veya doğrulanmamış kanal ilk yayının açık engelidir; yalnız bağlantı eklenmesi kabul kanıtı değildir.

SemVer kamuya açık CLI/config/Python/adaptör sözleşmelerini kapsar. Breaking değişiklik açıklama, migration ve deprecation politikasıyla sunulur. Haricî araç sürümleri uyumluluk matrisiyle kaydedilir; kullanıcı ortamı sessizce güncellenmez.

Bağımlılık ve devralınan kod kendi lisans/NOTICE gereğini korur. Yörünge'nin MIT lisansı başka projenin kodunu kendiliğinden yeniden lisanslamaz. Referans projelerden biçim ve ilke öğrenilir; proje özelindeki sahiplik/branch/CI kuralları kopyalanmaz.

`docs/analysis/private/` yayın girdisi değildir. Gitignore kaydı tek başına paket/site aracının dışlamasını garanti etmez; build, doküman yayını ve kaynak arşivi kontrolleri bu dizinin ve içeriğinin çıktıya girmediğini ayrıca doğrular. İlk gerçek üretimde hem girdi dosya listesi hem sdist/wheel üye listeleri, açılmış paket içeriği ve site/doküman çıktı ağacı incelenir; yolun yeniden adlandırılması içerik dışlama yerine geçmez. Sonuç, üretilen artefaktın kimliği/hash'iyle kaydedilir; henüz build yokken bu kontrol geçmiş sayılmaz. Özel arşiv dosyaları force-add ile eklenmez.
