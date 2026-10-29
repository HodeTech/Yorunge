# Teknoloji yaklaşımı

**Güncellendi:** 2026-10-29. **Durum:** P01-1–4 çekirdeği development'a teslim edildi; HTTP/SDK kararı ADR-0017 Accepted; P01-5 taşıma uygulaması/review sürüyor. İlk offline seçim [ADR-0008](decisions/0008-offline-core-stack.md), güncel teslim [P01-4 kapanışındadır](research/p01-4-implementation-validation.md#development-merge-kapanışı).

| Katman | Başlangıç tercihi | Gerekçe / durum |
|---|---|---|
| Dil | Python 3.11+ | EVREN ve eğitim ekosistemiyle uyum; `tomllib`, task/deadline araçları. Asgari hedef; test edilmiş platform iddiası değil. |
| Paket yapısı | Tek dağıtım, `src/yorunge`, Hatchling 1.30.1 | Wheel/sdist ve gerçek konsol girişi kuruldu. |
| Kullanıcı yüzeyi | CLI + Python API | Hızlı ve otomasyona uygun başlangıç; rehberli katman aynı çekirdeği kullanır. |
| CLI görünümü | Standart `argparse`, düz metin/JSON | Küçük komut ağacı için yeterli; Click/Typer import deneyinde daha yüksek başlangıç maliyeti. Rich eklenmedi. |
| HTTP | HTTPX0.28.1 AsyncClient/HTTP1.1 | ADR-0017 Accepted; tipli owned session/tek deadline/retry geliştiriliyor. SDK core bağımlılığı yok, public yerel komutlar HTTP import etmez. |
| Şema doğrulama | Pydantic 2.14.1 | Strict tip, unknown alan reddi ve ortak tipli API; yalnız yerel şemalar doğrulandı. |
| Profil | TOML | Python standart kütüphanesiyle okunur, sır referanslarını açık tutar. |
| İş reçetesi | PyYAML 6.0.3 SafeLoader + dar şema | Duplicate/alias/anchor/unknown tag reddi, boyut/derinlik/düğüm sınırı. |
| Durum | SQLite, şema 6 | Store/migration, identity/cache/plan/onay ve operation/lease/sonuç/reset uygulandı; explicit state kullanımında açılır. |
| Sırlar | Hizmete bağlı açık env çözümleme | Gereken hizmet sırrı açık kullanımda bir kez çözülür; kalıcı opak kimlik/nesil vardır, ham sır DB/çıktıya yazılmaz. Keychain uygulanmadı. |
| Eğitim | Ayrı ortamda araç adaptörleri | ForgeLM varsayılan; muadiller seçilebilir; torch/TRL çekirdek bağımlılığı olmaz. |
| Test/lint | pytest 9.1.1, Ruff 0.15.22, mypy 1.20.2 | `uv.lock` ile sabit; gerçek offline testler ve CI tanımı. |

Python ve SQLite gerekçeleri [resmî Python belgelerine](https://docs.python.org/3.11/library/sqlite3.html) ve [asyncio sözleşmesine](https://docs.python.org/3.11/library/asyncio-task.html) dayanır. Belirli parser/CLI sürümü veya bütün işletim sistemlerinde uyum bu belgede varsayılmamıştır.

## Bağımlılık kuralları

Temel istemci GPU, notebook sunucusu veya eğitim kütüphanesi istemez. İsteğe bağlı entegrasyonlar ayrı extra/ortamla dağıtılır. Kullanıcının başka araç için kurduğu ortamı Yörünge otomatik güncellemez. SDK kullanıldığında sır/hedef/retry/timeout sözleşmesi uçtan uca korunmalı; SDK ve çekirdek aynı isteği ayrı katmanlarda kontrolsüz tekrar etmemelidir.

`uv 0.11.2` ve `uv.lock` tekrar üretilebilir geliştirme kurulumunu sağlar. Runtime alt sınırları bu kilitteki doğrulanmış sürümlerdir; üst aralık her gelecek sürümün test edildiği iddiası değildir. Yardım/sürüm Pydantic/YAML dahi import etmez. [Kurulum ve kontroller](../CONTRIBUTING.md), [ölçüm kanıtı](research/p01-core-validation.md), [ADR-0003](decisions/0003-lightweight-python-core.md).
