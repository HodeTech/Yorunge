# ADR-0022: Platform keşfinde gözleme dayalı sınırlı tüketici sözleşmesi

**Durum:** Proposed — kullanıcı onayı bekleniyor; bu karara bağlı ürün veya kabul değişikliği uygulanmadı. **Tarih:** 2026-11-01. **İş:** P02-0d / P02-0b / P02-0 adım5.3. [Araştırma ve yeni canlı kanıt](../research/p02-platform-reverse-engineering.md), [kapalı public referans](../reference/context-discovery.md), [iş kartı](../roadmap/tasks/p02-0d-platform-context-discovery.md). Bu öneri ADR-0020/0021’in yalnız Platform read-only discovery nihai raw-kabul ve auth/principal/pagination belge kapısını kısmen değiştirir; iki karar halen Accepted ve bu öneri onaylanana kadar bağlayıcıdır.

## Bağlam

Kullanıcı ulaşabildiği mevcut dokümanlarla sınırlı olduğunu belirtti ve önceden sağladığı Platform key’iyle salt okunur tersine mühendisliği açıkça yetkilendirdi. Resmî yayımlanmış web consumer’ı ve6 istekli yeni koşu yararlı bilgi üretti: auth/me, organizations ve projects key’le200, anahtar yokken401; gerçek public API/üretim decoder’ı mevcut üç yanıtı kabul etti, Identifier/total predikatları geçti. Bir organizasyon ve boş proje listesi görüldü. Dolu/seçili proje/detail canlı kabulü yapılmadı.

Buna karşılık bütün provider alanlarının kararlılığı, iyi biçimli invalid-key grameri, principal/account semantiği ve pagination/tamlık garantisi çıkarılamadı. Web istemcisinin bildiği alanlar sunucunun bütün sözleşmesi değildir. Header yokken401, key değerinin gerçekten doğrulandığını tek başına göstermez. Mevcut product wire bu belirsizlikleri zaten unknown/unverified/null/not_guaranteed olarak sunar; discovery hiçbir yetki üretmez.

ADR-0021 ara projeksiyonu uygulamaya açarken nihai whole-raw katı decoder ve güçlü dış sözleşme/kabul kapılarını korudu. Böylece ihtiyaç duyulmayan PII/metadata alanlarının bütün varyasyonları dahi bu dar read-only gözlem işinin kapanışını bekletebilir. Tüketilen alanların sıkılığı ile sağlayıcının kullanılmayan tüm alanlarını doğrulama gereğini ayrı değerlendirmek gerekir.

## Karar önerisi

### 1. Nihai ürün sınırı tüketici sözleşmesidir

Platform discovery için aynı kapalı, tipli **PlatformContextDiscovery v1** gözlem varyantı nihai read-only ürün sınırı olur. İç sözleşme adı platform-discovery-observation-v1’dir; bu bir provider API sürümü veya server attestasyonu değildir. Kullanıcı config/API/CLI’den sözleşme sürümü, kanıt veya verified flag enjekte edemez. Mevcut Result, Context, Plan, credential/capability ve state şemaları değişmez.

Kanonik raw tüketim referansı endpoint bazında me success/data/id, organization items/total/id, bare project list id/org_id ve seçili detail bare/zarf/id-route kurallarını aynen korur. Tüketilen control ve alanlar strict; zorunlu alan, tür/null/ID, duplicate/limit veya logical-success hatası invalid_response olur. Tüketilen alanda unknown enum/şekil sessizce düşürülmez veya başka envelope denenerek başarıya çevrilmez.

Bütün ham yanıt için strict UTF-8/JSON, duplicate/nonfinite, byte/depth/node/header/chunk ve **tam raw-tree sır taraması** aynen sürer. Tüketilmeyen alan/control ayrımı açık kalır: root success asla atılan metadata değildir. Seçilen detail şeklinin dışındaki id/org_id/data alt ağaçları da muaf protokol anahtarı değildir. Tüketilmeyen metadata doğrulama/sır sınırlarından geçtikten sonra atılır; public DTO strict/frozen/extra=forbid kalır, ortak decode_response gevşetilmez. Ad/email/telefon/profil/ham role/admin_permissions yayımlanmaz. Reported ID’ler kişiye bağlanabilir; tüm PII ayıklama iddiası yoktur.

**Açık değişiklik:** ADR-0021’in nihai üretim yoluna whole-raw katı decoder geçişi ve bütün bilinmeyen ham metadata alanlarını reddetme zorunluluğu bu consumer için kaldırılır. Ara projeksiyon-only yaklaşımı, yukarıdaki tam güvenlik ve sıkı tüketilen alan sınırıyla bilinçli nihai tüketici politikası olur. Bu, mevcut kapıyı geçmiş gibi işaretlemek değil kabul kapsamını değiştirmektir. Kullanılmayan35 profil alanının bütün server varyasyonlarını tahmin eden ham model yazılmaz. Sonraki yetki/yazma tüketicileri için aynı istisna verilmez.

### 2. Bilinmeyen auth/kimlik/tamlık kabul edilebilir ürün sonucudur

