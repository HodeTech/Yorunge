# P01 ilk çevrimdışı dilim kabul kaydı

**Tarih:** 2026-10-27. **Sürüm:** `0.1.0.dev0` (yerel geliştirme, yayımlanmadı). **Kapsam:** P01-1 ve minimum P01-2/P01-3/ortak API alt kümesi. P01 bütünü tamamlanmadı.

## Çalışan kullanıcı sonucu

Kurulmuş `yorunge` komutu ve `yorunge.api` aynı yerel context → capability → seçim → plan → tipli sonuç akışını kullanıyor. TOML ve dar YAML doğrulanıyor; seçim kaynağı ve digest sonuçta korunuyor. Uygun LLM görevinde ForgeLM varsayılanı, açık alternatif, reçete/profil/çağrı önceliği ve native görevlerin bağımsızlığı sınandı. Kayıtlı Plan, profil yeniden okunmadan yükleniyor; değişmiş digest veya capability/engeller reddediliyor.

Başarılı planlama, `state=draft`, `executable=false`, `inputs_verified=false` ve eksik adaptör/uzak bağları gösteriyor. Model/veri dosyası okunmadı, eğitim çalıştırılmadı, uzak istek veya artefakt üretilmedi. `supported` yalnız yerel planlama politikası için kullanıldı. Genel EVREN/araç desteği ilan edilmedi.

## Yerel doğrulamalar

| Kontrol | Sonuç ve sınır |
|---|---|
| pytest | 87 test geçti; atlama/xfail yok. Unit, parser/error contract ve gerçek konsol subprocess integration |
| Negatif sözleşmeler | Bozuk/eksik dosya, yanlış tip/sürüm/alan, duplicate, YAML alias/tag/limit, JSON NaN/Infinity, bilinmeyen/uyumsuz araç, değişmiş/kurgulanmış plan |
| Sır ve yan etki | Sentetik credential değerleri çıktıya/hata/loga çıkmadı; named env okuması yasaklandı. CLI audit guard ağ/DB/alt süreç/keychain/ML kullanımını engelledi; yardım/sürüm config ve Pydantic/YAML importundan bağımsız |
| CLI/API | JSON zarf eşitliği, stdout/stderr ayrımı, uygulanmış 0/2 çıkış kodları, kurulmuş entrypoint ve import kökeni |
| Ruff/mypy | Format ve lint temiz; `src`/`scripts` strict mypy temiz |
| Belgeler | Genel belge izin listesinde H1, fence, yerel dosya/anchor ve özel sınır bağlantı denetimi; Mermaid görsel render testi yapılmadı |
| Build/kurulum | Wheel sdist'ten üretildi. Wheel ve sdist ayrı temiz venv'e, runtime sürümleri lock/hash ile kuruldu; `-I` import kökeni ve depo dışından yardım/sürüm/plan doğrulandı |
| Paket sınırı | Girdi izin listesi ve arşiv üye denetimi; yalnız genel kaynaklar. Wheel yalnız paket + dist-info; sdist açık kod/test/script/örnek/genel belge listesi |
| Bağımsız inceleme | Hizmet/ortam ayrımı, kanıtsız runtime durumu, IPv6 origin, seçenek kısaltması ve NUL dosya yolu bulguları düzeltildi; test eklendi |
| CI | İlk yerel kabulden sonra PR #1 Ubuntu/CPython 3.11.15 koşusunda 100 test ve bütün kontroller geçti; [canlı kayıt](branch-workflow-validation.md) |

Tekrar çalıştırılacak komutlar [CONTRIBUTING](../../CONTRIBUTING.md#geliştirme-ve-doğrulama) içindedir. Build çıktıları `dist/` altında kalır. Son arşiv kimliği/SHA-256 ve temiz kurulum sonuçları `dist/verification.jsonl` içinde üretilir; bu dosya build sonrası kanıttır, kaynak dağıtımının kendi hash'ini içine koymaz.

## Başlangıç ölçümü

Ortam: CPython 3.11.18, macOS 27.0.1 arm64, Apple M5 Max (`Mac17,6`), 36 GiB RAM, yerel APFS SSD. Kurulum: `uv 0.11.2`, lock'tan altı runtime bağımlılığı ve wheel'in ayrı venv'e kurulumu; editable paket ölçülmedi. Ölçüm sonrası `site-packages` disk kullanımı `du -sk` ile 9.884 KiB (yaklaşık 9,65 MiB); bytecode dahil, Python yorumlayıcısı ve geliştirme paketleri hariç. Profil sentetik ve 227 bayt. Ölçüm duvar saatiyle tam konsol sürecini kapsıyor; stdout yönlendirilmiş. Üç ısınma sonrası **her komut için 30 ayrı süreç**, p95 nearest-rank yöntemi.

| Yol | İlk süreç (ms) | Sıcak medyan (ms) | Sıcak p95 (ms) | Hedef | Durum |
|---|---:|---:|---:|---:|---|
| `--help` | 195,835 | 24,588 | 25,963 | ≤ 500 ms | Geçti |
| `--version` | 22,824 | 21,341 | 24,185 | ≤ 500 ms | Geçti |
| `context show` + TOML + JSON | 446,941 | 82,360 | 91,252 | ≤ 200 ms | Geçti |

[Ham ölçümler](p01-startup.json) 90 sıcak örneği ve ilk süreç sürelerini saklar. İlk süreç sütunu kurulumdan sonraki ilk komut çalıştırmasını gösterir; OS/disk önbelleği boşaltılmadı ve komutlar aynı venv'de sırayla ölçüldü. Fiziksel soğuk boot/soğuk disk sonucu değildir; sürüm komutu kendisinden önceki yardım çağrısının bytecode/cache faydasını görebilir. Bu sınır gizlenmeden sıcak başlangıç hedefi karşılandı. Yerel capability cache henüz yok; profil ölçümü cache ölçümü diye sunulmaz.

CLI/şema adaylarının kısa import deneyi ve seçimin gerekçesi [ADR-0008](../decisions/0008-offline-core-stack.md) içindedir. Benchmark betiği hedef aşımında hata kodu verir; hedefler değiştirilmedi.

## Kalan sınır ve sonraki iş

Gerçek EVREN/HTTP, credential kimliği/nesli/izin doğrulaması, capability cache/tazelik, SQLite operation/attempt/lease, execution/onay, gerçek ForgeLM/muadil adaptörleri, eğitim ve artefakt teslimi henüz planlandı. Aktarım RSS, eşzamanlılık ve ağ/deadline bütçeleri bu dilimde ölçülemez; ilgili fazlara aittir. İlk kabulden sonra Ubuntu/Python 3.11 CI kanıtı eklendi; diğer OS/Python sürümleri ve canlı hesap desteği doğrulanmadı.

Sıradaki somut iş P01-2'nin secret/context bağları ve anahtar değişim testleridir; ardından P01-3 capability cache/plan geçerliliği. [Etkin yol haritası](../roadmap/current.md).
