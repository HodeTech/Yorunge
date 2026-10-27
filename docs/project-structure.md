# Proje yapısı

**Güncellendi:** 2026-10-27. **Durum:** Offline çekirdek ve P01-2 yerel kimlik/state/config yerleşimi uygulanmıştır; P01-3 hazırlıktır.

```text
src/yorunge/
  __init__.py             # Hafif paket kimliği ve sürüm
  api.py                  # CLI ile ortak kullanım senaryoları
  domain/                 # Tipli context, seçim, capability, plan, sonuç ve hata
  application/            # Araç/ortam seçim politikası ve çevrimdışı plan
  adapters/files.py       # Sınırlı TOML/YAML/JSON okuma ve doğrulama
  adapters/state*.py      # SQLite yaşam döngüsü, validation ve immutable migration
  adapters/identity.py    # İşlemsel credential kimliği/nesli
  adapters/maintenance.py # Açık reset/restore/recover
  adapters/local_files.py # Private dosya/kilit/deadline ve platform sınırı
  adapters/configuration.py # Atomik config yazımı/backup; diagnostics ayrı adaptörde
  cli/                    # Argparse; metin/JSON render ve çıkış kodu
tests/
  unit/                   # Öncelik, seçim, plan bağları
  contracts/              # Şema, hatalı girdi, sır ve dosya sınırları
  integration/            # Gerçek kurulmuş konsol girişi ve API tutarlılığı
  fixtures/guards/        # Alt süreçte ağ/DB/keychain/ML ve keşif engeli
scripts/                  # Build/temiz kurulum, belge ve performans kontrolleri
examples/                 # Küçük sentetik profil ve reçete
.github/workflows/        # Gerçek kontrolleri çalıştıran CI tanımı
.agents/skills/           # Kanonik görev prosedürleri ve Codex UI metadata'sı
.claude/skills/           # Aynı skill klasörlerine göreli alias; içerik kopyası yok
docs/roadmap/tasks/       # Yalnız yakın/aktif işlerin ayrıntılı kabul kartları
```

`pyproject.toml` paket metadata'sını, `uv.lock` geliştirme/runtime çözümünü tutar. `domain` CLI, dosya adaptörü veya haricî araç import etmez. SQLite/identity/config adaptörleri P01-2'de gerçek tüketicileriyle uygulanmıştır. Henüz uygulanmayan HTTP, cache/execution ve araç adaptörleri için boş iskelet oluşturulmaz. Mantıksal sahiplik [modül haritasında](modules/README.md), bağımlılık yönü [mimaride](architecture/overview.md) tanımlıdır.

[Ajan kataloğu](../.agents/README.md) repo geliştirme girdisidir; runtime bağımlılığı değildir. Canonical `.agents` materyali sdist'e seçilir; wheel ve Claude alias symlink'leriyle karıştırılmaz. İstemci/global ayar veya otomatik izin hook'u eklenmez.

Root'ta README, MIT, katkı/güvenlik/topluluk belgeleri ve ajan rehberi; `docs` altında kanonik ürün/standart/mimari/karar/referans/yol haritası/kanıt belgeleri bulunur. Her belge alt dizininin README'si giriş noktasıdır.

`data`, `models`, `artifacts`, `.yorunge` kullanıcı çalışma alanıdır. `.local`, `.venv`, `dist` yerel araç/kurulum/build çıktısıdır; kaynak depoya eklenmez. Dağıtım girdileri `pyproject.toml` izin listesinde açıkça seçilir; arşiv üyeleri ayrıca `scripts/verify-distributions.py` ile doğrulanır.
