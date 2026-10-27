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

## P01-1 kapanış doğrulaması

**Tarih:** 2026-10-27. [P01-1a kartı](../roadmap/tasks/p01-1a-core-acceptance-hardening.md) kullanıcı onayıyla ilk teslimin hata ve dağıtım kabulünü sağlamlaştırır. Yukarıdaki 87/100 test ve ilk başlangıç ölçümü tarihsel sonuçtur; bu bölüm sonraki kapanış kanıtını taşır. Yeni HTTP, state, secret çözümleme veya yürütme yeteneği eklenmedi.

Bozuk YAML scalar literal ve scalar/mapping düğüm türü, C0/DEL/C1 manifest/URL karakterleri ve boş userinfo için gerçek dosya/API/CLI regresyonları eklendi. Geçersiz reçete kararlı `invalid_recipe`; konsol çıkış 2, boş stdout ve tek güvenli JSON hata kaydı üretir. Geçerli Unicode referans ve standart scalar tag desteği korunur; YAML mapping-to-scalar uyumluluk kısayolunun reddi [referansta](../reference/configuration.md) açıklanır. Capability sorgusunda uyumsuz sonuç ile plan hazırlamada hata ayrımı korunur.

Yerel kontrol: **404 pytest geçti**, atlama/xfail yok; 59'u gerçek sentetik ZIP/tar arşiv senaryosudur. Format/lint/strict mypy, 86 genel Markdown, altı skill/iki kart ve lock kontrolü temiz. Ham arşiv üye adı kök kırpılmadan doğrulanır; traversal/mutlak/kanonik olmayan yol, link/özel üye, duplicate ve dosya/dizin çakışması reddedilir. Tek sdist kökü ve dağıtım/sürüm eşleşmesi denetlenir. ZIP özgün adındaki NUL ve Python/uv arasında alternatif ad seçtiren Unicode Path extra alanı reddedilir; diğer düzgün metadata korunur. Gerçek wheel (17 üye) ve sdist (130 üye) ayrı temiz venv'lerde lock/hash runtime bağımlılıklarıyla kuruldu; depo dışından import kökeni/konsol/plan geçti. Son build'in arşiv kimliği ve SHA-256'sı `dist/verification.jsonl` içinde üretilir; belge/kaynak değişince sdist hash'i ve üye sayısı yeniden ölçülür.

Başlangıç ölçümü: aynı macOS 27.0.1 arm64 / CPython 3.11.18 referans makinede, wheel'den ayrı temiz venv'e kurulum; editable değil. Profil 227 bayt, üç ısınma ve her komut için 30 ayrı süreç. İlk süreç/OS cache sınırı yukarıdakiyle aynıdır; bu fiziksel soğuk boot ölçümü değildir. [Ham kapanış ölçümleri](p01-1a-startup.json).

| Yol | İlk süreç (ms) | Sıcak medyan (ms) | Sıcak p95 (ms) | Hedef | Durum |
|---|---:|---:|---:|---:|---|
| `--help` | 205,008 | 25,824 | 27,129 | ≤ 500 ms | Geçti |
| `--version` | 25,091 | 25,486 | 26,266 | ≤ 500 ms | Geçti |
| `context show` + TOML + JSON | 401,901 | 89,434 | 92,807 | ≤ 200 ms | Geçti |

İki adım da iki yeni bağımsız review turuyla tamamlandı; mapping/timestamp, ZIP NUL ve alternatif Unicode ad bulguları giderilip yeniden doğrulandı. Son ZIP düzeltmesi ek yeni bağımsız reviewer ile son kaynak build'inde doğrulandı. PR incelemesindeki test hata kapsamı/assertion ve izin listesi okunurluğu bulguları `016d2c3` ile giderildi; 404 test ve iki temiz kurulum yeniden geçti. Kullanıcı [PR #4](https://github.com/HodeTech/Yorunge/pull/4)'ü 2026-10-27 tarihinde [3d3c86b merge commit'i](https://github.com/HodeTech/Yorunge/commit/3d3c86bb623df9e5ce81a01583e7585431cf74da) ile development'a aldı. Son PR head'inde `offline-core`, `branch-policy`, SonarCloud, Sourcery ve CodeRabbit başarılı; [merge sonrası CI](https://github.com/HodeTech/Yorunge/actions/runs/40489316036) test/build/temiz kurulum/başlangıç kapılarını tekrar geçti. P01-1/P01-1a kapanışı tamamlandı; tam teslim kaydı karttadır. Canlı EVREN, başka OS/Python veya ürün yayını bu sonuçlarla doğrulanmış sayılmaz.

## Kalan sınır ve sonraki iş

Gerçek EVREN/HTTP, credential kimliği/nesli/izin doğrulaması, capability cache/tazelik, SQLite operation/attempt/lease, execution/onay, gerçek ForgeLM/muadil adaptörleri, eğitim ve artefakt teslimi henüz planlandı. Aktarım RSS, eşzamanlılık ve ağ/deadline bütçeleri bu dilimde ölçülemez; ilgili fazlara aittir. İlk kabulden sonra Ubuntu/Python 3.11 CI kanıtı eklendi; diğer OS/Python sürümleri ve canlı hesap desteği doğrulanmadı.

Sonraki işin kesin kapsamı ve state/credential bağımlılık sırası [etkin yol haritasında](../roadmap/current.md) tutulur; tarihsel kabul kaydı iş sırasının ikinci kaynağı değildir.
