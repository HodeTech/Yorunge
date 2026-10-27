# P03 — Eğitim, değerlendirme ve seçilebilir araçlar

**Durum:** Planlandı; işe başlamadan dar kart gerekir. **Bağımlılık:** İlgili P01/P02 alt kapıları. **Yetenekler:** C08–C10, C11 maliyet görünümü, C12/C13 sonuç. Native eğitim ve haricî LLM araçları iki ayrı hattır.

| ID | İlk teslim sınırı | Önkoşul | Kabul kanıtı | Durum |
|---|---|---|---|---|
| P03-1 | Yönetilen görsel eğitim sözleşmesi ve planı | P02-0, P02-3 veri sürümü, P01-3b | Proje/veri/mimari, tahmin kaynağı ve onay bağı; native motor ForgeLM'e çevrilmez | `draft` |
| P03-2 | Yönetilen işi başlat/izle/durdur ve sonucu topla | P03-1, P01-4b, P01-5b | Belirsiz POST, ham durum/uzak kimlik, doğrulanmış iptal ve eksik artefakt | `draft` |
| P03-3 | Tool port + ForgeLM yerel adaptörü; ilk görev SFT | P01-3b, P01-4b, P01-5b; ForgeLM sürüm/public yüzey incelemesi | Ayrı ortam, public giriş, parametre/veri/sonuç eşlemesi ve gerçek süreç sınırı | `draft` |
| P03-4 | Bir muadilde aynı dar SFT görevini tamamlamak | P03-3 ortak sözleşmesi; aday deneyi | ForgeLM + muadil aynı veri/model sınıfı ve çıktı rolü; kayıplı seçenek reddi | `draft` |
| P03-5 | Ayrı LLM yaşam döngüsü görevleri | Göreve bağlı P03-3/P03-4 ve native servis kabulü | Her görev için ayrı sürüm/format/parametre/kalite kanıtı; tek adaptör adı bütün görev desteği değil | `draft` |
| P03-6 | EVREN runtime erişim ve ortam araştırması | Resmî sözleşme; varsa açık pilot yetkisi | Auth/kurulum/GPU/ağ/disk/süre/artefakt sonucu; kapalı/unknown da geçerli araştırma sonucu | `draft` |

P03-3/P03-4 yerel araç hattı, P03-1/P03-2 yönetilen eğitimini veya EVREN workspace erişimini beklemez. Paylaşılan P01 kayıt/onay/teslim kuralları iki hatta da geçerlidir. ForgeLM sürüm/public yüzeyi P03-3 hazırlığında; muadil sürüm/rol seçimi B05 ve P03-4 hazırlığında doğrulanır. Alternatifin tamamlanması ForgeLM portunun önkoşulu değildir.

## Araç hattının büyüklüğü

P03-3 (L) önce manifest/check ve parametre eşlemesi, sonra izinli ayrı süreçte çalıştırma, sonra sonuç/artefakt/iptal olarak bölünür. Yörünge çekirdeğine Torch/transformers/TRL eklenmez. Kurulum keşfi otomatik indirme veya kullanıcı ortamını güncelleme sebebi değildir. İlk SFT kanıtı küçük, revision'ı sabitlenmiş model/veri ve açıklanmış kaynak bütçesini kullanır; CPU süreç testi gerçek GPU eğitimi diye sunulmaz.

P03-4 (M/L) adayın rol/lisans/sürüm/ortam deneyini ve ortak SFT sözleşmesini ayrı ele alır. Axolotl ilk adaydır; LlamaFactory veya bağımsız rolü doğrulanmış Unsloth kararla seçilebilir. Kullanıcının açık seçimi değiştirilemez. Henüz adaptörü olmayan aday `supported` olmaz.

## P03-5 görev ayrımı

Sıra kalite/veri bağımlılığına göre kartta belirlenir; aşağıdakiler aynı PR'ın kapsamı değildir:

| Görev | Bağımlı sonuç | Ek kabul |
|---|---|---|
| `llm.data.ingest` | Kaynak biçimi ve araç veri dönüşümü | Kaynak korunur; yeni manifest ve dönüşüm raporu |
| `llm.data.audit` | Doğrulanmış veri referansı | İçerik raporu, açıklanmış kalite kapısı |
| `llm.data.generate` | Öğretmen servis/kimlik/kota kabulü | Sayı/kalite/maliyet sınırı ve örnek kökeni |
| `llm.fit.check` | Model/ortam ve araç sürümü | Tahminin kaynağı; genel GPU envanteri erişim kanıtı değil |
| `llm.evaluate` | Model/adapter ve benchmark/judge yolu | Metrik türü, judge endpoint farkı, açık kalite sonucu |
| `llm.merge` | Geçerli adapter/base bağı | Eksik/uyumsuz base reddi ve beklenen model rolü |
| `llm.export` | Araç/model/format kabulü | Doğrulanmış format, boyut/hash; serving iddiası yok |

`llm.train` ilk ortak SFT işi olarak P03-3/P03-4'tedir. “judge” yeni bağımsız task kimliği değildir; evaluation'ın göreve özgü yolu olabilir. Kaynak/parametre kaybı görünür rapor veya açık ret üretir; sessiz düşürme yoktur.

## Çıkış kapısı ve kapsam dışı

Varsayılan ForgeLM ve açık muadil gerçekten kendi araçlarında aynı desteklenen SFT task/result sınıfını tamamlar. İptal/deadline, süreç kodu, kısmi/eksik artefakt, restart/uzlaştırma ve secret izolasyonu ortaktır. Maliyet tahmini gerçek tutar garantisi değildir; execution ve delivery ayrı raporlanır. Kurulum ve kaynak etkisi [standarda](../standards/performance.md) göre ölçülür.

Yönetilen eğitim için ayrıca güncel hesap/servis pilotu gerekir; bilinmeyen native sözleşme destek ilanına çevrilmez. P03-6 erişimi kanıtlamazsa workspace uygulaması P04-3 kapısında kalır; kullanıcı EVREN istemişken yerel GPU'ya geçilmez. Rezervasyon oluşturma/iptali, yayınlama/silme ve kullanıcı modeli serving bu fazın gizli yan etkisi değildir. Kapalı ürün hedefinin release kapsamına etkisi yayın öncesi açık kullanıcı kararı olarak kaydedilir.
