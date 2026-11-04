# P02-2 / PR #14 Sonar incelemesi

**Tarih:** 2026-11-04; güncellendi 2026-11-05. **Durum:** İlk 611 kayıt için kaynak paketi ve iki fresh review turu tamamlandı. `027b5c1` analizinde 564 kayıt kodla kapandı; kalan 21 false positive +26 accepted, gerekçeli yorumlarıyla Sonar’da uygulandı ve 47 kaydın tamamı API’den doğrulandı. O analizde kalite kapısı **OK**, reliability/security/maintainability **A** idi. Sonraki f7d6809 analizinde sekiz yeni kayıt ve failed gate görüldü; aşağıdaki follow-up bunları ayrı izler. [Kayıt bazlı istisnalar](p02-2-sonar-disposition.json), ilk koordinatları ve sonraki gerçek durumları ayırır. [Kabul kaydı](p02-2-implementation-validation.md) CI ve canlı kabulün ayrı sahibidir.

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

Kullanıcı Sonar oturumunu kendisi açtı. Yalnız issue kayıtlarının durumları ve gerekçe yorumları üç dar grupta değiştirildi; 21 false positive, 25 frozen accepted ve 1 private-boundary accepted. API geri okuması tam 47 benzersiz anahtar ve 47 yorumu doğruladı: 21 `FALSE_POSITIVE`, 26 `ACCEPTED`; bekleyen bu grupta kayıt yok. Gate `OK`, üç rating `1`, duplicate %0,5 ve hotspot review %100’dür. Kural, kapsam, severity, quality gate veya erişim ayarı değiştirilmedi. Önceki öneri ifadeleri hazırlık aşamasının gerekçeleridir; gerçek uygulama durumu JSON’daki `applied_resolution` ve `remote_status_after` alanlarıdır.

İlk source CI koşusu `41734832370`, hücreler hâlâ queued iken kaynak düzeltmesi için iptal edildi; tamamlanmış CI/ölçüm sayılmaz, üretilmiş Linux artefaktı yoktur. İki review turundan sonra önceden sabitlenen **02** referans serisi f088cd7 kaynağında seri ve birer kez çalıştı; beşi de geçti. Dört güncel kaynak kapısı ve 393 kayıpsız arşiv doğrulandı. Yeni source CI tek push ile başlatılır. Başarılı 01 serisi değiştirilmedi veya yeni kaynağın kanıtı diye yeniden etiketlenmedi. Canlı hesap denemesi ayrıca somut kullanıcı onayını bekler.


