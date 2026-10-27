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

Örnekteki kimlikleri yeni işe göre değiştir; var olan ID'yi ikinci karta verme. `size` S/M/L planlama sınıfıdır, süre taahhüdü değildir. `ready` yalnız doğrulanmış doğrudan bağımlılıkla kullanılabilir.

Kart gövdesinde gereken bilgi:

- **Kullanıcı sonucu ve bağlam:** Kim, hangi sonucu neden istiyor; mevcut kodun somut eksikliği ne?
- **Giren/girmeyen kapsam:** Bir PR'da tamamlanacak sınır; görev/araç/hizmet/ortam ve özellikle ertelenenler.
- **Bağımlılık/karar:** Bağlı işlerin PR/commit/kanıtı; açık ADR veya dış erişim. Eksik karar varsa önce o karar çıktısını ayır.
- **Değişen sözleşme ve yerler:** Mevcut domain/application/adaptör/yüzey, canonical referans ve kullanıcı belgesi. Dosya adı önerisi uygulanmış sınıf iddiası değildir.
- **Kabul:** Gözlenebilir olumlu sonuç, tehlikeli hata yolu, kaynak/UX bütçesi ve kanıt. “Test yaz” veya “hızlı olsun” kabul değildir.
- **Doğrulama:** [Değişiklik matrisinden](../../CONTRIBUTING.md#doğrulama-seçimi) seçilen gerçek kontroller; canlı pilot gerekiyorsa kapsam/yan etki/maliyet ve mevcut yetki.
- **Teslim kaydı:** Gerçekleşince PR/commit, sonuç ve kalan sınır. Teslimden önce bu alanın boş olduğunu açıkça yaz; sahte geçmiş kanıt ekleme.

Uygulamada yeni belirsizlik çıkarsa kapsam/bağımlılık güncellenir veya paket bölünür; kabul sessizce düşürülmez. `verified` bütün kart kabulünün kanıtını gerektirir; kapsamın geri kalanı ve yayın ayrıca değerlendirilir.
