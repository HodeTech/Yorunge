# Kullanıcı yolculukları

**Güncellendi:** 2026-11-06. **Durum:** Uçtan uca hedef deneyimler. Yerel context/capability/plan, config/profil/doctor, credential/state, execution hazırlığı/onayı ve jobs; ortak HTTP/NDJSON, sınırlı salt okunur hizmet keşfi, yerel dataset inspect/verify ve farklı içerikli dosyalar için onaylı private upload ile aynı-ID salt okuma uzlaştırması development’a teslim edildi. Keşif ve upload sonucu uzak kimlik/yazma yetkisi, fiyat veya uzaktan byte doğrulaması üretmez. [Uygulanan CLI sınırı](reference/cli-contract.md#uygulanan-alt-küme) kanoniktir; aşağıdaki tam indirme/verify, etkili resume, çıkarım ve eğitim yolculukları henüz uygulanmadı; dataset baytlarının API anahtarıyla indirilememesi nedeniyle uzak byte doğrulaması [P02-R5](roadmap/tasks/p02-r5-dataset-item-byte-access.md)’e bağlıdır. [P02-2 planı](roadmap/p02-2-delivery-plan.md) teslim edilen private upload paketini ve açık karar/otorite sınırlarını gösterir.

## 1. İlk bağlantı

Kullanıcı profili seçer, gerekli hizmetin anahtarını ortam/işletim sistemi sır deposuyla bağlar ve gerekiyorsa projeyi belirler. Yörünge yalnız gereken hizmeti sınar; dosya denetlemek için hesap veya ağ zorunlu olmaz. Sonuç hangi görevlerin yapılabildiğini, bilinmeyenleri ve düzeltilecek tek sonraki adımı gösterir.

**Kabul:** Anahtar görünmez; ilk proje sessizce seçilmez; salt yerel komut ağ yapmaz; profil seçimi bir sonraki çağrıda tekrar sorulmaz. Yeni kullanıcıdan mimari modül veya adaptör kuramını bilmesi beklenmez.

## 2. Klasörü veri setine dönüştürmek

Klasör seç → dosya/format/hash denetimi → ad ve görünürlük özeti → yükleme planı → aktarım → uzak/yerel doğrulama → veri seti kimliği ve rapor. Kesintide yeni veri seti açmak yerine önceki işlem uzlaştırılır. Aynı boyutta değişen dosya ve kök dışı symlink açıkça bildirilir. Sonrasında `datasets versions list|show` bir veri setinin sürümlerini gösterir, `bind` seçilen dondurulmuş sürümün sağlayıcı metadata’sını bir dosyaya sabitler (yerel Manifest ile dosya sayısı eşliği üyelik kanıtı değildir), `check` sağlayıcıdaki sürümün hâlâ aynı olduğunu söyler; hiçbiri içerik, üyelik ya da model uygunluğu iddia etmez ([başvuru](reference/dataset-versions.md)).

**Kabul:** Büyük dosya akışlı gider; ilerleme gerçek aktarılan bayta dayanır; `done` günlüğü tek başına başarı kanıtı olmaz; son çıktı eksik dosyaları belirtir. Yalnız veri taşımak isteyen kullanıcı eğitim aracı kurmaz.

## 3. LLM veya çıkarım servisini kullanmak

İşi seç → modelin görev/yeteneklerini gör → girdiyi ver → yanıtı al/kaydet. Metin üretimi, embedding ve görsel çıkarım farklı çıktı sözleşmeleriyle gösterilir. Akış yarıda kesilirse tamamlanmış yanıt gibi kaydedilmez. Kota engelinde hangi sınırın bilindiği ve ne zaman tekrar denenebileceği görünür.

**Kabul:** Model listesinde görünmek tek uyum kanıtı sayılmaz; gömülü hata ve bozuk yanıt ele alınır; çok anahtar aynı hesabın kotasını artırıyor gibi gösterilmez. Araç gerekmediğinde ForgeLM bağımlılığı yoktur.

## 4. EVREN'de yönetilen eğitim

Veri seti sürümü → proje ve desteklenen mimari → hiperparametre/hesaplama seçimi → tahmin ve onay → başlatma → izleme → metrik ve ağırlık indirme. Veri sürümü ve plan kimliği iş kaydına bağlanır. Kullanıcı bağlantıyı kaybedip döndüğünde işin kimliği ve son durumu bulunur. Bir model sürümünün ağırlığı kesin sürüm kimliği (Platform arayüzündeki model sürümü sayfasından) ve biçimiyle `models download` ile yeni bir dosyaya indirilir: var olan dosya ezilmez, yarım kalan indirme aynı komutla devam eder ve sonuç, baytların kullanıcının kendi `--sha256` değeriyle eşleşip eşleşmediğini (`sha256_matched`) ya da yalnız aktarımın tamamlandığını (`transfer_complete`) açıkça söyler; seviye nesnenin özgünlüğü, lisansı ya da model uygunluğu değildir ([başvuru](reference/download-engine.md)).

**Kabul:** Tahmin ve gerçek maliyet ayrı; belirsiz POST ikinci işi başlatmaz; durdurma etkisi açık; bilinmeyen durum başarı diye çevrilmez. Bu akış EVREN'in yönetilen hizmetidir; haricî LLM aracının seçimi bu hizmetin eğitim motorunu değiştirmez.

## 5. Varsayılan veya alternatif araçla LLM geliştirmek

Amaç/veri/model → görev yetenekleri → varsayılan ForgeLM veya açık alternatif → çalıştırma ortamı → plan → çalıştırma → sonuçları toplama. Desteklenmeyen seçenek varsa planlama aşamasında açıklanır; seçenek başka araca sessizce aktarılmaz.

Bugün çalışan **yalnız plan hazırlığı** örneği: `yorunge train plan --config examples/profile.toml --recipe examples/training.yaml --tool axolotl --execution local`. Sonuç yürütülemez draft ve adaptör eksikliği taşır; eğitim/artefakt üretmez. Kullanıcı araç belirtmezse uygun LLM görevi için ForgeLM çözülür. İleride gerçek adaptör kurulu değilse eksik ortam ve açık seçenekler gösterilir; otomatik ağır indirme yapılmaz.

**Kabul:** Aynı sınıftaki görev iki doğrulanmış araçla yapılabilir; modele/parametreye özel farklar kaybolmaz. EVREN runtime erişimi yoksa kullanıcıya “EVREN GPU'sunda çalışıyor” denmez; başka ortam için ayrı seçim gerekir.

## 6. Sonuca dönmek ve otomasyon

İş kimliğiyle son durum, seçilen araç/sürüm, ortam, veri/model sürümleri ve artefakt manifesti görülür. CI kullanıcısı JSON çıktı ve kararlı çıkış koduyla aynı akışı yürütür. Kullanıcıya bir klasör yığını yerine neyin üretildiği ve neyin eksik kaldığı gösterilir.

**Kabul:** Haricî aracın ham çıkış kodu ve Yörünge'nin görev sonucu ayrı tutulur; eğitim tamamlanıp çıktı indirilmediyse teslim tamamlandı sayılmaz. Gerekli onay CI'da bekleyen soru olarak asılı kalmaz.

## Deneyim araştırması

İlk pilotta veri aktarımı, çıkarım ve eğitim görevlerinin her birini temsil eden kişiler gözlenir. İlk başarılı iş süresi, hata sayısı, yardım ihtiyacı, tekrar edilen iş/bayt ve çıktı bulma süresi ölçülür. Öncelikler kullanıcı gözlemiyle sınanır; mevcut kapsam görüşmelerle doğrulanmış talep sayısı iddiası taşımaz.
