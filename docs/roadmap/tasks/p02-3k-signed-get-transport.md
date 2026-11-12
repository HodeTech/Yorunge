---
id: P02-3k
phase: P02
status: verified
size: M
depends_on: [P02-3j, P02-2f]
capabilities: [C03]
---
# P02-3k — İmzalı URL için kimliksiz, akışlı GET taşıması

**Tarih:** 2026-11-06. [P02-3 teslim planı](../p02-3-delivery-plan.md) adım 10. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) §2; ADR-0025’in kısmi değişikliği.

## Kullanıcı sonucu ve mevcut eksik

Mevcut storage portu yalnız PUT yapar ve 64 KiB yanıtla sınırlıdır; hizmet HTTP yolu imzalı query’yi yeniden kodlar ve DNS/public-IP korumasından geçmez. İmzalı bir model URL’sini kimlik göndermeden, güvenle ve akışlı okumanın tipli yolu yoktur.

## Giren ve girmeyen kapsam

Private `DownloadTarget` ve kapalı başlıklı `DownloadRequest`; ortak `TransferSession` üzerinde `download(consumer)` ve taşımada `open_download`; durum yorumu (200/206/416 için P02-3j’deki tipli `DownloadResponse`; hizmet görünümünün yalnız-2xx kapısı yeniden kullanılmaz; diğerleri kontrollü hata); Content-Length/chunked şartı ve tavan ön kontrolü; koşan sayaç taşımasının **yalnız gövde fazında** `download_limit_exceeded`a eşlenmesi (başlık fazı `invalid_response` kalır); gövde fazı kopmasının `download_incomplete`a eşlenmesi (zaman aşımı önceliği korunur); PUT penceresinden **bağımsız** GET penceresi (kullanıcı toplamı, 120 s PUT sınırı değişmez); kimlik/cookie/redirect yokluğu; guard uygulaması; literal-secret taraması girer. Dosya yazımı, engine, tüketici JSON çağrısı ve CLI girmez.

**Gerçekleşen kapsam (P02-3k).** `application/download_transport.py` (`DownloadTarget`, `DownloadRequest`, `DownloadView`, `DownloadTransport`) ve `adapters/storage_transport.py` (`TransferHttpxTransport.open_download`, `TransferSession.download`). Kararlar: `DownloadTarget` `StorageTarget._validate_url` ve yol/kod çözme denetimlerini yeniden kullanır (PUT yolu değişmedi); indirme ayrı bir oturum girişidir (`StorageTransport` protokolü değişmedi); tel isteği başlıkları tarif edilen (`public_headers`) listeyle karşılaştırılır; `Transfer-Encoding: identity` gibi HTTP yığınının kendisinin reddettiği çerçeve `transport_failed` olarak görünür (yine tek kapalı kod); `DownloadRequest.max_bytes` varsayılan 1 GiB’dir ve gövde sayacını sınırlar. R1 sonrası: gövde sonuna kadar okunup doğrulanınca deadline söner (tamamlanma checkpoint’i ve yayın taşıma tarafından zamanlanmaz; `view.complete`), `Content-Range` taşıyan 200 `invalid_response`dır (3j sözleşmesi), `DownloadTarget` bir parçasını kaybedemez. Çağıranın `max_bytes` sınırından büyük `Content-Length` gövde okunmadan reddedilir ve çağıranın kendi koddan çıkan `TimeoutError` aynen döner (yalnız pencerenin vuruşu `transport_timeout`tur). Testler: `tests/integration/test_download_transport.py` ve `test_download_transport_edges.py` (124; gerçek loopback TLS, sahte ağ akışları ve birim düzeyi: tel değişimi url/host/cookie/kimlik, başlık bloğunun tam sınırları, çok parçalı gövde ve sayaçlar, 5 s faz ve 1 s havuz bütçeleri, iki slotun paylaşımı ve sızmaması, GET penceresinin bağlantıya tam ulaşması, peer uyuşmazlığı, anahtarın imzalı adreste PUT hedefiyle aynı kuralla reddi, deadline sözleşmesi, giriş kapıları, iptalde bağlantının kapanması; ikinci tur mutasyon incelemesi 74 mutantın 49’unu ilk testlerin kaçırdığını gösterdi, bu dosyalar onları öldürür) ve `test_storage_transport.py` (39; PUT’un 120 s penceresi artık bir testle sabit); test sunucusu fixture’ına `omit_length` eklendi. Bilinen ve belgelenen: HTTP yığınının reddettiği çerçeveler `transport_failed` görünür (yukarıdaki referans bölümü); “imzalı adrese en çok iki GET” bu katmanda sayılmaz (her `open_download` tek fiziksel GET’tir, sayım motorun matrisindedir).

## Bağımlılıklar ve kararlar

P02-3j tiplerine ve P02-2f storage portuna bağlıdır. [ADR-0032](../../decisions/0032-bounded-download-and-verification-levels.md) Accepted’dir (2026-11-06); ADR-0025’in PUT kuralları (expiry zorunluluğu, header/yanıt sınırı, 120 s) değişmez, yalnız GET hedefi için `expires_at` aranmaz.

## Sözleşme ve uygulama sınırı

