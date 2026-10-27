# Dış hizmet ve erişim sınırları

**Durum:** Benimsenmiş sınırlar; dış kanıt başlangıcı 2026-10-26. **Güncellendi:** 2026-10-27.

## EVREN yüzeyleri

Platform REST API veri seti/proje/eğitim/kredi işleri, LLM gateway ise model servisleri için ayrı origin ve kimlik bağlamları taşır. Yükleme presign/PUT/confirm ve ZIP import ayrı akışlardır; etiket ve dosya biçimi ihtiyacına göre seçilir. Tek bir header veya yanıt zarfı bütün servislere dayatılmaz. [Kanıt kaydı](../research/evidence-register.md).

Kılavuz, yayımlanmış istemci ve topluluk ölçümlerinde durum adları, dosya sınırları veya statik kota değerleri farklı olabilir. Adaptör sıkı şema ve ham durum kaydını korur; bilinmeyen değer otomatik success veya boş sonuç olmaz. Hesap düzeyindeki paylaşılan kota çoklu key ile bağımsız kapasite gibi gösterilmez.

## Kaynak görünürlüğü ile çalıştırma yetkisi

GPU durumunu görmek ve rezervasyon yapmak farklı yeteneklerdir. İncelenen rezervasyon istemcisi doğrudan sunucu/SSH erişimi vermediğini açıklıyor. Notebook/runtime istemcisi mevcut olsa da başlangıç gözleminde admin preview ve execution kapıları var. Bunlar hesapla doğrulanmış genel erişim değildir.

Yörünge `evren-workspace` backend'ini; auth, Python/paket kurulumu, GPU erişimi, ağ, süre, kalıcı disk ve artefakt toplama doğrulanınca açar. Kullanıcı modeli gateway'e kaydetme/servis etme ayrı sözleşme gerektirir. Dış API şemasında bir yolun görülmemesi bütün özel/gelecek yeteneklerin yokluğu anlamına gelmez.

## SDK ve haricî araçlar

EVREN kılavuzunda referans verilen SDK uygun istemci işleri için değerlendirilebilir; tam kod denetimi ve endpoint bazlı test gerekir. SDK retry/redirect/stream davranışı Yörünge'nin üst katmanıyla birlikte sınanır. Dokümantasyonda “resmî” ifadesi bağımsız güvenilirlik sertifikası değildir.

ForgeLM öğretmen API'sinde base URL'ye `/chat/completions` eklenir; 26 Ekim'de incelenen judge yolunda tam endpoint bekleniyordu. Bu sürüme özel fark adaptör uyumluluk testine taşınır. Özel yardımcı fonksiyon kalıcı public entegrasyon API'si sayılmaz. Haricî süreç kendi HTTP trafiğini üretebilir; bütün trafiğin Yörünge taşımasından geçtiği iddia edilmez. Göreve verilen env/secret ve ağ izinleri dar tutulur.

Yerel proxy adresi ForgeLM'in HTTPS/özel IP politikasıyla otomatik uyumlu değildir. Geçit/araç güvenlik denetimini sessizce kapatan kolaylık sunulmaz. Kullanıcı parametresini ve araç tercihini değiştiren her dönüşüm plan raporunda görünürdür.

## Kanıt ve canlı doğrulama

Çevrimdışı sözleşme testi varsayılandır. Gerçek hesapta eğitim/veri/yayınlama veya kaynak tahsisi, kapsamı ve etkisi açık bir pilot işidir; sırlar rapora yazılmaz. Tasarım belgeleri bu işlemleri gerçekleştirmiş kabul etmez. Açık sorular ve geçiş ölçütleri [araştırma planındadır](../research/validation-questions.md).
