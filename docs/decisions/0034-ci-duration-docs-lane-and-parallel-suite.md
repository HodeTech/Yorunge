# ADR-0034: CI süresi — belge-only hat ve dosya bazlı paralel test yürütme

**Durum:** Accepted — [ADR-0019](0019-reference-startup-performance.md)’un “zorunlu kapılar” hükmünü belge-only küme için kısmen değiştirir (native ölçümler atlanır, referans doğrulayıcılar atlanmaz). Kullanıcı 2026-11-13 talimatıyla (belge-only PR’ların tam CI’ı beklememesi için “belge-only hızlı hat” seçeneğini seçti ve normal CI süresinin de aynı PR’da iyileştirilmesini istedi). **Tarih:** 2026-11-13. **İş:** CI (faz dışı altyapı). Ölçüm ve gerekçe: [CI süre profili](../research/ci-duration-profile.md).

## Bağlam

`core-checks` her PR olayında üç hücrenin tamamında 12.7 bin testi tek süreçte koşturur ve `offline-core` bunların hepsini ister. Son koşularda test adımı Linux 3.11’de 2.919–3.632 s, Linux 3.14’te 3.789–3.900 s, macOS’ta 2.398–3.189 s sürdü; Linux 3.11 işi 77 dakikaya (tavan 90) çıktı. P02-2 sonunda 6.600 test 1.026–1.342 s (0,16–0,20 s/test) iken bugün 12.781 test 2.919–3.632 s (0,23–0,28 s/test); P02-3’ün eklediği 6.181 test yaklaşık 0,3–0,4 s/test tuttu. Bu eğilim tavanı bir sonraki epikte aşabilir.

Üç sonuç ayrıca bu kararı gerektirdi:

- **Belge PR’ı da tam CI’ı bekliyordu.** `development` koruması `offline-core` ve `branch-policy` ister, strict’tir ve yönetici denetimi açıktır; yönetici bile check’ler yeşil olmadan birleştiremez ([Git/yayın standardı](../standards/git-release.md)).
- **Belge değişikliği testi kırabilir.** 45 test dosyası belge yoluna kod satırında başvurur (çalışma zamanında okur) (referans sözleşmeleri belgeye karşı sınanır, kanıt dizini, ajan rehberleri, indirme referansının “Sınır adları” paragrafı). P02-3’te geri tırnaklı iki ifade bir kill testinin ayrıştırıcısını kırdı. Bu yüzden “belge-only PR testsiz olabilir” doğru değildir; belgeyle ilgili testler çalışmalıdır.
- **İş seviyesinde atlama denenmiş ve geri çekilmiştir.** PR #12’de dinamik aggregate adı ve metadata-only hücre atlamalarıyla GitHub merge kutusu zorunlu `offline-core`u “Expected” gösterip birleştirmeyi engelledi; GitHub’ın seçim algoritması kesin saptanmadı, gözlem dinamik ad ve iş seviyesinde atlamayla uyumludur ([kayıt](../research/p02-0-implementation-validation.md#sonar-ve-native-merge-kapısı-takibi)).

Test süresi profili (269 dosya, 22.088 süre kaydı; ayrıntı [profil kaydında](../research/ci-duration-profile.md)): yük düz dağılıyor — en büyük dosya toplamın %5,9’u, ilk 25 dosya %53; dosya bazlı çizelgeleme 4 işçide ideal 4,00× hızlanma verir ve alfabetik sıra bile yalnız +%3,9 sapar. Fixture `setup` süresi toplamın %29’u (en büyük kalem `test_jobs_benchmark.py`, 44 kurulumda 238 s).

## Karar

### 1. Belge-only hat

