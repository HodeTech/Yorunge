# Katkı rehberi

Yörünge'nin ilk çevrimdışı paket/CLI/API dilimi uygulanmıştır; P01 devam ediyor. Ürün kapsamını [product-scope.md](docs/product-scope.md), etkin işi [current.md](docs/roadmap/current.md) tanımlar.

## Çalışma akışı

1. İlgili kapsam maddesini, modülü, sözleşmeyi ve standardı okuyun.
2. İlgili iş kaydını veya yol haritası görevini belirleyin. Küçük belge düzeltmeleri ayrı iş kaydı gerektirmez.
3. Güncel `origin/development` üzerinden kısa ömürlü `feat/`, `fix/`, `docs/` veya `ci/` çalışma dalı açın. Normal PR hedefi `development`; varsayılan dal da `development` olur.
4. Bir değişiklikte tek bir sonucu somutlaştırın. Kullanıcı davranışı değişirse sözleşme ve kabul ölçütünü aynı değişiklikte güncelleyin.
5. İlgili doğrulamayı yapıp sonucu PR açıklamasına yazın. Çalıştırılmayan kontrolü başarılı göstermeyin.
6. Yeşil zorunlu kontroller ve çözülmüş inceleme konuşmaları sonrası **merge commit** ile birleştirin. Squash/rebase merge ve korunan dallara doğrudan push kullanılmaz.

`Master` release dalıdır; aynı deponun `development` dalından açılan aktarım PR'ını bakım sahibi birleştirir. Ajan `Master` birleştirmesi veya yayın yapmaz. İlk kurulum sırası, tek yazma yetkilisi nedeniyle sıfır zorunlu review seçimi ve tam koruma koşulları [Git/yayın standardında](docs/standards/git-release.md) tanımlıdır.

## Belge değişiklikleri

Türkçe açıklama, İngilizce dosya/kimlik adları, UTF-8/LF ve göreli bağlantılar kullanın. Her Markdown dosyasının bir H1 başlığı olmalı. Planlanan komutu çalışan örnek diye sunmayın. Dizine eklenen belgeyi o dizinin README'sine bağlayın. Bağlantıları, başlıkları, kod bloklarını ve mevcut durumla tutarlılığı denetleyin. [Belgeleme standardı](docs/standards/documentation.md).

## Geliştirme ve doğrulama

[Python](docs/standards/python.md), [test](docs/standards/testing.md), [güvenlik](docs/standards/security.md), [performans](docs/standards/performance.md) ve [hata/çıktı](docs/standards/error-handling-observability.md) standartları uygulanır. Python 3.11+ hedeflenir; yerelde macOS/arm64 + CPython 3.11.18 doğrulandı. Ubuntu/Python 3.11 CI tanımı gerçek PR ve dal koşularıyla doğrulanır; yerel kontrol uzak CI koşmuş sayılmaz.

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
uv build
.venv/bin/python scripts/verify-distributions.py --uv .local/tooling/bin/uv > dist/verification.jsonl
.venv/bin/python scripts/benchmark-startup.py --command .venv/bin/yorunge --output dist/startup.json
```

`--uv` için gerçekten kullanılan uv executable yolunu verin. `uv.lock` geliştirme/runtime sürümleri ve hash'lerini sabitler; build backend'i `pyproject.toml` içinde sabittir. İlk kurulum/build paket indirmek için ağ kullanabilir; uygulama ve test senaryoları çevrimdışıdır. `uv build` wheel'i sdist'ten üretir. Dağıtım denetimi üyeleri izin listesiyle kontrol eder, her arşivi ayrı temiz ortama kurar, import kökenini ve konsol komutunu depo dışından doğrular. Build çıktısı `dist/` altında Git dışında kalır.

Dağıtım denetimi bir wheel ve aynı sürümden bir sdist gerektirir. Ham üye adı kök kırpılmadan denetlenir; mutlak/traversal/kanonik olmayan yol, yinelenen ad, dosya/dizin çakışması, link ve özel dosya reddedilir. Sdist'in tek kökü arşiv adıyla, wheel metadata dizini dağıtım/sürümle eşleşir. `dist/verification.jsonl` her başarılı temiz kurulum için arşiv adı/SHA-256/üye sayısı/köken/smoke sonucu taşır; komutun başarısı ve iki kayıt birlikte tam kabul kanıtıdır. Hatalı koşunun kısmi kaydı başarı sayılmaz. CI aynı kayıtları iş günlüğünde gösterir.

ZIP adında Python'un NUL kırpmasından önceki özgün alan denetlenir. `uv` ile Python'un farklı ad seçmesine yol açan Unicode Path (`0x7075`) alternatif ad alanı ve bozuk extra metadata reddedilir; diğer düzgün metadata alanları korunur. Bu denetim bu deponun ürettiği paketler içindir, genel amaçlı arşiv çıkarıcı değildir.

Performans betiği her komut için ilk süreç süresini ayrı, üç ısınma sonrası en az 30 ayrı sürecin p95'ini ayrıca kaydeder. OS/disk cache'i boşaltmaz. Hedef aşılırsa sıfır dışı kodla çıkar. Belge kontrolü yalnız açıkça seçilmiş genel belge dizinlerini okur; site/doküman yayın sistemi henüz yoktur.

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

PR; problemi, kullanıcı sonucunu, sözleşme etkisini ve gerçek doğrulamayı açıklamalı. Referans projelerin mimari kararları Yörünge'ye otomatik taşınmaz. Devralınan kodun lisans ve köken bildirimleri korunur; katkılar [MIT](LICENSE) altında sunulur. Güvenlik bildirimi için [SECURITY.md](SECURITY.md).
