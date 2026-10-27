# Doğrulama soruları ve deney planı

**Durum:** Açık araştırma; hesap/GPU deneyi yapılmadı. **Tarih:** 2026-10-27.

## Kullanıcı ihtiyacı

Veri seti sorumlusu, LLM/çıkarım geliştiricisi, görsel eğitim kullanıcısı ve LLM eğitimi yapan kişiden gerçek görev gözlemi alınmalı. Hangi adımda hata yapılıyor, ne kadar yardım gerekiyor, sonuç nasıl doğrulanıyor ve hangi muadil araç zaten kullanılıyor? Önceki araştırma ihtiyaç hipotezi üretir; pazar/kullanıcı istatistiği sayılmaz.

Pilot görevleri: ilk profil ve model sorgusu; kesintili klasör yükleme/indirme; LLM/çıkarım sonucu; eğitim planı ve çıktı toplama; ForgeLM yerine açık muadil seçimi. Süre/yardım/hata/tekrar bayt ve çıktı bulunabilirliği ölçülür. Kullanıcıdan gereksiz araç/mimari bilgisi istenmez.

## EVREN sözleşmesi

| Soru | Geçiş ölçütü |
|---|---|
| Güncel Platform şema ve anahtar yetkileri nerede? | Kapsamlı auth/endpoint/envelope/hata örnekleri; açık kaynak tarihi |
| Dosya boyutu/formatı ve presign hedefi ne? | Native upload/confirm/dedup doğrulaması; test edilmiş boyut ve resmî limit ayrı |
| Yönetilen eğitim durum/parametre/idempotency garantisi ne? | Model/veri sürümü, tahmin ve belirsiz POST için korelasyon |
| Kota ve kredi hangi hesap/gün kapsamında? | Paylaşılan key kapsamı, reset zamanı, tahmin/hold/gerçek tutar |
| Notebook/runtime kimlere açık? | Standart/pilot hesapta desteklenen auth ve execution yetkisi |
| Haricî paket/image, model ve veri erişimi var mı? | Python/GPU, ağ/cache, süre ve kalıcı disk deneyi |
| Çıktı nasıl alınır ve tekrar sürdürülür? | Checkpoint/model/kanıt indirme; restart ve maliyet uzlaştırması |
| Kullanıcı LLM/adapter gateway'e kaydedilebilir mi? | Açık registration/serving sözleşmesi; yalnız dosya yükleme yeterli değil |

Bu sorular hazırlanmış listedir; sağlayıcıya mesaj gönderilmedi. Gereken gerçek hesap denemesi kapsamı/etkisi açık bir iş olarak ayrıca yürütülür; sır veya özel veri rapora alınmaz.

## Araç muadili deneyi

ForgeLM + seçilmiş bir adayda aynı küçük SFT görevini hazırla. Girdi dönüşümü, method/epoch, model revision, başlangıç ve tepe kaynak, iptal/checkpoint, çıktı rolleri ve hata kodunu karşılaştır. Muadil araçta olmayan kalite/export özelliğini raporla; sessizce atlama. Destek ilanı yalnız denenen sürüm/görev/ortam birleşimini kapsar.

## Runtime kapısı

Yetkili ortamda araç kurulum/başlatma, atanmış GPU, birkaç adımlık gerçek eğitim, adapter/checkpoint ve kanıt dosyasını ortam dışına alma gösterilmelidir. Süre sonu/iptal, bağlantı kaybı ve restart sonrası uzlaştırma sınanır. Kapı geçmezse `evren-workspace` açılmaz; veri/çıkarım ve yerel araç işleri bağımsız ilerleyebilir.

## Performans kapısı

Seçilen paket/CLI ile sıcak/soğuk başlangıç; artan dosya boyutuyla istemci RSS; N+1/sayfalama çağrı sayısı; bounded worker ve yavaş servis davranışı ölçülür. Hedef ve gerçek sonuç [performans standardına](../standards/performance.md) bağlanır. Optimizasyon önce/sonra veri doğruluğu korunur.
