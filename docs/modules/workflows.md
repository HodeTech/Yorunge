# İş akışları ve işlem durumu modülü

**Durum:** Uygulanıyor — offline v1 ve kalıcı execution v2 hazırlığı/validity/onay/yönetim testli; operation/lease/recovery/reset çekirdeği testli; public jobs list/show ve yerel paket kabulü tamamlandı (P01-4b/4c bu dalda verified). Public run planlandı. **Kapsam:** C12/C13; gelecekte C14 yüzeyi. **Faz:** P01–P04.

Plan oluşturma, context/tool/execution çözümleme, onay, operation/attempt koordinasyonu ve restart sonrası uzlaştırmayı sahiplenir. İlk sürüm sınırlı, bilinen görev bileşimleri kullanır; genel amaçlı kod çalıştıran workflow dili oluşturmaz.

Yan etki öncesi kalıcı kayıt ve sahiplik gerekir. Modüller kendi durumunu açık portlardan verir; gerektiğinde aynı yerel transaction koordinasyonuna katılır. Uzak istek transaction içine alınarak atomikmiş gibi gösterilmez. Onay digest'i ve önemli girdiler değiştiğinde plan yeniden hazırlanır.

Uygulanan hazırlık/onay [execution referansındadır](../reference/execution-plan.md); operation_id=null ve executable=false kalır.

**Uygulanan yerel operation çıktısı:** Tek operation kimliği, sıralı durum/geçiş kayıtları ve bütünlüklü sonuç. Kullanıcı terminali kapatsa da uzak işin kimliği kaybolmaz. İzlemeyi bırakmak durdurma sayılmaz. Bilinmeyen iş otomatik yeni execution'a dönüşmez.

**İç çekirdek kabulü:** Aynı planın çift gönderimi, lease devri, sonuç yazma belirsizliği, bozuk durum, credential/onay yarışı ve reset ayrı süreçlerle sınandı; [kanıt](../research/p01-4-implementation-validation.md). Public jobs CLI/Python aynı yerel okuma kuralını kullanır; MCP ve uzak watch/stop sonraki fazlardadır. [Çalıştırma modeli](../architecture/execution-model.md).

[Operation/jobs sözleşmesi](../reference/operations.md) durum, cursor ve finite kapasite sınırını taşır. Jobs lease süresini uzatmaz, otomatik takeover yapmaz; son yerel durum stale olabilir.
