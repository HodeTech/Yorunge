# Yörünge

**EVREN platformunda veriden sonuca uzanan işleri kolaylaştıran kapsamlı yardımcı araç.**

Yörünge; hesap ve proje bağlamını, veri setlerini, modelleri, LLM ve çıkarım servislerini, eğitim işlerini, GPU/kota görünürlüğünü ve çalışma sonuçlarını tutarlı iş akışlarında bir araya getirmek için tasarlanıyor. Kullanıcı, bir işi tamamlamak için ayrı istemcilerin ayarlarını ve ilerleme kayıtlarını birleştirmek zorunda kalmamalı.

**Durum — 27 Ekim 2026:** İlk çevrimdışı CLI/Python dilimi çalışıyor (`0.1.0.dev0`, yayımlanmadı). Yerel context, sınırlı capability sorgusu ve araç seçimi sabitlenmiş plan taslağı üretilebilir. EVREN bağlantısı, eğitim, aktarım ve artefakt teslimi henüz uygulanmadı. P01 devam ediyor.

## Çalışan başlangıç

Python 3.11+ ve `uv 0.11.2` ile depo kökünde:

```sh
uv sync --frozen --python 3.11
.venv/bin/yorunge --help
.venv/bin/yorunge --version
.venv/bin/yorunge context show --config examples/profile.toml
.venv/bin/yorunge capabilities --task dataset.upload --output json
.venv/bin/yorunge train plan --config examples/profile.toml --recipe examples/training.yaml
.venv/bin/yorunge train plan --config examples/profile.toml --recipe examples/training.yaml --tool axolotl --output json
```

Bu komutlar ağ, anahtar, veritabanı ve eğitim ortamı gerektirmez. Örnek model/veri referansları sentetiktir; dosyalar okunmaz veya model indirilmez. Çıktı `draft`, `executable=false` ve açık engeller taşır. Başarı, **plan hazırlığının** tamamlandığını belirtir. Araç adaptörleri henüz yoktur; araç tercihi yürütme desteği anlamına gelmez.

Aynı kullanım senaryosu Python'dan:

```python
from pathlib import Path
from yorunge.api import load_plan, prepare_plan

result = prepare_plan(
    config=Path("examples/profile.toml"),
    recipe=Path("examples/training.yaml"),
    tool="axolotl",
)
print(result.data.selection.tool)
Path("offline-plan.json").write_text(result.data.model_dump_json(), encoding="utf-8")
saved = load_plan(Path("offline-plan.json"))
assert saved.data.digest == result.data.digest
```

`plan show --plan offline-plan.json` kayıtlı seçimi mevcut profilden yeniden çözmez. Digest bütünlük kontrolüdür; yürütme onayı değildir. Kurulum, kontrol ve build adımları [katkı rehberinde](CONTRIBUTING.md); kesin uygulama sınırı [CLI](docs/reference/cli-contract.md) ve [config](docs/reference/configuration.md) sözleşmelerindedir. Yerel doğrulama ve ölçümler: [P01 kabul kaydı](docs/research/p01-core-validation.md).

## Ürün yaklaşımı

- **EVREN odaklı kapsam:** Veri aktarımı, model keşfi, çıkarım, eğitim, kaynak görünürlüğü ve sonuç yönetimi aynı ürünün alanlarıdır.
- **Kolay başlangıç, doğrudan kullanım:** Rehberli akış ve kısa komutlar aynı çekirdeğe bağlanır; otomasyon için kararlı makine çıktısı tasarlanır.
- **Göreve göre araç seçimi:** İlgili LLM veri hazırlama, fine-tuning, değerlendirme ve dışa aktarma görevlerinde ForgeLM varsayılan tercih olur. Kullanıcı desteklenen muadil aracı seçebilir; seçim ve yetenek farkları görünür kalır.
- **Hafif kurulum:** Sadece EVREN veri/API işlemleri isteyen kullanıcı ağır eğitim bağımlılıkları kurmaz.
- **Ölçülen performans:** Akışlı dosya aktarımı, sınırlı eşzamanlılık, uygun önbellek ve kontrollü API kullanımı ilk tasarımın parçasıdır.
- **Güvenilir sonuç:** Kesinti, belirsiz uzak işlem, eksik çıktı ve maliyet tahmini açık durumlarla gösterilir.

## Planlanan yetenekler

| Alan | Kullanıcıya sağlayacağı fayda |
|---|---|
| Hesap, profil ve proje | Doğru hizmet, anahtar ve proje ile işe başlama |
| Veri setleri | Denetleme, yükleme, indirme, doğrulama, sürüm ve kesintiden devam |
| Model kataloğu ve çıkarım | Modele/göreve uygun servis keşfi, LLM, embedding, rerank ve görsel çıkarım akışları |
| Eğitim ve değerlendirme | Planlama, maliyet önizlemesi, başlatma, izleme, durdurma ve sonuç toplama |
| Kaynaklar ve kota | Yetkili erişimi, GPU kullanılabilirliğini, rezervasyon ve tüketimi doğru yorumlama |
| İş akışları ve araçlar | ForgeLM varsayılanı, alternatif sağlayıcılar, tekrarlanabilir reçete ve artefakt manifesti |

Tam kapsam ve aşamalar: [ürün kapsamı](docs/product-scope.md), [yetenek matrisi](docs/capability-matrix.md), [yol haritası](docs/roadmap/README.md).

EVREN'de GPU görünmesi veya rezervasyon yapılabilmesi, kullanıcıya genel Python/GPU çalışma ortamı verildiğini kanıtlamaz. EVREN üzerinde haricî eğitim aracı çalıştırma ve kullanıcı LLM'ini servis etme yetenekleri, erişim ve sözleşme doğrulamasına bağlıdır. [Entegrasyon sınırları](docs/architecture/integration-boundaries.md).

## Nereden başlamalı?

1. [Vizyon ve konumlandırma](docs/vision.md).
2. [Kapsam ve öncelikler](docs/product-scope.md).
3. [Kullanıcı yolculukları](docs/user-journeys.md).
4. [Mimari](docs/architecture/README.md) ve [modüller](docs/modules/README.md).
5. [Mevcut durum](docs/roadmap/current.md) ve [kararlar](docs/decisions/README.md).

Tüm belgeler: [dokümantasyon rehberi](docs/README.md). Katkı: [CONTRIBUTING.md](CONTRIBUTING.md). Ajan yönergeleri: [AGENTS.md](AGENTS.md).

Proje kayıtları: [değişiklik günlüğü](CHANGELOG.md), [güvenlik bildirimi](SECURITY.md), [topluluk ilkeleri](CODE_OF_CONDUCT.md), [Claude giriş rehberi](CLAUDE.md).

## Lisans ve proje ilişkisi

[MIT License](LICENSE). Yörünge, HodeTech altında geliştirilen bağımsız bir yardımcı araç projesidir. EVREN adı uyumluluk hedefini belirtir; platformun geliştirdiği veya onayladığı bir ürün olduğu iddia edilmez. ForgeLM ayrı bir projedir ve kendi lisansı/sürüm döngüsüyle kullanılır.
