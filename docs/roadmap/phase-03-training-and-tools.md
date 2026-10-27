# P03 — Eğitim, değerlendirme ve seçilebilir araçlar

**Durum:** Planlandı. **Bağımlılık:** P01/P02. **Yetenekler:** C08–C10, C11 yazma planları, C12/C13 tam akış.

| İş | Kapsam | Kabul |
|---|---|---|
| P03-1 | Yönetilen EVREN eğitim sözleşmesi | Proje/veri sürümü/mimari, tahmin ve plan geçerliliği |
| P03-2 | Başlatma/izleme/durdurma ve sonuç toplama | Belirsiz POST, ham durum, iade/gerçek tutar, eksik artefakt |
| P03-3 | Tool port ve ForgeLM adaptörü | Varsayılan çözüm, ayrı ortam, public CLI/API, parametre/veri/çıktı eşlemesi |
| P03-4 | En az bir muadil adaptör | Aynı desteklenen SFT görevinde ForgeLM ile ortak sözleşme deneyi |
| P03-5 | LLM veri hazırlama/denetim/üretim, fit/judge/merge/export alt yetenekleri | ForgeLM varsayılan çözümü, muadilin görev kapsamı, model/yanıt/format, kalite kapısı ve artefakt rolü; her alt görev ayrı destek kaydı |
| P03-6 | Runtime erişim araştırması | EVREN backend desteği için kanıtlı erişim/ortam sonucu; belirsizlik açık kayıt |

## Zorunlu araç seçimi kanıtı

Varsayılan çağrı ForgeLM'i seçer. Açık muadil seçimi gerçekten o araca gider. Araç yoksa/uyumsuzsa sessiz fallback olmaz. Aynı küçük veri/model sınıfı üzerinde ortak task ve çıktı manifesti doğrulanır; desteklenmeyen seçenek açık hata üretir. İptal, deadline, kısmi çıktı ve haricî exit code da sınanır.

Axolotl ilk muadil adayıdır; LlamaFactory ve gerekli rolü belirlenmiş Unsloth ayrıca değerlendirilebilir. Adayın kurulabilirliği, görev ve lisans/ortam koşulları doğrulanmadan release desteği ilan edilmez.

## Çıkış kapısı

Yönetilen eğitim ve haricî LLM eğitim yolları farklı yetenek/ortamla anlaşılır gösterilir. En az ForgeLM + bir muadil ortak görevde doğrulanır; performans/kurulum yükü ayrı ölçülür. Native iş bir araca zorlanmaz. Tahmin gerçek harcama garantisi gibi sunulmaz; plan/onay/restart/uzlaştırma zinciri testlidir.

EVREN runtime erişimi kapalıysa bu sonuç P03-6'nın geçerli araştırma çıktısı olabilir; `evren-workspace` desteklenmiş sayılmaz ve ilgili uygulama P04 kapısında kalır. Kullanıcı özellikle EVREN GPU'su istediğinde yerel GPU'ya sessiz geçiş yapılamaz.
