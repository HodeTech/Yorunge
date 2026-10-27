# ADR-0008: İlk çevrimdışı dilimin paket ve şema seçimi

**Durum:** Accepted — bu dilimde uygulandı. **Tarih:** 2026-10-27.

## Bağlam

İlk teslim çalışan CLI/API, strict yerel girdi ve ölçülen başlangıç gerektiriyor. HTTP veya eğitim henüz kullanılmıyor. Aday paketleri kurmak tek başına ihtiyaç kanıtı değil; daha az bağımlılık ve ortak doğrulama dengelenmeli.

## Karar

Python 3.11+, `src/yorunge`, Hatchling 1.30.1 ve `yorunge` konsol girişi kullanıldı. CLI standart `argparse`; çıktı düz metin veya JSON. Pydantic 2.14.1 strict/extra-forbid/sürümlü modelleri ve tipli sonucu sağlıyor. PyYAML 6.0.3 SafeLoader yalnız sınırlı reçete şemasını okuyor; duplicate, alias/anchor, özel tag, aşırı boyut/derinlik/düğüm reddediliyor. TOML standart `tomllib` ile okunuyor. HTTP, Rich, keychain ve eğitim bağımlılığı eklenmedi.

`uv 0.11.2`, `uv.lock`, pytest/Ruff/mypy geliştirme ortamını sabitliyor. Runtime alt sınırları test edilen sürümler; başka sürüm/OS desteği ayrıca kanıt ister. Backend doğrudan sürüme sabit; runtime/dev çözümü lock/hash ile korunur, build araçlarının tüm transitif bağımlılıkları için ayrı hash kilidi henüz yoktur.

## Deney ve alternatifler

CPython 3.11.18/macOS arm64 üzerinde her aday için 12 ayrı import sürecinin medyanı: `argparse` 14,45 ms, Click 8.5.0 27,18 ms, Typer 0.27.3 35,81 ms; `dataclasses` 22,94 ms, Pydantic 30,45 ms, PyYAML 20,72 ms. Bu küçük deney tam komut/özellik kıyası değildir. Dar komut ağacı `argparse` ile karşılanıyor; Typer/Click/Rich ek faydası bu dilimde maliyeti karşılamadı. Dataclass tek başına dış verinin strict doğrulamasını sağlamıyor; elle ikinci şema sistemi kurmamak için Pydantic seçildi. Şema/YAML importları yardım/sürümden sonra yapılıyor. Tam komut ölçümü [kabul kaydında](../research/p01-core-validation.md).

Resmî kaynaklar (erişim 2026-10-27; belge kanıtı, dış hizmet testi değildir): [argparse](https://docs.python.org/3.11/library/argparse.html), [Pydantic strict mode](https://pydantic.dev/docs/validation/latest/concepts/strict_mode/), [PyYAML SafeLoader](https://pyyaml.org/wiki/PyYAMLDocumentation), [uv kilitleme/senkronizasyon](https://docs.astral.sh/uv/concepts/projects/sync/). Güvenli YAML yükleyici tek başına duplicate/alias sınırı sağlamadığından ek denetimler uygulandı.

## Sonuçlar

Planlama başarı sonucu, eğitim/yürütme başarısı değildir. Adaptör yokluğu açık engeldir. İlk plan biçimi yalnız offline `draft` taşır; tam yürütme/onay planı ileride ayrı geçerlilik koşulları gerektirir. Yerel istemci ile uzak hizmet kimliği ayrıdır: veri/LLM istemci istekleri `local`, yönetilen görsel eğitim `evren-managed` ortamındadır. Bu karar HTTP/SQLite veya gerçek araç paketini kesinleştirmez.