Hücreler, iş adları, `needs` ve `offline-core` **değişmez**; yalnız adım koşulları ve geçit değişir (PR #12’nin hatası iş seviyesinde atlama ve dinamik addı).

- Her hücre, birleşim checkout’unun ilk ebeveyninden (hedef dal ucu) `scripts/ci_changes.py` kopyasını alıp **onu** çalıştırır: bir PR sınıflandırıcıyı değiştirerek kendini belge-only ilan edemez (sınıflandırıcıyı değiştirmek zaten belge değişikliği değildir ve tam koşuyu seçer). Sınır: PR’ın kendi `checks.yml`i de çalıştığından, workflow’u değiştirebilen kötü niyetli bir PR `docs_only`yi sabitleyebilir; bu risk bu karardan önce de vardı (workflow PR’ın kendisinde tanımlıdır) ve inceleme ile `.github` değişikliklerinin belge sayılmamasıyla sınırlanır. Sınıflandırıcı hedef dalda yoksa, bozuksa ya da `true`/`false` dışında bir şey basarsa sonuç `false`tur (tam koşu).
- **Belge**, yalnızca kökteki `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `AGENTS.md`, `CLAUDE.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `docs/` ve `.agents/` altındaki yollardır. `src`, `tests`, `scripts`, `.github`, `examples`, `pyproject.toml`, `uv.lock`, `LICENSE` ve diğer her yol belge değildir. Belge ağaçlarının altındaki **çalıştırılabilir dosyalar** (`.py`, `.sh`, `.bash`, `.js`, `.mjs`, `.ts`; örneğin `docs/research/probes/**/pilot.py`, hash’i sabitlenmiş ve bir test tarafından çalıştırılır) belge değil koddur. Boş değişiklik kümesi, denetim karakteri (NUL, satır sonu, CR, kaçış) ya da ters eğik çizgi içeren yollar, kaçışlı/ters eğik çizgili/`..` içeren yazımlar, mutlak yollar ve büyük/küçük harf farkıyla yazılmış adlar belge sayılmaz. Yeniden adlandırma silme + ekleme olarak görülür (kaynaktan belgeye taşınan dosya kaynak değişikliğidir).
- Yalnız `development`’a açılan `pull_request` olayı belge-only olabilir; `Master` hedefi, push ve manuel çağrı her zaman tam koşudur (post-merge CI tam kalır).
- Belge-only kümede her hücre statik kontrolleri (format/lint/tip/belge/ajan rehberi/kanıt `verify`), dağıtım doğrulamasını (sdist belge izin listesi belgeye bağlıdır) ve **belgeye başvuran testleri** koşturur. Seçim `ci_changes.py docs-tests` ile yapılır: kod satırında `docs/`, belge dosyası adı veya `.md` geçen ya da belge okuyan bir script’in (aynı tarama ile bulunur, doğrudan okuyucular) adını anan her test dosyası seçilir (yorum satırı saymaz); belgeye başvuran bir yardımcı/fixture/`conftest`/`__init__.py` varsa, seçilen bir ad kabuk bölünmesine uygun düz bir ad değilse, seçim boşsa ya da seçim komutu hata verirse **tüm** `tests` koşar. Linux 3.11’de beş **referans doğrulayıcı** (`verify-startup/jobs/dataset/upload/download-reference`) de koşar: arşivlenmiş referanslar belgedir ve katalog tutarlılığını denetleyen `verify` onların bütçe anlamını doğrulamaz. Atlanan, yalnız kod bağlı **native ölçümlerdir** (startup tanısı, raw stream, upload/download native bütçeleri); belge değişikliği kaynak haritasını değiştirmez. Belge-only hücrelerin `ci-environment.json` kaydı bütçe kapsamlarını `documentation_lane` diye yazar (çalışmayan ölçümü iddia etmez).
- `offline-core` hücrelerin `docs_only` çıktısını okur: üçü de aynı ve `true`/`false` olmak zorundadır; eksik/karışık/bozuk iddia, herhangi bir hücrenin başarısızlığı ya da atlanması geçidi düşürür. “Atlanan hücre yeşil sayılmaz” kuralı korunur; belge-only kümede hücreler atlanmaz, koşar.

Belgeye başvuran her testin bunu kod satırında belirtmesi **sözleşmedir**; `test_ci_changes.py` depodaki bütün test dosyalarını sözdizimi ağacıyla (düzenli ifadeden bağımsız) tarayıp belge yolu sabiti içeren her dosyanın seçimde olduğunu doğrular.

### 2. Dosya bazlı paralel test yürütme

Tam suite `pytest -n auto --dist loadfile` ile koşar (CPU başına bir işçi; bütün dosya tek işçide, modül fixture’ları dosya başına kalır). Seçilen araç `pytest-xdist` (MIT, pytest-dev) ve `execnet`tir; yalnız geliştirme grubuna girer ve `uv.lock` hash’lerine bağlıdır; wheel içeriği ve runtime bağımlılıkları değişmez (sdist yalnız `pyproject.toml` ve `uv.lock` satırlarını taşır). Ön koşul: bütün işçilerin **aynı test kimliklerini** toplaması; parametre değeri olarak `uuid4()` kullanan iki test sabit değerlere çevrildi (aksi hâlde xdist toplama aşamasında durur). `-n` yerel varsayılan değildir (`addopts`ta yok): geliştirici tek süreçle de koşabilir.

### 3. Görünürlük

Her koşu en yavaş 25 testi (`--durations=25`) yazar; bir sonraki iyileştirme ölçüme dayanır.

## Değerlendirilen alternatifler

- **Maintainer/yönetici bypass** (ruleset bypass actor, `enforce_admins` kapatma): politika bypass tanımlamaz; GitHub bunu “yalnız belge PR’ı” diye kısıtlayamaz ve ajan ile kullanıcı aynı GitHub kimliğini paylaştığından yalnız ajan yönergesiyle ayrılır. Reddedildi.
- **İş seviyesinde atlama / `paths-ignore`:** PR #12’de merge kutusunda zorunlu check “Expected” kaldı; bu karar iş adlarını ve `needs`i korur.
- **Belge-only’yi testsiz yapmak:** belge testleri kırabilir (yukarıda). Reddedildi.
- **Kendi çizelgeleyicimiz** (dosya başına süreç): bağımlılık eklemez ama bakım yükü ve özet/çıktı birleştirme kodu getirir; xdist standart ve bakımlıdır.
- **Yüksek maliyetli bütçe adımlarını ayrı işe almak:** `offline-core` bağımlılık listesini ve “testler başarılıysa ölçülür” sırasını değiştirir (PR #12 riski); ayrıca ölçümler sessiz makine ister. Ertelendi.
- **`TMPDIR`i tmpfs’e almak:** fsync’i ve dosya sistemi anlamını (ext4’ün inode’u hemen geri vermesi gibi) gizler; bu oturumda bir testin yalnız ext4’te düşmesi bunun risklerini gösterdi. Reddedildi.
- **Fixture `setup` iyileştirmeleri** (örneğin `test_jobs_benchmark.py`): ölçülmüş ama bu kararın dışında; ayrı iş olarak profil kaydında listelidir.

## Sonuçlar ve riskler

- `.github/workflows/checks.yml`, `scripts/` ve `tests/` kaynak bağlı M5 referans haritasındadır (`scripts/benchmark-jobs.py` workflow baytlarını da özetler): bu değişiklik `-8` referans serisini gerektirir ve PR bu seriyle birlikte teslim edilir. **Geri alma da aynı bedeli taşır.**
- **Paralellikte kararsızlık riski ölçüldü:** Linux’ta (4 CPU’ya sabitlenmiş laboratuvar) CPU’dan fazla işçi (6) 22 testin ürünün 5 sn durum bütçesini aşarak yalnız paralelde düşmesine yol açtı; CPU sayısına eşit işçi (4) tam suite’i 3,7× hızlandırdı ve tek süreç temelinde yeni düşen test üretmedi (bilinen `test_guarded_large_put…truncated_reset` flake’i ve bir ortam testi hariç; ayrıntı [profil kaydında](../research/ci-duration-profile.md#yerel-xdist-denemesi)). Bu yüzden `-n auto` (CPU başına bir işçi) seçildi, fazlası seçilmedi. Hâlâ gerçek CI’ın sonucu esastır: bilinen flake paralelde daha sık düşebilir. Başarısızlığı gizlemek için otomatik yeniden deneme yoktur; geri alma bir PR’dır (aşağıda).
- **Merge kutusu doğrulaması:** API başarısı native merge kabulünü tek başına kanıtlamaz ([P02-0 kaydı](../research/p02-0-implementation-validation.md#sonar-ve-native-merge-kapısı-takibi)). İlk gerçek belge-only PR’da `offline-core` ve merge düğmesi **kullanıcı tarafından** birlikte doğrulanır; sorun görülürse belge-only hat bu ADR’nin geri alma bölümüyle kapatılır.
- Sınıflandırıcı hatası her zaman tam koşuya düşer (güvenli yön); yanlış “belge-only” üretmesi için kodun belge yoluna taşınması gerekir ve bu yollar yukarıdaki sözleşmeyle sınırlıdır.
- Bu karar ürün API/wire, secret, onay/dispatch latch veya model doğrulama kurallarını değiştirmez; yayın ve `Master` kapıları aynıdır.

## Geri alma

Belge-only hat: `change-set` adımı ve koşulları kaldırılır ya da çıktısı sabit `false` yapılır; paralellik: `-n` bayrakları kaldırılır. İş adları değişmediğinden koruma ayarı dokunulmaz kalır, ama workflow ve onu sabitleyen sözleşme testleri (`test_ci_matrix.py`, `test_ci_docs_lane.py`) değiştiğinden geri alma bir PR’dır ve yeni bir kaynak bağlı referans serisi (yeniden ölçüm) ister; “tek satırlık” geri alma yoktur.
