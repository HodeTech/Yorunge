# ADR-0022: Platform keşfinde gözleme dayalı sınırlı tüketici sözleşmesi

**Durum:** Accepted — kullanıcı revize kararı 2026-11-01 tarihinde açıkça onayladı; aşağıdaki kapsam/kabul eşlemesi aynı onay commit’inde uygulandı. **Tarih:** 2026-11-01. **İş:** P02-0d / P02-0b / P02-0 adım 5.3. [Araştırma ve yeni canlı kanıt](../research/p02-platform-reverse-engineering.md), [kapalı public referans](../reference/context-discovery.md), [iş kartı](../roadmap/tasks/p02-0d-platform-context-discovery.md). Bu öneri ADR-0020/0021’in yalnız Platform read-only discovery nihai ürün sözleşmesi ve raw/auth/principal/pagination kabul kapsamını kısmen değiştirir; iki karar Accepted kalır; yalnız burada belirtilen Platform nihai tüketici/kabul kuralı bu kararla kısmen değişir.

## Bağlam

Kullanıcı ulaşabildiği mevcut dokümanlarla sınırlı olduğunu belirtti ve önceden sağladığı Platform key’iyle salt okunur tersine mühendisliği açıkça yetkilendirdi. Resmî yayımlanmış web consumer’ı ve 6 istekli yeni koşu yararlı bilgi üretti: auth/me, organizations ve projects key’le 200, anahtar yokken 401; gerçek public API/üretim decoder’ı mevcut üç yanıtı kabul etti, Identifier/total predikatları geçti. Bir organizasyon ve boş proje listesi görüldü. İlk koşuda dolu/seçili proje/detail yoktu. Sonra kullanıcı kendi private test projesini hazırladı; [ayrı 5 GET seçili-proje kabulü](../research/p02-platform-reverse-engineering.md#seçili-proje-canlı-kabulü--ayrı-koşu) mevcut Accepted gözlem yolunda geçti. İki koşu tek contract pilotu diye birleştirilmez.

Buna karşılık bütün provider alanlarının kararlılığı, iyi biçimli invalid-key grameri, principal/account semantiği ve pagination/tamlık garantisi çıkarılamadı. Web istemcisinin bildiği alanlar sunucunun bütün sözleşmesi değildir. Header yokken 401, key değerinin gerçekten doğrulandığını tek başına göstermez. Mevcut product wire bu belirsizlikleri zaten unknown/unverified/null/not_guaranteed olarak sunar; discovery hiçbir yetki üretmez.

ADR-0021 ara projeksiyonu uygulamaya açarken nihai whole-raw katı decoder ve güçlü dış sözleşme/kabul kapılarını korudu. Böylece ihtiyaç duyulmayan PII/metadata alanlarının bütün varyasyonları dahi bu dar read-only gözlem işinin kapanışını bekletebilir. Tüketilen alanların sıkılığı ile sağlayıcının kullanılmayan tüm alanlarını doğrulama gereğini ayrı değerlendirmek gerekir.

## Karar

### 1. Nihai ürün sınırı tüketici sözleşmesidir

Platform discovery için aynı kapalı, tipli **PlatformContextDiscovery v1** gözlem varyantı nihai read-only ürün sınırı olur. Tek kanonik ürün adı PlatformContextDiscovery v1’dir; bu bir provider API sürümü veya server attestasyonu değildir. Kullanıcı config/API/CLI’den sözleşme sürümü, kanıt veya verified flag enjekte edemez. Mevcut Result, Context, Plan, credential/capability ve state şemaları değişmez.

Kanonik raw tüketim referansı endpoint bazında me success/data/id, organization items/total/id, bare project list id/org_id ve seçili detail bare/zarf/id-route kurallarını aynen korur. Tüketilen control ve alanlar strict; zorunlu alan, tür/null/ID, duplicate/limit veya logical-success hatası invalid_response olur. Tüketilen alanda unknown enum/şekil sessizce düşürülmez veya başka envelope denenerek başarıya çevrilmez.

Bütün ham yanıt için strict UTF-8/JSON, duplicate/nonfinite, byte/depth/node/header/chunk ve **tüm ham ağaçta seçili credential için mevcut literal-secret denetimi** aynen sürer. Tüketilmeyen alan/control ayrımı açık kalır: root success asla atılan metadata değildir. Seçilen detail şeklinin dışındaki id/org_id/data alt ağaçları da muaf protokol anahtarı değildir. Tüketilmeyen metadata doğrulama/sır sınırlarından geçtikten sonra atılır; public DTO strict/frozen/extra=forbid kalır, ortak decode_response gevşetilmez. Ad/email/telefon/profil/ham role/admin_permissions yayımlanmaz. Reported ID’ler kişiye bağlanabilir; tüm PII ayıklama iddiası yoktur.

**Açık değişiklik:** ADR-0021’in nihai üretim yoluna whole-raw katı decoder geçişi ve bütün bilinmeyen ham metadata alanlarını reddetme zorunluluğu bu consumer için kaldırılır. Ara projeksiyon-only yaklaşımı, yukarıdaki tam güvenlik ve sıkı tüketilen alan sınırıyla bilinçli nihai tüketici politikası olur. Bu, mevcut kapıyı geçmiş gibi işaretlemek değil kabul kapsamını değiştirmektir. Gözlenen auth/me.data nesnesi toplam 35 alanlıdır; id, organization_id ve personal_org_id tüketilir, kalan 32 alanın bütün server varyasyonlarını tahmin eden ham model yazılmaz. Sonraki yetki/yazma tüketicileri için aynı istisna verilmez.

### Literal-secret kapsamının kesin anlamı

Bu karardaki ham ağaç taraması, **yalnız seçili credential SecretValue literal değerinin** P01’deki mevcut kuralıyla aranmasıdır: UTF-8 uzunluğu 8 byte’tan küçükse tam eşitlik; en az 8 byte ise tam eşitlik veya alt dize eşleşmesi reddedilir. Parse edilmiş tüm dinamik string değerleri ve muaf olmayan serbest metadata anahtarları kapsanır. Yalnız endpoint ve seçilmiş bare/zarf şekli için açıkça tanımlanan sabit protokol alan adları anahtar taramasından muaf olabilir; aynı adlı serbest alt metadata veya seçilmemiş şeklin alanları muaf değildir.

Bu, bilinmeyen başka anahtarları/sırları, Base64/hash/URL-encoding gibi türetilmiş credential biçimlerini veya bütün kişisel veriyi sınıflandıran genel DLP değildir. JSON kaçışlarının strict parse sırasında normal çözümlenmesi aynen geçerlidir. Tamlık ifadesi **ağacın ziyaret kapsamını**, tüm sır türlerini bulma garantisini anlatmaz. Tüketilmeyen metadata bu sınırlı denetim ve yapısal/boyut sınırlarından sonra atılır; ham metadata genel güvenli veri diye onaylanmaz.

### 2. Bilinmeyen auth/kimlik/tamlık kabul edilebilir ürün sonucudur

Bu ürünün başarılı sonucu uzak doğrulanmış context değildir. Public authentication=unknown, validation=unverified, authorization_scope=null, provider principal/account/org/project=null, identity_status=unverified ve consistency=not_guaranteed sabitleri korunur. Reported identity ID’leri yalnız tanımlı wire yollarından gelir; principal/user/account/üyelik olarak yorumlanmaz. Local credential binding sadece kullanılan yerel snapshot’ı tanımlar, server’ın anahtarı doğruladığının kanıtı değildir.

**Açık değişiklik:** P02-0d kartının verified teslimi, provider principal/account/pagination ve key-auth semantiği bilinmediği için tek başına engellenmez; bu bilinmeyenlerin doğru kapalı çıktısı ve güvenli davranışı ürün kabulü olarak sınanır. İş kartı verified ile public validation=unverified farklıdır. P02-0b başlığı ve kapsamı bu gözlem sınırıyla aynı commit’te hizalanır; tamamlanmış doğrulanmış kimlik/izin resolver’ı iddia edilmez.

Yeni 6 çağrılık key/no-key karşılaştırması yalnız kendi normalized origin/API kökü, üç endpoint/default parametre ve tarih kapsamındaki davranış kanıtıdır. İyi biçimli invalid-key testi yerine geçmez; böyle bir anahtar üretmek için sözdizimi tahmin edilmez. Normal discovery’ye no-key veya negatif kontrol eklenmez. Auth kontrolünün yokluğu veya farklı sonucu metadata’dan permission/verified üretme nedeni olamaz. Farklı custom host’a gözlem kanıtı miras verilmez; public unknown sabitleri korunur.

Listeler en çok 128 kayıtla sınırlı kalır. total>count incomplete; total=count en iyi unknown; projects completeness unknown. Cursor/Link veya tahmini limit/offset takip edilmez; output tam envanter diye sunulmaz. Provider’ın tamlık sözleşmesi veya pagination desteği daha sonra gerçek ihtiyaçla açık tüketici kararı olarak eklenebilir; bu read-only sürümün gizli bitmemiş implementasyonu sayılmaz. Veri aktarımı/katalog tam taraması kendi kapsam ve kabulünü ayrıca gerektirir.

### Özgün doğrulanmış kimlik ihtiyacının kanonik sahibi

[**P02-R1 — Doğrulanmış hizmet kimliği ve seçili context bağı**](../roadmap/tasks/p02-r1-verified-context-binding.md), özgün C01/C02 kimlik/bağ ihtiyacının açık takip işidir; sahip faz P02, modül identity-context’tir. [B14](../roadmap/backlog.md) yalnız bu karta yönlendirir. Bu iş gözlenen ID’yi principal/hesap yapmakla kapanmaz: provider’ın yetkili auth/principal/ilişki kaynağı ve gerekirse göreve özgü permission/bağımsız otorite kanıtı gerekir. Kaynak yoksa ihtiyaç draft/blocked olarak burada görünür kalır; P02-0b/d adını değiştirip kaybolmaz.

Onay sonrası P02-0b/d dar gözlem teslimi olarak kapanabilir; P02-R1 ayrı takip kapsamıdır ve bu mevcut tek P02-0 paketinin önkoşulu yapılmaz. Buna karşılık sonraki yan etkili tüketicinin gerçek güncel yetki kapısı kaldırılmaz; kendi task/endpoint kapsamındaki otorite olmadan işlem başlatamaz. P02-R1 yeni public verified biçimi/ayrı ADR ve dar alt kartlar gerekip gerekmediğini ready öncesinde belirler; bugünkü v1 sabitleri yerinde yükseltilmez. Bu takibin eklenmesi şu anda uygulama taahhüdü veya ürün kabulü değildir.

### 3. Değişmeyen platform güven ve etki kapıları

No-init mevcut store, tek service/credential/config snapshot, ağ sırasında kapalı DB transaction/lock, final credential ID/revision/epoch/clock-generation/deadline kapısı korunur. Ürün normal 3 GET; çözümlenen profil/override projesi varsa 4 GET, en çok 8 attempt/30 s/4 MiB, response 1 MiB/output 256 KiB; mevcut state 5 s/lock 1 s ve P01 retry/cleanup/iptal/UTF-8 kuralları aynıdır.

Provider read başarısı, hesap/proje seçimi, role, toplam veya gözlenen bir ID **execution/admission/permission kanıtı değildir**. ADR-0013 bağımsız otorite ve ADR-0014/0016 son yetki/credential kontrolleri değişmez. Public producer draft/blocked kalır; bu kararla upload/inference/ücretli export/terms accept/proje oluşturma/silme veya browser JWT fallback açılmaz. Sonraki yan etkili tüketici kendi endpoint/yetki/idempotency/fiyat sözleşmesini ayrıca kapatır; discovery bunu onun yerine yapmaz.

### 4. Dolu/seçili proje canlı kabulü korunur

Bu öneri **dolu proje ve seçili detail gerçek kabulünü kaldırmaz**. Yeni koşudaki boş dizi nonempty/detail consumer’ını kanıtlamaz; sentetik testler de canlı kabul yerine geçmez. Mevcut uygun projeden kullanıcının belirlediği bir örneğin aynı key’le görünmesi ve doğru ID’nin detail yolunda dönmesi gerekir. İlk proje kullanıcı seçimi diye otomatik alınmaz, config yazılmaz. Key’le liste boşken nedenin proje yokluğu/yetki/filtre olduğu varsayılmaz.

Kullanıcıda uygun proje yoksa yaratma bu ADR ile yetkilendirilmez; önce ayrı somut test kaynak/etki/varsa maliyet planı ve kullanıcının açık yetkisi gerekir. Yalnız bu koşul açık kaldığında kartın eksik live dalı açık kalır; resmi şema talebiyle aynı belirsiz dış beklemeye birleştirilmez. Bu karar onaylansa bile proje kabulü kapanmadan P02-0d/P02-0b/P02-0 verified yapılmaz. **1 Kasım son kanıtı:** kullanıcı kaynağıyla mevcut consumer’ın seçili-proje dalı ayrı 5/5 koşusunda geçti; [receipt](../research/p02-platform-selected-project-observations.json). Bu canlı gereklilik kaldırılmadı, gerçek mevcut uygulama üzerinde sınandı; formal auth/principal/pagination veya yeni nihai kapsam onayı bundan çıkarılmaz.

## Kabul ve uygulama sırası

1. Kullanıcı bu ADR’yi onaylar. ADR-0020/0021 forward notları ve karar indeksi yalnız Platform raw/kapanış kapsamındaki partial amendment’ı gösterir; önceki kararlar bütünüyle Superseded olmaz. Kanonik referans, P02-0d/0b, plan/current/faz/matris ve kullanıcı anlatımı birlikte hizalanır.
2. Mevcut tüketici kodu yeni nihai sözleşmeyle karşılaştırılır. Mevcut doğru uygulama sırf yeni bir kod adımı üretmek için yeniden yazılmaz. Eksik kontrol/oracle varsa gerçek consumer’da minimal geliştirme ve anlamlı regresyon yapılır; ortak codec gevşetilmez. Formal provider şeması veya kullanıcı rolü icat edilmez.
3. [Sürümlü özgün probe ve test kaynakları](../research/probes/platform-20261101/README.md) receipt.probe_sha256 ile karşılaştırılır; kaynak snapshot’ı biçim düzeltmesiyle dahi değiştirilmez. Arşiv testleri yalnız sentetik/geçici girdilerle ağsız yeniden çalıştırılabilir. Me/org/empty-project gerçek public API sonucu, schema/Identifier/total predikatları, key/no-key status ve tam sayaç/deadline receipt’i kanıt olarak bağlanır. Kaynak/probe/receipt hash’i gözlem kimliğidir; bağımsız attestation değildir. Önceki başarısız veya limit dışı koşular yeniden etiketlenmez; özel raw veri/ID/key repoya girmez.
4. Dolu/seçili proje gerçek kabulü kullanıcının belirlediği mevcut kaynak ve scoped bütçeyle tamamlanır. Yanıttaki ID eşliği ve parser sonucu değer yayımlamadan doğrulanır. Yeni resource veya key otomatik oluşturulmaz. Bu dal kapanmadan üst teslim verified olmaz.
5. Bağımsız fixture’larda boş/tek/çok/duplicate/128–129 kayıt, strict success/bool/int/null/missing, id-route/404/parent farkı, raw unknown metadata atımı, seçili credential’ın literal değerini taşıyan dinamik string/serbest metadata anahtarlarının reddi, kısa değerde tam eşitlik/uzun değerde alt dize ve seçilmiş şeklin sabit protokol anahtarı ayrımı, byte/deadline ve süreçler arası credential/reset/clock yarışları korunur. CLI/Python/text/JSON/NDJSON/UTF-8/pipe/SIGINT, local-only lazy ve state/schema 6 uyumu denetlenir.
6. Her gerçek geliştirme adımı commit ve iki farklı fresh review turuyla kapanır. Son kaynakta gerekli test/statik/iki temiz kurulum ve kaynak bağlı M5 kanıtı; nihai tek development PR ve üç ortam CI tamamlanır. Kaynak değişmediyse eski geçerli kaynak kanıtı sahte yeni koşuya çevrilmez; kaynak değişirse yeniden ölçülür. Master/release kullanıcıdadır.

## Kabul kapsamı eşlemesi — yalnız onay commit’inde

Bu tablo kullanıcı onayıyla aynı commit’te uygulanan değişikliği **madde bazında** tanımlar. Önceki Accepted ADR-0020/0021’in yalnız bu Platform hükümleri değiştirildi. Kaldırılan koşullar geçilmiş test veya verified kanıt olarak yazılmaz; korunmuş son kaynak/PR/CI kabulü ayrıca tamamlanır.

| Kanonik yer | İşlem | Onay sonrası kesin sınır |
|---|---|---|
| P02-0d kullanıcı sonucu / giren kapsam | Yeniden yazılır | Provider principal/account/org anlamını doğrulama yerine selected tercih + reported ID/liste/detail gözlemi; auth/kimlik/tamlık unknown/unverified. Doğrulanmış bağ P02-R1’de takip edilir |
| P02-0d bağımlılıklar / sözleşme / doğrulama / teslim kaydı | Yeniden yazılır | Nihai whole-raw decoder ve resmî auth/principal/pagination bilgisi bu dar teslimin kapısı değildir; eski tarihsel kanıtlara forward notu. Gerçek seçili-proje kanıtı ile son kaynak/PR/CI kabulü korunur; tamamlanan dal tamamlandı, eksik dal açık diye kaydedilir |
| P02-0d kabul 1 | Eski decoder zorunluluğu kaldırılır; sıkılık korunur | Tüketilen alan/control strict; tüm raw JSON/yapısal/byte sınırları ve seçili credential literal denetimi; tüketilmeyen metadata atımı; public extra=forbid |
| P02-0d kabul 2 | Verified önkoşulu olmaktan çıkar | İyi biçimli invalid-key kontrolü normal consumer’a eklenmez. Mevcut 8 GET/12 attempt/4 MiB/30 s contract pilotu yalnız ayrıca yetkili, grameri kapanmış opsiyonel araştırmadır; yeni 6 GET/6 attempt koşusunun yerine geçirilmez |
| P02-0d kabul 3 | Korunur | No-init/snapshot/final credential-epoch-generation/cleanup/CLI-API/TLS kapıları |
| P02-0d kabul 4 | Korunur ve terminoloji hizalanır | Proje yoksa 3 GET, profil veya override projesi varsa 4; route ID/404/null-parent/reason/list sınırları; ilk öğeyi otomatik seçme yok |
| P02-0d kabul 5 | Korunur | Dolu/seçili proje gerçek consumer kabulü, son kaynak kontrolleri ve iki fresh review/PR/CI zorunlu; bu canlı dal bitmeden verified yok |
| P02-0b kullanıcı sonucu / giren kapsam / bağımlılıklar / sözleşme / teslim kaydı | Yeniden yazılır | Hizmete bağlı dar read-only gözlem üst teslimi; doğrulanmış kimlik/proje bağı burada yapılmış sayılmaz ve P02-R1’ye bağlanır |
| P02-0b kabul 1 | Yeniden yazılır | Observed consumer alanları ve açık unknown durumları; normal discovery’ye no-key/negatif kontrol eklenmez. Negatif kontrol ve key/principal semantiği bu gözlem tesliminin verified önkoşulu değildir |
| P02-0b kabul 2 | Korunur | Aynı CLI/Python kullanım senaryosu, doğru hizmet/hedef/binding, tek env snapshot ve local-only sınırı |
| P02-0b kabul 3 | Korunur ve kesinleştirilir | Gerçek TLS/hata/byte sınırı; seçili credential için literal kuralı ve metadata anahtarı/protokol istisnaları; genel sır/PII sınıflandırma garantisi yok |
| P02-0b kabul 4 | Korunur | Liste/seçim/parent/404/ID/reason ve tamlık belirsizliği; görünürlük izin değildir |
| P02-0b kabul 5 | Sayı açıklaması düzeltilir; kapılar korunur | Normal Platform **en çok 4 GET, proje yoksa 3**; en çok 8 attempt/4 MiB/30 s, state 5 s/lock 1 s ve final yarış kapısı |
| P02-0b kabul 6 | Korunur | Public wire/UTF-8/NDJSON/stdio/yerel v1 uyumu ve UX; yeni yetki iddiası yok |
| P02-0b kabul 7 | Eski key-semantik engeli kaldırılır; live korunur | LLM kendi kabulü; Platform gerçek me/org/empty ve dolu/seçili detail kabulü; unknown sonuç beklenen gözlem sınırıdır, doğrulanmış principal ihtiyacı P02-R1’ye aittir |
| P02-0b kabul 8 | Korunur | Gerekli son kaynak test/statik/iki kurulum/M5 ve iki review turu; tek nihai development PR/CI |

Resmî sağlayıcı bilgisinin yokluğu tek başına bu dar işi bloklamaz. **Canlı dolu/seçili proje başarısı** korunmuş dış test kaynağı/kabul kapısıdır; kaynak kontrolleri, review ve uzak CI gibi diğer teslim koşulları da zorunludur. Uygun proje verilmesi bu kontrollerin otomatik geçtiği anlamına gelmez. Kullanıcı mevcut projesi olmadığını bildirdi; yeni test projesi hazırlığı ve ayrı scoped salt okuma kabulü ürün veri/anahtar üretme yetkisine çevrilmez.

## Onay sonrası belge ve kaynak geçişi

| Dosya / bölüm | Onay commit’indeki işlem |
|---|---|
| ADR-0022 / decisions/README | Gerçek onay tarihiyle Accepted; nihai ürün sözleşmesi ve kabul kapsamındaki dar partial amendment; güncel indeks tarihi |
| ADR-0020/0021 | Platform nihai raw/auth/principal/pagination kapısında bu karara forward notu; önceki kararlar bütünüyle Superseded olmaz. Tarihsel karar/araştırma metni silinmez |
| P02-0d / P02-0b kartları | Yukarıdaki bütün kullanıcı sonucu, kapsam ve kabul eşlemesi aynı commit’te uygulanır. Eski katı decoder/key-semantik kapısı aktif teslim koşulu gibi kalmaz; live/review/CI korunur |
| P02-R1 / backlog B14 / faz ve tasks indeksi | Özgün doğrulanmış kimlik/bağ ihtiyacı identity-context sahibiyle ayrı takipte görünür; bu pakette tamamlandı veya yeni önkoşul sayılmaz |
| reference/context-discovery: giriş ve raw kabul bölümü | Eski “nihai katı decoder ek kod adımı” anlatımı değiştirilir; sınırlı tüketici sözleşmesi ve literal-secret kapsamı kanonik olur; wire/sabitler aynı |
| reference/context-discovery: Platform başlığı | “Önerilen Platform gözlem varyantı” başlığı “Platform gözlem varyantı” yapılır; repo içindeki bütün inbound anchor’lar aynı commit’te güncellenir. Özellikle ADR-0021’deki iki link, P02-0d linki ve p02-0-implementation-validation tarihsel linki kontrol edilir; link düzeltmesi geçmiş statüyü değiştirmez |
| reference/cli-contract | Durum/girişte nihai katı parser kapısı yerine gözlem teslimi ve ayrı canlı proje/final CI kabulü; gerçek komut/API/exit davranışı değişmez |
| src/yorunge/application/platform_projection.py: modül açıklaması | Interim yerine nihai sınırlı tüketici politikası anlatılır. Salt bu docstring değişikliği bile source-bound referansı etkiler; son kaynak kabulü buna göre yapılır |
| README / CHANGELOG | Aktif Unreleased ürün anlatımında ayrı whole-raw katı decoder kapısı kaldırılır; unverified/unknown/no-authority ve canlı proje/final teslim sınırı açık kalır. Tarihsel kabul ölçümleri yeniden etiketlenmez |
| p02-account-setup / research/README | ADR-0022 Proposed notları gerçek onay durumuna çekilir; endpoint araştırması ve invalid-key kontrolünün artık opsiyonel ayrı kapsamı ayrılır; secret hazırlık kuralı aynı |
| roadmap/current / plan / README / tasks/README / phase-02 | Kullanıcı sonucu, P02-0/d kabul sahibi ve kalan live/PR/CI durumu aynı eşlemeyi söyler; verified için bütün korunmuş koşullar gerekir |
| capability-matrix | Gözlem teslimi doğrulanmış kimlik veya izin capability’si diye anlatılmaz; C01 özgün ihtiyaç P02-R1’ye bağlanır |

Onay commit’i kontrolü `katı decoder`, `katı parser`, `negatif kontrol`, `principal/account/org anlam`, `gerçekten doğruladı` ve ADR-0022 Proposed ifadeleriyle **bütün aktif belgeleri** tarar. Eşleşme körlemesine silinmez: tarihsel bölümde eski kabulü anlatan metin tarihsel/forward notuyla korunur; aktif normatif bölüm aynı nihai consumer sınırına bağlanır. Güncellenen dosyaların Güncellendi alanı gerçek düzenleme tarihini taşır. Belge/anchor/kart/matris kontrolü ve literal fixture’lar uygun kapsamda doğrulanır.

## Alternatifler

- **ADR-0020/0021’in önceki nihai kapısını korumak:** Seçilmedi. Daha fazla client araştırması sağlayıcının tüm principal/key/pagination sözleşmesini evrensel kanıtlamayabilir; dış kapı açık kalır.
- **Frontend davranışını aynen kopyalamak:** Seçilmedi. Web wrapper’ının esnek envelope/success/metadata davranışı Yörünge’nin strict tüketilen alan/control ve sır sınırını belirlemez.
- **Header yokken 401’i key/principal verified saymak veya tahmini invalid-key üretmek:** Seçilmedi. Bu kanıt, header varlığına bağlı davranışı gösterir; anahtar değerinin doğrulanmasını veya kimlik otoritesini göstermez.
- **Dolu/seçili canlı dalı silerek paketi bitirmek:** Seçilmedi. Bağımsız gerçek consumer kabulü korunur.
- **Kısıtlı ve açık unknown tüketici sınırı:** Kabul edilen seçimdir. Kullanıcıya bugün elde edilebilen faydayı verir; güven iddiasını büyütmez, gereken yetkiyi gelecekteki yan etkiye taşımaz.

## Sonuçlar ve sınırlar

Bu değişiklik resmî OpenAPI eksikliğini read-only gözlem tüketicisinin tüm kapanışına bağlamayı bırakır. Karşılığı, ürünün hiçbir zaman doğrulanmış principal/izin veya tam uzak envanter iddia etmemesi ve consumer alan değişiminde kontrollü ret vermesidir. Bilinmeyen metadata atımı yalnız tam raw güvenlik taramasından sonra olur. İleride provider sözleşmesi gelmesi faydalıdır; bu öneri onun doğruluğunu önceden ilan etmez.

Kullanıcı revize ADR-0022’yi 2026-11-01 tarihinde açıkça onayladı. Nihai sınırlı gözlem sözleşmesi ve kabul eşlemesi bu yetkiyle uygulanır; özgün doğrulanmış kimlik/bağ ihtiyacı P02-R1’de draft takipte kalır. Seçili-proje canlı kabulü ayrı 5 GET/5 attempt/4 MiB/30 s planında tamamlandı; bu sonuç veya karar onayı tek başına bütün P02-0 kaynak/PR/CI kabulü değildir. Gerçek kimlik yalnız Git dışındaki güvenli girdide tutulur.