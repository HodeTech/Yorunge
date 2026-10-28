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

Bu tablo mantıksal sahipliktir; identity temeli için üç tablo ve migration P01-4a'da, cache/clock için iki tablo ve 1→2 migration P01-3a'da uygulanır. Plan2→3 ve onay3→4 migration'ları P01-3b tüketicileriyle uygulanmıştır; diğer satırların DDL/işleyişi kendi tüketicileriyle gelir; varmış gibi çalışan örnek verilmez. [Gerçek uygulama kabulü](../research/p01-3-implementation-validation.md).

Kimlik karşılaştırması için özel HMAC doğrulayıcısı ve ayrı K dosyası [Accepted ADR-0012](../decisions/0012-credential-identity-and-change-detection.md) ile kullanıcı tarafından benimsenmiştir; genel sır saklama yasağı yalnız bu verifier için daraltılmıştır, ham sır/hash yasağı korunur. Verifier public kayıt, cache, Plan veya normal export verisi değildir. Bu kararın identity alt kümesi ve [ADR-0011 migration/yedek temeli](../decisions/0011-state-foundation-and-migrations.md) P01-2 içinde doğrulandı; [kanıt ve kapsam](../research/p01-2-implementation-validation.md). Operation/lease/uzak yürütüm henüz uygulanmadı.

Canlı DB üzerindeki identity reset ile eski DB snapshot'ını restore etmek farklıdır: restore snapshot sonrasındaki işlem geçmişini kaybedebilir. Benimsenmiş [restore kapısı](../decisions/0012-credential-identity-and-change-detection.md#identity-reset-ve-db-restore-ayrımı), operation tüketicisi eklendiğinde kayıp geçmiş için ayrı güvenilir uzlaştırma kurulana kadar DB restore'u reddeder; reset unknown işe yeniden gönderim yetkisi vermez. P01-3'te cache/plan/onay tüketicilerinin bakım uyumu [Accepted ADR-0014](../decisions/0014-execution-plan-validity-and-approval.md) ile 2026-10-27 tarihinde onaylandı; identity/cache/clock/plan/approval runtime allowlist'i ve eski intent yükseltmeleri uygulandı. Operation runtime restore yasağı sürer.

## Dosya yaşam döngüsü

Yerel dosya → kök/metadata denetimi → güncel hash → değişim politikası → aktarım → endpoint bazlı confirm → uzak öğe ve teslim doğrulaması. Dosya hash ile okunduktan sonra değişirse güvence kaybolur; açık descriptor, stat değişimi ve gerektiğinde değişmez staging birlikte ele alınır.

İndirmeler benzersiz geçici hedefe gider; tamamlanma/byte/hash doğrulamasından sonra güvenli biçimde görünür olur. No-clobber ve atomik davranış desteklenmiyorsa üstüne yazma yarışıyla devam edilmez. Kısmi aktarım kayıtları ile tamamlanmış artefakt ayrıdır.

## Önbellek ve mutabakat

Model listesi/yetenek cache'i okuma hızını artırır; yetki ve maliyet kararı gerektiğinde yenilenir. Done journal veya eski cache uzak dosyanın hâlâ bulunduğunu kanıtlamaz. Resume, uzak durum ve değişen yerel girdiyi uzlaştırır. Cache temizleme kritik operation kaydını silmez.

Durum dosyaları/artefaktlar özel kullanıcı verisi olabilir. İzinler, rotasyon/saklama ve silme etkileri açık olmalı; kaynak repoda tutulmaz. Kullanıcı isteği olmadan uzak veri seti veya model temizlenmez.
