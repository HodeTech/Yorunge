# CI süre profili ve iyileştirme kaydı

**Tarih:** 2026-11-13. **Durum:** Ölçüm ve karar kaydı; karar [ADR-0034](../decisions/0034-ci-duration-docs-lane-and-parallel-suite.md). Bu belge uygulanmış performans garantisi değildir: yerel profil çekişmeli bir makinede alındı, CI sonuçları aşağıda ayrı satırlardır.

## Soru

PR #15 ve #16’da her CI koşusu bir saatten uzun sürdü, belge-only PR de aynı süreyi bekledi. Süre nereden geliyor, hangi iyileştirme ne kazandırır, hangisi güvenli?

## CI’da süre nereden geliyor (ölçülen)

| Hücre (son üç koşu) | Test adımı | Tüm iş |
|---|---|---|
| Linux / Python 3.11 | 2.919 s (merge koşusu), 3.605 s, 3.632 s | 1 sa 0 dk – 1 sa 17 dk |
| Linux / Python 3.14 | 3.789 s, 3.831 s, 3.900 s | 1 sa 2 dk – 1 sa 7 dk |
| macOS / Python 3.11 | 2.398 s, 2.992 s, 3.189 s | 40 – 57 dk |

Linux 3.11’de testlerden sonra seri çalışan ölçüm adımları ek ~14 dakika tutar (877 s): yerel upload bütçesi 407 s, indirme 80 s, startup tanısı 60 s, beş kaynak bağlı doğrulayıcı (her biri ~51 s, toplam ~255 s), dağıtım doğrulaması ~75 s. Bunlar sessiz makine ister ve “testler başarılıysa ölçülür” sırasına bağlıdır; bu kararın dışında bırakıldı.

Aynı kodda macOS koşuları arasında %33 fark vardır (2.398 s ve 3.189 s): paylaşımlı runner gürültüsü büyüktür.

**Eğilim.** P02-2 sonunda 6.600 test 1.026–1.342 s sürdü (0,16–0,20 s/test); şimdi 12.781 test 2.919–3.632 s (0,23–0,28 s/test). P02-3’ün eklediği 6.181 test yaklaşık 0,3–0,4 s/test tuttu: test sayısı 1,9 kat, süre yaklaşık 2,8–3,5 kat arttı. Linux 3.11 işi 90 dakikalık tavana 13 dakika uzaktır.

## Yerel profil (dosya bazlı)

