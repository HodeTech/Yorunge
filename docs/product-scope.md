# Ürün kapsamı ve öncelikler

**Güncellendi:** 2026-10-27. **Durum:** Benimsenmiş kapsam; ilk offline planlama alt kümesi uygulandı. Tam özellik durumları [matristedir](capability-matrix.md).

## Kullanıcı problemleri

EVREN kullanıcılarının farklı hizmetler için doğru kimlik ve bağlamı seçmesi, dosya aktarımını doğrulaması, model/görev uyumunu anlaması, eğitim ve kota durumunu yorumlaması, kesintide doğru adımı atması ve çıktıyı bulması gerekir. Yörünge bu görevlerin ortak ve tekrar eden işlerini üstlenir.

## Ürün alanları

| Alan | Kapsanan işler | İlk değer |
|---|---|---|
| Hesap ve bağlam | Profil, hizmet anahtarı, organizasyon/proje seçimi, yetki tanılama | Yanlış hesaba/projeye işlem yapmamak |
| Veri seti yaşam döngüsü | Yerel denetim, manifest, private oluşturma, yükleme, indirme, sürdürme, doğrulama, sürüm/bölme bilgisi | Güvenilir veri girişi ve çıkışı |
| Katalog ve modeller | Model/veri keşfi, görev-yetenek uyumu, model sürümü ve ağırlık indirme | Uygun kaynağı seçmek |
| LLM ve çıkarım | Metin/akış, embedding, rerank, görsel çıkarım; sonraki aşamada OCR/ses gibi keşfedilmiş servisler | Uygulama kurmak ve çıktıyı kullanmak |
| Eğitim/değerlendirme | Yönetilen EVREN eğitim işi; haricî araçla LLM veri hazırlama/denetim/üretim, kaynak uygunluğu, eğitim/değerlendirme, merge/export | Planlanmış ve izlenebilir model geliştirme |
| Kaynak ve maliyet | GPU görünürlüğü, rezervasyon bilgisi, kuyruk, kredi/kota, tahmin ve gerçek tutar | Uygun zamanda ve kaynakla çalışmak |
| İş akışı ve artefakt | Plan, onay, kalıcı işlem durumu, uzlaştırma, metrik ve dosya manifesti | Sonucu kaybetmeden tekrar üretmek |
| Entegrasyonlar | ForgeLM varsayılanı; seçilebilir muadiller; Python API; daha sonra MCP | Kullanıcı tercihine ve otomasyona uyum |

## İlk kullanılabilir sürüm

İlk sürüm, bütün alanların bütün uçlarını açmayı hedeflemez. Şu işler tek başına tamamlanabilir olmalıdır:

1. Profil/proje ve servis yeteneklerini tanıla; model/kota bilgisini oku.
2. Yerel klasörü denetle, private veri setine güvenilir biçimde yükle; kesintiden sonra uzlaştır ve doğrula.
3. Desteklenen metin/çıkarım isteğini yap; yanıtı ve kullanım bilgisini kaydet; bozuk/kesilmiş yanıtı açık göster.
4. Yönetilen EVREN eğitimini uygun veri sürümüyle planla, başlat, izle ve sonucunu indir; sunucu sözleşmesi doğrulamasına bağlıdır.
5. Uygun LLM görevi için varsayılan ForgeLM veya doğrulanmış alternatifle hazırlık/çalıştırma planı oluştur; izinli ortamda yürüt ve artefaktları topla.

İlk eğitim/araç sürümünün kabulü en az bir ForgeLM sağlayıcısı ve aynı sınıftaki en az bir alternatifin ortak sözleşme deneyini gerektirir. Alternatif sağlayıcı yokken “araçtan bağımsız kullanım hazır” denmez. [P03](roadmap/phase-03-training-and-tools.md).

## Öncelik sırası

**P0:** Kolay başlangıç, net çıktı/hata, veri doğruluğu, doğru hizmet/bağlam, hafif kurulum, kalıcı işlem durumu ve ölçülebilir performans. **P1:** Eğitimin ve seçenekli araç akışının tamamlanması, kaynak takibi, artefakt/deney karşılaştırması. **P2:** MCP, gelişmiş akış/köprü, OCR/ses, ekip otomasyonu ve erişim doğrulanmış notebook/runtime. Bu ürün öncelikleri güvenlik açıklarının önem derecesi değildir.

Performans sonradan eklenen ayrı bir aşama değildir; her fazın kabul koşuludur. Çıktı bütünlüğü pahasına hız kazanımı optimizasyon sayılmaz. Aynı şekilde çok sayıda seçenek göstermek, kullanıcının işi daha kolay bitirdiğini kanıtlamaz.

## Erişimle sınırlı işler

- EVREN GPU'sunda haricî Python/eğitim aracı yürütme: standart kullanıcı runtime erişimi ve çalışma ortamı doğrulanmalı.
- Kullanıcı LLM/adapter'ını EVREN gateway'de servis etme: ayrı kayıt ve serving sözleşmesi doğrulanmalı.
- Genel LLM fine-tuning API'si: incelenen gateway şemasında görülmedi; mevcut kabul edilmiş yetenek gibi sunulmaz.
- Yayınlama/silme ve rezervasyon iptali: ayrı etkili işlem politikası ve önizleme gerektirir; normal veri yükleme sonucuna gizlenmez.

## İlk kapsamın dışında

EVREN'in etiketleme editörünü yeniden yapmak, hesap/şart kabulünü otomatikleştirmek, GPU pazar yeri kurmak, kendi model mimarisi/quantization kernel'i geliştirmek, genel inference altyapısı işletmek ve tüm istemci protokollerini dönüştürmek. Tam web/masaüstü uygulaması ilk teslim bağımlılığı değildir; sonraki ihtiyaç araştırmasıyla değerlendirilebilir.

## Kapsam değişikliği

Yeni yetenek; kullanıcı işi, kaynak sözleşmesi, modül sahibi, performans bütçesi ve kabul kanıtıyla önerilir. Bir varsayılanı veya güven sınırını değiştiren karar ADR ile kaydedilir. [Matriste](capability-matrix.md) mevcut durum ve dış erişim koşulu ayrı tutulur; planlanmış satırın tamamlanması uygulama ve test kanıtı gerektirir.
