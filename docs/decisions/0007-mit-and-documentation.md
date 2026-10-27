# ADR-0007: MIT lisansı ve kanonik belge yapısı

**Durum:** Accepted. **Tarih:** 2026-10-27.

## Bağlam

Kullanıcı MIT lisansını istedi ve HodeTech projelerindeki standart/mimari/karar/modül/yol haritası düzenini referans gösterdi. Bu projelerin ürün/teknoloji ve dil politikalarını olduğu gibi kopyalamak Yörünge'nin ihtiyaçlarını karşılamaz.

## Karar

Yörünge [MIT](../../LICENSE) altında geliştirilir. Ana açıklama dili Türkçe, teknik dosya ve kimlik adları İngilizcedir. Her belge türünün tek kanonik yeri ve alt dizin indeksleri vardır. Planlanmış, uygulanmış ve yayımlanmış yetenekler ayrı yazılır.

## Alternatifler

Tek büyük README ayrıntı bulmayı ve bakımı zorlaştırır. Aynı sözleşmeyi root, mimari ve kılavuzda çoğaltmak drift yaratır. İlk aşamada bütün belgeleri iki dilde tutmak kullanıcı talimatıyla gerekmeyen bakım yüküdür; ihtiyaç olursa kanonik metne bağlı çeviri eklenebilir.

## Sonuçlar

MIT seçimi bağımlılık/ödünç kod lisanslarını değiştirmez. Dil, belge durumu ve bağlantı denetimleri inceleme kapsamıdır. Referans projelerden alınan yapısal ilkeler [araştırma kaydında](../research/evidence-register.md) belirtilir; o projelerin canlı CI veya dal kuralları devralınmaz.
