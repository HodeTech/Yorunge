# Katkı rehberi

Yörünge'nin P01 hafif çekirdeği, kullanıcı review ve ADR-0019/Sonar takibi çalışma dalında verified; [son kaynak kabulü](docs/research/p01-remaining-implementation-validation.md#adr-0019-ve-sonar-son-kaynak-ci-kapanışı) gerçek üç ortam CI, altı kurulum ve kaynak bağlı referansları taşır. Development PR review/merge ve yayın ayrı süreçtir. Ürün kapsamını [product-scope.md](docs/product-scope.md), sıradaki işi [current.md](docs/roadmap/current.md) tanımlar.

## Çalışma akışı

1. İlgili kapsam maddesini, modülü, sözleşmeyi ve standardı okuyun.
2. İlgili iş kaydını veya yol haritası görevini belirleyin. Küçük belge düzeltmeleri ayrı iş kaydı gerektirmez.
3. Güncel `origin/development` üzerinden kısa ömürlü `feat/`, `fix/`, `docs/` veya `ci/` çalışma dalı açın. Normal PR hedefi `development`; varsayılan dal da `development` olur.
4. Bir değişiklikte tek bir sonucu somutlaştırın. Kullanıcı davranışı değişirse sözleşme ve kabul ölçütünü aynı değişiklikte güncelleyin.
5. İlgili doğrulamayı yapıp sonucu PR açıklamasına yazın. Çalıştırılmayan kontrolü başarılı göstermeyin.
6. Yeşil zorunlu kontroller ve çözülmüş inceleme konuşmaları sonrası **merge commit** ile birleştirin. Squash/rebase merge ve korunan dallara doğrudan push kullanılmaz.

`Master` release dalıdır; aynı deponun `development` dalından açılan aktarım PR'ını bakım sahibi birleştirir. Ajan `Master` birleştirmesi veya yayın yapmaz. İlk kurulum sırası, tek yazma yetkilisi nedeniyle sıfır zorunlu review seçimi ve tam koruma koşulları [Git/yayın standardında](docs/standards/git-release.md) tanımlıdır.

