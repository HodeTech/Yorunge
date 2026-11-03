# P02-2 / PR #14 Sonar incelemesi

**Tarih:** 2026-11-04. **Durum:** İlk gerçek analizdeki 611 kayıt için tek kaynak paketi ve iki fresh review turu tamamlandı. `027b5c1` gerçek takip analizinde 564 kayıt kapandı, bug sayısı 0 oldu; 47 gerekçeli disposition önerisi kaldı ve uzakta henüz uygulanmadı. [Kayıt bazlı istisnalar](p02-2-sonar-disposition.json), ilk `f71a0c3` koordinatları ile takip analizini ayırır. [Kabul kaydı](p02-2-implementation-validation.md) sonuçların kanonik sahibidir.

## Tek düzeltme grubu

545 aktif pytest assertion’ı 50 dosyada üst seviyede `And` ifadesidir. Sırayla ayrı assertion’lara çevrilir; kısa devre, mesajın yalnız hata halinde değerlendirilmesi, yorumlar ve kalan dosyanın AST’si korunur. Bağımsız AST genişletme ve yorum karşılaştırması dönüşümü denetler. Bu biçim değişikliği için yerel tam takım tekrar edilmez; değişen runtime sınırları hedefli testlerle, final CI kendi tam takımıyla doğrulanır.

Diğer 19 kapanan kod kaydı: beş native sink giriş kontrolü ve PTY okuma kontrolü; bir raises bloğunda hazırlık çağrıları; üç redundant exception alt sınıfı; üç context-manager biçimi; iki nested conditional; iki aynı regex satırındaki ASCII digit sınıfı; bir yinelenen manifest adı; bir URL authority karşılaştırması. Toplam **564 kayıt** kod grubuyla kapandı. CLI hata normalizasyonu da aynı pakette sadeleştirildi; aşağıda açıklanan tek S5754 kaydı analizörde açık kaldı. Wire, migration, eski golden veya ürün bütçesi değişmedi.

Native beş kontrol normal `-I` başlatıcıda zaten hatayı sayıp kabulü reddediyordu. Ayrı ağsız inceleme, `-O` altında assertion’ların kaybolduğunu gösterdi; açık `if`/`ValueError` kontrolleri bu precondition’ları iki kipte de korur. Bu düzeltme bütün provider fixture’larının `-O` desteği olduğu anlamına gelmez. Önceki `-I` native kanıtları tarihsel olarak geçerlidir.

## Kayıt bazlı yanlış pozitifler — 21

| Kural / sayı | Korunan sözleşme ve gerekçe |
|---|---|
| S8707 / 2 | Kaynak `argparse.parse_args()` ve açık operatör config/credential/workspace seçimi; HTTP veya sağlayıcı girdisi değildir. Yerel private-owner/mode/regular-file/boyut ve symlink retleri, canonical hedef ve no-clobber korunur. Symlink ön kontrolü atomik descriptor sandbox garantisi diye sunulmaz. |
| S8705 / 1 | Sabit `sys.executable`, sabit benchmark betiği, ayrı argv ve supervisor `--` sınırı; shell çalıştırılmaz. `--python` açık ölçülecek runtime seçimidir. |
| S8495 / 4 | `tuple[T, ...]` sabit ariteli kayıt değil, değişken URI/query/risk koleksiyonudur. Uzunluğu sabitlemek sözleşmeyi bozar. |
| S5727 / 1 | `start` closure’ı `nonlocal phase` değerini atar; `_safe` kimlik callback’ini eylem sonrası hatada kullanır. Guard kaldırılırsa post-result hatada operation kimliği kaybolur. |
| S5655 / 1 | `dataclasses.replace(UploadPreparationV2)` aynı türü üretir; `_seal` doğru türü alır. |
| S1940 / 1 | `not now < end`, NaN’da da fail-closed’dur. `now >= end` eşdeğer değildir. |
| S7483 / 1 | Resolver portunun phase timeout parametresi vardır ve gövde zaten `asyncio.timeout` kullanır. |
| S7503 / 1 | `ByteSource.aclose` async protokolüdür; synchronous descriptor kapanışı aynı sahip task’ta yapılır. Sahte await/executor eklenmez. |
| S1313 / 9 | IP sabitleri bağlantı hedefi değil, private/shared/link-local/multicast/reserved **ret listesi**dir. |

Güvenlik ve runtime-contract eksenleri bağımsız salt okunur ajan incelemesinden geçti. Kural, severity, quality gate, kapsam veya izin ayarı gevşetilmez; yalnız belirtilen issue kayıtlarının gerekçeli disposition’ı önerilir.

## Hash’e bağlı tarihsel kanıt — 25