Bu ürünün başarılı sonucu uzak doğrulanmış context değildir. Public authentication=unknown, validation=unverified, authorization_scope=null, provider principal/account/org/project=null, identity_status=unverified ve consistency=not_guaranteed sabitleri korunur. Reported identity ID’leri yalnız tanımlı wire yollarından gelir; principal/user/account/üyelik olarak yorumlanmaz. Local credential binding sadece kullanılan yerel snapshot’ı tanımlar, server’ın anahtarı doğruladığının kanıtı değildir.

**Açık değişiklik:** P02-0d kartının verified teslimi, provider principal/account/pagination ve key-auth semantiği bilinmediği için tek başına engellenmez; bu bilinmeyenlerin doğru kapalı çıktısı ve güvenli davranışı ürün kabulü olarak sınanır. İş kartı verified ile public validation=unverified farklıdır. P02-0b başlığı ve kapsamı bu gözlem sınırıyla aynı commit’te hizalanır; tamamlanmış doğrulanmış kimlik/izin resolver’ı iddia edilmez.

Yeni6 çağrılık key/no-key karşılaştırması yalnız kendi normalized origin/API kökü, üç endpoint/default parametre ve tarih kapsamındaki davranış kanıtıdır. İyi biçimli invalid-key testi yerine geçmez; böyle bir anahtar üretmek için sözdizimi tahmin edilmez. Normal discovery’ye no-key veya negatif kontrol eklenmez. Auth kontrolünün yokluğu veya farklı sonucu metadata’dan permission/verified üretme nedeni olamaz. Farklı custom host’a gözlem kanıtı miras verilmez; public unknown sabitleri korunur.

Listeler en çok128 kayıtla sınırlı kalır. total>count incomplete; total=count en iyi unknown; projects completeness unknown. Cursor/Link veya tahmini limit/offset takip edilmez; output tam envanter diye sunulmaz. Provider’ın tamlık sözleşmesi veya pagination desteği daha sonra gerçek ihtiyaçla açık tüketici kararı olarak eklenebilir; bu read-only sürümün gizli bitmemiş implementasyonu sayılmaz. Veri aktarımı/katalog tam taraması kendi kapsam ve kabulünü ayrıca gerektirir.

### 3. Değişmeyen platform güven ve etki kapıları

No-init mevcut store, tek service/credential/config snapshot, ağ sırasında kapalı DB transaction/lock, final credential ID/revision/epoch/clock-generation/deadline kapısı korunur. Ürün normal3 GET; çözümlenen profil/override projesi varsa4 GET, en çok8 attempt/30 s/4 MiB, response1 MiB/output256 KiB; mevcut state5 s/lock1 s ve P01 retry/cleanup/iptal/UTF-8 kuralları aynıdır.

Provider read başarısı, hesap/proje seçimi, role, toplam veya gözlenen bir ID **execution/admission/permission kanıtı değildir**. ADR-0013 bağımsız otorite ve ADR-0014/0016 son yetki/credential kontrolleri değişmez. Public producer draft/blocked kalır; bu kararla upload/inference/ücretli export/terms accept/proje oluşturma/silme veya browser JWT fallback açılmaz. Sonraki yan etkili tüketici kendi endpoint/yetki/idempotency/fiyat sözleşmesini ayrıca kapatır; discovery bunu onun yerine yapmaz.

### 4. Dolu/seçili proje canlı kabulü korunur

Bu öneri **dolu proje ve seçili detail gerçek kabulünü kaldırmaz**. Yeni koşudaki boş dizi nonempty/detail consumer’ını kanıtlamaz; sentetik testler de canlı kabul yerine geçmez. Mevcut uygun projeden kullanıcının belirlediği bir örneğin aynı key’le görünmesi ve doğru ID’nin detail yolunda dönmesi gerekir. İlk proje kullanıcı seçimi diye otomatik alınmaz, config yazılmaz. Key’le liste boşken nedenin proje yokluğu/yetki/filtre olduğu varsayılmaz.

Kullanıcıda uygun proje yoksa yaratma bu ADR ile yetkilendirilmez; önce ayrı somut test kaynak/etki/varsa maliyet planı ve kullanıcının açık yetkisi gerekir. Yalnız bu koşul açık kaldığında kartın eksik live dalı açık kalır; resmi şema talebiyle aynı belirsiz dış beklemeye birleştirilmez. Bu karar onaylansa bile proje kabulü kapanmadan P02-0d/P02-0b/P02-0 verified yapılmaz.

## Kabul ve uygulama sırası