`DownloadTarget` ADR-0025 direct hedef kurallarını yeniden kullanır (HTTPS/443, ham query korunur, ≤16 KiB, userinfo/fragment/dot-segment/çift kodlama reddi, tek önceden bilinen origin, tüketici yol öneki — yanıt genişletemez). İstek başlıkları kapalıdır: yalnız `Range: bytes=N-` ve güçlü ETag’li `If-Range` ile `Accept-Encoding: identity` (isteğin kendi açık listesi; `Host`u HTTP katmanı ekler). Tek deneme; retry, proxy veya kimlikli fallback yok (protokol dönüşü motor katmanındadır). Servis ve indirme aynı iki slotluk havuzu paylaşır.

## Kabul

1. Gerçek loopback TLS: kimlikli JSON çağrısından sonra aynı origin’de (bağlantı yeniden kullanımı olsun olmasın) indirme isteği `X-API-Key`, Authorization, Cookie taşımaz; Platform ve LLM kimliği hiçbir koşulda eklenmez.
2. Kapalı başlık kümesi dışındaki her başlık, zayıf ETag ve çoklu aralık ağdan önce reddedilir; hazırlanan wire hedefi/headers descriptor’la eşit olmalıdır.
3. İstek sayımı: imzalı URL’ye en çok iki GET; bağlantı JSON çağrısı ayrı sayılır (ADR-0017). 3xx takip edilmez (`remote_failed`); Content-Encoding ≠ identity gövde okunmadan `invalid_response` olur; 401/403 `remote_access_denied`, 429 `remote_rate_limited`, 404/diğer 4xx `remote_failed` (tablo satırı satırına oracle; kapalı tablonun kanonik hâli indirme referansındadır); Content-Length ve chunked yokken kapanışla sınırlanan gövde reddedilir; `Content-Length` çağıranın sınırını ya da 1 GiB’ı aşarsa ön kontrolle (gövdesi okunmayacak `discard_and_retry` yanıtı hariç), koşan sayaç aşarsa gövde fazında `download_limit_exceeded` olur; kısa gövde `download_incomplete`, söz verdiğinden fazlasını HTTP katmanı söz verilen yerde keser (görünmez) ve çelişkili `Content-Length` yığının reddi olarak `transport_failed` görünür; 416 tipli sonuç olarak döner.
4. Yavaş/duran gövde faz ve toplam deadline ile durur (GET penceresi 120 s PUT sınırına takılmaz); iptal cleanup sonrası yayılır; private/karışık DNS ve peer uyuşmazlığı HTTP baytından önce reddedilir.
5. URL ham baytları korunur: **query’de** `%2F`/`%2B`/`%3D` geçerli, **path’te** `%2F` ve `%2e%2e` ret; 16 KiB aşımı ve literal-secret içeren URL parçaları reddedilir; URL/query hata, log ve repr’e girmez.
6. Mevcut PUT taşıma testleri ve ADR-0025 kabulü değiştirilmeden geçer.

## Doğrulama

Gerçek TLS/guard integration testleri, mevcut storage testleri, Ruff ve strict mypy. Yazıcı ve engine davranışı P02-3l/3m’dedir.

## Teslim kaydı

- PR/commit: tek development PR’ı bu daldan açılır (bağlantı PR açıklamasındadır); adım commit’leri `feat/p02-3-dataset-recovery` dalındadır: uygulama [8305b89](https://github.com/HodeTech/Yorunge/commit/8305b8927f8b9da5e2927a73c1902585634e5527); R1 düzeltmeleri [b7fe159](https://github.com/HodeTech/Yorunge/commit/b7fe159e6056464ff85ed931671a03f8a9cd506f), [dbbe740](https://github.com/HodeTech/Yorunge/commit/dbbe7409eef1969f0ae1d9e9b74070c09e2efb23); R2 düzeltmeleri [2f7c9b5](https://github.com/HodeTech/Yorunge/commit/2f7c9b53e93194dac026b7eaa640587e4255d4b4), [3b1c97e](https://github.com/HodeTech/Yorunge/commit/3b1c97e703636c2aff84d5cc93684f07eaf64444).
- Sonuç: İmzalı URL için kimliksiz, akışlı, tek denemelik GET taşıması: kapalı başlık kümesi, ham query baytları, guard, faz bütçeleri (5 sn bağlantı/okuma, 1 sn havuz), deadline ve iptal, kaynak sınırları; PUT yolu değişmez (önce/sonra farkı); gerçek h11/httpcore üzerinde kapalı yanıt tablosunun her satırı (R1 ve R2 kapandı; Adım 14). Tam paket: 12.716 geçti, 1 atlandı, 0 düştü (`9ab9d6a`, temiz klon, macOS; ilk tam paket 21 integration hatası, ilk üç CI koşusu 6 testte hata, bir admission yarış kusuru ve durum deposunda bir journal yarışı buldu, düzeltildi (açık kayıtlar araştırma kaydındadır); ayrıntı araştırma kaydındadır).
- Kalan sınır: Canlı sağlayıcı ve CDN davranışı gözlenmedi; Linux ve Python ≥ 3.12 hücreleri PR aşamasında sınanır.
