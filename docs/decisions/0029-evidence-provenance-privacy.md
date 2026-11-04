# ADR-0029 — Kayıpsız kanıtta tarihsel makine provenance’ı ve yeni çıktı gizliliği

**Durum:** Proposed; kullanıcı onayı bekleniyor. **Tarih:** 2026-11-04. **İş:** P02-2 / PR #14 kullanıcı review takibi. **Değişen sınır:** Belgeleme standardının kişisel yol yasağıyla ADR-0019/araştırma kanıtı standardının özgün baytları koruma kuralı arasındaki dar çatışma. Bu öneri bir genel PII istisnası, yeni hesap çağrısı veya geçmiş yeniden yazma yetkisi değildir. Bağımlı politika/kontrol kodu başlamadı.

## Bağlam

[Belgeleme standardı](../standards/documentation.md#tek-kaynak-ve-doğru-durum), kişisel mutlak yolların ve özel verinin repo belgelerine yazılmamasını ister. [Kanıt standardı](../standards/research-evidence.md) ve [ADR-0019](0019-reference-startup-performance.md) ise başarılı/başarısız özgün raporları, byte/hash ilişkisini ve kayıpsız kalıcı arşivi korur. Geçmişte üretilmiş ölçüm raporları kurulu interpreter, wheel, çalışma kökü ve komut yollarını; bazı eski CI özetleri Git author e-posta metadata’sını taşır. Bunları sonradan değiştirip aynı ölçüm diye sunmak dürüst olmaz. Değerlerin sır olmaması kişiye bağlanabilirliklerini ortadan kaldırmaz.

[Dar envanter](../research/p02-2-evidence-provenance-inventory.json), fd083a2’deki 442 arşivden bilinen yerel hesap yolu veya mevcut yayımlanmış Git author e-posta literal’iyle eşleşen 90 arşivi ad/content SHA-256/gzip SHA-256 ile sabitler: 87 yol, 8 e-posta, örtüşenler vardır. Literal değerler envantere kopyalanmaz. Bu tarama yalnız ilan edilen bilinen değerleri özgün açılmış JSON baytlarında arar; genel PII/secret sınıflandırması veya base64 içindeki ZIP/gömülü yüklerin tam taraması değildir. Envanter bulunmuş sır sızıntısı kanıtı değildir.

## Önerilen karar

1. **Dar tarihsel retention:** Envanterde ad ve her iki SHA-256’sı birebir kayıtlı özgün raporlardaki sır olmayan makine provenance’ı, kullanıcı bu kararı onaylarsa tarihsel kabulün incelenebilirliği için korunur. Kapsam yerel çalışma/interpreter/wheel/komut yolları ve yayımlanmış Git author kimlik metadata’sıdır. Dataset içeriği, özel müşteri/hesap profili, key/token/password, signed URL veya özel analiz arşivi bu istisnaya girmez. Onay bir raporun içindeki her başka alanı güvenli ilan etmez.
2. **Özgün byte ve geçmiş:** Mevcut gzip’ler, content hash’leri, başarısız örnekler ve ölçülen source kimliği değiştirilmez. İndeks/original_commit gibi yanlış katalog metadata’sı, özgün içeriği değiştirmeden kanıtla düzeltilebilir. Git history rewrite/force push yoktur. Daha sonra gerçek sır veya istisna dışı özel veri bulunursa bu karar onu meşrulaştırmaz; ilgili içerik için ayrı somut müdahale gerekir.
3. **Yeni raporlar:** Yeni yerel ölçüm/kurulumlar kişiye özgü home/checkout adı taşımayan kontrollü çalışma kökünde üretilir. Kaynak, kurulu paket ve fixture doğrulaması korunur; önce rapor üretip path’leri değiştirerek hash ilişkisi yeniden etiketlenmez. Kaynak koduna nötr sabit yol veya sahte makine kimliği gömülmez.
4. **Arşiv öncesi sınırlı kontrol:** Yeni producer raporlarında ilan edilmiş kişisel home/hesap yolu ve gereksiz Git author e-posta alanı aranır; beklenmeyen eşleşme public arşivden önce reddedilir. Üretilmiş özgün çıktı yerel özel çalışma alanında korunur, sessiz redaksiyon/başarı üretilmez. Genel secret/PII detector garantisi verilmez; bilinen credential literal kuralı ve özel analiz referans yasağı ayrıca geçerlidir.
5. **CI kaynak seçimi:** Yeni CI arşivi için gerekli özgün measurement/receipt/witness/installation ve source/artefakt hash bağları korunur. Tüm API yanıtını, PR gövdesini veya bütün job logunu toplamak zorunlu değildir; gereksiz kişisel alanlar türetilmiş özete alınmaz. Gerekli özgün kanıtın kendisi istisna dışı kişisel veri içerirse otomatik yayımlama durur; yeni rapor bu tarihsel 90 kayıt istisnasına kendiliğinden eklenmez. Seçilmiş kanıt kapsamı açık yazılır; tam ZIP/log saklanmadıysa saklandı denmez.

Bu ayrım yeni bir performans/kurulum rapor biçimi veya yeni ürün wire sürümü gerektirmez. Envanter araştırma metadata’sıdır, ürün girdisi veya yetki kanıtı değildir. Manifestteki 90 kayıt üst sınırı yeni arşiv geldikçe büyütülmez; farklı ad/hash ile yeni rapor otomatik grandfather edilmez.

## Alternatifler

- Tarihsel özgünleri yalnız özel alanda tutup public kaydı projection olarak yeniden sürümlemek: gizliliği artırır fakat bugün public olan kanıtın bağımsız yeniden incelenebilirliğini ve katalog bağlantılarını değiştirir; bu öneri seçmez. Kullanıcı retention’ı uygun bulmazsa ayrı somut geçiş tasarımı gerekir.
- Bütün arşivleri sonradan redakte edip mevcut ölçüm diye tutmak: özgün byte/hash sınırını bozar; seçilmez.
- Bütün geçmiş/gelecek kanıt metadata’sına sınırsız istisna: kişisel veriyi normalleştirir; seçilmez.
- Gizlilik kontrolünü genel e-posta/path regex’iyle bütün sırları tespit ediyormuş gibi anlatmak: kapsamı kanıtlamaz; seçilmez.

## Sonuçlar ve uygulama kapısı

Onay sonrası belgeleme/kanıt standartlarında dar tarihsel istisna ve yeni üretim öncesi/sonrası kontrolün sahibi açık yazılır. Arşiv katalogunun v1 byte biçimi, geçmiş gzip’ler ve native kabul eşikleri değişmez. Yeni nötr çalışma kökünde source-bound kabul gerçek kaynak ve kurulu paket eşliğiyle yeniden üretilir; önceki başarısız ölçümler korunur.

Kabul: envanterdeki her ad/digest’in katalogla eşliği; sır/özel analiz referansı için istisna olmaması; yeni raporun known-personal-path/e-posta negatifinde public yazı olmaması; nötr workspace pozitifinin gerçek source/kurulum/oracle kapılarını geçmesi; original_commit düzeltmesinde gzip/content byte değişmemesi. Kontrol genel PII temizliği sayılmaz. Belge revizyonu iki farklı fresh review turundan sonra kullanıcı onayına sunulur; onay gelmeden retention istisnası veya bağımlı araç politikası uygulanmaz. Bağımsız ağ/receipt/UX/test bugfix’leri bu kararı beklemez.


**Öneri review kapanışı:** d5f04c5 sabit metni fresh R1 Sol/high ve farklı fresh R2 Astra/high salt okunur değerlendirdi; doğrulanmış bulgu yok. R2 442 katalog kaydında 90 benzersiz envanter adı ve iki digest’in eşliğini, 90 gzip’in byte SHA-256’sını teyit etti; ham içerik veya literal taraması tekrar edilmedi. Bu review kullanıcı onayı değildir; karar Proposed kalır.
