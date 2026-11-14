# ADR-0030: Yerel performans kabulünü geliştirme tesliminden ayırma

**Durum:** Proposed — kullanıcı onayı bekleniyor; mevcut CI kapıları henüz değişmedi. **2026-11-13 notu:** [ADR-0034](0034-ci-duration-docs-lane-and-parallel-suite.md) yalnız belge değiştiren `development` PR’larında tam suite’in ve kod bağlı native ölçümlerin atlanmasına izin verir; aşağıdaki “zorunlu CI davranışı” tablosu kod, test, betik, workflow, kilit dosyası ya da belge olmayan her değişiklik için olduğu gibi geçerlidir. **Tarih:** 2026-11-05. **İş:** P02-2 teslimi ve [P02-R3](../roadmap/tasks/p02-r3-isolated-performance-acceptance.md). [ADR-0019](0019-reference-startup-performance.md) yalnız aşağıdaki geliştirme/kabul kapısında kısmen değiştirilir.

## Bağlam

[09 serisi](../research/p02-2-implementation-validation.md#5-kasım--09-ac-serisi-ve-açık-performans-kabulü) startup cache ve dört jobs süre kapısını reddetti. Dataset/raw/upload sayaçları ve iki temiz kurulum olumludur; özgün retler dahil 467 arşiv saklandı. AC ve 61,50 saniyelik düşük yük spot kontrolü sürekli makine izolasyonu değildir. Kullanıcı ölçüm sonrasında arka planda sürekli başka bir test çalıştığını bildirdi; bunun hangi örneğe ne kadar etkisi olduğu kanıtlanmadı. ADR-0019’un eşzamanlı ağır iş bulunmaması koşulu sağlanmış sayılmaz; 09 bu koşullu referans kabulünü kapatmaz.

Kullanıcı bu engelin diğer geliştirme ve teslim işlerini durdurmamasını, gerekirse ölçümün ertelenmesini istedi. Aynı paylaşılan makinede tekrar seri almak, sayısal sınırı yükseltmek veya düşük örnekleri seçmek çözüm değildir. Mevcut dört M5 referansı tüm workflow/test/script baytlarına bağlıdır; yalnız CI düzenlemesi bile bu haritayı değiştirebilir. Eski olumlu dataset/upload kaydı yeni haritanın kabulü gibi gösterilemez.

## Karar önerisi

### Ayrı teslim ve açık kabul sahibi

Geliştirme PR’larının tamamlanması/merge önerisi için dört **yerel M5 referans kapısı** yerine açık `deferred` durumunu doğrulayan zorunlu CI denetimi gelir. Bu, performansın geçtiği anlamına gelmez. P02-2 ve sonraki bağımsız geliştirmeler tam işlevsel kabul ve korunmuş aşağıdaki kapılarla ilerleyebilir; P02-2’nin kapsamından ayrılan izole yerel performans kabulünün kanonik sahibi P02-R3 olur.

P02-R3; **P02-7 faz kapanışından ve ilk Master/release önerisinden önce** kapanmak zorundadır. P02-3 veya başka bağımsız geliştirme başlatmak için önkoşul değildir. Sahibi işi teslim eden maintainer/ajandır; dış koşul, eşzamanlı ağır iş bulunmayan referans makine veya ayrıca kabul edilmiş yönetilen ortamdır. Mevcut M5 ortamını değiştirme yetkisi bu kararın kapsamında değildir. Otomatik tekrar veya süre taahhüdü yoktur; uygun pencere geldiğinde o andaki son kaynakla tek önceden planlı seri alınır.

Bu süre içinde roadmap/current/matris ve PR açıklaması **işlevsel teslim / yerel performans kabulü bekleniyor** ayrımını birlikte gösterir. Kartların verified durumu yalnız onayla açıkça değiştirilen işlevsel/native CI kabulünü ifade eder; bütün faz veya M5 performansı tamamlandı denmez.

### Zorunlu CI davranışı

| Kontrol | Onay sonrası davranış |
|---|---|
| Üç ortam tam test, lint/type/belge, build ve altı temiz kurulum | Zorunlu; eksik/failed/skipped hücre aggregate’i reddeder |
| Linux aynı-host startup AB/BA ve receipt/baseline eşliği | ADR-0019’un strict tanı yolu korunur; yalnız doğrulanmış mutlak aşım nonblocking tanıdır |
| Güncel Linux raw ve upload native byte/hash/graph, kaynak/kurulum, bellek ve deadline bütçeleri | Zorunlu; gerçek ölçüm, 64/8 MiB ve mevcut timeout sınırları korunur |
| Dataset native kabulü | Yeni güncel Linux ölçümü zorunludur: aynı 24 süreç, strict çıktı/kurulum/kaynak ve 64/8 MiB, tek API çağrısı ≤30 s. Linux sonucu M5 diye etiketlenmez |
| M5 startup/jobs/dataset/upload reference | Zorunlu durum denetimi `deferred`; başarılı performans iddiası üretmez. Eski strict `verify-*-reference` komutları aynen korunur |
| Kanıt bütünlüğü/gizlilik, artifact upload ve kalıcı saklama | ADR-0019/0029 aynen zorunlu; kayıp/bozuk çıktı veya saklama açığı başarı değildir |

Yeni durum denetimi dört sabit 09 arşivini normal bounded decoder/özet/boyut/hash kurallarıyla okur. Eksik veya bozuk tarihsel kanıt **CI hatasıdır**. Her biri için gerçek ölçülen kaynak, yeniden hesaplanmış passed/bütçe sonucu ve güncel kaynak eşliği ayrı kaydedilir; ret, eski kaynak veya eşlik eksikliği `passed` diye değiştirilmez. Güncel tam kaynak snapshot’ı da receipt’e bağlanır; önce/sonra değişim reddedilir. Bu snapshot yeni bir ölçüm değildir ve tarihsel rapora eklenmez.

Linux job çıktısı, step/aggregate summary ve public artifact **local_reference_acceptance=deferred / P02-R3** durumunu görünür taşır. Eksik, bilinmeyen veya receipt’le uyuşmayan durum aggregate’i reddeder; sıradan success veya boş dosya yeterli değildir. `continue-on-error`, koşulsuz hata yutma, gizli env/CLI override’ı veya GitHub required-check bypass’ı eklenmez. Kullanıcı tarafından seçilecek bir başarı sonucu yoktur; politika sürümlü kaynak/CI değişikliğiyle sabittir. R3 kapanışında zorunlu fresh M5 reference kapıları geri bağlanır ve `deferred` yolu kaldırılır.

### Korunan ürün sınırları

500/200 ms hedefleri, üç ısınma/en az 30 süreç/nearest-rank yöntemi, tüm örneklerin saklanması ve tam kaynak/kurulum/fixture eşliği değişmez. M5 sonucunun ertelenmesi timeout, strict validation, clock/lease, izin/onay, dispatch/replay, sır/PII, byte/hash veya bellek kurallarını gevşetmez. Ürün API/Result/plan/receipt/DDL değişmez. Yeni EVREN çağrısı, ücret, silme, izin ayarı, merge veya yayın yetkisi verilmez.

## Kısmi değişiklik ve belge geçişi

| Kanonik yer | Onay sonrası değişiklik |
|---|---|
| ADR-0019 | Özgün metin korunur; geliştirme CI’ındaki dört yerel reference kapısı ve merge şartı için tarihli ADR-0030 forward notu eklenir |
| Performans/kanıt standartları ve CONTRIBUTING | Strict ölçüm/verifier yöntemi korunur; geliştirme aggregate’i, görünür deferred receipt ve R3 faz/yayın kapısı ayrılır |
| checks.yml, artifact izin listesi ve CI/kanıt testleri | Tek durum denetimi, mandatory Linux dataset native, receipt upload/aggregate ve olumsuz vektörler uygulanır |
| P02-2 planı/a/b/c ve P02-2v | Yerel araç kabulünün geçmişi korunur; final teslimde M5 reference yerine R3’e ayrılan kapı ve mandatory native Linux kabulü açıkça eşlenir |
| current, phase-02/P02-7, tasks/backlog/matris ve PR | İşlevsel teslim ve açık performans durumu birlikte; R3 faz ve ilk yayın öncesi zorunlu |
| P02-R3 | Tüm dört referansın son kaynakta gerçek izole kabulü ve strict CI geri bağlama işinin tek sahibi |

Onaydan önce bağımlı CI/kabul değişikliği uygulanmaz. Doküman geçişi ve kaynak dilimi commit + iki farklı fresh review turuyla kapanır; tam yerel testler sırf tekrar sayısı için koşulmaz, son üç ortam CI ayrıca çalışır.

## Alternatifler

- Sürekli paylaşılan makinede aynı seriyi tekrarlamak: seçilmedi; güvenilir yeni koşul sağlamaz ve kaynak tüketir.
- Eşiği yükseltmek, retleri başarılı saymak veya admin bypass: seçilmedi.
- Şimdi yönetilen özel runner kurmak: ayrı altyapı/erişim/bütçe kararı gerektirir; bu onay onu yetkilendirmez.
- Bütün geliştirmeyi uygun yerel pencereye kadar durdurmak: kullanıcı ihtiyacına uymuyor; açık faz/yayın takibi ve zorunlu native CI ile ayrılır.

## Sonuçlar ve kabul

PR’ın işlevsel CI’ı yeşilken M5 performansı hâlâ kabul edilmemiş olabilir; bu bilinçli kapsam kararı ve görünür risktir. Güncel Linux native kabulü diğer host’ların duvar saati garantisi değildir. Kaynağın bilinen işlevsel/güvenlik hatası ertelenemez; yalnız bu açık performans hattı ayrılır.

Kabul testleri: dört tarihsel passed/failed/stale kaydın gerçek sonucunun korunması; corrupt/missing/hash/source-change/bozuk receipt/eksik aggregate output retleri; görünür deferred summary/artifact; geçerli strict native Linux dataset/raw/upload; gerçek altı kurulum ve üç ortam; R3 kapanmadan faz/release tamamlanmış gösterilmemesi. Sonar ve zorunlu saklama takibi ayrıca kapanır. 07/08/09 retleri ve bütün özgün örnekler değiştirilmez.
