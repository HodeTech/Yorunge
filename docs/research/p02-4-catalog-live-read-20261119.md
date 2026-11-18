# P02-4 katalog canlı salt okuma kaydı (2026-11-19)

**Durum:** Kanıt kaydı (K4). **Kapsam:** yalnız salt okuma GET; yazma, indirme, ücretli çağrı ve veri değişikliği yok. **Hesap:** yerel pilot profili; kimlik, ad, adres ve anahtar değerleri bu kayda girmez. **Kaynak:** [ADR-0035](../decisions/0035-catalog-reads-fixed-references-and-selection.md) K4, [katalog başvurusu](../reference/catalog.md). Ham yanıt gövdeleri ve kimlikler bu depoda tutulmaz.

## Yöntem ve bütçe

İki çalıştırma, toplam **12 mantıksal GET** (bütçe 20). Her çalıştırma ürünün kendi katalog API'sini (`yorunge.api`, gerçek TLS ve gerçek DNS) kullandı; anahtarlar yerel kimlik dosyasından yalnız süreç ortamına okundu. Betik çıktısı yalnız sayı, kategori ve kapalı hata kodlarıdır.

| Çağrı | Uç | Sorgu | Sonuç |
|---|---|---|---|
| Platform modelleri | `models` | `page=1`, `page_size=20` | tamam; toplam 0 |
| Platform modelleri | `models` | `page=1`, `page_size=100` | **kabul edildi** (422 yok) |
| Veri setleri (owned) | `datasets` | `page=1`, `page_size=20`, `scope=owned` | tamam; 6 satır |
| Veri setleri (filtresiz) | `datasets` | `page=1`, `page_size=20` | tamam; 6 satır |
| LLM listesi | `models` | — | tamam; 15 model |
| LLM modeli | `models/{id}` | — | tamam; görev `ocr` |

Platform modeli ayrıntısı, sürüm listesi ve sürüm indirmesi bu hesapta **test edilemedi**: hesapta platform modeli yok (toplam 0). Sürüm kimliğiyle indirme için kullanıcı tarafından bir sürüm kimliği ve ek yetki verilmedi (K5); o kabul "yapılmadı" olarak kalır.

## Gözlemler

- **Veri seti sayfa başlıkları.** `X-Has-Next` değeri `0` veya `1` (tamsayı) olarak geliyor; `true`/`false` değil. `X-Total-Count` ondalık sayı (`6`). İlk çalıştırmada katalog kodu `true`/`false` beklediği için tamlığı doğru olarak `unknown` yaptı; bu bir teyit uyuşmazlığıydı ve kod `0`/`1` olarak düzeltildi (ilgili commit ve testler). Düzeltmeden sonra tamlık `complete`.
- **Kapsam filtresi.** `scope=owned` ile ve filtresiz ilk sayfa aynı sayıda (6) satır döndü. Bu hesapta filtrenin etkisi **gözlenmedi**; etiket `unknown` kalır, "sahip olunan" iddiası kurulmaz.
- **Sayfa üst sınırı.** `page_size=100` kabul edildi. 100'ü aşan değer bu kayıtta denenmedi; ürün 100 ile sınırlıdır.
- **LLM kimlik alfabesi.** 15 kimliğin 15'i `[A-Za-z0-9._-]` alfabesinde; `/` içeren yok.
- **LLM görev değerleri.** Gözlenen görevler: `chat`, `ocr`, `vision_chat`, `embedding`, `rerank`, `audio_transcription`, `guard`, `tts`, `decision`. Başvurudaki liste `decision` ve `guard` içermiyordu; görev alanı açık dize olarak kaldığı için bu bir hata değil, belgeye eklendi.
- **LLM fiyat ve bağlam.** 15 modelin tamamında `pricing` ve `context_length` dolu; `free_until` her modelde dolu (değerler kayıtta yok; maliyet kapısı değildir).
- **LLM ayrıntısı.** Bir modelde `modalities` iki değer, `precision` boş.
- **Hata kodu.** Bu iki çalıştırmada hiçbir uç 4xx/5xx dönmedi.

## Ne kanıtlanmadı

- Platform model listesi, sürüm listesi (`model_id` yolu) ve sürüm çözümü: hesapta model yok, bu yüzden kanıt üretilemedi.
- Platform sayfasında 100'ün üstü, `page` üst sınırı ve büyük `model_card` alanıyla 1 MiB sınırı.
- Kapsam filtresinin etkisi (bu hesapta ayırt edilemedi).
- Kullanıcı yetkisi, erişim kapsamı ve "bu anahtara görünen" kümenin tamlığı: LLM listesi tamlığı `unknown` olarak kalır.

## Sonuç

K4 okuması, katalog sözleşmesinin Platform veri setleri ve LLM listesi bölümlerini gerçek hizmete karşı doğruladı ve bir biçim uyuşmazlığını (`X-Has-Next`) yakaladı. Platform model okuması ve K5 indirmesi için bu hesapta veri yok; bu kabul açık bırakıldı.
