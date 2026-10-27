# Veri, durum ve artefakt modeli

**Durum:** Benimsenmiş tasarım. **Tarih:** 2026-10-27.

## Yerel kayıt

SQLite ayrı servis gerektirmeden transaction, migration ve yeniden başlatma sonrası durum sağlar. Aynı anda bir koordinatörün operation üzerinde yazma sahipliği olmalı; lease süresi, fencing token ve expiry test edilir. Kısa transaction içinde uzak HTTP/uzun hash işlemi bekletilmez. Ağ dosya sistemindeki SQLite/WAL davranışı desteklenmiş varsayılmaz; ilk hedef yerel disk.

| Kayıt grubu | Tutulan bilgi | Tutulmayan bilgi |
|---|---|---|
| Profil referansları | Hizmet, hesap/proje tercihi, secret ref | Ham anahtar |
| Capability cache | Kaynak/kapsam/zaman/destek durumu | Tüm hesaplar için geçerli olduğu varsayımı |
| Plans | Sürüm, digest, seçimler, etki ve girdi bağları | Sır veya tüm veri kümesi |
| Operations / attempts | Durum, sahiplik, uzak kimlik, hata/korelasyon | Sınırsız ham cevap/günlük |
| Commitments | Tahmin, rezervasyon, gerçekleşen ve mutabakat kaydı | İadeleri bugünkü borca bağsız düşme |
| Transfers | Dosya kimliği, güncel hash, aşama, uzak öğe | Günlük var diye kalıcı uzak başarı varsayımı |
| Artifacts | Yerel/uzak referans, boyut/hash, köken ve doğrulama | Bütün model ağırlığının DB içine alınması |

Bu tablo mantıksal sahipliktir; kesin DDL ve migration P01'de karara bağlanacaktır. SQL şeması varmış gibi çalışan örnek verilmez.

## Dosya yaşam döngüsü

Yerel dosya → kök/metadata denetimi → güncel hash → değişim politikası → aktarım → endpoint bazlı confirm → uzak öğe ve teslim doğrulaması. Dosya hash ile okunduktan sonra değişirse güvence kaybolur; açık descriptor, stat değişimi ve gerektiğinde değişmez staging birlikte ele alınır.

İndirmeler benzersiz geçici hedefe gider; tamamlanma/byte/hash doğrulamasından sonra güvenli biçimde görünür olur. No-clobber ve atomik davranış desteklenmiyorsa üstüne yazma yarışıyla devam edilmez. Kısmi aktarım kayıtları ile tamamlanmış artefakt ayrıdır.

## Önbellek ve mutabakat

Model listesi/yetenek cache'i okuma hızını artırır; yetki ve maliyet kararı gerektiğinde yenilenir. Done journal veya eski cache uzak dosyanın hâlâ bulunduğunu kanıtlamaz. Resume, uzak durum ve değişen yerel girdiyi uzlaştırır. Cache temizleme kritik operation kaydını silmez.

Durum dosyaları/artefaktlar özel kullanıcı verisi olabilir. İzinler, rotasyon/saklama ve silme etkileri açık olmalı; kaynak repoda tutulmaz. Kullanıcı isteği olmadan uzak veri seti veya model temizlenmez.
