# Yetenek ve teslim matrisi

**Güncellendi:** 2026-10-27. **Durum:** Kanonik kapsam ve uygulama durum kaydı.

İlk çevrimdışı context/capability/planlama alt kümesi yerelde test edilmiştir; tam yetenek satırları tamamlanmış sayılmaz. Dış platform kanıtı ile bizim uygulama durumumuz farklı sütunlardır. `P01`–`P04` geliştirme fazlarıdır; teslim tarihi taahhüdü değildir. Kanıt: [P01 kabul kaydı](research/p01-core-validation.md), çalışma sürümü `0.1.0.dev0` (yayımlanmadı).

| Kimlik | Yetenek | Kullanıcı sonucu | EVREN/araç kanıtı | Yörünge durumu | Hedef |
|---|---|---|---|---|---|
| C01 | Profil, servis kimliği ve proje | Doğru hedefle başlamak | Platform/LLM kimlik yüzeyleri incelendi | Uygulanıyor — yerel profil/context testli; uzak kimlik yok | P01 yerel / P02-0b uzak |
| C02 | Doctor ve yetenek keşfi | Ne yapabileceğini öğrenmek | Şema/kılavuz + hesapla doğrulama gereği | Uygulanıyor — offline görünüm testli; doctor/keşif/cache yok | P01 yerel / P02 hesap kanıtı |
| C03 | Veri denetim/yükleme/indirme/doğrulama | Veriyi kayıpsız taşımak | Resmî veri seti/yükleme kılavuzu; hesapla doğrulanacak | Planlandı | P02 |
| C04 | Sürüm, bölme ve veri bağları | Aynı girdiyi tekrar kullanmak | Platform kılavuzu; endpoint uyumu doğrulanacak | Planlandı | P02/P03 |
| C05 | Model/veri kataloğu | Uygun modeli bulmak | Platform kataloğu ve LLM model şeması | Planlandı | P02 |
| C06 | LLM metin, akış, embedding, rerank | Uygulama çıktısı üretmek | Resmî gateway OpenAPI | Planlandı | P02 |
| C07 | Görsel çıkarım | Görsel modele istek ve sonuç | Kılavuz ve referans verilen SDK | Planlandı | P02/P03 |
| C08 | Yönetilen EVREN eğitimi | Görsel eğitim ve ağırlık sonucu | Resmî eğitim kılavuzu; hesap sözleşmesi doğrulanacak | Planlandı | P03 |
| C09 | Seçilebilir LLM eğitim aracı | ForgeLM veya muadille aynı görevi yapmak | ForgeLM kodu; muadil adaptörleri araştırılacak | Planlandı | P03 |
| C10 | LLM veri hazırlama/denetim/üretim, fit, değerlendirme, merge/export | Eğitim çevrimini tamamlamak | ForgeLM ilgili yetenekleri; göreve özel uyum gerekli | Planlandı | P03 aşamalı |
| C11 | GPU, kuyruk, rezervasyon, kota | Kaynak ve tüketimi görmek | Kamu altyapısı ve istemci/kota şeması | Planlandı | P02/P03 |
| C12 | İş kaydı, izleme, uzlaştırma, artefakt | Kesintiden toparlanmak | Yörünge'nin çekirdek gereksinimi | Uygulanıyor — yalnız offline draft; operasyon/teslim yok | P01–P03 |
| C13 | Tekrarlanabilir reçete ve JSON API | Otomasyon kurmak | Yeni Yörünge sözleşmesi | Uygulanıyor — dar YAML/JSON ve ortak Python API testli | P01–P03 |
| C14 | MCP ve gelişmiş terminal/köprü | Ajanlardan aynı işi yürütmek | Yörünge adaptörü ve protokol/host doğrulaması gerekli | Planlandı | P04 |
| C15 | OCR/ses ve ileri servisler | Metin dışı girdi/çıktı işlemek | Gateway şemasında servis yüzeyi var | Planlandı | P04 |
| C16 | EVREN runtime'da haricî araç | EVREN GPU'sunda LLM eğitmek | İstemci gözlemi; genel kullanıcı erişimi doğrulanmadı | Erişim kapılı plan | P03 keşif / P04 uygulama |
| C17 | Kullanıcı LLM/adapter serving | Kendi modeliyle EVREN'de çıkarım | Genel sözleşme doğrulanmadı | Araştırma | P04-R1; implementasyon kapı sonrası |
| C18 | Yayınlama, silme, rezervasyon yazma | Kaynak yaşam döngüsünü yönetmek | İşleme özel yetki/etki sözleşmesi gerekli | Sınırlı plan | P03/P04 |

## Uygulama durumları

Roadmap iş kartlarının `ready`/`verified` durumu bu satırın tamamlandığı anlamına gelmez. Kart, belirli bir alt teslimi kanıtlar; satırın kapsamı ve dış erişim koşulları ayrıca değerlendirilir. [İş hazırlığı](roadmap/README.md#hazır-iş-paketi).

`Araştırma` → `Planlandı` → `Uygulanıyor` → `Deneysel` → `Doğrulandı` → `Yayımlandı`. Deneysel veya doğrulandı durumuna geçişte test/işlem kanıtı ve sürüm/commit kaydı gerekir. Bir fazın yapılmış olması tüm satırlarının yayımlandığı anlamına gelmez. Dış erişime bağlı satır, erişim kapısı geçilmeden genel kullanıcı desteği kazanmaz.

## Hesap yeteneği durumları

Çalışma sırasında kullanılan `supported`, `unsupported`, `unknown`, `requires_access` değerleri bu teslim durumlarından ayrıdır. Yetkili bir hesaba 403 dönmesi tek başına tüm platformun o yeteneği desteklemediğini söylemez. Önbelleğin tarihi ve yetki kapsamı korunur. [Yetenek kaydı](reference/capability-record.md).

## Araç desteği

ForgeLM varsayılan tercihi kullanıcı talimatıdır; adaptörün bugün var olduğu iddiası değildir. P03, varsayılan ForgeLM ile en az bir muadil aracı aynı görev için doğrular. Axolotl ve LlamaFactory adaydır; Unsloth hem bazı araçların hızlandırma backend'i hem ayrı entegrasyon adayı olabilir. Hangi rolün desteklendiği açık yazılmadan eşdeğerlik iddiası kurulmaz. [Araç sözleşmesi](reference/tool-provider-contract.md), [kaynak kaydı](research/evidence-register.md).

## Kanıt güncelliği

EVREN bulgularının başlangıç anı 26 Ekim 2026'dır. Kılavuz metni, yayımlanmış istemci ve gerçek hesap davranışı ayrı kanıt türleridir. İlk canlı entegrasyonda ve önemli API değişikliğinde yeniden doğrulama yapılır. Güncel API listesi, fiyat/kota veya donanım tahsisi bu statik tabloda sabitlenmez.
