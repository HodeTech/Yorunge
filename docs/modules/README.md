# Modül haritası

**Durum:** Bütün modüller planlanıyor; uygulama yok. **Tarih:** 2026-10-27.

| Modül | Sahip olduğu alan | Yetenekler |
|---|---|---|
| [Kimlik ve bağlam](identity-context.md) | Profil, secret ref, hesap/proje seçimi | C01 |
| [Yetenekler](capabilities.md) | Destek ve kanıt çözümleme/cache | C02 |
| [Veri setleri](datasets.md) | Dosya/manifest/aktarım/sürüm | C03/C04 |
| [Katalog ve modeller](catalog-models.md) | Kaynak arama ve model sürümü | C05 |
| [LLM ve çıkarım](llm-inference.md) | Metin/akış, embedding/rerank, görsel ve ileri servisler | C06/C07/C15 |
| [Eğitim ve değerlendirme](training-evaluation.md) | Yönetilen eğitim, araçlı LLM görevleri, metrik | C08/C09/C10 |
| [Kaynak ve tüketim](compute.md) | GPU/kuyruk/rezervasyon/kota/maliyet | C11/C16 |
| [İş akışları](workflows.md) | Plan, onay, operation/attempt ve uzlaştırma | C12/C13 |
| [Artefaktlar](artifacts.md) | Çıktı teslimi, hash, köken ve saklama | C12/C17 araştırma |
| [Araç entegrasyonları](tool-integrations.md) | ForgeLM ve muadil sağlayıcı adaptörleri | C09/C10/C14 bağlantıları |

Modüller alan sahipliğidir; hepsi ayrı paket/servis olmak zorunda değildir. Başka modülün tablosuna veya özel yardımcısına doğrudan erişim yoktur. İş akışı farklı modül sonuçlarını açık portlarla bağlar. Somut kaynak yerleşimi P01'de [proje yapısına](../project-structure.md) göre kurulur.
