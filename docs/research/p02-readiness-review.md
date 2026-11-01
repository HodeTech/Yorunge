# P02 fazına geçiş hazırlık incelemesi

**Tarih:** 2026-10-30. **İnceleme tabanı:** `5e5b53941c9eb2e431177ae18879cecd223b2823`, `feat/p02-0a-sdk-pilot`; development `bc9532c`. **Yetki:** Faz/bağlı belgeleri incele ve gerekli hazırlık düzenlemelerini yap. Ürün implementasyonu, canlı hesap veya ücretli pilot bu çalışmaya dahil değildir.

## Sonuç ve hazır olma sınırı

P02 ürün yönü P01 ve benimsenmiş mimariyle uyumludur. Önceki belge epik seviyesinde yararlıydı; gerçek upload/çıkarım uygulamasına doğrudan geçmek için yeterli değildi. Hazırlık eksikleri giderildi: ilk [P02-0a araştırma kartı](../roadmap/tasks/p02-0a-contract-sdk-pilot.md) `ready`; diğer uygulama işleri somut endpoint/karar/kart kabulünden önce `draft` kalır. Böylece faza **araştırma adımıyla başlanabilir**; bütün fazın tek seferde kodlanabileceği iddia edilmez.

Bu tur yeni mimari tercihi benimsemedi. Signed URL/stream upload güven sınırı, çok aşamalı kalıcı transfer ve gerekiyorsa plan/bütçe değişikliği için araştırma/ADR kapıları görünür hale getirildi. Seçenekler güncel sözleşme araştırmasında somutlaşınca yeni ADR kullanıcı onayına sunulur; bağımlı kod onaydan önce başlamaz. Mevcut Accepted ADR’lerin anlamı değiştirilmedi.

## Kapsam ve yöntem

- Roadmap README, P02, current, task şablonu/indeksi, backlog ve P01 kapanış/bağımlılıkları okundu; P03/P04 sınırıyla karşılaştırıldı.
- Ürün kapsamı, capability matrisi ve kullanıcı yolculukları; identity/datasets/catalog/inference/compute/artifacts modülleri; mimari ve ilgili güvenlik/UX/test/performans/belgeleme standartları incelendi.
- Referans HTTP/stream/execution/operation/local-state ve Accepted ADR-0010/0016/0017/0018’in ilgili kuralları mevcut kodla karşılaştırıldı. ADR-0014/0015’in plan/migration sınırları referans ve tüketici üzerinden kontrol edildi.
- Kodda `application/http_transport.py`, `application/execution.py`, `application/operations.py`, `domain/execution.py`, `adapters/input_files.py` ve `api.py` üzerinden gerçek P01 sınırları doğrulandı. Bu, bütün ürün kodunun yeni tam review’si değildir.
- İlk geçişte kapsam/bağımlılık/teslim; ikinci geçişte sır, etki, dosya bütünlüğü, kesinti, kaynak bütçesi ve kanıt iddiaları ayrı değerlendirildi. Son diff’in durum/bağlantı/kart uyumu ayrıca denetlendi. Bu tur bağımsız review ajanı çalıştırılmadı; çok boyutlu inceleme aynı ajan tarafından yapıldı.

## Bulgular ve alınan aksiyonlar

Öncelikler belge hazırlığının geliştirmeyi yanlış yönlendirme etkisidir; uygulanmış üründe yeni güvenlik açığı veya üretim hatası saptandığı anlamına gelmez. Taban bağlantıları değişiklik öncesi metin/kodu sabitler. Bazı konular önceki belgede risk olarak anılıyordu; burada eksik olan ilk tüketici/karar/kabul bağının kapatılmasıdır.

