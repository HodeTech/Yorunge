# Artefakt ve sonuç modülü

**Durum:** Planlandı. **Kapsam:** C12; C17 için yalnız araştırma bağlantısı. **Faz:** P02–P04.

Model/adapter, ağırlık, veri raporu, metrik ve audit/evidence dosyalarının teslimi, kökeni ve hash manifestini sahiplenir. Uzak model serving kaydı doğrulanana kadar dosya export etmek serving desteği diye sunulmaz.

Artefakt manifesti operation/run kimliği, üretici araç/sürüm, veri/model bağları, dosya adı/boyut/hash ve doğrulama türünü taşır. Büyük içerik DB'ye veya stdout'a basılmaz. Gerekli dosya eksikse bütün görev success olmaz; yeniden toplama mümkünse kullanıcı eğitimi tekrarlamadan devam eder.

İndirmeler boyut/hedef/isim ve no-clobber kurallarıyla akışlıdır. Aynı görevde farklı araç çıktıları tipli rollerle normalize edilir; birinin adapter'ı diğerinin tam model ağırlığı diye etiketlenmez. Hassas örnek/prompt içeren raporlar açık veri paylaşımı kapsamına girer; varsayılan metadata özeti tercih edilir.

**Kabul:** Eksik/bozuk dosya, hash uyuşmazlığı, indirme kesintisi, hedef yarışı ve yeniden toplama test edilir. Kullanıcı çıktı yolunu ve ne kadarının doğrulandığını tek sonuçta görür.
