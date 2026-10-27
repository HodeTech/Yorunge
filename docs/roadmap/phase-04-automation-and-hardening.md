# P04 — Otomasyon, ileri görevler ve yayın kapısı

**Durum:** Planlandı. Tek büyük implementasyon veya bütün opsiyonel özellikleri tamamlama fazı değildir. İlgili önceki işin kanıtı ve her hat için ayrı ready kart gerekir.

## Bağımsız ve koşullu hatlar

| ID | İlk teslim sınırı | Önkoşul / açık kapı | Kabul kanıtı | Durum |
|---|---|---|---|---|
| P04-1 | Aynı çekirdeğe bağlı dar MCP görev yüzeyi | P01 sonuç/onay; seçilen görevin P02/P03 kabulü | Host yetkisi, bounded araç çıktısı, deadline/iptal ve CLI/API ile aynı kural | `draft` |
| P04-2 | Seçilmiş bir OCR/ses/ileri medya görevi | Model/görev/format sözleşmesi ve bütçe | Büyük girdi/çıktı, bilinmeyen model, yarım yanıt; her görev ayrı kart | `draft` |
| P04-3 | EVREN workspace execution | P03-6 olumlu erişim/ortam kanıtı | Atanmış GPU'da gerçek küçük iş, restart/süre sonu ve kalıcı artefaktı dışarı alma | `draft` |
| P04-4 | İhtiyaç doğrulanırsa terminal/yerel köprü | B08 kullanıcı gözlemi ve ADR | Yerel auth/framing/erişilebilirlik ve kaynak sınırı; varsayılan GUI projesi değil | `draft` |
| P04-5 | Seçilmiş bir rezervasyon/yayınlama/silme işlemi | İşleme özel yetki, önizleme ve uzlaştırma sözleşmesi | Bir işlem ailesi/PR; belirsiz etki güvenli; hesap şartı kabul edilmez | `draft` |
| P04-6 | Paket yayınına hazırlık ve kullanıcıya ait release kararı | Aşağıdaki zorunlu yayın kanıtı; B11/B12 | Kurulumdan kanıtlı kullanıcı sonucuna, recovery ve doğru sürüm/kapsam | `draft` |
| P04-R1 | C17 için registration/serving araştırması | B07; güncel resmî sözleşme ve gerekirse yetkili pilot | Destek kapsamı veya doğrulanamayan koşul; implementasyon ancak ayrı kapsam kararıyla | `draft` |

P04-1–P04-5/P04-R1 (M/L) ihtiyaca veya dış erişime bağlıdır. Release adayı bu yetenekleri vaat etmiyorsa bunlar P04-6'nın gizli zorunluluğu olmaz. Önceki fazın temel güvenilirliği veya performansı ise “hardening sonra” gerekçesiyle ertelenmez.

## Runtime kapısı

P04-3, yalnız notebook açılması veya CUDA/envanter görünürlüğüyle hazır olmaz. Kullanıcı/pilot hesabının auth, araç kurma, model/veri ağı, GPU tahsisi, kalıcı disk ve süre koşulları kayıtlı olmalı; küçük gerçek işten adapter/checkpoint ve kanıt ortam dışına alınmalıdır. İptal/süre sonu, bağlantı kaybı ve restart/maliyet uzlaştırması sınanır. Olumsuz sonuç dış kapı kaydıdır; kodun başka ortamı sessizce seçme gerekçesi değildir.

## Zorunlu yayın kanıtı

P04-6 bir yayın izni değildir; kullanıcıya review edilebilir release adayı hazırlar:

- Kullanıcının seçtiği sürüm kapsamı, ürünün ilk kullanılabilir hedeflerine ve capability matrisine tek tek bağlanır. Kapalı/ertelenen hedef açık karardır; kaynak dosya export'u serving diye sunulmaz.
- Vaat edilen görevlerde P01 ve ilgili P02/P03 kabulü vardır. Eğitim/araç desteği vaat ediliyorsa ForgeLM + en az bir muadil ortak SFT kanıtı gerekir.
- Gerçek wheel/sdist üyeleri, lisans, lock/build, temiz kurulum/import kökeni ve desteklenen OS/Python/araç sürümleri kanıtlıdır. Ajan materyali veya yerel arşiv runtime verisi gibi paketlenmez.
- Bozuk veri/ağ/disk, migration/restart ve unknown toparlanması; görev sonuçları/artefakt teslimi ve geri dönüş yolu sınanır. Temel aktarım/başlangıç bütçeleri [standarttan](../standards/performance.md) doğrulanır.
- Soğuk kullanıcı kurulumu ve tekrar eden iş gözlemi; süre/yardım/yanlış seçim ve çıktı bulunabilirliği release kartındaki hedeflerle karşılaştırılır. Henüz denenmemiş platform destekleniyor diye yazılmaz.
- B12 özel güvenlik ana/alternatif kanal doğrulaması tamamlanır. Sürüm, changelog, README, matris ve örnek komutlar aynı gerçek teslimi anlatır.

Master'a aktarım, tag/release ve dağıtım kullanıcı tarafından [Git/yayın standardına](../standards/git-release.md) göre yapılır. P04-6 kabulü bütün ileri görevlerin tamamlandığı veya paketin yayımlandığı anlamına gelmez.
