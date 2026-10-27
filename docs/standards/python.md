# Python geliştirme standardı

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

## Kod ve kaynak yönetimi

Kamuya açık işlev/portlar tipli olmalı; sınırda sıkı şema doğrulaması yapılmalı. Alan modellerinde belirsiz `Any` kullanımını daraltın. Kod, yorum, API kimliği ve makine hata kodları İngilizcedir; insan mesajları yerelleştirme katmanından gelir.

HTTP istemcisi, veritabanı, dosya ve alt süreç yaşam döngüsü açıkça kapatılır. Async işlerin sahibi, iptal ve deadline bütçesi bellidir. Durdurma başarısı yalnız yerel task iptaliyle ilan edilmez; uzak işin durumu ayrıca ele alınır. Zaman farkı hesabı monotonic clock, kayıt zamanları UTC kullanır.

## Bağımlılık ve import

Torch, transformers, TRL ve muadil eğitim paketleri temel import ağacına girmez. Yardım/sürüm/local config komutu ağ, keychain veya model yüklemez. Opsiyonel araç eksikliğinde açıklayıcı hata/kurulum yönlendirmesi verilir; import hatası sessizce `None` yapılmaz.

Sürüm aralıkları uyumluluk deneyiyle belirlenir, build/test ortamı tekrar üretilebilir kaydedilir. Paket API'si ve adaptör bağımlılığı ayrı sürümlenebilir. [Teknoloji](../tech-stack.md).

## Dosya ve config

JSON'da NaN/Infinity, yinelenen anahtar ve bilinmeyen şema sürümü reddedilir. Boyut, hash, yol, sayfa ve sayısal maliyet alanları beklenen tür/sonluluk/işaret kurallarıyla doğrulanır; imzalı ledger tutarı ile negatif olamayan tahmin aynı kural değildir. Config davranışı açık profil/reçeteden gelir; env yalnız sır referanslarında kullanılır.

Format/lint/type araçları ilk dilimde `pyproject.toml`, `uv.lock` ve CI tanımına bağlandı; yerelde ve PR #1 Ubuntu/CPython 3.11.15 koşusunda çalıştırıldı. Komutlar [katkı rehberinde](../../CONTRIBUTING.md), gerçek sonuç [canlı kayıttadır](../research/branch-workflow-validation.md). Bu kanıt yalnız koşulan sürüm ve ortamı kapsar; sonraki PR'lar zorunlu CI ile ayrıca doğrulanır.
