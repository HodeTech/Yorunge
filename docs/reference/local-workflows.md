# Yerel kullanım rehberi

**Güncellendi:** 2026-11-02. Çalışan CLI/Python akışları; [güncel teslim durumu](../roadmap/current.md) ve her bölümdeki kanonik sözleşme geçerlidir. Yayımlanmış paket yoktur; kaynak checkout’u kullanılır.

Başlangıç için [README](../../README.md), kesin komut/çıktı biçimleri için [CLI sözleşmesi](cli-contract.md). Bu rehber örnekleri bir araya getirir; uzak yürütme veya eğitim desteği vaat etmez.

Private aktarım için ayrı [upload rehberi](upload-workflows.md) vardır; teslim ve kabul sınırı o belgenin başında belirtilir.

## Çalışan başlangıç

Kurulum için [README başlangıcını](../../README.md#çalışan-başlangıç) izleyin. Aşağıdaki örnekler depo kökünde çalıştırılır:

```sh
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

`plan show --plan offline-plan.json` kayıtlı seçimi mevcut profilden yeniden çözmez. Digest bütünlük kontrolüdür; yürütme onayı değildir. Kurulum, kontrol ve build adımları [katkı rehberinde](../../CONTRIBUTING.md); kesin uygulama sınırı [CLI](../reference/cli-contract.md) ve [config](../reference/configuration.md) sözleşmelerindedir. Yerel doğrulama ve ölçümler: [P01 kabul kaydı](../research/p01-core-validation.md).

Profilde belirtilen env değeri hazırsa, yalnız seçilen hizmetin sır ayarını açıkça kontrol edebilirsiniz:

```sh
.venv/bin/yorunge context credential --service evren-platform --config examples/profile.toml --output json
```

Python karşılığı `yorunge.api.check_credential("evren-platform", config=Path("examples/profile.toml"))` çağrısıdır. Sır değeri çıktıya girmez; bu kontrol ağ/DB açmaz ve uzak kimlik/yetki doğrulaması yapmaz. Kalıcı `context identity` gözlemi seçili env'yi açık istekle okur; varsayılan offline komutlar okumaz.

Development sürümünde LLM şart durumu açıkça sorgulanabilir. Önce [yerel hesap hazırlığını](../p02-account-setup.md) tamamla. Yönergedeki **Hazırlıktan normal discovery’ye** bloğu anahtarı yalnız seçili hizmetin çocuk sürecine aktarır ve aşağıdaki çağrıyı çalıştırır; anahtarı komut satırına yazma. Aşağıdaki doğrudan komut, ilgili env zaten çağıran süreçte hazırsa kullanılır. Mevcut private store gereklidir:

```sh
.venv/bin/yorunge context discover --service evren-llm --config .local/p02-pilot/config.toml --state-dir .local/p02-pilot/state --output json
```

Python karşılığı `api.discover_context("evren-llm", config=Path(".local/p02-pilot/config.toml"), state_dir=Path(".local/p02-pilot/state"))` çağrısıdır. Bu komut gerçek ağ erişimi ve yerel registry/clock gözlemi yapar; store oluşturmaz, şart kabul etmez. Terms cevabı auth/hesap/proje/izin kanıtı değildir. LLM için account/project ID gerekmez; Platform profili LLM seçimine kopyalanmaz. Platform için `--service evren-platform` aynı komutta üç salt okuma yapar; profilde veya `--project ID` ile proje seçiliyse dördüncü detail okuması eklenir. Sonuç yalnız doğrulanmamış ID bildirimi, liste ve seçim gözlemidir; auth/hesap/izin veya liste tamlığı kanıtı değildir. Bildirilen ID’ler kişiye bağlanabilir; çıktıyı paylaşırken koru. ADR-0022 ile bu dar gözlem nihai consumer sınırıdır; gerçek liste/seçili-detail ve kaynak/review/PR CI kabulü tamam; PR #12 ile development’a teslim edildi. Doğrulanmış kimlik/bağ P02-R1’de açık kalır. [Kesin discovery sınırı ve kabul durumu](../reference/context-discovery.md).

Açık yerel capability cache sorgusu:

```sh
.venv/bin/yorunge capabilities --task llm.train --refresh --output json
.venv/bin/yorunge capabilities --task llm.train --cached --output json
```

Bu iki seçenek private SQLite state/clock kullanır; `--state-dir PATH` ile ayrı dizin seçilebilir. `--cached` keşif yapmaz, `--refresh` bu sürümde yalnız uygulanmış yerel politikayı yeniler. Hit/freshness ile etkin destek ve tarihsel kayıt ayrıdır; uzak hesap/araç desteği yaratılmaz. Python karşılığı `api.query_capabilities` ve ayrıntılar [cache sözleşmesindedir](../reference/capability-record.md#açık-cache-v2-sorgusu). Ayrı kalıcı execution hazırlığı ve onay yönetimi aşağıdadır; run yoktur.

Yerel ayar ve kimlik yönetimi:

```sh
.venv/bin/yorunge init --profile work
.venv/bin/yorunge context profiles
.venv/bin/yorunge context set-project project-id
.venv/bin/yorunge doctor --output json
.venv/bin/yorunge context identity --service evren-platform --output json
```

`init` var olan config'i ezmez; profil/proje değişimleri özgün dosyayı yedekler. Doctor env/K içeriği veya uzak erişimi kontrol etmez; sonuçtaki durumları değerlendirin. Kimlik gözlemi yerel DB/key oluşturabilir; ağ açmaz veya execution izni vermez. Reset/restore için önce etki önizlemesi ve açık digest onayı gerekir; restore snapshot sonrası geçmişi kaybedebilir. [Config/doctor sözleşmesi](../reference/configuration.md#yerel-config-yazma-ve-tanılama), [kimlik bağları](../reference/credential-binding-v1.md) ve [bakım/kurtarma](../reference/local-state.md#açık-reset-restore-ve-kesilmiş-restore-kurtarması).

Kalıcı execution hazırlığı:

```sh
.venv/bin/yorunge plan execution prepare --task llm.train --state-dir ./private-state --output json
.venv/bin/yorunge plan execution list --state-dir ./private-state --output json
```

Bu açık komutlar private state oluşturabilir. Execution planı ayrı v2 kaydıdır; gerçek araç/uzak auth/tam girdi kapanışı eksik olduğundan public plan draft ve onaylanamazdır. Yerel manifest bağlamak için recipe ve açık input-root gerekir; yalnız manifest dosyasının hash'i veri kümesinin tamamını doğrulamaz. Güncel validate, tam digest approve ve seçili revoke/forget [execution referansında](../reference/execution-plan.md); eski offline v1 komutları stateless kalır. [Test, review ve performans kanıtı](../research/p01-3-implementation-validation.md).

## Yerel dosya manifesti

`datasets inspect/verify`, macOS/Linux yerel diskte anahtar/config/state/ağ gerektirmez. [Kabul ve teslim durumu](../roadmap/current.md) ayrıdır. Sentetik örnek:

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

Python karşılıkları `api.inspect_dataset(Path(root), manifest_out=Path(target))` ve `api.verify_dataset(Path(root), manifest=Path(target))` çağrılarıdır. Inspect normal dosyaların ad/byte/hash envanterini root dışındaki yeni, 0600 manifest dosyasına kaydeder; mevcut hedefi ezmez. Parent mevcut olmalıdır. İki işlem text/JSON/NDJSON küçük özeti verir; bütün dosya listesi yalnız artifact’tadır. Gizli dosyalar dahil edilir; symlink/özel dosya, Unicode/case ad çakışması ve desteklenmeyen adlar reddedilir. Python Unicode sürümü sonuçta görünür; yeni sürüm yeni çakışmaları reddedebilir. Verify bütün içerikleri yeniden hash’ler; boş dizin farkı içerik uyuşmazlığı değildir. Sonuç veri formatı, ML uygunluğu, atomik snapshot veya upload/yürütme izni değildir. Manifest adlar/hash’ler içerebilir; paylaşırken koru. [Sınırlar, iptal ve hata/exit sözleşmesi](../reference/dataset-manifest.md).

## Yerel iş geçmişi

```sh
.venv/bin/yorunge jobs list --state-dir ./private-state --output json
.venv/bin/yorunge jobs list --status unknown --limit 20 --state-dir ./private-state
```

Listeden alınan kimlik `jobs show --operation-id UUID --state-dir ./private-state` ile okunur. Python karşılıkları `api.list_jobs(...)` ve `api.show_job(operation_id, ...)` çağrılarıdır. Filtre/cursor ve tam wire [jobs referansındadır](../reference/operations.md). Boş store boş liste verir; plan hazırlamak/onaylamak job oluşturmaz. Public run ve EVREN yürütme adaptörü henüz yoktur.

Bu sorgular yalnız son yerel kaydı gösterir; `running` güncel uzak çalışma kanıtı değildir. Config/env/girdi/sağlayıcı okunmaz, uzlaştırma veya yeniden gönderim yapılmaz. Unknown/failed işin başarıyla okunması exit 0 ve dış Result completed demektir; gerçek iş durumu data içindedir. Açık state erişimi store kurulumunu/migration veya SQLite kurtarmasını çalıştırabilir.

İç koordinasyon plan başına tek operation ve kalıcı gönderim niyetiyle ikinci gönderimi önler. Kimlik reset'i gönderim öncesi işi cancelled, gönderim niyeti olan işi unknown yapar; daha önce arm edilmiş dış etkiyi kesin durdurmaz. Tarihçe otomatik silinmez; 1.024 lifetime operation bütün plan slotlarını bağladıysa yeni plan üretimi kontrollü reddedilir. Yeni state dizini eski unknown işi yeniden gönderme çözümü değildir.

## Otomasyonda çıktı ve yerel iptal

Mevcut normal komutlarda `--output ndjson` veya `--output=ndjson`, tek başarılı sonucu tek UTF-8 `result` olayıyla verir. Olayın `payload` alanı mevcut JSON Result v1 ile aynıdır; text/JSON varsayımları değişmez. Örneğin:

```sh
.venv/bin/yorunge context show --config examples/profile.toml --output ndjson
.venv/bin/yorunge jobs list --state-dir ./private-state --output=ndjson
```

Help/version insan çıktısı kalır. İlk sonuçtan önceki hata stdout’u boş bırakıp stderr’e tek JSON yazar. Ctrl-C ve kapalı pipe yerel çağrıyı bırakır (exit 6); kayıtlı işi geri almaz veya uzakta durdurmaz. Config yayınında veya operation gönderiminde belirsizlik varsa exit 5 ve ilgili kimlik korunur; otomatik tekrar yapılmaz. Kesin wire ve çıktı boyutu sınırları [akış sözleşmesindedir](../reference/stream-results.md).

Ortak HTTP/stream altyapısı gerçek TLS loopback, ayrı süreç ve kurulu wheel/sdist ile doğrulandı. P02 LLM terms ve Platform gözlem adaptörleri PR #12 ile development’a teslim edildi; kullanıcıya açık uzak watch/run sonraki fazlardadır. [P01 kabulü ve development teslimi](../research/p01-remaining-implementation-validation.md#development-merge-kapanışı) PR #11 ile tamamlandı.
