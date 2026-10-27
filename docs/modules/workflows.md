# İş akışları ve işlem durumu modülü

**Durum:** Uygulanıyor — offline v1 ve kalıcı execution v2 hazırlığı/validity/onay/yönetim testli; operation/lease/run planlandı. **Kapsam:** C12/C13; gelecekte C14 yüzeyi. **Faz:** P01–P04.

Plan oluşturma, context/tool/execution çözümleme, onay, operation/attempt koordinasyonu ve restart sonrası uzlaştırmayı sahiplenir. İlk sürüm sınırlı, bilinen görev bileşimleri kullanır; genel amaçlı kod çalıştıran workflow dili oluşturmaz.

Yan etki öncesi kalıcı kayıt ve sahiplik gerekir. Modüller kendi durumunu açık portlardan verir; gerektiğinde aynı yerel transaction koordinasyonuna katılır. Uzak istek transaction içine alınarak atomikmiş gibi gösterilmez. Onay digest'i ve önemli girdiler değiştiğinde plan yeniden hazırlanır.

Uygulanan hazırlık/onay [execution referansındadır](../reference/execution-plan.md); operation_id=null ve executable=false kalır.

**Planlanan operation çıktısı:** Tek operation kimliği, sıralı durum/geçiş kayıtları ve bütünlüklü sonuç. Kullanıcı terminali kapatsa da uzak işin kimliği kaybolmaz. İzlemeyi bırakmak durdurma sayılmaz. Bilinmeyen iş otomatik yeni execution'a dönüşmez.

**Sonraki operation kabulü:** Aynı planın çift yürütümü, lease devri, kritik kayıt hatası, bozuk durum, CI onayı, cancellation ve yeni profile geçiş sınanır. CLI/Python/MCP aynı iş kurallarını çağırır. [Çalıştırma modeli](../architecture/execution-model.md).
