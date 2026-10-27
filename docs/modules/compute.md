# Kaynak, kota ve maliyet modülü

**Durum:** Planlandı. **Kapsam:** C11/C16 ve C18'in kaynak işlemleri. **Faz:** P02–P04.

GPU/kuyruk/rezervasyon görünürlüğü, kredi/kota, maliyet tahmini ve gerçekleşen tüketim bu alandadır. Yörünge kaynak satıcısı veya GPU tahsis otoritesi olmaz; EVREN'in doğrulanmış hizmetlerini kullanır.

Kamuya açık envanter, anlık boş GPU, hesabın rezervasyonu ve runtime'a atanmış GPU farklı kayıtlardır. Birinin varlığı diğerini kanıtlamaz. Tahmin, hold/rezervasyon, gerçekleşen tutar ve iade ayrı tutulur; günlük gün/saat sınırı kaynağı kaydedilir.

İzleme adaptive polling ve kısa ömürlü cache ile gereksiz sorguyu azaltır. Sabit kota sayısı yerine hesabın güncel cevabı kullanılır. Geçersiz/sonlu olmayan maliyetle plan ilerlemez. Yerel rezervasyon platform bakiyesi veya kesin gerçek harcama tavanı gibi sunulmaz.

**Kabul:** Paylaşılan hesap kotası, eski cache, gecikmeli ledger, gün değişimi, belirsiz kaynak işlemi ve runtime erişim eksikliği sınanır. Rezervasyon yaratma/iptal/sonlandırma ayrı etki planına bağlıdır. Kaynak yazma desteği doğrulanmadan salt okunur görünürlüğün yanında açık görünür.