1. Kullanıcı bu ADR’yi onaylar. ADR-0020/0021 forward notları ve karar indeksi yalnız Platform raw/kapanış kapsamındaki partial amendment’ı gösterir; önceki kararlar bütünüyle Superseded olmaz. Kanonik referans, P02-0d/0b, plan/current/faz/matris ve kullanıcı anlatımı birlikte hizalanır.
2. Mevcut tüketici kodu yeni nihai sözleşmeyle karşılaştırılır. Mevcut doğru uygulama sırf yeni bir kod adımı üretmek için yeniden yazılmaz. Eksik kontrol/oracle varsa gerçek consumer’da minimal geliştirme ve anlamlı regresyon yapılır; ortak codec gevşetilmez. Formal provider şeması veya kullanıcı rolü icat edilmez.
3. Me/org/empty-project gerçek public API sonucu, schema/Identifier/total predikatları, key/no-key status ve tam sayaç/deadline receipt’i kanıt olarak bağlanır. Kaynak/probe/receipt hash’i gözlem kimliğidir; bağımsız attestation değildir. Önceki başarısız veya limit dışı koşular yeniden etiketlenmez; özel raw veri/ID/key repoya girmez.
4. Dolu/seçili proje gerçek kabulü kullanıcının belirlediği mevcut kaynak ve scoped bütçeyle tamamlanır. Yanıttaki ID eşliği ve parser sonucu değer yayımlamadan doğrulanır. Yeni resource veya key otomatik oluşturulmaz. Bu dal kapanmadan üst teslim verified olmaz.
5. Bağımsız fixture’larda boş/tek/çok/duplicate/128–129 kayıt, strict success/bool/int/null/missing, id-route/404/parent farkı, raw unknown metadata atımı ve içindeki secret, kısa secret/fixed protocol ayrımı, byte/deadline ve süreçler arası credential/reset/clock yarışları korunur. CLI/Python/text/JSON/NDJSON/UTF-8/pipe/SIGINT, local-only lazy ve state/schema6 uyumu denetlenir.
6. Her gerçek geliştirme adımı commit ve iki farklı fresh review turuyla kapanır. Son kaynakta gerekli test/statik/iki temiz kurulum ve kaynak bağlı M5 kanıtı; nihai tek development PR ve üç ortam CI tamamlanır. Kaynak değişmediyse eski geçerli kaynak kanıtı sahte yeni koşuya çevrilmez; kaynak değişirse yeniden ölçülür. Master/release kullanıcıdadır.

## Onay sonrası belge geçişi

| Belge | Değişiklik |
|---|---|
| ADR-0022 / karar indeksi | Gerçek kullanıcı onayıyla Accepted; read-only consumer sınırı ve dar partial amendment |
| ADR-0020/0021 | Yalnız Platform nihai raw/authority-document kapısında bu karara forward link; etki/yetki/live-proje sınırı korunur |
| ContextDiscovery referansı | Ara projeksiyonu nihai sınırlı tüketici sözleşmesi olarak anlat; public wire/sabitler ve kontrol/metadata ayrımı aynı |
| P02-0d/0b ve faz | Kapalı observed consumer kabulünü göster; doğrulanmış kimlik/izin işini bu paket yapılmış sayma. Dolu/seçili live dalı bitene kadar verified yok |
| Plan/current/matris/README | Kalan işin mevcut kod farkı + gerçek proje kabulü + final PR/CI olduğunu açık göster; kaynak/genel sağlayıcı doğrulaması iddia etme |

## Alternatifler

- **ADR-0020/0021’in mevcut nihai kapısını korumak:** Geçerli seçenek; onay gelmezse bu uygulanır. Daha fazla client araştırması sağlayıcının tüm principal/key/pagination sözleşmesini evrensel kanıtlamayabilir; dış kapı açık kalır.
- **Frontend davranışını aynen kopyalamak:** Seçilmedi. Web wrapper’ının esnek envelope/success/metadata davranışı Yörünge’nin strict tüketilen alan/control ve sır sınırını belirlemez.
- **Header yokken401’i key/principal verified saymak veya tahmini invalid-key üretmek:** Seçilmedi. Bu kanıt, header varlığına bağlı davranışı gösterir; anahtar değerinin doğrulanmasını veya kimlik otoritesini göstermez.
- **Dolu/seçili canlı dalı silerek paketi bitirmek:** Seçilmedi. Bağımsız gerçek consumer kabulü korunur.
- **Kısıtlı ve açık unknown tüketici sınırı:** Önerilen seçimdir. Kullanıcıya bugün elde edilebilen faydayı verir; güven iddiasını büyütmez, gereken yetkiyi gelecekteki yan etkiye taşımaz.

## Sonuçlar ve sınırlar

Bu değişiklik resmî OpenAPI eksikliğini read-only gözlem tüketicisinin tüm kapanışına bağlamayı bırakır. Karşılığı, ürünün hiçbir zaman doğrulanmış principal/izin veya tam uzak envanter iddia etmemesi ve consumer alan değişiminde kontrollü ret vermesidir. Bilinmeyen metadata atımı yalnız tam raw güvenlik taramasından sonra olur. İleride provider sözleşmesi gelmesi faydalıdır; bu öneri onun doğruluğunu önceden ilan etmez.

ADR halen Proposed’dır. Kullanıcının tersine mühendislik yetkisi araştırmayı açtı; bu yeni kabul/kapsam değişikliğinin onayı yerine kullanılmaz. Ürün/kart kapanışı bu belgeyle yapılmadı; seçili proje sorusu ayrıca açıktır.
