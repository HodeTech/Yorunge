# Proje yapısı

**Güncellendi:** 2026-10-27. **Durum:** Bugün belge temeli; kaynak yerleşimi tasarım.

## Mevcut dosyalar

Root'ta README, MIT lisansı, katkı/güvenlik/topluluk belgeleri, changelog, ajan rehberi ve küçük editör/Git kuralları bulunur. `docs` altında ürün belgeleri ile `standards`, `architecture`, `decisions`, `modules`, `reference`, `roadmap`, `research` dizinleri yer alır. Her alt dizinin README'si o bölümün giriş noktasıdır.

## P01'de eklenecek kaynak yerleşimi

Aşağıdaki yollar **öneridir; bugün bu dizinler veya uygulama dosyaları yoktur**:

```text
src/yorunge/
  domain/                 # Kimlikler, görev/plan/durum, hata ve yetenek modelleri
  application/            # Kullanım senaryoları; ports; çözümleme ve koordinasyon
  modules/                # Alan kullanım senaryoları; domain/application kurallarına uyar
  adapters/
    evren_platform/       # Platform hizmeti
    evren_llm/            # LLM/çıkarım hizmeti veya SDK sarmalayıcısı
    tools/                # ForgeLM ve muadil araçlar
    execution/            # Yerel / yönetilen / koşullu runtime
    storage/              # SQLite, dosya, sır ve önbellek
  cli/                    # Komut çözümleme, insan/JSON çıktısı, rehberli akış
tests/
  unit/
  contracts/
  integration/
  performance/
```

Bu görünüm fiziksel yerleşim adayını anlatır; [modül haritası](modules/README.md) alan sahipliğini, [mimari](architecture/overview.md) bağımlılık yönünü tanımlar. Domain çekirdek adaptör veya CLI import etmez. Bir modül başka modülün durum tablosuna doğrudan yazmaz. Somut arayüzler [referans sözleşmelerinde](reference/README.md) tek yerde tutulur.

`data`, `models`, `artifacts`, `.yorunge` ve çalışma veritabanları kullanıcı çalışma alanıdır; kaynak depoya eklenmez. Reprodüksiyon fixture'ları yalnız küçük ve sentetik örnekler içermeli. Ham özel veri ve araştırma çalışma notları üretim sözleşmesine bağımlılık olamaz.
