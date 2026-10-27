# Mimari standardı

**Durum:** Benimsenmiş. **Tarih:** 2026-10-27.

Domain modelleri hizmet SDK'sı, CLI, SQLite veya eğitim paketi bilmez. Kullanım senaryoları portlara bağımlıdır; somut adaptörler dış katmanda bu portları uygular. CLI ve gelecekteki MCP aynı kullanım senaryosunu çağırır. [Mimari görünüm](../architecture/overview.md).

## Ayrı tutulacak eksenler

- Görev: kullanıcının istediği sonuç.
- Araç sağlayıcısı: görevi bir haricî araçla nasıl yapacağımız.
- Çalıştırma ortamı: işin nerede ve hangi kaynakla yürüdüğü.
- EVREN hizmeti: Platform API/gateway gibi uzak servis sınırı.

Bir default araç bütün görevleri sahiplenmez. Bir execution backend'i de bütün araçları çalıştırabiliyor sayılmaz. Çözümleme, tüm birleşimin yeteneğini plan öncesinde denetler.

## Modül sınırı

Her modül kendi veri/durumunu yazar, diğerine açık port veya kayıtlı olay/sonuçla başvurur. Başka modülün tablosuna, özel SDK tipine veya gizli yardımcı fonksiyonuna doğrudan bağımlılık kurulmaz. Genel sözleşmeye servis ham cevabı `dict` olarak sızdırılmaz; ham alanlar açık `provider_data` bağlamında sınırlandırılabilir.

## Yeni adaptör kabulü

Yeni adaptör sürüm/görev matrisi, parametre eşleme/kayıp raporu, dosya/ağ/alt süreç yetkileri, deadline/iptal davranışı, çıktı doğrulaması ve ortak sözleşme testleriyle eklenir. “Kurulu” ile “uyumlu” ayrı durumdur. Geçersiz adaptör, ana CLI'nin `--help` işlemini bozmaz.

İlk uygulama monolitik Python paketi olarak modüler kalır. Ayrı servis veya genel plugin yükleyici eklemek, kullanıcı ihtiyacı ve ölçülmüş darboğaz gerektirir.
