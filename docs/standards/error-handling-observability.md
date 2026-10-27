# Hata, sonuç ve gözlemlenebilirlik standardı

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

Hata kodları kararlı İngilizce kimliktir; insan açıklaması yerelleştirilebilir. Türler en az kullanım/config, kimlik/erişim, destek/uyum, uzak servis, belirsiz yan etki, iptal ve bütünlük sınıflarını ayırır. Kamuya açık kod/çıktı tablosu yalnız [CLI sözleşmesinde](../reference/cli-contract.md) tutulur.

## Sonuç semantiği

Başarı, görev için vaat edilen sonucu kapsar. Uzak eğitim bitmiş ama artefakt indirilmemişse yürütme tamamlandı ve teslim bekliyor ayrı gösterilir. `unknown` hata yutma şekli değildir; belirsiz etkiyi ve uzlaştırma ihtiyacını taşır. Bozuk veya eksik cevap boş liste/sıfır harcama olarak normalleştirilmez.

Sağlayıcının ham hata kodu/çıkış kodu ayrı, sınırlı metadata'da korunur. ForgeLM çıkış kodları Yörünge kodlarının yerine geçirilmez. Adaptörün açıklaması kullanıcının güvenli sonraki adımını belirtir; gizli traceback veya sır içeren ham gövde gösterilmez.

## Log ve metrik

Yapısal ve kaçışlı kayıt, tek fiziksel kayıt semantiği, UTC zaman ve operation/attempt/request korelasyonu kullanılır. Model/dosya/oturum gibi metadata tür ve uzunluk sınırından geçer. Varsayılan log prompt, yanıt, araç argümanı veya anahtar tutmaz. Debug modu da sırları yazmaz. Saklama/rotasyon sınırlıdır.

Süreler: hazırlık, kuyruk, ilk veri, aktarım, uzak çalışma ve toplama olarak ayrılır. Tahmin, rezerve, gerçekleşen maliyet ve token kotası ayrı metriklerdir. Cache oranı veya proxy ölçümü kesin fatura gibi sunulmaz. Kullanıcıya/merkeze telemetry göndermek başlangıç varsayılanı değildir.

Log yazılamadığında kullanıcıya iletilmiş sonuç yeniden sınıflandırılıp tekrar başlatılmaz. Ancak yan etki öncesi zorunlu kalıcı işlem kaydı yazılamıyorsa işlem başlamaz. Kritik durum kaydı ve isteğe bağlı gözlem logunun dayanıklılık gerekleri farklıdır.