**4 Kasım güncel sınır:** 47 kayıt için uzak disposition ve kalite kapısı kapanmıştır. CI/live bölümlerindeki önceki gelecek zaman ifadeleri o hazırlık anının kaydıdır. Sonrasında ilk source CI’ın macOS kabulü ve iki Linux timeout’u ile başarısız nihai canlı create/tanı koşuları [kanonik kabul kaydına](p02-2-implementation-validation.md#4-kasım--onaylanan-canlı-koşu-sonar-kapanışı-ve-linux-ci-tanısı) alınmıştır. Sonar OK, P02-2’nin bütünleşik kabulünün tamamlandığı anlamına gelmez.


## F7d6809 sonrası sekiz yeni kayıt

Yerel read-only public Sonar API ve açık UI sekiz benzersiz issue anahtarını/kurallarını teyit etti; JSON’daki followup_analyses önceki 611/47 kaydı değiştirmez. Bu gözlem anında disposition uygulanmamıştı; aşağıdaki kapanış notu gerçek sonraki durumu kaydeder.

- S1192: storage diagnostic’te datasets/ sabiti çıkarıldı; request byte/path aynı kalır.
- İki S5778: expected SecretValue hazırlığı raises öncesine alındı; blok yalnız hedef put_ack çağrısını kapsar.
- S3415: karşılaştırmanın beklenen error envelope’u ayrı değişkenle adlandırıldı; gerçek çıktı solda kalır. Sonar kapanışı yeni analizden sonra teyit edilir.
- İki S8707 önerisi false_positive: dosya konumu açık izole operator CLI girdisi ve ayrı pilot-consent bayrağıdır; HTTP/LLM yanıtından gelen hedef yoktur. Exact historical resource/target, private-input/no-clobber/fresh canonical workspace ve script/source guard’ları korunur. Genel filesystem/LLM sandbox iddiası değildir.
- S4143 önerisi false_positive: stage bir phase marker’dır. owned_shape hesaplaması bozuk JSON’da yükselirse ilk marker kalıcı diagnostic receipt’in hata aşamasını gösterir; başarılıysa owned_locator’a geçer. Yeni malformed fixture bu farkı doğrular.
- S5754 önerisi accepted: private read-only CLI KeyboardInterrupt/SystemExit/CancelledError’ı sabit durma mesajı/exit 1’e çevirir; provider veya private exception zincirini çıktıya vermez. Product API Task.cancel sözleşmesi değişmez. Üç yeni interrupt canary vektörü bu sınırı doğrular.

197 ilgili descriptor/diagnostic/API-CLI vektörü geçti; source disposition iki fresh review turundan sonra gerekçeyle uygulanabilir. Kural/quality gate/severity/exclusion değiştirilmez; genel ret veya gizli sır tespit garantisi üretilmez.


E562015 kaynak dilimi iki fresh contract/safety turunda bulgusuz kapandı. Üç false-positive ve bir accepted disposition Sonar’da gerekçeli birer yorumla uygulandı; dört exact anahtarın durumu, yorum varlığı ve gerekçe eşliği API’den ayrıca doğrulandı. Follow-up kalite kapısı bu f7d6809 analizinde **OK** oldu. Dört source-fix kaydı yeni kaynak analizini bekler; mevcut gate sonucu o düzeltmelerin kapanışı veya bütün P02-2 kabulü sayılmaz. Kural, severity, exclusion ve kalite kapısı değişmedi.


### 7e5675c yeni analizinin tek kalan uyarısı

Yeni analiz üç source-fix kaydını kapattı; gate OK ve tek açık S3415 kaldı. Analyzer’ın flow konumları incelendi: `test_upload_content_eligibility.py` içindeki `(len(server.requests), counts(data[0])) == before` assertion’ını “expected first” sayıyor. Sol taraf çağrı sonrası güncel gerçek gözlem, `before` sağ tarafta beklenen işlem-öncesi snapshot’tır; dosyanın diğer actual-first assertion’larıyla tutarlıdır. Önceki expected_error adlandırması bu uyarıyı kapatmadı; kodla kapandı diye sayılmaz. Bu tek kayıt için `current_actual_tuple_compared_to_before_expected_snapshot` gerekçesiyle false-positive önerilir. Ürün/test byte haritası, assertion oracle’ı veya kaynak bağlı kabul sırf analizörü susturmak için değiştirilmez. Uzak disposition henüz uygulanmadı; dar iki fresh review ve gerçek geri okuma beklenir.


Dar R1 Sol/high ve farklı fresh R2 Astra/high, before/after veri akışı ve oracle’ı bağımsız doğruladı; bulgu yok. Son tek false-positive gerekçeli yorumuyla uygulandı ve UI/API’den teyit edildi. 7e5675c analizinde sekiz kaydın gerçek karşılığı **3 FIXED +4 FALSE_POSITIVE +1 ACCEPTED**; her disposition’ın tek gerekçe yorumu doğrulandı. Açık kayıt **0**, gate **OK**. İlk 611 kaydın tarihsel sayımı değiştirilmedi. Test/runtime/workflow kaynağı değişmedi, native06 yeniden çalıştırılmadı.


## 5 Kasım — 36f9442 sonrası 20 yeni kayıt

Sonar PR analizinin 36f9442 kaynağında 20 yeni issue’su ve gate ERROR gözlendi; önceki 7e5675c/611 kayıtlarının tarihsel kapanışı değiştirilmez. [Exact anahtarlar](p02-2-sonar-disposition.json) ayrı followup_analyses grubundadır. Yeni kaynak paketi ve aşağıdaki sekiz disposition iki fresh review sonrasında uygulanır; henüz uzakta kapandı sayılmaz.

**12 kaynak düzeltmesi:** İki S6353 için opaque-text marker regex’i strict UTF-8 metinde açık re.ASCII ile aynı ASCII sözcük sınıfına taşınır; decoded değer aramada kullanıldığı için S2201 de açıklığa kavuşur. Geçersiz UTF-8 reddi ve bounded encoding/gizlilik taraması korunur. İki S5713’te ValueError alt sınıflarının redundant yakalaması kaldırılır. Original-commit hata mesajı tek sabite alınır (S1192); archive context seçimi ayrı küçük yardımcıya çıkarılır (S3776). Beş S5778’de coroutine hazırlığı raises öncesindedir; blok tek asyncio.run çağrısını kapsar. Hata beklentileri, istek sayısı ve no-replay sınırı değişmez.

**Dört security false-positive önerisi:** S8705/S8707 girdileri açık maintainer/CI operatörünün argparse namespace’idir; HTTP/provider/LLM yanıtından üretilmez. Git komutu sabit executable/subcommand ve ayrı argv ile `-C` operandını kullanır, shell yoktur. Read/copy/private-write yolları açık seçilmiş yerel evidence/context hedefleridir; regular/no-follow/nonblocking/byte sınırları, no-clobber/context mode ve staging hash kapıları korunur. Bu araç genel kötü niyetli operatör/LLM/filesystem sandbox’ı değildir; Accepted ADR-0029 bu sınırı açık tanımlar.

**Dört S5754 false-positive önerisi:** `_publish_completed`, `_cleanup_batch` ve `_put_batch` yakalanan özgün BaseException nesnelerini cleanup boyunca taşır; `_prefer_failure` gerçek CancelledError’a öncelik verir ve ilk olağan hatayı korur. Başarılı her task en çok bir receipt publish denemesi alır; bütün prepared call’lar kapatıldıktan sonra `_put_batch` seçilen özgün hatayı yeniden yükseltir. Dar Exception yakalamak cancellation/interrupt cleanup’ını, catch içinde hemen raise etmek diğer tamamlanmış receipt’leri/kaynakları kaybettirir. Bu, private CLI’daki kasıtlı başka sinyale çeviren eski accepted örneğinden ayrıdır: burada hata başarıya veya başka tipe çevrilmez. Genel BaseException suppression/exclusion eklenmez.

Kalite kapısı, severity, kural veya izin ayarı değiştirilmez. Kaynakla kapanacak 12 kayıt yeni gerçek analizle; sekiz false-positive önerisi ise tek tek gerekçe/durum geri okumasıyla ayrıca teyit edilecektir.
