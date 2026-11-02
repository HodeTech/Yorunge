# Upload input ve current hazırlık sözleşmesi

**Tarih:** 2026-11-03. **Durum:** P02-2o.1 input/revalidation kodlandı, iki fresh tur bekliyor; o.2/o.3 henüz uygulama öncesi dar hedeftir. [Transfer](dataset-transfer.md#gönderilen-ve-doğrulanan-içerik), [v2 current gate](dataset-upload-v2.md), [provider](platform-upload-consumer.md) ve [HTTP bütçesi](dataset-upload-http.md) kanoniktir; public API henüz uygulanmış değildir.

## Yerel güncel içerik

Plan, approve ve original start'ın her biri manifestin tam dosya kümesini yeniden hash'ler; kaydedilmiş digest veya eski metadata tek başına inputs_verified değildir. Manifest parse ve kaynak hash no-follow/nonblocking descriptor, root/ancestor, ad/Unicode/üyelik ve hash öncesi/sonrası stat kurallarıyla P02-1 yolunu kullanır. Yerel validation kontrol noktaları en çok 30 s bütçedir; original total end daha erkense uygulanır. Upload alt kümesi 1–128 dosya, dosya başına 500.000.000 byte, toplam 1 GiB ve encoded manifest 256 KiB ile ayrıca sınırlıdır; boş envanter input_invalid, geçerli ama upload kotası üstü envanter input_budget_exceeded verir. Tam içerik eşliği yoksa input_changed; desteklenmeyen primitive ve özel dosya mevcut kontrollü input hatalarını korur.

Başarılı hash sonrasında private observation root anchor/device/inode, mutlak ancestor zinciri, bütün file stat/parent zincirleri ve dizin stat/üyelik kümelerini yakalar. FD tutulmadan immutable gözlem saklanabilir; her sonraki effect/current kapısında yeni descriptor'larla bütün bu metadata/üyelik ve root zinciri yeniden denetlenir. Yeniden açmada ENOENT/ELOOP/ENOTDIR gözlenmiş root/ancestor değişimi olarak input_changed verir; EACCES gibi gerçek okunabilirlik hataları file_unreadable kalır. İlk capture başlangıç hataları mevcut sınıflandırmasını korur. Bu ara recheck içerikleri yeniden hash'lemez ve yerel hash kontrolünün yerine geçmez. PUT kaynağı kendi güncel descriptor'ını açar ve gönderilen bütün byte/SHA-256/size eşliğini ayrıca doğrular. Gözlenmeyen değişimler/seri gözlem aralığı atomik snapshot veya düşmanca local sandbox değildir.

Private input observation PID/thread'e bağlıdır; aynı çağrının async/sync köprüsünde kullanılabilir. Kopyalanamaz/serialize edilmez, repr root/path/content dökmez. Recheck aynı immutable observation'ı taşır; yeni total end üretmez. Her kısa local recheck yeni dar I/O bütçesi alır, original total end'i genişletemez. Root/manifest/path dinamik değerleri seçili credential literal kuralıyla ağ/state/output öncesinde denetlenir.

## Warning üretmeyen request revalidation

Frozen/model_copy/model_construct kanıt değildir. Private request codec'i önce Python scalar/nested model verisini strict yeniden doğrular, sonra bounded canonical JSON model kontrolü yapar. Hatalı modeli warning yayımlayan serializer ile dışarı dökmez; warning-as-error ortamı ham UserWarning'e dönmez. Geçersiz girdinin repr'i, warning metni ve validation exception chain'i public hatada yer almaz. Ret invalid_request/2'dir; bilinen seçili literal kuralı ve fixed protocol key istisnaları değişmez.

## Provider ve kompozisyon dilimleri

O.2 zorunlu GET'leri aynı budget/session/credential üzerinden provider codec'ine bağlar; geçerli bildirilen context not_exposed üretir, grant/cost üretmez. Dataset bilindiğinde my-role upload etiketi zorunludur; read/metadata yetki kanıtı değildir. Exact hata/proof/freshness tablosu v2 referansında kalır.

O.3 private prepare/approve/revoke kullanım senaryolarını bu input/current gözlemlerine bağlar. Açık state init gerekir; captured scope/store/epoch/clock/credential son kısa transaction'da yeniden karşılaştırılır. Ağ veya tam hash boyunca SQLite store/deadline tutulmaz. Bu son iki dilimin tam internal imzaları kod başlamadan kendi reference maddeleriyle somutlaştırılır; burada henüz uygulanmış yüzey iddia edilmez.
