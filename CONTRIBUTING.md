# Katkı rehberi

Yörünge'nin ilk çevrimdışı paket/CLI/API dilimi uygulanmıştır; P01 devam ediyor. Ürün kapsamını [product-scope.md](docs/product-scope.md), etkin işi [current.md](docs/roadmap/current.md) tanımlar.

## Çalışma akışı

1. İlgili kapsam maddesini, modülü, sözleşmeyi ve standardı okuyun.
2. İlgili iş kaydını veya yol haritası görevini belirleyin. Küçük belge düzeltmeleri ayrı iş kaydı gerektirmez.
3. Mevcut varsayılan daldan kısa ömürlü bir çalışma dalı açın. İlk boş repo `Master` dalıyla klonlandı; uzaktaki dal politikası doğrulanmadan `main` veya `development` varsaymayın.
4. Bir değişiklikte tek bir sonucu somutlaştırın. Kullanıcı davranışı değişirse sözleşme ve kabul ölçütünü aynı değişiklikte güncelleyin.
5. İlgili doğrulamayı yapıp sonucu PR açıklamasına yazın. Çalıştırılmayan kontrolü başarılı göstermeyin.

## Belge değişiklikleri

Türkçe açıklama, İngilizce dosya/kimlik adları, UTF-8/LF ve göreli bağlantılar kullanın. Her Markdown dosyasının bir H1 başlığı olmalı. Planlanan komutu çalışan örnek diye sunmayın. Dizine eklenen belgeyi o dizinin README'sine bağlayın. Bağlantıları, başlıkları, kod bloklarını ve mevcut durumla tutarlılığı denetleyin. [Belgeleme standardı](docs/standards/documentation.md).

## Geliştirme ve doğrulama

[Python](docs/standards/python.md), [test](docs/standards/testing.md), [güvenlik](docs/standards/security.md), [performans](docs/standards/performance.md) ve [hata/çıktı](docs/standards/error-handling-observability.md) standartları uygulanır. Python 3.11+ hedeflenir; yerelde macOS/arm64 + CPython 3.11.18 doğrulandı. Ubuntu/Python 3.11 CI tanımı eklenmiştir; yerel kontrol CI koşmuş sayılmaz.

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
uv build
.venv/bin/python scripts/verify-distributions.py --uv .local/tooling/bin/uv
.venv/bin/python scripts/benchmark-startup.py --command .venv/bin/yorunge --output dist/startup.json
```

`--uv` için gerçekten kullanılan uv executable yolunu verin. `uv.lock` geliştirme/runtime sürümleri ve hash'lerini sabitler; build backend'i `pyproject.toml` içinde sabittir. İlk kurulum/build paket indirmek için ağ kullanabilir; uygulama ve test senaryoları çevrimdışıdır. `uv build` wheel'i sdist'ten üretir. Dağıtım denetimi üyeleri izin listesiyle kontrol eder, her arşivi ayrı temiz ortama kurar, import kökenini ve konsol komutunu depo dışından doğrular. Build çıktısı `dist/` altında Git dışında kalır.

Performans betiği her komut için ilk süreç süresini ayrı, üç ısınma sonrası en az 30 ayrı sürecin p95'ini ayrıca kaydeder. OS/disk cache'i boşaltmaz. Hedef aşılırsa sıfır dışı kodla çıkar. Belge kontrolü yalnız açıkça seçilmiş genel belge dizinlerini okur; site/doküman yayın sistemi henüz yoktur.

## İnceleme ve lisans

PR; problemi, kullanıcı sonucunu, sözleşme etkisini ve gerçek doğrulamayı açıklamalı. Referans projelerin mimari kararları Yörünge'ye otomatik taşınmaz. Devralınan kodun lisans ve köken bildirimleri korunur; katkılar [MIT](LICENSE) altında sunulur. Güvenlik bildirimi için [SECURITY.md](SECURITY.md).
