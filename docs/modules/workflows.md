# İş akışları ve işlem durumu modülü

**Durum:** Uygulanıyor — seçim/digest/offline draft testli; yürütme/kalıcı durum planlandı. **Kapsam:** C12/C13; gelecekte C14 yüzeyi. **Faz:** P01–P04.

Plan oluşturma, context/tool/execution çözümleme, onay, operation/attempt koordinasyonu ve restart sonrası uzlaştırmayı sahiplenir. İlk sürüm sınırlı, bilinen görev bileşimleri kullanır; genel amaçlı kod çalıştıran workflow dili oluşturmaz.

Yan etki öncesi kalıcı kayıt ve sahiplik gerekir. Modüller kendi durumunu açık portlardan verir; gerektiğinde aynı yerel transaction koordinasyonuna katılır. Uzak istek transaction içine alınarak atomikmiş gibi gösterilmez. Onay digest'i ve önemli girdiler değiştiğinde plan yeniden hazırlanır.

**Çıktı:** Tek operation kimliği, sıralı durum/geçiş kayıtları ve bütünlüklü sonuç. Kullanıcı terminali kapatsa da uzak işin kimliği kaybolmaz. İzlemeyi bırakmak durdurma sayılmaz. Bilinmeyen iş otomatik yeni execution'a dönüşmez.

**Kabul:** Aynı planın çift yürütümü, lease devri, kritik kayıt hatası, bozuk durum, CI onayı, cancellation ve yeni profile geçiş sınanır. CLI/Python/MCP aynı iş kurallarını çağırır. [Çalıştırma modeli](../architecture/execution-model.md).
