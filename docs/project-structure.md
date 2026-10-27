# Proje yapısı

**Güncellendi:** 2026-10-27. **Durum:** İlk çevrimdışı kaynak ve test yerleşimi uygulanmıştır.

```text
src/yorunge/
  __init__.py             # Hafif paket kimliği ve sürüm
  api.py                  # CLI ile ortak kullanım senaryoları
  domain/                 # Tipli context, seçim, capability, plan, sonuç ve hata
  application/            # Araç/ortam seçim politikası ve çevrimdışı plan
  adapters/files.py       # Sınırlı TOML/YAML/JSON okuma ve doğrulama
  cli/                    # Argparse; metin/JSON render ve çıkış kodu
tests/
  unit/                   # Öncelik, seçim, plan bağları
  contracts/              # Şema, hatalı girdi, sır ve dosya sınırları
  integration/            # Gerçek kurulmuş konsol girişi ve API tutarlılığı
  fixtures/guards/        # Alt süreçte ağ/DB/keychain/ML ve keşif engeli
scripts/                  # Build/temiz kurulum, belge ve performans kontrolleri
examples/                 # Küçük sentetik profil ve reçete
.github/workflows/        # Gerçek kontrolleri çalıştıran CI tanımı
```

`pyproject.toml` paket metadata'sını, `uv.lock` geliştirme/runtime çözümünü tutar. `domain` CLI, dosya adaptörü veya haricî araç import etmez. Henüz uygulanmayan HTTP, SQLite, araç/execution adaptörleri ve alan modülleri için boş iskelet dizinleri oluşturulmadı. Mantıksal sahiplik [modül haritasında](modules/README.md), bağımlılık yönü [mimaride](architecture/overview.md) tanımlıdır.

Root'ta README, MIT, katkı/güvenlik/topluluk belgeleri ve ajan rehberi; `docs` altında kanonik ürün/standart/mimari/karar/referans/yol haritası/kanıt belgeleri bulunur. Her belge alt dizininin README'si giriş noktasıdır.

`data`, `models`, `artifacts`, `.yorunge` kullanıcı çalışma alanıdır. `.local`, `.venv`, `dist` yerel araç/kurulum/build çıktısıdır; kaynak depoya eklenmez. Dağıtım girdileri `pyproject.toml` izin listesinde açıkça seçilir; arşiv üyeleri ayrıca `scripts/verify-distributions.py` ile doğrulanır.
