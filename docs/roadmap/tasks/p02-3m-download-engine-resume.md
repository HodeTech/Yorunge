---
id: P02-3m
phase: P02
status: verified
size: M
depends_on: [P02-3k, P02-3l]
capabilities: [C03]
---
# P02-3m — İndirme motoru, resume kararı ve uçtan uca uyumluluk

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 12. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md); taşıma ve yazıcıyı birleştiren uygulama katmanı. Büyüme kuralı P02-3l ile aynıdır (s–z harfleriyle bölme).

## Kullanıcı sonucu ve mevcut eksik

Taşıma ve yerel yazıcı hazır olsa bile hangi durumda devam edileceği, ne zaman baştan başlanacağı, protokol dönüşünün (uygulanmayan resume → bir Range’siz istek) nasıl sayıldığı, seviyenin nasıl hesaplandığı ve hata/iptal önceliği tek bir yerde sınanmış olmalıdır.

## Giren ve girmeyen kapsam

Uygulama katmanı: iki aşamalı giriş — (1) **yerel durum** (hedef/stage/kilit/sidecar kararı, ağsız; tam-stage ise hiçbir ağ isteği olmadan yayın) ve (2) ağ koşusu (JSON çağrısından sonra imzalı GET), istek, kapalı yanıt tablosunun uygulanması, yazma, resume kararı (kimlik/ETag/boyut/ön ek özeti), tek protokol dönüşü, başlık ve tamamlanma checkpoint’lerinin sırası, beklenti karşılaştırması (uyuşmazlıkta stage/sidecar silme) ve yayın; bounded ilerleme sayacı; iptal/deadline önceliği (yayın adımları deadline dışı) girer. Model tüketicisi, CLI ve ölçüm araçları girmez.

## Bağımlılıklar ve kararlar

P02-3k ve P02-3l verified olmalıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) §2 yanıt tablosu ve §4 resume koşulları değişmez. Karar gerekmez.

## Sözleşme ve uygulama sınırı

Motor tek akışlıdır; devam yalnız çağrı yeniden başlatıldığında ve koşullar sağlanıyorsa olur. İmzalı URL’ye komut başına en çok iki GET vardır (ilk istek + resume uygulanmazsa bir Range’siz istek); bağlantı JSON çağrısı ayrı sayılır (ADR-0017 en çok iki deneme). Seviye ve kaynak P02-3j kurallarıyla hesaplanır; uyuşmazlık yayın öncesi 7. Hata sırası: iptal/uncertain önce, sonra yerel yazma, sonra beklenti, sonra uzak. İlerleme yalnız bayt sayısı/toplam taşır; URL, yol, ETag içermez.

## Kabul

Gerçek loopback TLS sunucusunda (Range/ETag/206/416 betiklenebilir) şu matris, her satır için hedefin son durumu ve istek sayısıyla birlikte: tam indirme; kesik → aynı komutla 206 devam; ETag değişti → baştan; Range’i yok sayan 200 → baştan (ek istek yok); `206` ETag/Content-Range/Content-Length uyumsuz → yarım içerik atılır + bir Range’siz istek, döngü yok; `416` → aynı; Range göndermeyen isteğe 206 → ret; güçlü ETag yok → yarım dosya tutulmaz; toplam değişti; gövde fazında erken kapanış ve kesik chunked (`download_incomplete`; zaman aşımı önceliği); tam-stage (hiçbir ağ isteği yok, JSON çağrısı dahil; revoke edilmiş anahtar yayını engellemez) ve aynı stage farklı hizmet hedefiyle (aynı sürüm UUID’si/biçim/hedef adı) tam-stage dahil hiçbir yoldan yayımlanmaz/devam etmez (kimlik anahtarı farkı → atılır, ağ koşusu); chunked tam gövdede tamamlanma checkpoint’i sonrası kesinti → sonraki koşu ağsız yayımlar; Content-Length uyuşmazlığı; kapanışla sınırlanan gövde reddi; beklenen boyut/SHA uyuşmazlığı → hedef yok ve stage/sidecar silinir (yeniden çalıştırma baştan indirir, ağsız exit-7 döngüsü yok); hedef var; `--no-resume` (sahiplik ✓ stage silinir, ✗ dokunulmaz); gövde bittikten sonra deadline aşımı → stage korunur ve sonraki koşu tam-stage satırıyla yayımlar; farklı süreçte kill sonrası devam. Her başarıda bağımsız hashlib oracle’ı eşleşir, devam başarısında ön ek yeniden hash’lenir, bellek sınırlı ve ilerleme birleştirilir.

## Doğrulama

Gerçek TLS + süreç integration testleri, Ruff, strict mypy. Native bellek/süre ölçümü P02-3o’dadır; canlı Platform kabulü P02-3n/3b’dedir.

