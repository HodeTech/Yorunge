# Kimlik ve bağlam modülü

**Durum:** Planlandı. **Kapsam:** C01. **Faz:** P01.

Profil, hizmet adresi, secret referansı, hesap/organizasyon/proje tercihleri ve bunların doğrulanmasını sahiplenir. Hesap oluşturma, şart kabulü veya uzakta anahtar üretme ilk kapsam değildir.

**Girdi:** Kullanıcının seçtiği profil ve gerektiği kadar yetkili hizmet bilgisi. **Çıktı:** Sır içermeyen, işleme sabitlenen context kimliği ve açıklayıcı erişim sonucu. Uzak SDK kimlik tipi çekirdek modeline sızmaz.

Birden fazla proje varsa açık seçim gerekir; geçmiş profil tercihi tekrar kullanılabilir. Anahtar gerektiğinde okunur; salt yerel yardım/manifest kontrolü keychain veya ağ açmaz. Hata yanlış anahtar türü, erişim reddi ve bağlantı sorununu ayırır; secret'ın son karakterlerini göstermek varsayılan tanılama gereği değildir.

**Kabul:** Profil/hizmet karışması, cache kapsamı, env/keychain eksikliği ve sır yansıması test edilir. Context değişince plan geçerliliği yeniden değerlendirilir. [Yapılandırma sözleşmesi](../reference/configuration.md).
