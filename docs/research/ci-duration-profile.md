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

Temiz klonda (`69efc8d`) tam suite altı kabukta (contracts+unit ve beş integration kabuğu) `--durations=0` ile koşuldu: 12.785 geçti, 1 atlandı. 271 test dosyasından 269’u ve 22.088 süre kaydı (çağrı+kurulum+temizlik) toplanıp dosya başına toplandı; pytest 5 ms altındaki kayıtları yazmaz (`--durations-min` varsayılanı), iki dosya listede yoktur (büyük olasılıkla bütün kayıtları bu eşiğin altındadır). Altı süreç aynı anda koştuğundan **mutlak süreler CI’ya taşınmaz; oranlar taşınır**.

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
2. **Paralel test yürütme.** `pytest -n auto --dist loadfile` (CPU başına bir işçi, bütün dosya bir işçide); CPU’dan fazla işçi ölçümde bütçe aşımı üretti. İki testin `uuid4()` parametre değeri sabitlendi; xdist her işçide aynı test kimliklerini ister, ilk deneme toplama aşamasında bu yüzden durdu (iki testin üç satırı).
3. **Görünürlük:** `--durations=25`.

## Yerel xdist denemesi

Dört ölçüm, hepsi bu dalın testleriyle (12.957 test; belge-only hat testleri dahil). **Sonuç: işçi sayısı CPU sayısına eşit olmalı (`-n auto`); fazlası ürünün kendi bütçesini aşan testler üretir.**

| Ortam | Koşu | Süre | Sonuç |
|---|---|---|---|
| macOS M5, 4 işçi (makine boş değildi) | tam suite | 1.698 s | 12.957 geçti, 1 atlandı, 0 düştü (xdist ile sinyal/fork testleri dahil) |
| macOS M5, 8 dosyalık ağır alt küme | tek süreç / 4 işçi | 412 s / 252 s (1,64×) | 494 geçti; tek süreçte yalnız 70 s kullanıcı + 34 s sistem CPU’su: süre CPU’da değil beklemede (CPU kullanımı %25) |
| Linux lab (Docker, overlayfs, **4 CPU’ya sabitlenmiş**), aynı alt küme | tek süreç / 3 / 4 / 6 / 8 işçi | 358 / 161 / 150 / 114 / 125 s | 494 geçti her seferinde |
| Linux lab, **tam suite** | önceki tek süreçli lab koşuları | 3.398–3.528 s | ortam kaynaklı ~120–180 düşen test |
| | 3 işçi | 1.255 s (2,8×) | tek süreç temelinde olmayan yeni düşen test: 1 (ortam) |
| | **4 işçi** | **932 s (3,7×)** | tek süreç temelinde olmayan yeni düşen test: 2 (bilinen `test_guarded_large_put…truncated_reset` flake’i ve bir ortam testi) |
| | 6 işçi (CPU’nun 1,5 katı) | 853 s (4,1×) | **22 test yalnız paralelde düştü** (tek süreçte geçtiler) |

6 işçili koşuda düşenler `test_upload_journal`, `test_capability_cache`, `test_maintenance`, `test_state` ve `test_unsupported_platform` dosyalarındaki durum deposu açan testlerdir; hata ürünün kendi 5 sn durum bütçesidir (“Yerel durum meşgul veya süre bütçesi doldu”): CPU’yu aşan işçi sayısı SQLite/fsync işlerini geciktirip bütçeyi aşıyor. Bütçeyi gevşetmek bir ürün kararıdır (ve bu kararın konusu değildir); işçi sayısını CPU sayısına eşitlemek bu sınıfı üretmedi. Alt kümede 6 işçi en hızlıydı (114 s), ama güvenilirlik hızdan önce gelir.

Ölçülen hız, test süresinin önemli bir kısmının CPU’da değil beklemede (alt süreç başlatma, TLS, SQLite) geçtiğini gösterir: 4 işçi 4 CPU’da 3,7× verdi.

**Beklenen CI etkisi (tahmin; ölçüm aşağıdaki CI satırında):** Linux 3.11 test adımı ~3.600 s → ~1.000 s; iş ~77 dk → ~35 dk (ölçüm adımları ~13 dk seri kalır). Belge-only PR ~10–15 dk.

## CI denemesi

@@CI@@

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
