# Kullanım kolaylığı ve etkileşim standardı

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

Kullanıcı görevi seçer; uygulama ona gereken bağlam ve seçenekleri sırayla gösterir. Hesap/görev için ilgisiz ayarlar başlangıçta sorulmaz. Sonuç odaklı dil kullanılır; adaptör, port veya tablo adı normal kullanıcı akışına taşınmaz.

## Ortak davranış

- Başarılı sonuç: ne oldu, uzak kimlik, çıktı konumu ve gerekiyorsa sonraki adım.
- Hata: ne başarısız, ne korunmuş, düzeltilecek girdi veya güvenli toparlanma.
- Belirsizlik: işlemin oluşmuş olabileceği ve uzlaştırma yolu; otomatik yeniden başlatma önerisi değil.
- Desteklenmeyen kombinasyon: hangi yetenek eksik ve hangi açık seçenekler var.

Araç seçimi kullanıcıyı etkiler; plan özetinde araç/sürüm, ortam ve dönüştürülemeyen ayarlar gösterilir. Varsayılan ForgeLM kullanıldığında her görevde tekrar seçim sorulmaz. Kullanıcının açık seçimi kurulum/uyum sorunu nedeniyle sessizce değiştirilemez.

## Etkileşimli ve otomasyon kullanımı

TTY varsa rehberli adımlar ve ilerleme görünümü sunulabilir. Pipe/CI yolunda asılı kalan prompt, renk zorunluluğu veya gizli varsayılan onay olmaz. `--output` biçimi açık seçilir; sadece non-TTY olmak JSON'a geçme nedeni değildir. Onay bekleyen etkileşimsiz iş açık sonuç/kodla biter.

Klavye ile tüm adımlar tamamlanır. Bilgi yalnız renkle aktarılmaz; dar terminal ve ekran okuyucuya uygun düz metin modu vardır. Büyük yanıtlar özetlenir ve dosyaya yazma seçeneği sunulur; hata veya riskli satır sessizce kırpılmaz.

Her ana kullanıcı yolculuğunda süre, yardım müdahalesi, yanlış seçim ve sonuca ulaşma ölçülür. Tüm çıktıyı güzelleştirmek için eklenen pahalı render işlemi, temel komutun gecikme bütçesini aşmamalıdır.
