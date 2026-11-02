# Yörünge

**EVREN platformunda veriden sonuca uzanan işleri kolaylaştıran kapsamlı yardımcı araç.**

Yörünge; hesap ve proje bağlamını, veri setlerini, modelleri, LLM ve çıkarım servislerini, eğitim işlerini, GPU/kota görünürlüğünü ve çalışma sonuçlarını tutarlı iş akışlarında bir araya getirmek için tasarlanıyor. Kullanıcı, bir işi tamamlamak için ayrı istemcilerin ayarlarını ve ilerleme kayıtlarını birleştirmek zorunda kalmamalı.

**Durum — 2 Kasım 2026:** P01 hafif çekirdek ve P02-0 dar salt okuma gözlemleri development’a teslim edildi ([P01 kapanışı](docs/research/p01-remaining-implementation-validation.md#development-merge-kapanışı), [P02-0 kapanışı](docs/research/p02-0-implementation-validation.md#development-merge-kapanışı)). P02-1 yerel dosya envanteri, Manifest v1 ve inspect/verify CLI/Python yüzeyi çalışma dalında verified; [PR #13](https://github.com/HodeTech/Yorunge/pull/13) kullanıcı review/merge aşamasında. Kurulum, native ölçüm ve üç ortam CI kabulünün kaynakları/sınırları [güncel kabul kaydındadır](docs/research/p02-1-implementation-validation.md#pr-13-review-bulguları-ve-saklama-kapanışı). `0.1.0.dev0` yayımlanmadı; uzak veri aktarımı, çıkarım ve eğitim adaptörleri sonraki paketlerdedir. Master/release kullanıcı sürecidir.

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

Profilde belirtilen env değeri hazırsa, yalnız seçilen hizmetin sır ayarını açıkça kontrol edebilirsiniz:

```sh
.venv/bin/yorunge context credential --service evren-platform --config examples/profile.toml --output json
```

Python karşılığı `yorunge.api.check_credential("evren-platform", config=Path("examples/profile.toml"))` çağrısıdır. Sır değeri çıktıya girmez; bu kontrol ağ/DB açmaz ve uzak kimlik/yetki doğrulaması yapmaz. Kalıcı `context identity` gözlemi seçili env'yi açık istekle okur; varsayılan offline komutlar okumaz.

Development sürümünde LLM şart durumu açıkça sorgulanabilir. Önce [yerel hesap hazırlığını](docs/p02-account-setup.md) tamamla. Yönergedeki **Hazırlıktan normal discovery’ye** bloğu anahtarı yalnız seçili hizmetin çocuk sürecine aktarır ve aşağıdaki çağrıyı çalıştırır; anahtarı komut satırına yazma. Aşağıdaki doğrudan komut, ilgili env zaten çağıran süreçte hazırsa kullanılır. Mevcut private store gereklidir:

```sh
.venv/bin/yorunge context discover --service evren-llm --config .local/p02-pilot/config.toml --state-dir .local/p02-pilot/state --output json
```

Python karşılığı `api.discover_context("evren-llm", config=Path(".local/p02-pilot/config.toml"), state_dir=Path(".local/p02-pilot/state"))` çağrısıdır. Bu komut gerçek ağ erişimi ve yerel registry/clock gözlemi yapar; store oluşturmaz, şart kabul etmez. Terms cevabı auth/hesap/proje/izin kanıtı değildir. LLM için account/project ID gerekmez; Platform profili LLM seçimine kopyalanmaz. Platform için `--service evren-platform` aynı komutta üç salt okuma yapar; profilde veya `--project ID` ile proje seçiliyse dördüncü detail okuması eklenir. Sonuç yalnız doğrulanmamış ID bildirimi, liste ve seçim gözlemidir; auth/hesap/izin veya liste tamlığı kanıtı değildir. Bildirilen ID’ler kişiye bağlanabilir; çıktıyı paylaşırken koru. ADR-0022 ile bu dar gözlem nihai consumer sınırıdır; gerçek liste/seçili-detail ve kaynak/review/PR CI kabulü tamam; PR #12 ile development’a teslim edildi. Doğrulanmış kimlik/bağ P02-R1’de açık kalır. [Kesin discovery sınırı ve kabul durumu](docs/reference/context-discovery.md).

Açık yerel capability cache sorgusu:

```sh
.venv/bin/yorunge capabilities --task llm.train --refresh --output json
.venv/bin/yorunge capabilities --task llm.train --cached --output json
```

Bu iki seçenek private SQLite state/clock kullanır; `--state-dir PATH` ile ayrı dizin seçilebilir. `--cached` keşif yapmaz, `--refresh` bu sürümde yalnız uygulanmış yerel politikayı yeniler. Hit/freshness ile etkin destek ve tarihsel kayıt ayrıdır; uzak hesap/araç desteği yaratılmaz. Python karşılığı `api.query_capabilities` ve ayrıntılar [cache sözleşmesindedir](docs/reference/capability-record.md#açık-cache-v2-sorgusu). Ayrı kalıcı execution hazırlığı ve onay yönetimi aşağıdadır; run yoktur.

Yerel ayar ve kimlik yönetimi:

```sh
.venv/bin/yorunge init --profile work
.venv/bin/yorunge context profiles
.venv/bin/yorunge context set-project project-id
.venv/bin/yorunge doctor --output json
.venv/bin/yorunge context identity --service evren-platform --output json
```

`init` var olan config'i ezmez; profil/proje değişimleri özgün dosyayı yedekler. Doctor env/K içeriği veya uzak erişimi kontrol etmez; sonuçtaki durumları değerlendirin. Kimlik gözlemi yerel DB/key oluşturabilir; ağ açmaz veya execution izni vermez. Reset/restore için önce etki önizlemesi ve açık digest onayı gerekir; restore snapshot sonrası geçmişi kaybedebilir. [Config/doctor sözleşmesi](docs/reference/configuration.md#yerel-config-yazma-ve-tanılama), [kimlik bağları](docs/reference/credential-binding-v1.md) ve [bakım/kurtarma](docs/reference/local-state.md#açık-reset-restore-ve-kesilmiş-restore-kurtarması).

Kalıcı execution hazırlığı:

```sh
.venv/bin/yorunge plan execution prepare --task llm.train --state-dir ./private-state --output json
.venv/bin/yorunge plan execution list --state-dir ./private-state --output json
```

Bu açık komutlar private state oluşturabilir. Execution planı ayrı v2 kaydıdır; gerçek araç/uzak auth/tam girdi kapanışı eksik olduğundan public plan draft ve onaylanamazdır. Yerel manifest bağlamak için recipe ve açık input-root gerekir; yalnız manifest dosyasının hash'i veri kümesinin tamamını doğrulamaz. Güncel validate, tam digest approve ve seçili revoke/forget [execution referansında](docs/reference/execution-plan.md); eski offline v1 komutları stateless kalır. [Test, review ve performans kanıtı](docs/research/p01-3-implementation-validation.md).

## Yerel dosya manifesti

P02-1 çalışma dalında `datasets inspect/verify` uygulanmıştır; iki fresh kod review turu, üç temiz wheel/sdist kurulum turu ve kaynak bağlı M5/native kabulü tamamlandı. Üç ortam source/metadata CI ve Linux kanıt saklama kabulü de geçti; P02-1 çalışma dalında verified ve [PR #13](https://github.com/HodeTech/Yorunge/pull/13) kullanıcı incelemesindedir. Henüz development teslimi veya sürüm yayını değildir. macOS/Linux yerel diskte, anahtar/config/state/ağ gerektirmeyen sentetik örnek:

```sh
demo_dir=$(python3 -c 'import tempfile; from pathlib import Path; print(Path(tempfile.mkdtemp(prefix="yorunge-demo-")).resolve())')
mkdir "$demo_dir/source"
printf 'abc' > "$demo_dir/source/a.txt"
.venv/bin/yorunge datasets inspect "$demo_dir/source" --manifest-out "$demo_dir/manifest.json"
.venv/bin/yorunge datasets verify "$demo_dir/source" --manifest "$demo_dir/manifest.json" --output json
printf 'xyz' > "$demo_dir/source/a.txt"
.venv/bin/yorunge datasets verify "$demo_dir/source" --manifest "$demo_dir/manifest.json" --output json
# Son komut exit 7: aynı boyutlu içerik değişimi, stdout boş, hata stderr.
```

Python karşılıkları `api.inspect_dataset(Path(root), manifest_out=Path(target))` ve `api.verify_dataset(Path(root), manifest=Path(target))` çağrılarıdır. Inspect normal dosyaların ad/byte/hash envanterini root dışındaki yeni, 0600 manifest dosyasına kaydeder; mevcut hedefi ezmez. Parent mevcut olmalıdır. İki işlem text/JSON/NDJSON küçük özeti verir; bütün dosya listesi yalnız artifact’tadır. Gizli dosyalar dahil edilir; symlink/özel dosya, Unicode/case ad çakışması ve desteklenmeyen adlar reddedilir. Python Unicode sürümü sonuçta görünür; yeni sürüm yeni çakışmaları reddedebilir. Verify bütün içerikleri yeniden hash’ler; boş dizin farkı içerik uyuşmazlığı değildir. Sonuç veri formatı, ML uygunluğu, atomik snapshot veya upload/yürütme izni değildir. Manifest adlar/hash’ler içerebilir; paylaşırken koru. [Sınırlar, iptal ve hata/exit sözleşmesi](docs/reference/dataset-manifest.md).

## Yerel iş geçmişi

```sh
.venv/bin/yorunge jobs list --state-dir ./private-state --output json
.venv/bin/yorunge jobs list --status unknown --limit 20 --state-dir ./private-state
```

Listeden alınan kimlik `jobs show --operation-id UUID --state-dir ./private-state` ile okunur. Python karşılıkları `api.list_jobs(...)` ve `api.show_job(operation_id, ...)` çağrılarıdır. Filtre/cursor ve tam wire [jobs referansındadır](docs/reference/operations.md). Boş store boş liste verir; plan hazırlamak/onaylamak job oluşturmaz. Public run ve EVREN yürütme adaptörü henüz yoktur.

Bu sorgular yalnız son yerel kaydı gösterir; `running` güncel uzak çalışma kanıtı değildir. Config/env/girdi/sağlayıcı okunmaz, uzlaştırma veya yeniden gönderim yapılmaz. Unknown/failed işin başarıyla okunması exit 0 ve dış Result completed demektir; gerçek iş durumu data içindedir. Açık state erişimi store kurulumunu/migration veya SQLite kurtarmasını çalıştırabilir.

İç koordinasyon plan başına tek operation ve kalıcı gönderim niyetiyle ikinci gönderimi önler. Kimlik reset'i gönderim öncesi işi cancelled, gönderim niyeti olan işi unknown yapar; daha önce arm edilmiş dış etkiyi kesin durdurmaz. Tarihçe otomatik silinmez; 1.024 lifetime operation bütün plan slotlarını bağladıysa yeni plan üretimi kontrollü reddedilir. Yeni state dizini eski unknown işi yeniden gönderme çözümü değildir.

## Otomasyonda çıktı ve yerel iptal

Mevcut normal komutlarda `--output ndjson` veya `--output=ndjson`, tek başarılı sonucu tek UTF-8 `result` olayıyla verir. Olayın `payload` alanı mevcut JSON Result v1 ile aynıdır; text/JSON varsayımları değişmez. Örneğin:

```sh
.venv/bin/yorunge context show --config examples/profile.toml --output ndjson
.venv/bin/yorunge jobs list --state-dir ./private-state --output=ndjson
```

Help/version insan çıktısı kalır. İlk sonuçtan önceki hata stdout’u boş bırakıp stderr’e tek JSON yazar. Ctrl-C ve kapalı pipe yerel çağrıyı bırakır (exit 6); kayıtlı işi geri almaz veya uzakta durdurmaz. Config yayınında veya operation gönderiminde belirsizlik varsa exit 5 ve ilgili kimlik korunur; otomatik tekrar yapılmaz. Kesin wire ve çıktı boyutu sınırları [akış sözleşmesindedir](docs/reference/stream-results.md).

Ortak HTTP/stream altyapısı gerçek TLS loopback, ayrı süreç ve kurulu wheel/sdist ile doğrulandı. P02 LLM terms ve Platform gözlem adaptörleri PR #12 ile development’a teslim edildi; kullanıcıya açık uzak watch/run sonraki fazlardadır. [P01 kabulü ve development teslimi](docs/research/p01-remaining-implementation-validation.md#development-merge-kapanışı) PR #11 ile tamamlandı.

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

Geliştirme ve normal PR hedefi `development`, release dalı `Master`'dır. PR'lar merge commit ile alınır; Master'a aktarımı kullanıcı yapar. [Dal ve koruma politikası](docs/standards/git-release.md).

Proje kayıtları: [değişiklik günlüğü](CHANGELOG.md), [güvenlik bildirimi](SECURITY.md), [topluluk ilkeleri](CODE_OF_CONDUCT.md), [Claude giriş rehberi](CLAUDE.md).

## Lisans ve proje ilişkisi

[MIT License](LICENSE). Yörünge, HodeTech altında geliştirilen bağımsız bir yardımcı araç projesidir. EVREN adı uyumluluk hedefini belirtir; platformun geliştirdiği veya onayladığı bir ürün olduğu iddia edilmez. ForgeLM ayrı bir projedir ve kendi lisansı/sürüm döngüsüyle kullanılır.