| Kimlik | Doğrulanan hazırlık açığı | Etki ve yapılan düzenleme |
|---|---|---|
| R1 / P2 | [P02 başlangıcı](https://github.com/HodeTech/Yorunge/blob/5e5b539/docs/roadmap/phase-02-data-and-inference.md#L3) tümüyle draft; ilk araştırmanın ayrıntılı kartı yoktu | P02-0a kapsamı, kanıtlı P01 bağımlılıkları, yedi kabul maddesi ve teslim sınırıyla hazırlandı. B03/B04 çözümünün araştırmanın önkoşulu sanılması önlendi; araştırma ile hesap pilotu ayrıldı |
| R2 / P2 | [HTTP portu](https://github.com/HodeTech/Yorunge/blob/5e5b539/src/yorunge/application/http_transport.py#L186) bytes request ve göreli hizmet endpoint’i kabul ediyor; P02 büyük upload/signed URL tüketiyor | P01 raw response ölçümünün upload desteği sanılmaması için stream request ve depolama hedef/secret/expiry/redirect kararı P02-2b/3b önkoşulu oldu. Mevcut HTTPS/443 ve secret sınırı gevşetilmedi |
| R3 / P2 | [Dispatch akışı](https://github.com/HodeTech/Yorunge/blob/5e5b539/src/yorunge/application/operations.py#L246) tek arm/start/latch; P02 create/presign/PUT/confirm ve resume istiyor | Çok aşamalı aktarımın kalıcı kimliği, her fazın replay/unknown/correlation modeli P02-2a öncesi karar çıktısı oldu. Yeni attempt ile ikinci gönderim veya kör create tekrarı yasak sınır olarak korundu |
| R4 / P2 | [Execution bütçeleri](../reference/execution-plan.md) ≤128 input/64 KiB plan ve 1 GiB/30 s çağrı; P02 klasör/büyük aktarım kapsamı sayısal hazır karta bağlı değildi | Büyük manifest bağı, dosya/adet/byte kuyruğu, validation–transfer deadline ayrımı ve etki öncesi kapasite kontrolü ilk tüketiciye atandı. Mevcut kotalar/eşikler yükseltilmedi |
| R5 / P2 | [Faz bağımlılıkları](https://github.com/HodeTech/Yorunge/blob/5e5b539/docs/roadmap/phase-02-data-and-inference.md#L9) P02-4/5’i bütün P02-0/4’e bağlıyor; indirme portunun alt sahibi yoktu | Hizmet alt kabulü ve somut bağımlılık ID kuralı eklendi. Katalog okuma ağırlık indirmeyi beklemiyor; P02-3b ortak güvenli indirme, P02-4b tüketicisi oldu. Yerel audit/LLM/compute hatları gereksiz upload/Platform kapısından ayrıldı |
| R6 / P2 | [Faz kabulü](https://github.com/HodeTech/Yorunge/blob/5e5b539/docs/roadmap/phase-02-data-and-inference.md#L34) genel “native çıktı” diyor; stream/embed/rerank/vision, weights ve compute kapanışı yeterince izlenemiyordu | P02-2a–6b sabit alt ID’ler, P02-7 bütünleşik kapanış, görev/negatif/kanıt matrisi eklendi. Erişim kapalı sonucu araştırmayı kapatabilir; entegrasyonu verified yapamaz. Kapsam azaltımı açık kullanıcı kararına bağlandı |
| R7 / P2 | [P01 stream sınırı](../reference/stream-results.md#p01-kabulünün-sınırı) SSE/EVREN codec’i içermiyor; P02 stream ve ücretli inference tüketiyor | P02-5b SSE framing/terminal/usage/message EOF eşlemesine ayrıldı. Inference POST, model warmup ve stream retry’sinin salt okuma sanılmaması; bilinmeyen maliyetin sıfır sayılmaması açıklandı |
| R8 / P3 | [PR kuralı](https://github.com/HodeTech/Yorunge/blob/5e5b539/docs/roadmap/README.md#L37) P01’e özgü; P02 alt paketleri PR sınırı gibi de okunabiliyordu | P02 araştırma/hesap ayrımı ve sonraki epik PR varsayılanı yazıldı. Alt kart/commit/review ile PR sınırı ayrıldı; büyük işi gerekçeli bölme ve önce ilan etme kuralı korundu |
| R9 / P3 | P02 faz yeteneklerinde C01/C02 uzak alt küme yok; C07 hedefi P02/P03 belirsizdi; [P03-1](../roadmap/phase-03-training-and-tools.md) bütün P02-3’e bağlıydı | C01/C02/C13 faz bağı eklendi; C07 predict P02-5e, eğitim C08/P03 olarak netleşti. P03-1 somut P02-3c veri sürümü ve Platform kabulüne bağlandı; B04 eğitim kısmı P03’te korundu |

R1–R9 hazırlık düzeyinde ele alındı. Karar çıktıları uygulandı veya pilot geçti diye kapatılmadı. Sözleşmelerde aynı kuralı çoğaltmak yerine P02 tablosu ilgili kanonik HTTP/operation/execution/stream ve standarda bağlanır. İş kartı ayrıntılı araştırma kabulünün tek sahibidir; current/indeks yalnız sırayı ve durumu gösterir.

## Dış kaynak kontrolü

30 Ekim’de kamuya açık [EVREN kılavuzu](https://evren.ssyz.org.tr/guide), [LLM OpenAPI](https://evren-llmapi.ssyz.org.tr/openapi.json) ve [SDK PyPI metadata’sına](https://pypi.org/pypi/evren-sdk/json) credentialsız GET yapıldı. Web okuyucusu ilk iki adrese erişemedi; yerel Python HTTPS GET’i üçünü de HTTP 200 olarak aldı. Gövde boyutu/hash, şema path sayısı ve dağıtım kimlikleri [kaynak kaydına](evidence-register.md#p02-hazırlığında-dar-güncellik-kontrolü--30-ekim-2026) eklendi. Token/env veya kullanıcı hesabı kullanılmadı.

LLM şeması 26 Ekim’deki 30 path ve `200e493…` hash’inden bu kontrolde 33 path ve `5ba9b1b…` hash’ine değişmiştir. Bu yalnız güncellik farkını kanıtlar; bütün yeni endpoint’lerin public/destekli olduğu sonucu çıkarılmaz. Kılavuzun dönen HTML’i istemci kabuğudur; tam Platform sözleşmesi doğrulandı denmez. [SDK açıklamasındaki](https://pypi.org/project/evren-sdk/) retry/idempotency iddiası da Yörünge’nin Accepted retry politikasını veya gerçek gateway davranışını kanıtlamaz.

Bu dar kontrol P02-0a’nın endpoint matrisi, SDK kaynak/lisans/timeout/stream denetimi veya yetkili pilotu yerine geçmez. Ham HTML/OpenAPI/bundle kopyaları genel review bağlamına/repoya alınmadı; kişisel arşiv kullanılmadı.

## Önerilen iş akışı

1. P02-0a: tarihli sözleşme/SDK araştırması, seçenekler ve gerekiyorsa Proposed ADR, kapsamlı fakat küçük pilot **planı**. İlk teslimin canlı hesap gerektirmeyen kısmı başlayabilir.
2. Yeni ADR gerekiyorsa somut belge kullanıcıya sunulur; onaydan sonra yalnız bağımlı uygulama açılır. P02-0b hesabın gerçek salt okunur keşfini ve ilgili hizmetin context/yetki bağını kanıtlar. Mevcut yetki olmayan canlı pilot otomatik başlamaz.
3. P02-1 → 2 → 3 veri hattı; P02-4 → 5 katalog/çıkarım; P02-6 compute okuma, alt bağımlılıklara göre ilerler. Her yakın uygulama kartı ve paket planı koddan önce hazırlanır. Hazır olmayan büyük epik tek adım alınmaz.
4. Uygulama talebinde yetkilendirilmiş commit/review/fix döngüsü alt adımlarda yürür; son bütünleşik kabul P02-7’de kapanır. PR’lar development hedefli merge commit akışını korur; Master/release kullanıcıdadır. Bu hazırlık için ayrı PR açılmaz.

## Doğrulama ve kalan sınır

Hazırlık değişikliği yalnız Markdown’dır; ürün/CI/lock/test kodu ve kanıt arşivleri değişmez. Link/başlık/fence/anchor, skill/kart metadata ve diff boşluk denetimleri uygulandı. İlk metadata denetimi kabul matrisindeki üç etiketin iş tanımı gibi yinelendiğini buldu; etiketler düzeltildi, kimlik denetimi gevşetilmedi. Son sonuçlar:

- `.venv/bin/python scripts/check-docs.py`: 129 public Markdown, 0 sorun.
- `.venv/bin/python scripts/check-agent-guides.py`: 6 skill, 13 gerçek iş kartı, 0 sorun.
- `git diff --check`: geçti.
- Tek seferlik belge yapısı kontrolü: P02’de 25 tekil iş ID’si; yazılı P02 bağımlılıkları mevcut, epik–alt iş kenarları dahil döngü yok; yalnız P02-0a ready. Ana değişen roadmap/indeks tablolarında hücre sayıları tutarlı. Bu statik kontrol gelecekteki hizmet davranışını sınamaz.

Bunlar dokümandaki gelecekteki endpoint davranışını veya UX/performance hedefinin geçildiğini kanıtlamaz. Tam ürün takımı, build/kurulum, performans, canlı EVREN ve Mermaid görsel render bu turda çalıştırılmadı.

P02-0a başlamadan kullanıcıdan çözülmesi gereken yeni ürün kararı yoktur: araştırma seçenekleri hazırlamak içindir. İlgili ürün kartlarını açmadan çözülecek gerçek kararlar [fazın karar kapısı tablosundadır](../roadmap/phase-02-data-and-inference.md#p01den-devralınan-sınırlar-ve-karar-kapıları). “Faz başlangıcı hazır” ifadesi yalnız bu sıralı, sınırları belli süreci anlatır; erişim/SDK/aktarımı hazır ilan etmez.
