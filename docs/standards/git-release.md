# Git, inceleme ve yayın standardı

**Durum:** Etkin — dal/PR korumaları ve zorunlu CI; yayın kapıları ayrıca geçerli. [Canlı doğrulama kaydı](../research/branch-workflow-validation.md). **Tarih:** 2026-10-27.

## Dal modeli ve birleştirme

Kanonik geliştirme dalı ve GitHub varsayılanı `development`; release dalı büyük/küçük harfi korunarak `Master`'dır. `development` ilk kez `Master`'ın `6ec4b16` commit'inden oluşturulur. Yeni işler güncel `origin/development` üzerinden kısa ömürlü dallarda geliştirilir; kod, doküman, bağımlılık ve CI dahil bütün değişiklikler PR ile `development`'a girer.

`development` → `Master` aktarımı aynı depodan PR ile yapılır. Bu PR'ı ve release/yayın işlemlerini kullanıcı (`cemililik`) yürütür. Ajan development PR'larını kapsamı ve zorunlu kontrolleri uygunsa birleştirebilir; `Master`'ı kendiliğinden birleştirmez. Aynı hesapla çalışan ajan/kullanıcı GitHub tarafından ayırt edilemez; bu sınır ayrıca ajan yönergesiyle korunur.

Her iki aşamada **merge commit** kullanılır. Repo ayarında `allow_merge_commit=true`, `allow_squash_merge=false`, `allow_rebase_merge=false`; linear history kapalıdır. Commit kimlikleri ve PR birleşme noktaları korunur. Kalıcı dallar rebase/reset ile yeniden yazılmaz. `Master`'da release için yapılan sürüm düzeltmeleri PR ile `development`'a geri taşınır; normal aktarımda cherry-pick kullanılmaz. [ADR-0009](../decisions/0009-development-and-release-branches.md).

## Koruma ve CI sözleşmesi

İki dalda klasik branch protection kullanılır; bu ölçekte doğrudan kullanıcı bazlı `Master` yazma sınırı yeterlidir. PR zorunlu, çözülmemiş konuşma engeli etkin, force push/silme kapalı ve yönetici denetimi etkindir. Genel yönetici bypass veya PR bypass listesi tanımlanmaz. `Master` yazma listesi yalnız `cemililik`; diğer yöneticilerin ayar değiştirme yetkisini bu politika ortadan kaldırmaz.

Required check kimlikleri `offline-core` ve `branch-policy`, kaynak uygulama GitHub Actions'tır. `offline-core` format/lint/type, genel belge, offline test, build/temiz kurulum ve başlangıç bütçelerini uygular. PR'da GitHub'ın geçici birleşim sonucu test edilir. `branch-policy` yalnız güvenilen varsayılan dal commit'inden checkout yapar ve PR metadata'sını okur; PR head kodunu çalıştırmaz. `Master` hedefinde head dalının **aynı depodaki** `development` olması gerekir; fork'ta aynı adı kullanmak geçmez. Politika `edited` olayında da yeniden koşar; PR hedefi değişimi denetimsiz kalmaz.

Normal CI `development`/`Master` PR'larında, bu iki dala push'ta ve manuel çağrıda çalışır; feature push + PR için yinelenen tam koşu üretilmez. Token `contents: read`, süre ve concurrency sınırı taşır. Metadata kontrolü ayrı `pull_request_target` workflow'udur; token salt okunur, checkout açık `github.sha` ile güvenilen commit'e sabittir, PR kodu/artefaktı ve cache'i kullanılmaz.

`development` required check'leri strict'tir: özellik dalı güncel tabanla sınanır. `Master` check'leri loose'tur: iki uzun ömürlü dal arasında her release merge commit'ini salt soy ağacı için geri taşıma zorunluluğu yaratılmaz. Master aktarım PR'ları kullanıcı tarafından tek tek ele alınır; taban değişmişse kontroller yeniden çalıştırılır. PR'ın oluşturulduğu/güncellendiği anın birleşim sonucu test edilir; loose ayar eşzamanlı PR'lar için merge queue garantisi vermez.

