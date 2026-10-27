# Yörünge ajan rehberi

Bu dosya bu depoda çalışan bütün kodlama ajanlarının ortak yönergesidir. Kullanıcının mevcut görev ve tercihleri önceliklidir.

## Önce oku

1. [Mevcut durum](docs/roadmap/current.md).
2. [Ürün kapsamı](docs/product-scope.md) ve [yetenek matrisi](docs/capability-matrix.md).
3. [Standartlar](docs/standards/README.md), ardından değişikliğe uyan standart.
4. İlgili modül, mimari belge, karar ve referans sözleşmesi.

## Ürün kuralları

- Yörünge, EVREN platformunun kapsamlı yardımcı aracıdır. İlgili görevlerde ForgeLM varsayılandır; desteklenen alternatifler açıkça seçilebilir.
- Görev, araç sağlayıcısı, EVREN hizmeti ve çalıştırma ortamı ayrı kavramlardır. Desteklenmeyen bir kombinasyonu sessizce dönüştürme.
- Kullanım kolaylığı, somut fayda, işlevsellik, performans ve kaynak verimliliği kabul ölçütlerine bağlanır.
- Planlanan özelliği uygulanmış, doküman bilgisini canlı doğrulanmış veya genel GPU görünürlüğünü kullanıcı erişimi diye anlatma.
- Ağır eğitim paketlerini temel istemci bağımlılığına taşıma; sırları çıktıya/günlüğe/koda koyma.
- Yan etkili ve belirsiz işlemi otomatik tekrar etme; hesap şartlarını kullanıcı adına kabul etme.

## Değişiklik disiplini

Türkçe ürün/mühendislik açıklamaları; İngilizce dosya, API, config anahtarı, kod kimliği ve makine çıktısı kullanılır. Yeni dokümanın kanonik konumunu seç; aynı sözleşmeyi farklı dosyalara kopyalama. Uygulama yokken boş `src`/test iskeleti veya yeşil görünen göstermelik CI oluşturma. Gerçek uygulama başladığında sözleşme, anlamlı test ve kullanıcı belgesini birlikte güncelle.

Doğrulamayı değişikliğe göre seç. Sadece belge değişikliğinde bağlantı, başlık, fence ve tutarlılık denetimleri yeterli olabilir. Çalıştırılmayan testleri açıkça belirt. Başka projelerin yönergeleri bu deponun kurallarının yerine geçmez. Remote ayarlarını, yayınları ve repo izinlerini sıradan belge işi kapsamında değiştirme.

## Özel analiz sınırı

`docs/analysis/private/` yerel analiz arşividir ve Git dışında tutulur. Buradaki dosya, proje adı, kaynak bağlantısı veya test sonuçlarına üretim kodunda, yayımlanabilir dokümanlarda, changelog'da ve commit/PR içeriklerinde referans verme. Gerekli ürün kararını kendi kanonik belgesinde bağımsız anlat; doğrulanabilir dış sözleşme için resmî kaynak kullan. Özel arşivi paket, site, doküman üretimi veya yayın girdisine dahil etme; zorla stage etme.