P01 için [epik başına PR sözleşmesi](docs/roadmap/README.md#epik-başına-pr) geçerlidir. Alt kart/commit/review birimleri aynı epik dalında tamamlanır; ortak önkoşullar ve bütünleşik kabul paket planında görünür tutulur.

## Belge değişiklikleri

Türkçe açıklama, İngilizce dosya/kimlik adları, UTF-8/LF ve göreli bağlantılar kullanın. Her Markdown dosyasının bir H1 başlığı olmalı. Planlanan komutu çalışan örnek diye sunmayın. Dizine eklenen belgeyi o dizinin README'sine bağlayın. Bağlantıları, başlıkları, kod bloklarını ve mevcut durumla tutarlılığı denetleyin. [Belgeleme standardı](docs/standards/documentation.md).

## Geliştirme ve doğrulama

[Python](docs/standards/python.md), [test](docs/standards/testing.md), [güvenlik](docs/standards/security.md), [performans](docs/standards/performance.md) ve [hata/çıktı](docs/standards/error-handling-observability.md) standartları uygulanır. Python 3.11+ hedeflenir; yerelde macOS/arm64 + CPython 3.11.18 doğrulandı. CI tanımı Linux/Python 3.11, Linux/Python 3.14 ve macOS/Python 3.11 hücrelerinde tam test, statik kontroller, build ve iki temiz kurulum çalıştırır. Zorunlu `offline-core` bu üç hücrenin tamamı başarılıysa geçer; failure/cancelled/skipped kabul edilmez. Başlangıç/raw stream Linux/Python 3.11'de seri ölçülür. Jobs 200 ms referans kapısı aynı yerel M5/SSD ortamında ölçülür; CI, başarılı ham referansın kaynak/lock/fixture/ölçüm kodu baytlarını güncel checkout ile zorunlu eşleştirir. Bu kayıt denetimi Linux'ta jobs performansı ölçülmüş/geçmiş sayılmaz. [Referans ve ölçüm sınırı](docs/standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) ile [gerçek CI kaydı](docs/research/p01-remaining-implementation-validation.md) ayrı okunur.

Ajan alias'ları ve bunları sınayan fixture'lar gerçek göreli symlink gerektirir. Desteklenen tam geliştirme/test checkout ortamı macOS veya Linux'tur; Git symlink'leri normal dosyaya dönüştüren Windows checkout'ları doğrulanmamıştır ve bu kontrolü çalıştıramaz. Bu sınır runtime için Windows desteği kanıtı veya yeni bir runtime kısıtı değildir.

`uv 0.11.2` zaten kuruluysa doğrudan `uv sync` adımına geçin. İzole araç kurulumu:

```sh
python3.11 -m venv .local/tooling
.local/tooling/bin/pip install uv==0.11.2
```

Aşağıdaki komutlarda `uv` yerine gerekirse `.local/tooling/bin/uv` kullanın:

```sh
uv sync --frozen --python 3.11
.venv/bin/ruff format --check src tests scripts
.venv/bin/ruff check src tests scripts
.venv/bin/mypy
.venv/bin/pytest
.venv/bin/python scripts/check-docs.py
.venv/bin/python scripts/check-agent-guides.py
.venv/bin/python scripts/research_evidence.py verify
uv build
.venv/bin/python scripts/verify-distributions.py --uv .local/tooling/bin/uv > dist/verification.jsonl
mkdir -p .local
startup_fixture=$(mktemp -d .local/yorunge-startup.XXXXXX)
.venv/bin/python tests/fixtures/seed_capability_cache.py "$startup_fixture/state" examples/profile.toml
.venv/bin/python scripts/benchmark-startup.py --command .venv/bin/yorunge --cache-state "$startup_fixture/state" --installation-label "editable .venv; frozen uv environment" --output dist/startup.json
```

`--uv` için gerçekten kullanılan uv executable yolunu verin. `uv.lock` geliştirme/runtime sürümleri ve hash'lerini sabitler; build backend'i `pyproject.toml` içinde sabittir. İlk kurulum/build paket indirmek için ağ kullanabilir; uygulama ve test senaryoları çevrimdışıdır. `uv build` wheel'i sdist'ten üretir. Dağıtım denetimi üyeleri izin listesiyle kontrol eder, her arşivi ayrı temiz ortama kurar, import kökenini ve konsol komutunu depo dışından doğrular. Build çıktısı `dist/` altında Git dışında kalır.

Dağıtım denetimi bir wheel ve aynı sürümden bir sdist gerektirir. Ham üye adı kök kırpılmadan denetlenir; mutlak/traversal/kanonik olmayan yol, yinelenen ad, dosya/dizin çakışması, link ve özel dosya reddedilir. Sdist'in tek kökü arşiv adıyla, wheel metadata dizini dağıtım/sürümle eşleşir. `dist/verification.jsonl` her başarılı temiz kurulum için arşiv adı/SHA-256/üye sayısı/köken ve basic/NDJSON/HTTP/stream/cache/execution/jobs smoke sonucunu taşır. HTTP/stream sınaması gerçek yerel TLS sunucusu ve ayrı `-I` runtime-only süreç kullanır; EVREN erişimi değildir. Komutun başarısı ve iki kayıt birlikte tam kabul kanıtıdır. Hatalı koşunun kısmi kaydı başarı sayılmaz. CI aynı kayıtları iş günlüğünde gösterir.

ZIP adında Python'un NUL kırpmasından önceki özgün alan denetlenir. `uv` ile Python'un farklı ad seçmesine yol açan Unicode Path (`0x7075`) alternatif ad alanı ve bozuk extra metadata reddedilir; diğer düzgün metadata alanları korunur. Bu denetim bu deponun ürettiği paketler içindir, genel amaçlı arşiv çıkarıcı değildir.

Performans kabulü help/version/context ile birlikte 1.024 kayıtlı cache sorgusunu da kapsar; `--cache-state` zorunludur. Yukarıdaki hazırlık her koşu için repo içindeki `.local` altında yeni bir geçici dizin seçer (macOS `/var`/`/tmp` symlink atalarını kullanmaz), mevcut state verisini kullanmaz veya ezmez; sentetik dizin ve ölçüm kaydı denetim için korunur. CPU/disk/kurulum etiketleri ölçülen gerçek ortamı belirtmelidir; bilinmeyen disk türü `unknown` kalır. Performans betiği her komut için ilk süreç süresini ayrı, üç ısınma sonrası en az 30 ayrı sürecin p95'ini ayrıca kaydeder. OS/disk cache'i boşaltmaz. Hedef aşılırsa sıfır dışı kodla çıkar. Belge kontrolü yalnız açıkça seçilmiş genel belge dizinlerini okur; site/doküman yayın sistemi henüz yoktur.

CI ile aynı izole runtime kurulumunu ve eşli ölçümü yerelde çalıştırmak için, mevcut olmayan bir workspace/çıktı adı seçin:

```sh
.venv/bin/python scripts/check-startup.py --uv .local/tooling/bin/uv --workspace .local/startup-check --output dist/startup-isolated.json
```

Önceki bir kaynak checkout'u varsa `--baseline-project PATH` eklenir; aday ve taban tek host'ta AB/BA sırasıyla ölçülür. A/A kontrolü için `--baseline-project .` kullanılabilir. Helper her tarafın frozen runtime gereksinimleriyle ayrı wheel/venv ve yeni fixture oluşturur; hazırlık ölçülen süreç süresine dahil değildir. Test/profiler/büyük build işleri benchmark ile eşzamanlı çalıştırılmaz. Varsayılan disk bilgisi `unknown`'dır; gerçek ortam biliniyorsa `--disk-type`/`--cpu-label` verilir. Sonuç dosyası mevcutsa yeni bir ad seçilir; tekrar koşularından en hızlısını seçerek kabul verilmez. [Ölçüm ve kabul kuralları](docs/standards/performance.md#aynı-makinede-başlangıç-karşılaştırması) kanoniktir.

Aynı aday runtime ile, önceki komut tamamlandıktan sonra jobs ve raw stream kabulünü ayrı ve yeni workspace/çıktılara seri çalıştırın:

```sh
.venv/bin/python scripts/benchmark-jobs.py --python .local/startup-check/candidate/env/bin/python --workspace .local/jobs-check --output dist/jobs.json --wheel .local/startup-check/candidate/dist/*.whl --disk-type unknown
.venv/bin/python scripts/benchmark-stream.py --python .local/startup-check/candidate/env/bin/python --workspace .local/stream-check --output dist/stream.json --disk-type unknown
```

Jobs normal/yoğun list/show için ayrı ilk süreç, üç ısınma ve en az 30 ölçülmüş süreç kullanır; sonuç doğruluğu süre dışında bağımsız doğrulanır. Raw stream ayrı TLS sunucusu ve kurulu istemci sürecinde 16/256/1024 MiB okur; byte/SHA-256 ve anlık native RSS baseline, yaşam boyu HWM ve ek RSS alt/üst sınırlarını kaydeder. Sunucu RSS'i istemciye eklenmez. [Bellek yöntemi ve sınırları](docs/standards/performance.md#kurulu-jobs-ve-raw-stream-ölçümü) kanoniktir. Kaynak/kurulum/fixture değişirse ölçüm kabul edilmez. Üretilmiş JSON, [kanıt aracıyla](docs/standards/research-evidence.md) arşivlenir.

Kaynak bağlı jobs kapısı test-only ve workflow değişikliklerini de kapsar; böyle bir PR için eski yeşil kayıt yeterli değildir. Bu bakımın mevcut M5/SSD referansına erişebilen bir sahibi olmalıdır. Yukarıdaki `--disk-type unknown` genel ölçüm kaydı zorunlu M5/SSD referansını yenilemez. Referans yenilemede `NEXT` yer tutucusunu yeni kayıt kimliğiyle değiştirin; aynı JSON dosya adını workflow ve testte **ölçümden önce** seçip kaynakları sabitleyin. Referans host'ta yukarıdaki kurulu hazırlığı yeni workspace/çıktıyla tamamladıktan sonra, `--python` ve `--wheel` yollarını bu yeni aday kuruluma eşleyerek şu ayrı komutu çalıştırın:

```sh
.venv/bin/python scripts/benchmark-jobs.py --python .local/startup-check/candidate/env/bin/python --workspace .local/jobs-reference-NEXT --output dist/p01-6-reference-jobs-NEXT.json --wheel .local/startup-check/candidate/dist/*.whl --cpu-label "Apple M5 Max" --disk-type "internal SSD/APFS"
```

Bu etiketler yalnız gerçek referans ortamı **Apple M5 Max/arm64, macOS 27.0.1, Python 3.11, internal SSD/APFS** ise kullanılır. Hazırlık ve ölçümleri seri çalıştırın; ardından [kanıt standardındaki](docs/standards/research-evidence.md) arşivleme ve `verify-jobs-reference p01-6-reference-jobs-NEXT.json` doğrulamasını tamamlayın. Hazırlık ve ölçüm için ayrıca zaman ayırın; toplam süre host/I/O yüküne bağlıdır. Kaynak kapsamını daraltmak bu zorunluluğun yerine geçmez; yalnız belge değişikliği mevcut kaynak baytlarını koruyorsa yeniden ölçüm gerektirmez.

## Sabit startup referansını yenileme

[ADR-0019](docs/decisions/0019-reference-startup-performance.md) Accepted; startup 500/200 ms hedefinin kabul ortamı jobs ile aynı **Apple M5 Max/arm64, macOS 27.0.1, Python 3.11, internal SSD/APFS**'dir. Önce workflow ve testte yeni startup/jobs kayıt adları seçilir; tam kaynaklar sabitlenir. Aşağıdaki `NEXT` ve taban checkout yolu gerçek yeni ad/yolla değiştirilir; taban runtime içeren ayrı, sabit Git checkout'u olmalıdır:

```sh
.venv/bin/python scripts/check-startup-evidence.py --uv .local/tooling/bin/uv --baseline-project .local/startup-baseline --workspace .local/startup-reference-NEXT --output dist/p01-6-reference-startup-NEXT.json --cpu-label "Apple M5 Max" --disk-type "internal SSD/APFS"
.venv/bin/python scripts/research_evidence.py archive dist/p01-6-reference-startup-NEXT.json
.venv/bin/python scripts/research_evidence.py verify-startup-reference p01-6-reference-startup-NEXT.json
```

Helper fresh wheel/venv ve ayrı iki cache fixture hazırlar; üç ısınma ve her komutta 30+ süreç, typed/sabit çıktı oracle'ı ve before/after kaynak/kurulum/fixture eşliği zorunludur. Her taraf kendi sürümünü ve kendi kurulu Python wire modelini doğrular; ortak aday profil baytları kullanılır. Aynı yeni aday runtime ile jobs referansı ve raw ölçümü **seri** alınır. Bu sırada test/build/profiler çalıştırılmaz. Eski `benchmark-startup.py` / `check-startup.py` v2 çıktıları bu yeni kapıyı geçmez. Yalnız README metadata açıklaması değişiminde tarihsel wheel hash'inin yeni wheel'e eşit olması aranmaz; runtime/entry point/lock/ölçüm kodu/workflow değişikliği eski referansı geçersiz kılar.

Linux CI aynı-host AB/BA startup'ı ölçmeyi sürdürür. Yalnız tam doğrulanmış mutlak aşım `diagnostic_budget_exceeded` ile görünür nonblocking tanıdır; setup/timeout/bozuk rapor/yanlış çıktı/stale kaynak engelleyicidir. M5 kabulü Linux'a özgü regresyonu önlemez: 200 ms tabana karşı 2 s aday diğer kapılar geçtiğinde yeşil olabilir ve insan incelemesi gerektirir. Step/aggregate summary, warning, özgün raw ve hash bağlı receipt bu farkı gösterir; M5 startup/jobs ve gerçek Linux raw kapıları zorunlu kalır.

İşi teslim eden ajan/maintainer, son incelenen kaynak kapsamının CI raw ve receipt'ini 90 günlük artifact'tan indirip özgün byte/hash'leriyle kalıcı gzip/manifest/indekse alır ve kabul raporuna bağlar. Arşiv hatasında kabul açık kalır. Son belge commit'i veya kullanıcı merge'ünün aynı kaynakla ürettiği ek koşu için açık takip kaydedilir; mevcut veya sonraki yetkili dalda sonraki kabul/merge önerisinden önce ve artifact süresi dolmadan arşivlenir. İptal tamamlanmış ölçüm sayılmaz; var olan dosya korunur, yoksa run/adım ve eksik kanıt açık yazılır. [Kanonik saklama kuralı](docs/decisions/0019-reference-startup-performance.md#linux-tanısının-görünürlüğü-ve-kalıcı-saklanması) geçerlidir. Yeşil aggregate insan saklama sorumluluğunu tamamlamaz.

## Doğrulama seçimi

Komutlar yukarıdaki kanonik listededir. Bu tablo yerelde hangisinin neden gerektiğini belirler; CI korunan dala giren her değişiklikte kendi tam kapısını çalıştırır.

| Değişiklik | Yerelde gerekli kanıt |
|---|---|
| Yalnız açıklama/link/durum | `check-docs.py`, `git diff --check`; kod testi eklenmez |
| Skill, alias, iş kartı metadata veya ajan rehberi | Belge kontrolü + `check-agent-guides.py`; yeni/değişen helper için anlamlı negatif test ve lint/type |
| Runtime/config/CLI/API | Anlamlı unit/contract/integration, Ruff format/lint ve strict mypy; kullanıcı sözleşmesi ve belge güncel |
| Paket/bağımlılık/yerleşim veya yayın girdisi | Yukarıdakilere build, arşiv izin listesi ve temiz kurulum/import kökeni; wheel ile sdist ayrımı |
| Import/başlangıç veya aktarım/worker yolu | İlgili performans standardı ve veri doğruluğu; ortam/örnek/ilk süreç ve p95 kayıtlı |

Rehber denetimi Git checkout'undaki canonical skills/Claude alias'larını, tekil faz ID'lerini, kart metadata/bölümlerini ve işe başlanabilecek durumların bağımlılıklarını kontrol eder. `verified` için teslim alanları aranır; kanıtın doğruluğu ve kabulü karşılaması review gerektirir. Doğal dil skill seçimi, inceleme kalitesi veya live EVREN desteği bu araçla kanıtlanmaz. Ajan kullanımı [katalogda](.agents/README.md); anlamlı yeni işin hazır olma koşulu [roadmap'tedir](docs/roadmap/README.md#hazır-iş-paketi). Ajan materyali sdist'te geliştirme kaynağıdır; Claude alias'ları yalnız checkout'ta, wheel ise yalnız runtime'dır.

## İnceleme ve lisans

Ham ölçümler, sabit test vektörleri ve kabul raporları [kanıt standardına](docs/standards/research-evidence.md) göre ayrılır. `docs/research/raw/` içindeki gzip baytları normal kod review'üne verilmez; manifest/indeks, ölçüm betikleri ve test vektörleri incelenir. CI arşiv ve özgün JSON hash'lerini, bütün örneklerden türetilen özeti ve indeksi denetler. Arşivler source package'a girmez; Git checkout'unda kalır. Önceki fazların kök dizindeki kayıtları geriye dönük taşınmaz; yeni büyük üretilmiş çıktılar bu arşiv akışını kullanır.

PR; problemi, kullanıcı sonucunu, sözleşme etkisini ve gerçek doğrulamayı açıklamalı. Referans projelerin mimari kararları Yörünge'ye otomatik taşınmaz. Devralınan kodun lisans ve köken bildirimleri korunur; katkılar [MIT](LICENSE) altında sunulur. Güvenlik bildirimi için [SECURITY.md](SECURITY.md).
