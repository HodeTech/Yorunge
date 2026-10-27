# İş kartı şablonu

**Durum:** Şablon; gerçek görev veya kabul kanıtı değildir. **Tarih:** 2026-10-27.

Anlamlı yeni uygulama dilimi için `tasks/<id>-<english-slug>.md` oluştur. Dosya aşağıdaki YAML metadata ile başlar; ardından tek H1 gelir. Aynı kabulü faz/current'a kopyalama. Başlamak için [ready tanımını](README.md#hazır-iş-paketi) uygula; küçük yazım düzeltmesine kart zorunlu değildir.

```yaml
---
id: P01-2a
phase: P01
status: draft
size: S
depends_on: [P01-1]
capabilities: [C01]
---
```

Örnekteki kimlikleri yeni işe göre değiştir; var olan ID'yi ikinci karta verme. `size` S/M/L planlama sınıfıdır, süre taahhüdü değildir. `ready`, `in_progress`, `in_review` ve `verified` doğrulanmış doğrudan bağımlılık gerektirir. Aşağıdaki yedi ad kartın gerçek `##` bölüm başlıklarıdır; ready ve sonraki durumlarda içerikleri boş bırakılamaz.

Kart gövdesinde gereken bilgi:

- **Kullanıcı sonucu ve mevcut eksik:** Kim, hangi sonucu neden istiyor; mevcut kodun somut eksikliği ne?
- **Giren ve girmeyen kapsam:** Bir PR'da tamamlanacak sınır; görev/araç/hizmet/ortam ve özellikle ertelenenler.
- **Bağımlılıklar ve kararlar:** Bağlı işlerin PR/commit/kanıtı; açık ADR veya dış erişim. Eksik karar varsa önce o karar çıktısını ayır.
- **Sözleşme ve uygulama sınırı:** Mevcut domain/application/adaptör/yüzey, canonical referans ve kullanıcı belgesi. Dosya adı önerisi uygulanmış sınıf iddiası değildir.
- **Kabul:** Gözlenebilir olumlu sonuç, tehlikeli hata yolu, kaynak/UX bütçesi ve kanıt. “Test yaz” veya “hızlı olsun” kabul değildir.
- **Doğrulama:** [Değişiklik matrisinden](../../CONTRIBUTING.md#doğrulama-seçimi) seçilen gerçek kontroller; canlı pilot gerekiyorsa kapsam/yan etki/maliyet ve mevcut yetki.
- **Teslim kaydı:** Gerçekleşince PR/commit, sonuç ve kalan sınır. Teslimden önce bu alanın boş olduğunu açıkça yaz; sahte geçmiş kanıt ekleme.

`verified` teslim kaydında şu etiketler bulunur: `- PR/commit:` gerçek depo PR/commit bağlantısı, `- Sonuç:` kabulü karşılayan kontrol/ölçüm ve kanıt bağlantıları, `- Kalan sınır:` bu kabul dışındaki sınır veya açıkça yok bilgisi. Şablon yer tutucuları gerçek kanıt değildir. Helper bölüm/alan varlığını kontrol eder; kanıtın kabulü gerçekten karşılayıp karşılamadığı review'de değerlendirilir.

Uygulamada yeni belirsizlik çıkarsa kapsam/bağımlılık güncellenir veya paket bölünür; kabul sessizce düşürülmez. `verified` bütün kart kabulünün kanıtını gerektirir; kapsamın geri kalanı ve yayın ayrıca değerlendirilir.