**Gerçekleşen kapsam (P02-3m).** `adapters/download_engine.py`: `DownloadJob`, `run_download` (anlatım [referanstaki “Motor (P02-3m)” bölümündedir](../../reference/download-engine.md#motor-p02-3m)). Kararlar: yerel durum ağdan önce (`open_sink`; tam-stage’de JSON çağrısı dahil istek yok); en çok iki GET ve bir protokol dönüşü; gövde TLS kaydı geldikçe yazılır (tamponlama yok); deadline koşunun başında başlar, JSON çağrısı ayrı 30 sn’dir ve düşülmez; deadline `deadline=` ile çağıranın elindeki mutlak ana bağlanabilir (testler 30 sn’lik alt sınırı beklemez); ilerleme saniyede en çok on kez. Testler: `tests/integration/test_download_engine.py` (74), `test_download_engine_gaps.py` (52) `test_download_engine_r2.py` (24: ikinci turun 117 mutantından yaşayan 14 gerçek boşluk) ve `test_download_engine_kill.py` (2: ayrı süreçte SIGKILL, ilk checkpoint’ten sonra ve önce). Beklenti yalnız SHA-256’dır (`expected_sha256`); Kabul’deki “beklenen boyut” uyuşmazlığı ADR-0032 §5 gereği ertelenmiş boyut beklentisidir (`size_matched`) ve motorda yoktur. Birinci inceleme turu (R1) sonrası: anahtar işte değil oturumdadır (`TransferSession.secret`); oturum ve `deadline` yerel duruma dokunulmadan doğrulanır; çözümleyici bütçe + 1 sn sonunda motor tarafından bitirilir ve geri verilen süre bütçeyi aşamaz; gövde çerçevesi bittiği anda `complete(terminated=True)` yazılır (raporlardan önce); ilerleme alıcısı yazıdan önce çağrılır, geri gitmez ve tekrarlanmaz; test sayıları R2 sonrası yukarıdaki gibidir. İkinci inceleme turu (R2) sonrası: bir `DownloadJob.timeout` yalnız gerçek bir `int`’tir; çözümleyicinin bütçesi olay döngüsünün saatiyle (`asyncio.timeout`) ve işbirliğiyle uygulanır (iptali yutup geç dönen çözümleyici de `transport_timeout` ile biter); `TransferSession` kimlik bilgisinin türünü kurulurken sınar (`invalid_credential`); gövdesi uzunluğuyla tam yazılmış bir stage, etiketi olmasa da `complete()` öncesi gelen bir iptalde korunur (chunked gövde için bu tek olay döngüsü turu hâlâ bir sınırdır ve belgelidir); ilerleme alıcısının fırlattığı hata stage’i ancak devam ettirilebiliyorsa ya da tamsa korur; raporun yazıdan önce yapıldığı sıra zamanlayıcıdan bağımsız sabitlenir; hedefin üst dizinindeki kontrol/bidi karakteri istekten önce reddedilir; matris satırlarının istek sayıları testle sabitlenir; ikinci turun B gözden geçiricisi sonrası: gövde `complete()` kabul ettiği andan itibaren tamdır ve içindeki hiçbir hata (ikinci bir kesinti, G/Ç hatası) stage’i atmaz; ilk raporun gövdeden önce geldiği, hiçbir raporun yazıdan sonra yapılmadığı, varsayılan 1 sn payı, 0,1 sn’lik raporlama aralığı ve deadline sınırı, iş alt sınıfının iş sayılmadığı ve Unicode çift yönlü denetim sınırları testle sabittir; bağlantının havuzda takılması bir kesinti ile deadline’ın tesadüfü değil, gövde okunurken gelen her kesintidir (belge düzeltildi). Kartın “gövde bittikten sonra deadline aşımı → stage korunur” satırı şöyle gerçekleşti: taşıma gövde bitince deadline’ı söndürür ve yayın zamanlanmaz, bu yüzden deadline geçmiş bir gövde sonrası indirme **başarıyla** yayımlanır (test); gövdeden sonra gelen bir I/O hatası (örn. `full_sync`) tamamlanmış stage’i korur ve sonraki çağrı onu ağsız yayımlar (test).

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: uygulama [98dfa75](https://github.com/HodeTech/Yorunge/commit/98dfa7598c274ff054cb7344e3f88e51c32cdedc); test [5e0a334](https://github.com/HodeTech/Yorunge/commit/5e0a3342feaee8f1bdb9c813e757bcd44a69bbe9); R1 düzeltmeleri [84e4e88](https://github.com/HodeTech/Yorunge/commit/84e4e88cce6726bd08ab94a86bd4a7fad0114a76); R2 düzeltmeleri [dcd5ba6](https://github.com/HodeTech/Yorunge/commit/dcd5ba6892822f7c5fcc81b9f87e312decde3735), [4b288a4](https://github.com/HodeTech/Yorunge/commit/4b288a40474078b1e2e7687d843baa983c788106).
- Sonuç: İndirme motoru: yerel durum her istekten önce karar verir, en çok iki imzalı GET (yarım ön ek varsa `Range` + `If-Range`), gövde TLS kaydı geldikçe yazılır, deadline ve iptal önceliği, doğal hata önceliği; tam stage ağsız yayımlanır; gövde tamamlandığı an kayıtlıdır ve içindeki hiçbir hata stage’i atmaz (R1 ve R2 kapandı; Adım 17). Tam paket: 12.721 geçti, 1 atlandı, 0 düştü (`1b2cc1f`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Sapmalar: Kartın Kabul’ündeki “beklenen boyut” (`size_matched`) ADR-0032 §5 gereği ertelendi ve motorda yoktur; “gövde bittikten sonra deadline aşımı → stage korunur” satırı başka biçimde gerçekleşti (taşıma gövde bitince deadline’ı söndürür; geçmiş bir deadline sonrası indirme başarıyla yayımlanır).
- Kalan sınır: Canlı sağlayıcı gözlenmedi (gerçek ETag biçimleri, CDN kodlamaları); kayıt başına bir `os.write` maliyeti P02-3o/3z sayaçlarıyla ölçülür, kayıtları birleştirme kararı sessiz makinede alınacak ölçüme bağlıdır; Linux, uvloop ve gerçek TTY Ctrl-C denenmedi.
