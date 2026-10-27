# ADR-0010: Hazır iş kartı ve ortak ajan skill kütüphanesi

**Durum:** Accepted. **Tarih:** 2026-10-27. **Dayanak:** Kullanıcının aktif ürün geliştirmesinden önce roadmap/belge review'si ve repo ajan rehberleri talebi.

## Bağlam ve karar

Faz satırları ürün yönünü anlatıyor fakat özellikle state/kimlik sırası ve çok sonuçlu P02/P03 işleri doğrudan uygulama birimi değil. Yakın işin ayrıntılı kabulü tek kartta tutulur; faz bağımlılık/boyut, current aktif/sonraki iş ve matris gerçek capability teslimini gösterir. Durum ve hazırlık sözleşmesi [roadmap indeksinde](../roadmap/README.md#hazır-iş-paketi) kanoniktir. Yalnız ilk yakın kart oluşturulur; bütün gelecek fazlar için boş dosya üretilmez.

Ajan prosedürleri `.agents/skills` altında altı dar, instruction-only skill'dir. `.claude/skills` aynı dizinlere göreli bağlantı taşır; root AGENTS kanonik kural, CLAUDE ince giriş dosyası olarak kalır. Skill bir ürün yetkisi, repo yönetimi, otomatik release veya alt ajan izni vermez. İstemci/model/hook ve kullanıcı global ayarı kopyalanmaz.

## Alternatifler ve sonuçlar

Her işte bütün belge kataloğunu yüklemek bağlamı şişirir; görev bazlı okuma tercih edilir. Her platform için kopya skill drift üretir; aynı kaynağa alias kullanılır. Yalnız faz tablosu ise tek PR sınırını/kabulünü açık bırakır; yakın kart bunu kapatır. Her ufak belge düzeltmesine kart, ADR ve zorunlu onay eklemek gerekli görülmedi.

Kullanıcının belirttiği yerel örneklerden kapsam/uygulama ayrımı, şema-tüketici-test izi, bağlamı ilgili sınıra daraltma ve kanıtlı durum geçişi örüntüleri incelendi. Bu projelerin ürün/mimari/CI/izin ve release kuralları devralınmadı; metinler Yörünge için yazıldı. Uyarlama sınırı [review kaydındadır](../research/roadmap-readiness-review.md); yerel checkout kimlikleri yayımlanabilir kararın girdisi değildir.

Doğrulama metadata, bağlantı/alias ve hazır kart bağımlılığını denetler; modelin her doğal dil isteğinde doğru skill'i seçtiğini kanıtlamaz. Canonical ajan materyali sdist geliştirme kaynağına seçilir, wheel'e girmez; istemci alias'ları ve özel/yerel çalışma arşivi dağıtım girdisi değildir.
