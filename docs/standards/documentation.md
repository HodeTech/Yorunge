# Belgeleme standardı

**Durum:** Benimsenmiş; mevcut belge temelinde uygulanır. **Tarih:** 2026-10-27.

## Dil, biçim ve yerleşim

Kanonik açıklama dili Türkçedir. Dosya/dizin adları İngilizce `kebab-case`; kod, config anahtarı, hata kimliği ve makine sözleşmeleri İngilizcedir. Çeviri eklenirse kanonik belgeye ve güncellik durumuna bağlanır; bugün İngilizce eş doküman zorunluluğu yoktur.

Bir Markdown dosyası ilk satırda tek H1 ile başlar; skill ve iş kartında gereken YAML frontmatter önce, tek H1 hemen ardından gelir. Kod bloğundaki örnek başlık gerçek belge başlığı sayılmaz. Yaşayan belgede tarih/durum belirtilir. UTF-8/LF, GitHub Markdown ve gerekli yerde Mermaid kullanılır. İndeksler yalnız bağlantı/amaç haritasını tutar; ayrıntıyı çoğaltmaz. Belge alt dizininin README'si vardır; tek görevli skill klasörüne gereksiz README eklenmez. Kanonik klasör `docs/standards`'tır.

## Tek kaynak ve doğru durum

| Bilgi | Kanonik yer |
|---|---|
| Ürün sınırı | `product-scope.md` |
| Özellik teslimi | `capability-matrix.md` |
| Modül sahibi | `modules/README.md` ve ilgili modül |
| CLI/config/adaptör biçimi | `reference` altındaki ilgili sözleşme |
| İş sırası/aktif çalışma | `roadmap` |
| Kararın nedeni | `decisions` |
| Dış kanıt ve açık sorular | `research` |
| İş paketi hazırlığı ve ayrıntılı kabul | `roadmap/README.md` ve ilgili `roadmap/tasks` kartı |
| Ajanın tekrarlanan görev prosedürü | `.agents/skills`; ortak kurallar root `AGENTS.md` |

Taslak/benimsenmiş tasarım ile uygulanmış/yayımlanmış davranış ayrı yazılır. Belge tarihini yenilemek canlı kaynağın tekrar doğrulandığını göstermez. Örnek komutlar henüz çalışmıyorsa üstünde açık “taslak” ibaresi ve uygun `text` bloğu bulunur; kurulmamış pakete kurulum önerilmez.

İç bağlantılar göreli ve mevcut dosyaya gider. Kişisel mutlak yollar, başka checkout'a bağımlı belge bağlantıları ve sır/özel veri repo belgelerine yazılmaz. Dış kaynakta URL, erişim tarihi, kanıt türü ve sınır kaydedilir. Ham site metni ve büyük bundle kopyalanmaz; kendi sözlerimizle tespit yazılır.

## Özel analiz arşivi

`docs/analysis/private/` Git'ten ve yayın kapsamından dışlanır. Bu arşivin içeriği, kaynak proje adları, bağlantıları veya deney sonuçları yayımlanabilir belgelerin ve uygulama kodunun referansı olamaz. Arşive yönlendiren içerik bağlantısı oluşturulmaz; ürünün gerektirdiği karar kanonik belgede bağımsız anlatılır. Arşivdeki tarihsel belgeler mevcut biçimleriyle korunur; genel belge indeks/biçim kontrolleri ve yayın taramaları bu dizini kapsamaz.

## ADR ve değişiklik

ADR adı `NNNN-short-title.md`; durum, tarih, bağlam, karar, alternatifler ve sonuçlar içerir. Kullanıcı talimatıyla verilmiş karar kabul edildi diye kaydedilebilir; hâlâ açık seçim Proposed kalır. Accepted kararın anlamı değişirse yeni ADR ile ilişki kurulur. Düzeltme ve supersede bağlantıları görünür kalır.

Teslimden önce yerel dosya/anchor bağlantıları, başlıklar, fence'ler, sıralı ADR/modül/faz kimlikleri ve özellik durumu karşılaştırılır. Diyagram saymak render testi değildir; render edilmediyse ayrıca başarı iddiası yazılmaz.
