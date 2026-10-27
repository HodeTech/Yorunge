# Eğitim ve değerlendirme modülü

**Durum:** Planlandı. **Kapsam:** C08/C09/C10. **Faz:** P03.

İki eğitim yolu vardır: EVREN'in yönetilen eğitim hizmeti ve seçilmiş haricî araçla LLM görevi. Veri/model sürümü, görev türü, hiperparametreler, maliyet ve sonuçlar açık planla bağlanır. Bu iki yol aynı CLI ailesinde anlaşılır gösterilebilir; motor/erişim farkları silinmez.

Uygun LLM görevlerinde varsayılan ForgeLM'dir. Kullanıcı desteklenen muadili seçebilir. LLM veri dönüştürme/denetim/üretim, kaynak uygunluğu, değerlendirme, merge ve export yetenekleri görev bazında çözülür; bir trainer'ın bulunması tüm değerlendirme/format seçeneklerini desteklediğini göstermez. Salt aktarım/path/hash kontrolü ise veri seti modülünün native görevidir.

**Çıktı:** Execution durumu, ham sağlayıcı kimliği/kodu, tipli metrikler ve beklenen artefakt tanımı. mAP ile LLM judge puanı aynı skor alanında karşılaştırılmaz. Ortak kalite kapısı seçilen araçta uygulanamıyorsa plan reddedilir veya kullanıcıya açıkça başka akış önerilir; kapı sessizce düşürülmez.

**Kabul:** Yönetilen iş tahmin/başlatma/izleme/durdurma, araç seçimi, belirsiz POST, metrik bağlamı, eksik çıktı ve ForgeLM + en az bir muadil SFT pilotu doğrulanır. EVREN runtime erişimi yoksa haricî araç yerelde çalıştırılmış sonuç EVREN GPU eğitimi diye sunulmaz.
