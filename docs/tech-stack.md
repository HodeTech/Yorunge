# Teknoloji yaklaşımı

**Güncellendi:** 2026-10-29. **Durum:** P01-1–4 development'a teslim edildi; ADR-0017/0018 Accepted. P01-5a/b ve P01-6b çalışma dalında verified; gerçek üçlü CI/kurulum/kaynak kabulü [kapanıştadır](research/p01-remaining-implementation-validation.md#faz-kapanışı-ve-gerçek-ci). Development PR review/merge ve yayın ayrı kalır. [İlk offline seçim](decisions/0008-offline-core-stack.md) ve [önceki development teslimi](research/p01-4-implementation-validation.md#development-merge-kapanışı) korunur.

| Katman | Başlangıç tercihi | Gerekçe / durum |
|---|---|---|
| Dil | Python 3.11+ | `tomllib`, task/deadline araçları. Linux3.11/3.14 ve macOS3.11 gerçek CI ile testli; minimum hedef bütün platform/Python sürümlerinin doğrulandığı anlamına gelmez. |
| Paket yapısı | Tek dağıtım, `src/yorunge`, Hatchling 1.30.1 | Wheel/sdist ve gerçek konsol girişi kuruldu. |
| Kullanıcı yüzeyi | CLI + Python API | Hızlı ve otomasyona uygun başlangıç; rehberli katman aynı çekirdeği kullanır. |
| CLI görünümü | Standart `argparse`, düz metin/JSON/NDJSON | Ortak UTF-8 renderer ve yerel iptal/çıktı hata sözleşmesi testli; help/version lazy kalır. Rich eklenmedi. |
| HTTP | HTTPX0.28.1 AsyncClient/HTTP1.1 | Tipli owned session/tek deadline/bounded retry gerçek yerel TLS ile testli; EVREN adaptörü değildir. SDK core bağımlılığı yok, public yerel komutlar HTTP import etmez. |
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
