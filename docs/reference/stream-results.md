# Akış sonucu sözleşmesi

**Durum:** Taslak; Proposed [ADR-0018](../decisions/0018-stream-results-and-cancellation.md)'e bağlı. NDJSON/iptal ürün uygulaması başlamadı. **Tarih:** 2026-10-29.

## Kapalı StreamEvent v1

Her olayın tam anahtar kümesi `schema_version`, `stream_id`, `sequence`, `event`, `operation_id`, `payload`'dır. Ek/eksik/duplicate alan, bilinmeyen sürüm, bool/float sürüm veya sıra, NaN/Infinity ve geçersiz UTF-8 reddedilir. `schema_version` strict integer 1; `stream_id` canonical UUIDv4; `sequence` strict integer 1..2^63−1, ilk 1 ve kesintisiz artar. Bir stream aynı stream_id ve bağlanmış operation_id'yi korur; başka invocation'ın olayları birleştirilmez. Operation ID canonical UUIDv4 veya null'dır; normal mevcut komutta null'dır. Yeni stream ID kalıcı resume/dispatch kimliği değildir.

| event | payload | Terminal |
|---|---|---|
| progress | Tam `{stage, completed, total}`; stage `connecting`/`receiving`/`validating`, completed strict integer 0..2^63−1, total aynı aralık veya null; total varsa completed≤total | Hayır |
| result | Çağrının beklenen domain modeline bağlı **mevcut Result v1**, status=completed/operation_id=null; serbest dict değil | Evet |
| error | Güvenli mevcut YorungeError/OperationError zarfı; bilinen code, o kodun kapalı details'i, operation ID bağlamla aynı | Evet |

Outer operation ID akışın bağlamıdır; Result v1'in null ID'sini değiştirmez. Error zarfında operation biliniyorsa aynı ID bulunur. Progress provider metni, prompt, raw URL, body/header, env adı veya secret taşımaz. Normal tek-sonuç komut başarıda progress üretmez; sequence=1 tek result emit eder. Metadata `--help`/`--version` makine akışına dönüşmez.

## Byte ve protokol kuralları

UTF-8 compact JSON, bir fiziksel satır ve sonunda LF; string newline'ı JSON escape olur. Tek encoded event LF hariç en çok **512 KiB**; producer serialize etmeden/çıktıya yazmadan sınırı ve tipi denetler. Decoder LF veya CRLF kabul eder; boş satır/BOM/lone CR/son LF'siz parça/protokol dışı byte reddedilir. Her record [HTTP/JSON yapısal sayım kuralını](http-transport.md#boyut-ve-süre) kullanır; depth32/node65.536 sınır fixture'ları sabitlenir. Bir satırın network chunk veya UTF-8 codepoint sınırında bölünmesi sonucu değiştirmez.

Progress'ler anında doğrulanıp publish edilebilir. Upstream decoder terminal adayını **HTTP response mesajı tam bitene kadar** bounded buffer'da tutar; trailing byte/event veya EOF yerine deadline hatası varsa completed publish etmez. Message EOF, TCP keepalive bağlantısının kapanması demek değildir. Tam bir terminal olmadan EOF `stream_interrupted`; terminalden sonra veri veya sıra/tip/kimlik bozukluğu `invalid_response` olur. Başlamış consumer akışında bu kusur tek güvenli terminal error'a çevrilir, ikinci terminal/başarılı özet eklenmez. Trusted local producer da terminalden sonra emit edemez.

Tüketici okumayı bırakırsa response/iterator context'i kapanır; bütün akış listede biriktirilmez. Aynı task/context ve tek total deadline boyunca okuma, decoder, callback ve backpressure uygulanır. Raw/decoded provider veri ürün stdout'una kendiliğinden akmaz. Bilinen secret canary'si aynı record'un farklı chunk'larında gelse de doğrulanmadan publish edilemez. Birden çok record'un anlamsal birleşiminden bütün PII/sırları çıkarma garantisi yoktur; uygulama provider metnini progress'e taşımaz.

## CLI, hata ve iptal sınırı

`--output ndjson` mevcut bütün normal CLI komutlarına opt-in seçenektir; `json`/`text` varsayımları ve public Python Result v1 imzaları değişmez. İlk event publish öncesinde hata stdout boş/stderr tek JSON; ilk tam publish sonrasında stdout bir terminal error ve aynı kontrollü exit, stderr'de ikinci JSON yoktur. Parser bu kuralı `--output=ndjson` ve iki argümanlı form için uygular. Kısmi çıktı mümkün olan I/O hatasında tamamlanmış event teslimi iddia edilmez.

Task.cancel/erken context çıkışı yerel okumayı bırakır. CLI SIGINT request_cancelled/6'dır; kesin yerel rollback veya uzak cancelled garantisi değildir. Critical publish/commit belirsizliği mevcut ilgili hata ve exit5'i korur. Dispatch latch sonrası start belirsizliği operation_uncertain/5; iş ID'si, kalıcı latch ve retry yasağı korunur. Salt izleme iptali kayıtlı işi provider_cancelled/unknown'a kendiliğinden taşımaz. Trusted provider observation ile kesin cancelled farklıdır.

BrokenPipe output_closed/6: stdout'a yeniden yazma yok, kaynaklar kapanır, safe stderr best-effort. Diğer output I/O output_write_failed/1. Önceden belirlenen operation/config belirsizliği exit5 önceliklidir; kalıcı terminal başarı output kırılmasıyla değişmez. CLI kapanış flush'ı ham traceback üretmez. Kütüphane CancelledError'ı cleanup sonrası yeniden yükseltir; bu CLI hata normalizasyonu değildir. Tek kanonik kod/exit/tetik tablosu [CLI referansındadır](cli-contract.md#önerilen-p01-5-hata-kataloğu).

## P01 kabulünün sınırı

Çok olaylı stream gerçek TLS loopback + ayrı süreç fixture'ında ortak ürün hattını çalıştırır. Kullanıcıya açık demo/network/run/watch/stop/reconcile komutu, EVREN endpoint codec'i veya SSE desteği eklenmez. Service adaptörü gelecekte kendi cevaplarını tipli modele dönüştürür. Ürün içindeki ortak codec/renderer'ın test kompozisyonunda kullanılması, test double'ın ürün backend'i olarak sunulması değildir.