Üç frozen araştırmanın kaynak ve testleri kabul receipt/README hash’leriyle bağlıdır. Bu dosyalar yeni ürün kodu gibi yeniden biçimlendirilmez: [preflight](probes/platform-upload-preflight-20261102/README.md), [ilk pilot](probes/platform-upload-pilot-20261102/README.md), [aynı dataset salt okuma](probes/platform-created-dataset-read-20261102/README.md). Pilotun görsel üreticisi ayrıca canlı runner’ın sabit `FROZEN_SHA` kontrolüyle kullanılır.

19 assertion, beş raises ve bir complexity kaydı bu değişmez kanıt kopyalarındadır. Bunlar yeni runtime borcu veya sonraki işe atılan ürün düzeltmesi değildir; doğrulanabilir tarihsel kaynak korunur. Kayıt bazlı `accepted` gerekçesi önerilir; genel dosya/rule exclusion eklenmez. Bu Sonar disposition’ı yapılmadan yapılmış diye raporlanmaz.

## Bilinçli private CLI hata sınırı — 1

S5754 / `AaGjoDpro3Mt4jn-uIMX`, bütün provider/iptal hatalarını özel `_PilotStopped` sinyaline çeviren `_run_guarded` sınırında kaldı. Özgün istisna yeniden yükseltilmez; `main` yalnız özel sinyali yakalayıp sabit güvenli mesaj ve exit 1 üretir. Bu işlem başarı üretmez ve private exception zincirini dışarı vermez. Analyzer farklı özel exception yükseltilmesini yeterli görmedi; bu sonuç kodla kapanmış diye raporlanmaz. Ayrı `accepted / intentional_private_cli_error_boundary` gerekçesi önerilir; frozen 25 kayda dahil değildir. Her iki R2 reviewer’ı bu dar sınıflandırmayı kaynak üzerinden teyit etti; test/kod/02 ölçüm değişikliği gerekmedi.

Güncel tam eşleme: **564 kapanan + 21 false positive + 25 tarihsel accepted + 1 bilinçli accepted = 611**. Takip analizindeki 47 açık issue anahtarı bu 47 öneriyle birebir eşleşir; yeni, sınıflandırılmamış kayıt yoktur.

## Sonraki doğrulama

Ruff format/check ve strict mypy (140 dosya) geçti. Ayrı negatif testlerde native beş precondition normal ve optimize kipte reddedildi; runner’ın RuntimeError/KeyboardInterrupt/SystemExit yollarında private exception zinciri çıktıya taşınmadı: 13 passed. İlgili mevcut runtime/HTTP/bütçe/maintenance/CI/reference seçkisi 724 passed; gerçek PTY kapanış testi ayrıca geçti. Bu kümeler birbirinden ayrıdır; tam takım tekrar edilmedi. 50 dosyanın bağımsız AST/yorum karşılaştırması 545 assertion dönüşümünü doğruladı; dört elle değiştirilen/yeni test fonksiyonu bu eşdeğerlik iddiasından çıkarılıp yukarıdaki testlerle sınandı. Frozen probe kaynak ve testleri değiştirilmedi.

`deb9772` kod paketi iki fresh turda, her turda ayrı contract/safety ajanlarıyla incelendi (R1 Sol/high + Astra/high; R2 farklı Astra/high + Sol/high ajanları). Dört inceleme de temizdir; yeni doğrulanmış bulgu veya kod değişikliği gerekmedi. Ajanlar geçen test/build/ölçümleri tekrar çalıştırmadı. 196 Markdown, 6 skill/44 kart ve actionlint kontrolleri geçti. İlk agent-guide çağrısı desteklenmeyen sistem Python 3.9 ile hatalı metadata sonucu verdi; proje Python 3.11 ortamında aynı dosyalar 0 sorunla doğrulandı, kaynak değişmedi.

Üç güvenlik kaydı ve bütün istisnaların tam issue anahtarları JSON’dadır. Uygulanan Sonar durumları ayrıca API’den geri okunur. Tarayıcı şu anda giriş istiyor; ekran girişte hizmet şartlarının kabulünü belirttiğinden bu adım açık kullanıcı onayı gerektiriyor. Anahtar/token istenmez veya aranmaz.

İlk source CI koşusu `41734832370`, hücreler hâlâ queued iken kaynak düzeltmesi için iptal edildi; tamamlanmış CI/ölçüm sayılmaz, üretilmiş Linux artefaktı yoktur. İki review turundan sonra önceden sabitlenen **02** referans serisi f088cd7 kaynağında seri ve birer kez çalıştı; beşi de geçti. Dört güncel kaynak kapısı ve 393 kayıpsız arşiv doğrulandı. Yeni source CI tek push ile başlatılır. Başarılı 01 serisi değiştirilmedi veya yeni kaynağın kanıtı diye yeniden etiketlenmedi. Canlı hesap denemesi ayrıca somut kullanıcı onayını bekler.