Şimdilik zorunlu onay sayısı **0**'dır; PR ve CI zorunluluğu devam eder. Tek yazma yetkilisinin kendi PR'ını onaylayamaması nedeniyle 1 review şartı kurulmaz. İkinci bağımsız yazma yetkilisi geldiğinde 1 onay, stale approval iptali ve sahiplik gereksinimleri yeniden değerlendirilir.

## İlk kurulum sırası

İlk uygulama commit'i `bb67b3a`, dal politikası benimsenmeden önce `Master` tabanlı `feat/offline-core` dalında hazırlanmıştır. Bu mevcut çalışma korunur; `development`'a doğrudan taşımak yerine ilk PR'a dahil edilir. Bu taban istisnası yeni geliştirmeler için emsal değildir.

İlk PR'da `offline-core` gerçek koşusu doğrulanır, bu check ile development koruması açılır ve PR merge commit ile alınır. Ardından varsayılan dal `development` yapılır. Güvenilen metadata workflow'u artık varsayılan dalda vardır; takip eden doğrulama PR'ında `branch-policy` koşusu görülünce bu check de iki dalda zorunlu hale getirilir. Böylece henüz var olmayan check ilk kurulumu kilitlemez. `Master` içeriği kurulum sırasında ilerletilmez; ilk release aktarımını kullanıcı yapar.

Canlı ayarlar API'den geri okunarak; merge commit'in iki parent'ı, PR hedefi ve gerçek Actions sonuçlarıyla doğrulanır. Belge tek başına bu ayarların uygulanmış olduğuna kanıt değildir.

Commit türleri `docs`, `feat`, `fix`, `test`, `refactor`, `perf`, `build`, `ci`, `chore` gibi açık amaç taşır. PR problemi, kullanıcı sonucunu, sözleşme/uyumluluk etkisini ve gerçek kontrolleri anlatır. Reviewer davranış doğruluğu, kullanıcı kolaylığı, kaynak bütçesi ve toparlanmaya öncelik verir.

## Yayın kapısı

İlk sürümden önce paket metadata'sı, MIT bildirimi, tekrar üretilebilir build, sır/veri dışlama, destek matrisi, kullanıcı komutları ve anlamlı test/performans sonuçları gerekir. `Unreleased` veya accepted ADR yayın değildir. Tag/build ile paket yayımlama ayrı işlemlerdir; bir dosya oluşturma görevi dış yayımlamayı otomatik kapsamaz.

[SECURITY.md](../../SECURITY.md) ana özel bildirim kanalını ve doğrudan özel yedek kanalı kullanılabilirlik doğrulama tarihiyle sunmalıdır. Kapalı veya doğrulanmamış kanal ilk yayının açık engelidir; yalnız bağlantı eklenmesi kabul kanıtı değildir.

SemVer kamuya açık CLI/config/Python/adaptör sözleşmelerini kapsar. Breaking değişiklik açıklama, migration ve deprecation politikasıyla sunulur. Haricî araç sürümleri uyumluluk matrisiyle kaydedilir; kullanıcı ortamı sessizce güncellenmez.

Bağımlılık ve devralınan kod kendi lisans/NOTICE gereğini korur. Yörünge'nin MIT lisansı başka projenin kodunu kendiliğinden yeniden lisanslamaz. Referans projelerden biçim ve ilke öğrenilir; proje özelindeki sahiplik/branch/CI kuralları kopyalanmaz.

`docs/analysis/private/` yayın girdisi değildir. Gitignore kaydı tek başına paket/site aracının dışlamasını garanti etmez; build, doküman yayını ve kaynak arşivi kontrolleri bu dizinin ve içeriğinin çıktıya girmediğini ayrıca doğrular. İlk gerçek üretimde hem girdi dosya listesi hem sdist/wheel üye listeleri, açılmış paket içeriği ve site/doküman çıktı ağacı incelenir; yolun yeniden adlandırılması içerik dışlama yerine geçmez. Sonuç, üretilen artefaktın kimliği/hash'iyle kaydedilir; henüz build yokken bu kontrol geçmiş sayılmaz. Özel arşiv dosyaları force-add ile eklenmez.
