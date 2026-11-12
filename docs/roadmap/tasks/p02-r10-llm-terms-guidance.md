---
id: P02-R10
phase: P02
status: ready
size: S
depends_on: [P02-0c]
capabilities: [C01, C02]
---
# P02-R10 — LLM şart durumunda tek sonraki adım

**Tarih:** 2026-11-08. **Sahip:** P02 / context discovery. [Şema yeniden okuması ve dış inceleme doğrulamasından](../../research/p02-llm-gateway-schema-review.md) çıkan küçük kullanıcı deneyimi boşluğudur; ürün sözleşmesini genişletmez ve yeni karar gerektirmez.

## Kullanıcı sonucu ve mevcut eksik

`yorunge context discover --service evren-llm`, şartlar kabul edilmemişse text çıktısında yalnız "Sunucunun şart durumu: kabul edilmemiş (sürüm N)" der (`discovery_text_result`, [cli/__init__.py](../../../src/yorunge/cli/__init__.py)). Kullanıcıya bunun ne anlama geldiğini ve Yörünge'nin şart kabul etmediğini söylemez. [Kullanıcı yolculuğu 1](../../user-journeys.md) sonucun "düzeltilecek tek sonraki adımı" göstermesini ister. JSON/NDJSON'da `terms_not_accepted` nedeni zaten vardır; eksik olan insan okuyan metindir.

## Giren ve girmeyen kapsam

Girer: `terms.accepted=false` iken **text** çıktısına tek satırlık sabit, **gözlem** biçiminde yönlendirme. Önerilen metin: "Sunucu şartları kabul edilmemiş bildiriyor. Yörünge şart kabul etmez; karar kendi EVREN hesabınızda size aittir." (kesin metin review'de kapanır). Satır bir zorunluluk veya erişim sonucu iddia etmez. `accepted=true` iken satır yoktur. [Context discovery referansı](../../reference/context-discovery.md) ve text çıktı testi güncellenir.

Girmez: JSON/NDJSON alanı veya neden kümesi değişikliği; `doc_path`/URL gösterme ya da takip; şart metnini gösterme ([B17](../backlog.md) kararıdır); şart kabulü; yönlendirmeye komut, URL veya sürüm-kabul örneği ekleme; diğer hizmet çıktıları.

## Bağımlılıklar ve kararlar

P02-0c verified ve PR #12 ile development'a teslim edildi. Yeni karar gerekmez: davranış [AGENTS.md](../../../AGENTS.md) ("hesap şartlarını kullanıcı adına kabul etme") ve [ADR-0020](../../decisions/0020-service-bound-context-discovery.md) (`accepted=false` otomatik şart kabulü üretmez; `doc_path` ve URL takip edilmez) ile uyumludur. Kabulün hangi yoldan yapılacağı (portal, API) doğrulanmış kaynak olmadan yazılmaz. **Zorunluluk iddiası kurulmaz:** şema `accepted` alanını "anahtar sahibi güncel *material* sürümü kabul etti mi" diye tanımlar; `is_material` Yörünge'de çözülür ama hiçbir yerde kullanılmaz ve metin üretimine de girmez. `accepted=false` iken `is_material=false` ise "şart kabulü gerekir" cümlesi yanlış olabilir; ayrıca kabul edilmemiş bir anahtarın hangi uçlara erişebildiği canlı doğrulanmadı ([araştırma kaydı](../../research/p02-llm-gateway-schema-review.md#kararlar)). Bu yüzden satır yalnız sunucunun bildirdiğini ve Yörünge'nin kabul etmediğini söyler; zorunluluk, erişim kaybı veya sonraki komutların başarısızlığı iddiası, canlı doğrulama ve karar olmadan eklenmez.

## Sözleşme ve uygulama sınırı

Yalnız text biçimlendirici ve belge değişir. Domain modeli, Result/ContextDiscovery şeması, hata kodu, exit kodu ve JSON/NDJSON çıktısı değişmez. Text insan çıktısıdır; otomasyon JSON/NDJSON ve exit kodunu kullanır.

## Kabul

1. `accepted=false` text çıktısı tek yönlendirme satırı içerir; satır sır, host, URL, `doc_path` veya çalıştırılabilir komut içermez. Mevcut "kimlik doğrulaması: doğrulanmadı" ve "yürütme izni vermez" satırları korunur.
2. `accepted=true` text çıktısı değişmez. İki durumda da JSON ve NDJSON çıktıları önceki golden'larla aynıdır.
3. Gerçek CLI girişi ve ortak API sonucuyla iki durum sınanır; negatif: yönlendirme metni `--yes`, `terms accept` ve `http(s)://` içermez, Yörünge'nin kabul ettiğini ima etmez.
4. `is_material` değerine bağlı dallanma yoktur: `accepted=false` için `is_material` true ve false iken metin aynıdır (test). Metin "gerekir", "zorunlu", "erişemezsiniz" gibi zorunluluk veya erişim iddiası taşımaz (negatif test).
5. En az bir fresh review; güvenlik sınırı (kabul/komut/URL yok) ve gözlem dili (zorunluluk iddiası yok) review'in açık maddesidir.

## Doğrulama

[Doğrulama matrisinde](../../../CONTRIBUTING.md#doğrulama-seçimi) runtime/CLI satırı: ilgili unit/CLI testleri, Ruff format/lint, strict mypy ve `check-docs.py`. Canlı EVREN çağrısı gerekmez.

## Teslim kaydı

Ready; uygulama veya kabul kaydı yoktur.
