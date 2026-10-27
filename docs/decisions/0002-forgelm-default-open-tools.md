# ADR-0002: ForgeLM varsayılanı ve seçilebilir muadiller

**Durum:** Accepted. **Tarih:** 2026-10-27. **Dayanak:** Kullanıcının varsayılan/seçim gereksinimi.

## Bağlam

ForgeLM ilgili LLM görevlerinde güçlü bir başlangıç sağlıyor. Kullanıcı mevcut başka bir eğitim/veri/değerlendirme aracını kullanmak isteyebilir. Tek araca göre CLI ve çalışma modeli kurmak bu seçimi sonradan pahalılaştırır.

## Karar

Uygun LLM görevlerinin ürün varsayılanı ForgeLM'dir. Kullanıcı görev bazında doğrulanmış alternatif araç seçebilir. TaskProvider ile ExecutionBackend farklı portlardır. Varsayılan seçim ağır otomatik kurulum veya sessiz fallback yaratmaz. P03 kabulü ForgeLM + aynı sınıfta en az bir muadil sözleşme deneyini içerir.

## Alternatifler

ForgeLM'i zorunlu çekirdek bağımlılığı yapmak veri/çıkarım kullanıcılarını gereksiz yükler. Araçlara özel üst seviye komut ağaçları kullanıcı işini araç adına bağlar. Her aracın parametresini tek dar şemaya sıkıştırmak işlev kaybı yaratır; bunun yerine ortak görev ve adlandırılmış sağlayıcı seçenekleri kullanılır.

## Sonuçlar

Araç/sürüm, çevrilen ve desteklenmeyen ayarlar planda görünür. Yeni adaptör ortak kabul testinden geçer. Muadillerin ForgeLM ile bütün görevlerde eşit olduğu iddia edilmez. [Sağlayıcı modeli](../architecture/tool-providers.md), [araç sözleşmesi](../reference/tool-provider-contract.md).
