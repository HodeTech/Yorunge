---
id: P02-R9
phase: P02
status: draft
size: L
depends_on: [P01-5a, P02-0c]
capabilities: [C01, C02]
---
# P02-R9 — Kullanıcıya dönük ağ/TLS tanısı ve açık kurumsal CA/proxy yolu

**Tarih:** 2026-11-08. **Sahip:** P02 / transport ve doctor. [Şema yeniden okuması ve dış inceleme doğrulamasında](../../research/p02-llm-gateway-schema-review.md) bulunan boşluğun açık sahibidir; kendisi uygulama veya ready yetkisi değildir.

## Kullanıcı sonucu ve mevcut eksik

Zorunlu proxy, TLS denetimi veya özel kurum CA'sı olan bir ağdaki kullanıcı uzak komutlarda bağlanamaz ve nedenini göremez. Ortam proxy/CA/netrc değerleri bilinçli olarak yok sayılır ([ADR-0017](../../decisions/0017-bounded-http-transport.md), `trust_env=False`; testle korunur) ve açık bir seçenek yoktur. `transport_failed` DNS, bağlantı reddi, sertifika doğrulama ve protokol hatasını ayırmaz (zaman aşımı `transport_timeout` ile zaten ayrıdır). `yorunge doctor` uzak erişimi `not_checked` bırakır. Upload ve model indirme oturumunun (`TransferSession`) bağlantı havuzu çözülen adresi kendisi denetler ([ADR-0025](../../decisions/0025-isolated-storage-streaming.md)): adreslerden biri genel değilse (private, CGNAT `100.64.0.0/10`, loopback, karma küme) bağlanmadan `invalid_service_target` döner; split-horizon DNS, dahili ayna veya adres çeviren ağ geçidi/ZTNA olan kurumsal ağlarda upload ve `models download` bu kodla düşer. Kodun mesajı ("HTTPS adresini kontrol edin") kullanıcıyı yanlış yöne çeker: neden yapılandırılan adres değil, çözülen adresin politikaya uymamasıdır. Roadmap'teki eski "HTTP tanılaması P01-5" ifadesi yanıltıcıydı: P01-5 yalnız ortak taşımayı teslim etti. Kullanıcı belgesindeki sınır 2026-11-08'de [yazıldı](../../reference/http-transport.md#kurumsal-ağ-ve-ortam-proxysi); davranış değişmedi.

## Giren ve girmeyen kapsam

Girer (kullanıcı kararlarına bağlı alt kümeler): (1) `transport_failed` altında DNS / bağlantı reddi / TLS doğrulama / protokol için ve upload adres-politikası retinin (`invalid_service_target`, bugünkü yanıltıcı mesaj) ayırt edilmesi için sır, host ve ham URL içermeyen güvenli alt kod ya da neden alanı; (2) kullanıcının açıkça seçtiği, yapılandırmada adlandırılmış kurum CA dosyası ve/veya açık proxy hedefi (ortam değişkeni değil); (3) isteğe bağlı, açıkça istenen salt okuma ağ tanısı (varsayılan doctor ağsız kalır) ve sağlayıcının `/healthz`, `/readyz` uçları yalnız yardımcı sinyal olarak; (4) kullanıcı belgesi, hata kataloğu ve JSON şema güncellemesi.

