# Teknoloji yaklaşımı

**Güncellendi:** 2026-10-27. **Durum:** Temel tercihler benimsendi; paketler/sürümler henüz kurulmadı.

| Katman | Başlangıç tercihi | Gerekçe / durum |
|---|---|---|
| Dil | Python 3.11+ | EVREN ve eğitim ekosistemiyle uyum; `tomllib`, task/deadline araçları. Asgari hedef; test edilmiş platform iddiası değil. |
| Paket yapısı | Tek dağıtım, `src/yorunge` | Ayrı servisler olmadan modül sınırı; P01'de kurulacak. |
| Kullanıcı yüzeyi | CLI + Python API | Hızlı ve otomasyona uygun başlangıç; rehberli katman aynı çekirdeği kullanır. |
| CLI görünümü | Typer/Click ve Rich değerlendirilecek | Kesin paket seçimi startup/çıktı/erişilebilirlik spike'ına bağlı. |
| HTTP | Ortak taşıma politikası; HTTPX veya uygun SDK adaptörü | Bağlantı havuzu, stream ve açık deadline; paket seçimi P01 sözleşme deneyiyle kesinleşir. |
| Şema doğrulama | Sıkı tipli modeller; Pydantic v2 aday | Dış yanıt ve yerel config için açık, sürümlü sözleşme. |
| Profil | TOML | Python standart kütüphanesiyle okunur, sır referanslarını açık tutar. |
| İş reçetesi | Doğrulanan YAML | İnsan/CI için paylaşılabilir görev tanımı; parser ve boyut/alias sınırı P01'de kesinleşir. |
| Durum | SQLite | Yerel işlemsel kayıt; ayrı sunucu gerekmez. Eşzamanlı yazma/migration/lease tasarlanır. |
| Sırlar | Env referansı; isteğe bağlı işletim sistemi keychain | Düz metin credential'ı profile veya duruma yazmaz. Keychain opsiyoneldir. |
| Eğitim | Ayrı ortamda araç adaptörleri | ForgeLM varsayılan; muadiller seçilebilir; torch/TRL çekirdek bağımlılığı olmaz. |
| Test/lint | pytest, Ruff, mypy aday | Komutlar ve kesin sürümler gerçek P01 paket/CI tanımında sabitlenecek. |

Python ve SQLite gerekçeleri [resmî Python belgelerine](https://docs.python.org/3.11/library/sqlite3.html) ve [asyncio sözleşmesine](https://docs.python.org/3.11/library/asyncio-task.html) dayanır. Belirli parser/CLI sürümü veya bütün işletim sistemlerinde uyum bu belgede varsayılmamıştır.

## Bağımlılık kuralları

Temel istemci GPU, notebook sunucusu veya eğitim kütüphanesi istemez. İsteğe bağlı entegrasyonlar ayrı extra/ortamla dağıtılır. Kullanıcının başka araç için kurduğu ortamı Yörünge otomatik güncellemez. SDK kullanıldığında sır/hedef/retry/timeout sözleşmesi uçtan uca korunmalı; SDK ve çekirdek aynı isteği ayrı katmanlarda kontrolsüz tekrar etmemelidir.

İlk paket kurulumu minimum/supported sürüm ve ortam kilidiyle tekrar üretilebilir olmalıdır. Bu depoda şu an `pyproject.toml`, lock veya çalışma zamanı bağımlılığı bulunmaz; bu belge onların yerine geçmez. [ADR-0003](decisions/0003-lightweight-python-core.md).