Temiz klonda (`69efc8d`) tam suite altı kabukta (contracts+unit ve beş integration kabuğu) `--durations=0` ile koşuldu: 12.785 geçti, 1 atlandı. 271 test dosyasından 269’u ve 22.088 süre kaydı (çağrı+kurulum+temizlik) toplanıp dosya başına toplandı (dosya tablosu, en yavaş 40 test ve lab özeti [kalıcı kayıtta](evidence.md#p02-3-ci-duration-profile-20261113)); pytest 5 ms altındaki kayıtları yazmaz (`--durations-min` varsayılanı), iki dosya listede yoktur (büyük olasılıkla bütün kayıtları bu eşiğin altındadır). Altı süreç aynı anda koştuğundan **mutlak süreler CI’ya taşınmaz; oranlar taşınır**.

| Ölçü | Değer |
|---|---|
| Toplam ölçülen (çağrı 5.380 s, kurulum 2.185 s, temizlik 87 s) | 7.653 s |
| En büyük tek dosya | `test_upload_continuation_start.py` 451 s (%5,9) |
| İlk 25 dosya | toplamın %53’ü |
| Kurulum (`setup`) payı | %29 |
| En yavaş tek test | `test_real_cli_maximum_file_inventory_has_complete_distinct_graph` 125 s |
| En büyük kurulum kalemi | `test_jobs_benchmark.py`: 44 kurulumda 238 s (çağrılar 2 s) |

İlk 10 dosya: `test_upload_continuation_start` 451 s, `_stages` 307 s, `_lineage` 272 s, `test_jobs_benchmark` 240 s, `test_upload_resume_prepare` 224 s, `_resume_observation` 207 s, `_continuation_store_wide` 205 s, `_continuation_reconcile` 200 s, `test_operation_reconciliation` 176 s, `_continuation_start_r2` 173 s.

**Çizelgeleme benzetimi (ölçülen dosya maliyetleriyle):** dosya bazlı paylaşım, işçi sayısı kadar doğrusal ölçeklenir çünkü hiçbir dosya baskın değildir.

| İşçi | İdeal | Alfabetik sıra (xdist `loadfile` toplama sırası) | En ağır önce |
|---|---|---|---|
| 3 | 2.551 s | 2.592 s (+%1,6) | 2.551 s |
| 4 | 1.913 s | 1.988 s (+%3,9) | 1.913 s |

Alfabetik sıra bile ideale yakın olduğundan ağırlık dosyası/yeniden sıralama kancası eklenmedi.

**Kurulum maliyeti neden basit bir fixture düzeltmesi değil.** Temsilî ağır bir testin (`test_continuation_admission`) kurulumu boş makinede ~1,0 s; baskın kalem SQLite `execute` çağrıları (1.477 çağrı, 0,59 s: şema, migrasyon, yedek ve fsync). Aynı kurulum altı süreçlik yükte 2,3 s ölçüldü. Önceden kurulmuş bir durum dizinini kopyalayarak hızlandırmak her kopyada aynı kimlik dönemi (identity epoch) ve credential nesli demektir; kimliğin benzersiz olduğunu varsayan testler için sessiz bir risk olduğundan bu PR’da yapılmadı.

## Kararlar (ayrıntı ADR-0034’te)

1. **Belge-only hat.** Hücreler ve iş adları aynı kalır, adım koşulları ve geçit değişir; hedef dalın sınıflandırıcısı değişiklik kümesine karar verir; belgeyle bağlı test dosyaları (bu dalda 58) ve beş referans doğrulayıcı koşar, yalnız kod bağlı native ölçümler atlanır. Bir belge değişikliği testi gerçekten kırabilir: P02-3’te bir indirme referansı paragrafındaki geri tırnak, kill testinin sınır adı ayrıştırıcısını kırdı.
2. **Paralel test yürütme.** `pytest -n <vCPU − 1> --dist loadfile` (Linux 4 vCPU’da 3, macOS 3 vCPU’da 2; bütün dosya bir işçide). CPU’dan fazla işçi ölçümde bütçe aşımı üretti; `-n auto` kota (cgroup) altında CPU sayısından fazla işçi başlatır (laboratuvarda 18). İki testin `uuid4()` parametre değeri sabitlendi; xdist her işçide aynı test kimliklerini ister, ilk deneme toplama aşamasında bu yüzden durdu (iki testin üç satırı).
3. **Görünürlük:** `--durations=25`.

## Yerel xdist denemesi

Dört ölçüm, hepsi bu dalın testleriyle (12.957 test; belge-only hat testleri dahil). **Sonuç: işçi sayısı CPU sayısını aşmamalı; seçilen politika vCPU − 1’dir.** Aşağıdaki ölçümler CPU’ya eşit işçinin (4) yüklü laboratuvarda temiz geçtiğini ama iki işçide bile nadir düşüşler görüldüğünü, CPU’nun 1,5 katı işçinin (6) ise ürünün kendi bütçesini aşan 22 paralele özgü düşüş ürettiğini gösterir; bunlar tarihsel gözlemdir, yürütme önerisi değildir. `-n auto` önerilmez (kota altında CPU sayısından fazla işçi başlatır).

| Ortam | Koşu | Süre | Sonuç |
|---|---|---|---|
| macOS M5, 4 işçi (makine boş değildi) | tam suite | 1.698 s | 12.957 geçti, 1 atlandı, 0 düştü (xdist ile sinyal/fork testleri dahil) |
| macOS M5, 8 dosyalık ağır alt küme | tek süreç / 4 işçi | 412 s / 252 s (1,64×) | 494 geçti; tek süreçte yalnız 70 s kullanıcı + 34 s sistem CPU’su: süre CPU’da değil beklemede (CPU kullanımı %25) |
| Linux lab (Docker, overlayfs, **4 CPU’ya sabitlenmiş**), aynı alt küme | tek süreç / 3 / 4 / 6 / 8 işçi | 358 / 161 / 150 / 114 / 125 s | 494 geçti her seferinde |
| Linux lab, **tam suite** | önceki tek süreçli lab koşuları | 3.398–3.528 s | ortam kaynaklı ~120–180 düşen test |
| | 3 işçi | 1.255 s (2,8×) | tek süreç temelinde olmayan yeni düşen test: 1 (ortam) |
| | **4 işçi** | **932 s (3,7×)** | tek süreç temelinde olmayan yeni düşen test: 2 (bilinen `test_guarded_large_put…truncated_reset` flake’i ve bir ortam testi) |
| | 6 işçi (CPU’nun 1,5 katı) | 853 s (4,1×) | **22 test yalnız paralelde düştü** (tek süreçte geçtiler) |

**Laboratuvar düzeltmesi (umask).** Bu tablodaki Linux lab koşuları `docker exec`in varsayılan `umask 0000` değeriyle yapıldı; bu umask’ta birçok test xdist olmadan da düşer (dört dosyalık bir alt kümede 26 test, `umask 022` ile hepsi geçti) ve CI runner’ları `0022` kullanır. Tablo bu yüzden “tek süreç temelinde olmayan yeni düşen test” ölçütünü kullanır ve umask nedeniyle düşen testler (sayıları ölçülmedi; en az 26) paralelde sınanmamış sayılmalıdır. Bu nedenle tam suite `umask 022` ile ve seçilen işçi sayısıyla (3 işçi, 4 CPU’ya sabitlenmiş) iki kez yeniden koşuldu:

| Koşu (Linux lab, `umask 022`, 4 CPU, 3 işçi) | Süre | Sonuç |
|---|---|---|
| a | 1.188 s (19 dk 48 sn) | 12.981 geçti, 2 atlandı, **1 düştü** (`test_put_failure_never_accepts_or_replays_and_closes_source[changed_file]`: tek süreçte de düşer ve önceki tek süreçli lab temelinde vardı; CI’da geçiyor: lab dosya sistemine özgü) |
| b | 1.201 s (20 dk 0 sn) | 12.979 geçti, 2 atlandı, **3 düştü**: aynı lab testi ve bilinen P02-2 flake’i `test_guarded_large_put_accepts_full_reply_and_rejects_truncated_reset` (iki parametre; tek süreçli lab koşularında da ~%35 düşüyordu) |

İki koşuda paralele özgü yeni bir düşüş yoktur. Bu hâlâ kısa bir örnekleme (iki koşu); 4 işçi `umask 022` ile ölçülmedi.

6 işçili koşuda düşenler `test_upload_journal`, `test_capability_cache`, `test_maintenance`, `test_state` ve `test_unsupported_platform` dosyalarındaki durum deposu açan testlerdir; hata ürünün kendi 5 sn durum bütçesidir (“Yerel durum meşgul veya süre bütçesi doldu”): CPU’yu aşan işçi sayısı SQLite/fsync işlerini geciktirip bütçeyi aşıyor. Bütçeyi gevşetmek bir ürün kararıdır (ve bu kararın konusu değildir); işçi sayısını CPU sayısına eşitlemek bu sınıfı üretmedi. Alt kümede 6 işçi en hızlıydı (114 s), ama güvenilirlik hızdan önce gelir.

Ölçülen hız, test süresinin önemli bir kısmının CPU’da değil beklemede (alt süreç başlatma, TLS, SQLite) geçtiğini gösterir: 4 işçi 4 CPU’da 3,7× verdi.

**Beklenen CI etkisi (tahmin; ölçüm aşağıdaki CI satırında):** 3 işçili laboratuvar koşusu 1.190–1.200 s sürdü (tek süreçli lab: 3.400–3.530 s, 2,9×). Linux 3.11 test adımı ~3.600 s → ~1.250 s; iş ~77 dk → ~38 dk (ölçüm adımları ~14 dk seri kalır). macOS (2 işçi) ~3.000 s → ~1.600 s. Belge-only PR ~10–15 dk.

## CI denemesi

Bu PR’ın ilk CI koşusu ([43348860041](https://github.com/HodeTech/Yorunge/actions/runs/43348860041); hedef dalda `ci_changes.py` olmadığından **tam koşu**, işçi sayısı vCPU − 1: Linux 4 vCPU’da 3, macOS 3 vCPU’da 2) üç hücrede de başarılıdır:

| Hücre | Test adımı (önceki üç koşu → bu koşu) | Test sonucu | İş süresi (önce → şimdi) |
|---|---|---|---|
| Linux / Python 3.11 | 2.919–3.632 s → **1.349 s** (2,2–2,7×) | 13.007 geçti, 2 atlandı | 60–77 dk → **39 dk 58 sn** |
| Linux / Python 3.14 | 3.789–3.900 s → **1.088 s** (3,5×) | 13.007 geçti, 2 atlandı, 94 uyarı (bilinçli fork testleri) | 62–67 dk → **20 dk 13 sn** |
| macOS / Python 3.11 | 2.398–3.189 s → **1.847 s** (1,3–1,7×) | 13.011 geçti, 1 atlandı | 40–57 dk → **34 dk 47 sn** |

Tüm koşu **40 dakikada** bitti (önceki üç koşu 66–77 dk). Üç hücrede de paralele özgü bir düşüş görülmedi (bilinen P02-2 flake’i dahil hiçbir test düşmedi); bu tek koşudur ve bir güvence değil bir gözlemdir. Beş referans doğrulayıcı (`-8`) Linux 3.11’de geçti (her biri 59–63 s). Kritik yol artık Linux 3.11: testler 22,5 dk, ardından seri ölçüm adımları ~14,6 dk (dağıtım doğrulaması 76 s, beş doğrulayıcı ~303 s, raw stream 8 s, native upload 416 s, native indirme 73 s) işin yaklaşık %37’sini tutar; macOS’ta yalnız 2 işçi çalıştığı için kazanç en küçüktür. Sonraki iyileştirme adayları “yapılmayan iyileştirmeler” tablosundadır; **belge-only hat bu koşuda sınanmadı** (hedef dalda sınıflandırıcı yoktu): ilk gerçek ölçüm ve merge kutusu doğrulaması bu PR birleştikten sonraki ilk belge-only PR’dadır.

## Referans serisi `-9` (son seri)

Belge-only hat, paralel yürütme ve inceleme düzeltmeleri `.github/workflows/checks.yml`, `scripts/` ve `tests/` ile `pyproject.toml`/`uv.lock` dosyalarını değiştirdi; ürün kaynağı `src/` değişmedi. Kaynak bağlı referanslar geçersiz olduğundan `-9` serisi kod `20a6b46`’da (adları ölçümden önce seçilmiş) kişisiz kökte **bir kez** alındı ve arşivlendi; altı aşama da ilk denemede geçti, beş kaynak bağlı doğrulayıcı ve `research_evidence.py verify` (591 arşiv) geçti. `-1`…`-8` tarihsel kayıttır. `-8` ölçümü bu işin ara adımıydı: `-9`, gate özeti ve iki takılma korumasının düzeltmesinden sonra yeniden alındı.

**Tam paket** (temiz klon, macOS, altı kabuk, `20a6b46`): tests/contracts + tests/unit 8.300 geçti, 1 atlandı; tests/integration 913, 779, 1.002, 1.032, 985: toplam **13.011 geçti, 1 atlandı, 0 düştü**. (`-8` denemesinde contracts+unit kabuğunda yük altında bir zaman aşımı düştü; `-9`da düşmedi. Bu, zamana duyarlı sınırların bilinen sınıfıdır.)

| Kayıt | Sonuç |
|---|---|
| [Startup](evidence.md#p02-3-reference-startup-9) | aday help/version/context/cache p95 **23,34/23,13/75,19/119,51 ms** (sınırlar 500/500/200/200); taban 23,10/22,91/74,75/124,85 ms |
| [Jobs](evidence.md#p02-3-reference-jobs-9) | normal list/show **102,48/103,67 ms**, yoğun list/show **151,13/106,74 ms** (200 ms sınırı; yoğun list’te %24,4 pay) |
| [Dataset](evidence.md#p02-3-reference-datasets-9) | 24 süreç, en uzun **0,6830 s**; U≤**20.905.984 byte**, inspect/verify G=**622.592/655.360 byte** |
| [Raw](evidence.md#p02-3-reference-raw-9) | 16/256/1024 MiB geçti; 1024 MiB **1,56 s**, ek RSS üst sınırı en çok **1.359.872 byte** |
| [Upload](evidence.md#p02-3-reference-upload-9) | 12 süreç, tam accepted graph ve kaynak kapıları geçti; en uzun çağrı **63,30 s**, U≤**4.538.368**, G=**1.179.648 byte** |
| [Download](evidence.md#p02-3-reference-download-9) | 12 süreç **accepted**; 16 MiB 0,09–0,10 s, 256 MiB 0,85–0,86 s, 1.024 MiB **3,22–3,25 s**, `resume` 0,94–0,95 s ve üçünde `resumed_from` = kesim = 202.326.595; U≤**4.947.968**, G≤**3.850.240 byte** (8 MiB sınırın yaklaşık yarısı) |

[Koşul kaydı](evidence.md#p02-3-native9-conditions): aşama süreleri 33,3/42,8/11,6/3,6/247,1/33,7 sn, sessiz pencere 61,4 sn (31 örnek, sıfırlama yok), AC güç ve sınırlarda bilinen yapı/test/derleyici süreci yok. Ölçüm, bilgisayar pilde iken ilk denemede reddedildi (güç koşulu; hiçbir aşama çalışmadı) ve AC bağlandıktan sonra alındı; bu sonuç ilk ve tek kabul edilen ölçümdür. Ölçüm seçilmemiştir; fiziksel izolasyon attestasyonu yoktur.

## Zamana duyarlı sınırlar (paralellikte en kırılgan olanlar)

İkinci tur inceleme, CPU baskısında yer değiştirebilecek testleri sıraladı (ayrıca ürünün varsayılan 5 sn durum bütçesini açan ~100 test dosyası vardır, bu sınıf 6 işçili koşuda ölçüldü). Bu PR bunları değiştirmez; iyileştirme adayları:

| Test (dosya:satır) | Sınır |
|---|---|
| `test_signal_job_baseline.py:46-70` | iç içe pytest, 45 sn zaman aşımı, 5 sn durum bütçesi (laboratuvarda iki işçide 14 koşunun 1’inde düştü) |
| `test_cli_signals.py:34-70` | alt yorumlayıcı başına 10 sn soket/`communicate` sınırı (laboratuvarda bir koşuda düştü) |
| `test_stream_results.py:591-612` | 0,15 sn toplam deadline TLS el sıkışmasını ve ilk olayı kapsamalı |
| `test_http_transport.py:226-236` | 429 `timeout=0.4` içinde gelmeli, sonra `< 1.0` |
| `test_download_transport_edges.py:238-247`, `:645-660` | 1,4 sn deadline içinde 4×0,3 sn parça (0,2 sn pay); 0,8 sn gövde deadline’ı |
| `test_download_engine_gaps.py:150-166`, `:511` | `seconds=0.25` tam bir okuma; `0.49 <= … <= 0.62` |
| `test_context_discovery.py:258-275` | gerçek SQLite’ı da kapsayan 3,0 sn bütçe |

## Bu PR’da yapılmayan iyileştirmeler (ölçülmüş)

| Fırsat | Ölçülen kazanç sınırı | Neden yapılmadı |
|---|---|---|
| `test_jobs_benchmark.py` fixture kapsamı | ~238 s kurulum (%3) | Testlerin bir kısmı fixture’ı bozar (`test_corrupt_fixture…`); modül kapsamı için kopya/yeniden kurulum tasarımı gerekir |
| Önceden kurulmuş durum dizini kopyası | kurulum payının bir kısmı (%29’un içinde) | Kimlik dönemi/credential nesli çiftlenir; benzersizliği varsayan testlerde sessiz risk |
| Ölçüm adımlarını ayrı işe almak | ~13 dk (yalnız Linux 3.11) | `offline-core` bağımlılığını ve “testler başarılıysa ölçülür” sırasını değiştirir; PR #12 riski |
| `TMPDIR`i tmpfs’e almak | fsync maliyeti | Dosya sistemi anlamını gizler (ext4 inode yeniden kullanımı yalnız ext4’te görüldü) |
| 125 sn’lik tek test (`maximum_file_inventory`) | ~125 s tek işçide | Gerçek CLI’nin azami envanteri sınanıyor; kabul kapsamını küçültmek ayrı karar |

## Sınırlar

Yerel profil macOS/M5 üzerinde altı eşzamanlı süreçle alındı; CI’da fsync, çekirdek sayısı (Linux 4, macOS 3 vCPU) ve gürültü farklıdır. Paralellikte zamana duyarlı bir testin yük altında düşme olasılığı vardır; CI sonuçları aşağıda ayrı kaydedilir ve başarısızlık otomatik yeniden denemeyle gizlenmez.