Girmez: upload ve model indirme adres politikasını gevşetme veya kapatma (private/CGNAT hedefi bağlama; politika ADR-0025'in güvenlik sınırıdır, burada yalnız hatanın anlaşılır olması hedeflenir); TLS doğrulamasını kapatma veya doğrulamasız el sıkışmayla zincir okuma; başka güven kaynağını sessizce deneme; ortam proxy/CA'sını sessizce açma (`trust_env=True`); anahtar önek/biçim sezgisi; sağlık sonucunu yetki veya anahtar geçerliliği diye sunma; yeniden deneme politikasını genişletme.

## Bağımlılıklar ve kararlar

Koddan önce kullanıcı kararı ve ADR gerekir ([B16](../backlog.md)). (a) Yeni güvenli alt hata kodları [CLI hata kataloğunu](../../reference/cli-contract.md#p01-5-hata-kataloğu) değiştirir (sözleşme değişikliği, `yorunge-contract-change`). (b) Açık CA/proxy yolu ADR-0017'nin env/CA/proxy kararını kısmen değiştirir; proxy kimlik bilgisi, CA dosyasının güven kapsamı (servis ve depolama ayrımı, tek hedef mi tüm hedefler mi) ve ek kök olarak doğrulamanın açık kalması kararlaştırılmalıdır. (c) Ağ tanısı için sağlık uçları [ADR-0020](../../decisions/0020-service-bound-context-discovery.md) biçiminde endpoint kapsamlı hedef bağı ister. P02-3/4/5 bu işi beklemez.

**Boyut ve bölünme:** Kart L'dir; birbirinden bağımsız üç sonuç içerir ve ready'ye alınmadan önce bölünür: (i) hata kodu/neden ayrımı (adres-politikası reti dahil), (ii) açık CA dosyası ve/veya proxy, (iii) isteğe bağlı ağ tanısı. Bölünmüş her kart kendi kabulüyle ilerler; (i) diğerlerini beklemez.

**Açılma ölçütü ve hedef:** B16'daki alt kararların kullanıcı onaylı kısa Proposed ADR'si (veya ADR-0017 değişiklik notu). Hedef: P02-7 faz kapanışı ve ilk release önerisi öncesi; kurumsal ağ kullanıcısı gerçek bir engel olarak bildirirse öne alınır. Önerilen sıra: önce hata kodu ayrımı, sonra açıkça seçilen CA dosyası; proxy ve ağ tanısı sonra.

## Sözleşme ve uygulama sınırı

Mevcut: ortak taşıma (`trust_env=False`, redirect ve cookie kapalı), depolama taşıması (aynı ilke), `transport_failed`/`transport_timeout` eşlemesi. Kanonik referanslar [http-transport](../../reference/http-transport.md) ve [cli-contract](../../reference/cli-contract.md). Yeni alanlar/kodlar kapalı sözlüktür; `retryable=false`, ham host/IP/exception/sertifika içeriği yoktur. Kurum CA'sı bir güven köküdür: dosya yolu yapılandırmadadır, içeriği çıktıya veya state'e kopyalanmaz. Dosya adı ve alan adı önerisi uygulanmış sınıf iddiası değildir; ayrıntı kart ready'ye alınırken kapatılır.

## Kabul

Karar sonrası kesinleşir; en az: (1) gerçek TLS loopback sunucusunda yanlış CA, ad uyuşmazlığı, DNS başarısızlığı, bağlantı reddi ve upload'ta genel olmayan çözülen adres ayrı güvenli kodlarla görünür; adres-politikası reti için mesaj yapılandırılan adresi suçlamaz, politika bağlanmadan reddetmeye devam eder; ham host, IP ve sertifika çıktıda yoktur. (2) Seçilen CA dosyası olumlu, eksik/bozuk dosya kontrollü ret; ortamdaki `HTTPS_PROXY`/`SSL_CERT_FILE` hâlâ yok sayılır (mevcut regresyon testi korunur). (3) Varsayılan doctor ağ yapmaz; ağ tanısı yalnız açık istekle çalışır ve hiçbir sonuç kimlik/yetki kanıtı veya "doğrulandı" demez. (4) JSON/NDJSON/text tutarlıdır, exit kodu katalogla uyumludur. (5) İki fresh review turu olmadan verified olmaz.

## Doğrulama

Önce karar/ADR; sonra gerçek TLS loopback ve proxy CONNECT fixture'ı, hata kataloğu/şema sözleşme testleri, Ruff/strict mypy ve belge kontrolleri. Canlı EVREN çağrısı gerekmez; sağlık uçları kullanılacaksa kapsam, anahtarsız GET ve bütçe kartta yazılır.

## Teslim kaydı

Draft; uygulama, ADR veya kabul kaydı yoktur. Yalnız kullanıcı belgesi sınırı yazıldı (2026-11-08).
