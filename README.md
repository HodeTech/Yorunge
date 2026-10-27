# Yörünge

**EVREN platformunda veriden sonuca uzanan işleri kolaylaştıran kapsamlı yardımcı araç.**

Yörünge; hesap ve proje bağlamını, veri setlerini, modelleri, LLM ve çıkarım servislerini, eğitim işlerini, GPU/kota görünürlüğünü ve çalışma sonuçlarını tutarlı iş akışlarında bir araya getirmek için tasarlanıyor. Kullanıcı, bir işi tamamlamak için ayrı istemcilerin ayarlarını ve ilerleme kayıtlarını birleştirmek zorunda kalmamalı.

**Durum — 27 Ekim 2026:** Kapsam ve dokümantasyon temeli oluşturuluyor. Çalışan Yörünge CLI'si, Python paketi veya yayımlanmış sürüm henüz yok. Belgelerdeki komutlar ve sözleşmeler tasarımdır; uygulanmış yetenek olarak sunulmaz.

## Ürün yaklaşımı

- **EVREN odaklı kapsam:** Veri aktarımı, model keşfi, çıkarım, eğitim, kaynak görünürlüğü ve sonuç yönetimi aynı ürünün alanlarıdır.
- **Kolay başlangıç, doğrudan kullanım:** Rehberli akış ve kısa komutlar aynı çekirdeğe bağlanır; otomasyon için kararlı makine çıktısı tasarlanır.
- **Göreve göre araç seçimi:** İlgili LLM veri hazırlama, fine-tuning, değerlendirme ve dışa aktarma görevlerinde ForgeLM varsayılan tercih olur. Kullanıcı desteklenen muadil aracı seçebilir; seçim ve yetenek farkları görünür kalır.
- **Hafif kurulum:** Sadece EVREN veri/API işlemleri isteyen kullanıcı ağır eğitim bağımlılıkları kurmaz.
- **Ölçülen performans:** Akışlı dosya aktarımı, sınırlı eşzamanlılık, uygun önbellek ve kontrollü API kullanımı ilk tasarımın parçasıdır.
- **Güvenilir sonuç:** Kesinti, belirsiz uzak işlem, eksik çıktı ve maliyet tahmini açık durumlarla gösterilir.

## Planlanan yetenekler

| Alan | Kullanıcıya sağlayacağı fayda |
|---|---|
| Hesap, profil ve proje | Doğru hizmet, anahtar ve proje ile işe başlama |
| Veri setleri | Denetleme, yükleme, indirme, doğrulama, sürüm ve kesintiden devam |
| Model kataloğu ve çıkarım | Modele/göreve uygun servis keşfi, LLM, embedding, rerank ve görsel çıkarım akışları |
| Eğitim ve değerlendirme | Planlama, maliyet önizlemesi, başlatma, izleme, durdurma ve sonuç toplama |
| Kaynaklar ve kota | Yetkili erişimi, GPU kullanılabilirliğini, rezervasyon ve tüketimi doğru yorumlama |
| İş akışları ve araçlar | ForgeLM varsayılanı, alternatif sağlayıcılar, tekrarlanabilir reçete ve artefakt manifesti |

Tam kapsam ve aşamalar: [ürün kapsamı](docs/product-scope.md), [yetenek matrisi](docs/capability-matrix.md), [yol haritası](docs/roadmap/README.md).

EVREN'de GPU görünmesi veya rezervasyon yapılabilmesi, kullanıcıya genel Python/GPU çalışma ortamı verildiğini kanıtlamaz. EVREN üzerinde haricî eğitim aracı çalıştırma ve kullanıcı LLM'ini servis etme yetenekleri, erişim ve sözleşme doğrulamasına bağlıdır. [Entegrasyon sınırları](docs/architecture/integration-boundaries.md).

## Nereden başlamalı?

1. [Vizyon ve konumlandırma](docs/vision.md).
2. [Kapsam ve öncelikler](docs/product-scope.md).
3. [Kullanıcı yolculukları](docs/user-journeys.md).
4. [Mimari](docs/architecture/README.md) ve [modüller](docs/modules/README.md).
5. [Mevcut durum](docs/roadmap/current.md) ve [kararlar](docs/decisions/README.md).

Tüm belgeler: [dokümantasyon rehberi](docs/README.md). Katkı: [CONTRIBUTING.md](CONTRIBUTING.md). Ajan yönergeleri: [AGENTS.md](AGENTS.md).

Proje kayıtları: [değişiklik günlüğü](CHANGELOG.md), [güvenlik bildirimi](SECURITY.md), [topluluk ilkeleri](CODE_OF_CONDUCT.md), [Claude giriş rehberi](CLAUDE.md).

## Lisans ve proje ilişkisi

[MIT License](LICENSE). Yörünge, HodeTech altında geliştirilen bağımsız bir yardımcı araç projesidir. EVREN adı uyumluluk hedefini belirtir; platformun geliştirdiği veya onayladığı bir ürün olduğu iddia edilmez. ForgeLM ayrı bir projedir ve kendi lisansı/sürüm döngüsüyle kullanılır.
