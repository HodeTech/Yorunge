# Katkı rehberi

Yörünge şu anda dokümantasyon ve tasarım aşamasındadır. Ürün kapsamını [product-scope.md](docs/product-scope.md), etkin işi [current.md](docs/roadmap/current.md) tanımlar. Henüz paket kurma veya uygulama testi çalıştırma komutu yoktur.

## Çalışma akışı

1. İlgili kapsam maddesini, modülü, sözleşmeyi ve standardı okuyun.
2. İlgili iş kaydını veya yol haritası görevini belirleyin. Küçük belge düzeltmeleri ayrı iş kaydı gerektirmez.
3. Mevcut varsayılan daldan kısa ömürlü bir çalışma dalı açın. İlk boş repo `Master` dalıyla klonlandı; uzaktaki dal politikası doğrulanmadan `main` veya `development` varsaymayın.
4. Bir değişiklikte tek bir sonucu somutlaştırın. Kullanıcı davranışı değişirse sözleşme ve kabul ölçütünü aynı değişiklikte güncelleyin.
5. İlgili doğrulamayı yapıp sonucu PR açıklamasına yazın. Çalıştırılmayan kontrolü başarılı göstermeyin.

## Belge değişiklikleri

Türkçe açıklama, İngilizce dosya/kimlik adları, UTF-8/LF ve göreli bağlantılar kullanın. Her Markdown dosyasının bir H1 başlığı olmalı. Planlanan komutu çalışan örnek diye sunmayın. Dizine eklenen belgeyi o dizinin README'sine bağlayın. Bağlantıları, başlıkları, kod bloklarını ve mevcut durumla tutarlılığı denetleyin. [Belgeleme standardı](docs/standards/documentation.md).

## Kod eklendiğinde

[Python](docs/standards/python.md), [test](docs/standards/testing.md), [güvenlik](docs/standards/security.md), [performans](docs/standards/performance.md) ve [hata/çıktı](docs/standards/error-handling-observability.md) standartları uygulanır. Bağımlılık ve araç komutları P01'de gerçek paket/CI kurulunca kanonik geliştirici rehberine eklenir. Bugün bulunmayan test veya paket dizini için başarı beyanı oluşturmayın.

## İnceleme ve lisans

PR; problemi, kullanıcı sonucunu, sözleşme etkisini ve gerçek doğrulamayı açıklamalı. Referans projelerin mimari kararları Yörünge'ye otomatik taşınmaz. Devralınan kodun lisans ve köken bildirimleri korunur; katkılar [MIT](LICENSE) altında sunulur. Güvenlik bildirimi için [SECURITY.md](SECURITY.md).
