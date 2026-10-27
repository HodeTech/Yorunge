# Hizmet hedefi ve özel credential binding v1

**Durum:** Benimsenmiş — Accepted ADR-0012'nin bağlı sözleşmesi; Hedef kapısı, secret byte sınırı ve kalıcı binding/HMAC gözlemi uygulandı; gözlem ve reset/restore ikişer review turuyla doğrulandı. **Tarih:** 2026-10-27. [Kararın nedeni ve tehdit sınırı](../decisions/0012-credential-identity-and-change-detection.md) kanoniktir. Bu belge hedef eşlemesi ve HMAC bayt biçiminin tek kaynağıdır.

## Hizmet hedefi: service-target-v1

Plan, capability ve registry karşılaştırmasında aynı hedef normalleştirme kullanılır. Sonuç yalnız `service_origin` ve `api_base_path` ikilisidir; `service_id` ayrıca ayrılır. Normalleştirme idempotent olmalıdır; DNS/ağ/sır erişimi yapmaz. Geçersiz veya belirsiz girdi kontrollü hedef hatasıdır, başka hedefe fallback değildir.

1. Girdi mevcut v1 profilinin HTTPS/2048 karakter/hizmet ayrımı sınırlarını sağlamalıdır; kanonik tam URL de 2048 karakteri aşamaz. Userinfo, query/fragment ayıracı (boş olsa da), kontrol karakteri, boşluk, ters slash ve HTTPS dışı scheme reddedilir. Credential çözümlemesi için aşağıdaki daha dar hedef kuralları ayrıca uygulanır; bugünkü offline config parser'ı genişletilmiş/daraltılmış sayılmaz.
2. Host ASCII DNS adı, dört ondalık oktetli IPv4 veya köşeli parantezli IPv6'dır. DNS etiketleri 1–63 ASCII harf/rakam/hyphen, baş/son harf veya rakam; toplam en çok 253 karakter, boş etiket/son nokta yoktur. ASCII case küçültülür. Unicode host otomatik IDNA'ya çevrilmez; açık ASCII A-label kullanılabilir. IPv4'te baştaki sıfırlar reddedilir. IPv6, Python `ipaddress.IPv6Address(...).compressed` küçük harf temsiline getirilip köşeli parantezle yazılır; zone ID reddedilir.
3. Port yoksa veya sayısal 443 ise etkin port 443'tür; başka port reddedilir. Origin metni **443 içermez**: `https://host` veya `https://[ipv6]`. “Etkin port” ayrı bir origin yazımı değildir; mevcut `Scope.service_origin` alanıyla eşleme budur.
4. Boş path ve `/` → `/`; `/v1/` → `/v1`. Sonu `//` ile biten path ve literal `.`/`..` segmentleri reddedilir. İç `//`, path case'i ve diğer segmentler korunur; slash birleştirme/dot segment çözümleme yapılmaz. Path ASCII `pchar` (`A–Z a–z 0–9 - . _ ~ ! $ & ' ( ) * + , ; = : @`), `/`, geçerli `%HH` ve geçerli Unicode karakterlerinden oluşabilir. Raw Unicode UTF-8 yüzde kodlamasına çevrilir; NFC/NFKC uygulanmaz.
5. `%HH` hex harfleri büyük yazılır; yüzde kodlu unreserved karakterler **decode edilip eşitlenmez**. Yalnız doğrulama için tek kez UTF-8 çözülür; bozuk escape/UTF-8, çözülen kontrol/boşluk, kodlu slash/ters slash/dot/yüzde (`%2F`, `%5C`, `%2E`, `%25`, case bağımsız) reddedilir. Böylece belirsiz segment/double encoding kabul edilmez. `%31` ile `1` ayrı binding'dir; bu daha az cache paylaşımı pahasına ihtiyatlı ayrımdır. Kabul edilen kodlama isteğe aktarılırken tekrar decode edilmez.

Host/port/case ve yüzde kodlamasının genel sözdizimi [RFC 3986](https://www.rfc-editor.org/rfc/rfc3986) temel alınarak incelendi; yukarıdaki ret ve ayrı tutma kuralları Yörünge'nin daha dar önerisidir. Python IPv6 temsili: [ipaddress](https://docs.python.org/3.11/library/ipaddress.html). Erişim: 2026-10-27. Hedefi kanonikleştirmek host güveni, TLS veya API uyumu kanıtı değildir; HTTP adaptörü aynı hedefi koruyamıyorsa credential gönderemez.

| Girdi | Origin | API kökü / sonuç |
|---|---|---|
| `https://API.EXAMPLE.TEST:443/api/v1/` | `https://api.example.test` | `/api/v1` |
| `https://api.example.test` veya `https://api.example.test/` | `https://api.example.test` | `/` |
| `https://[2001:0DB8:0000::1]:443/v1` | `https://[2001:db8::1]` | `/v1` |
| `https://api.example.test/v%31` | `https://api.example.test` | `/v%31`, `/v1` ile birleştirilmez |
| `https://api.example.test/örnek` veya `https://api.example.test/%c3%b6rnek` | `https://api.example.test` | `/%C3%B6rnek` |
| `https://api.example.test/a//b` | `https://api.example.test` | `/a//b`, `/a/b` ile birleştirilmez |
| `https://api.example.test/v1//`, `/a/../b`, `/a%2fb`, `/%252E`, `/%ZZ` | — | Ret (son dört path aynı örnek origin'e eklenir) |
| `https://api.example.test:8443/v1`, `https://api.example.test./v1`, `https://api.example.test/v1?` | — | Ret |

### Mevcut planlarla uyumluluk

P01-2 mevcut v1 offline Plan üretimi/yükleme ve digest baytlarını değiştirmez. `scope_for` bugün portu atar fakat örneğin IPv6 yazımını sıkıştırmaz; “origin/etkin port” ifadesi bu eski kaydı başka kimlik sayma gerekçesi değildir. Registry için tam context URL'si; gelecekte plan/capability karşılaştırması için kayıtlı origin + API kökü aynı `service-target-v1` kuralıyla **geçici karşılaştırma değeri** üretir. Kayıtlı Plan rewrite edilmez, digest yeniden yazılmaz ve offline Plan execution planına yükseltilmez.

Mevcut parser'ın kabul edip bu yeni credential hedef kapısının reddettiği Unicode host, bozuk escape veya belirsiz path için açık hata gerekir; sessiz hedef düzeltmesi yoktur. Gelecekte prepared plan biçimi değişirse P01-3 kendi açık şema/uyumluluk kararıyla ilerler. P01-2a ürün testleri hedef örnekleri ve eski v1 dosyalarının değişmeden yüklenmesini kapsar; kalıcı registry kimliği açık gözlem API’sinde ayrıca kaydedilir.

## Binding alan kümesi

`credential_bindings` UNIQUE anahtarı ve HMAC binding JSON'u **aynı altı alanı** içerir; ek/eksik alan, null ve duplicate key reddedilir:

| Alan | v1 tür/değer |
|---|---|
| `identity_epoch` | Küçük harf, hyphen'lı kanonik UUIDv4 string |
| `service_id` | `evren-platform` veya `evren-llm` |
| `service_origin` | Yukarıdaki kanonik origin |
| `api_base_path` | Yukarıdaki kanonik API kökü |
| `reference_type` | Yalnız `env`; başka backend bu v1'e sessizce eklenmez |
| `reference_name` | 1–128 ASCII karakter; `^[A-Z_][A-Z0-9_]*$` |

`credential_id`, revision, gözlem zamanı, tag ve `tag_format` bu altı alanın dışında kayıt metadata'sıdır. Tag biçimi `hmac-sha256-v1` olarak sabittir. Biçim değişikliği açık migration ister; UNIQUE anahtarı değiştirilmeden tag mesajı değiştirilemez. Hesap/proje/izinler ayrı context/cache/plan bağlarıdır; burada veya bir profil adıyla ikame edilmez.

## HMAC mesajı ve sınırlar

Binding JSON'u `json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")` ile üretilir: BOM/newline yok, whitespace yok, yalnız yukarıdaki ASCII alanlar ve string değerler vardır. `ensure_ascii=True` kuralı gelecekte Unicode alan eklemek için izin değildir. JSON key/escape davranışı [Python 3.11 json](https://docs.python.org/3.11/library/json.html) üzerinden incelendi (erişim: 2026-10-27).

Secret'ın tam UTF-8 baytları 1–16.384 bayt olmalıdır; boş, fazla uzun veya strict UTF-8'e çevrilemeyen değer kontrollü credential hatasıdır. Bu Yörünge kaynak sınırıdır, sağlayıcının token uzunluğu iddiası değildir. Trim/case/Unicode normalizasyonu veya kesme yoktur. Sınır ve encoding transaction'dan önce denetlenir; değer tekrar env'den okunmaz. HMAC K tam 32 bayttır.

```text
B = canonical_binding_json_bytes
S = exact_secret_utf8_bytes
M = b"yorunge:credential-observation:v1\x00" + uint64_be(len(B)) + B + uint64_be(len(S)) + S
tag = HMAC-SHA-256(K, M)   # 32 bayt; DB içinde özel, public kimlik değil
```

Uzunluklar **bayt** sayısıdır, uint64 işaretsiz big-endian tam 8 bayttır. Key-check farklı sabit purpose kullanır: `b"yorunge:key-check:v1\x00" + canonical_key_check_json_bytes`; JSON yalnız sıralı/kompakt `active_key_id`, `identity_epoch`, `store_id` kanonik UUIDv4 string alanlarını taşır, aynı JSON encoding kuralını kullanır. Store/epoch/key ID'ler DB satırıyla eşleşmelidir; böylece farklı dosya yanlış credential rotation sanılmaz. Secret veya gözlem tag'i key-check mesajına girmez.

Sentetik K/secret, tam binding/key-check JSON'u, UTF-8 uzunlukları, mesaj hex'i ve beklenen tag hex'leri [review probe'unun ham vektörlerindedir](../research/p01-2-review-probe.json). Bunlar gerçek sır değildir. [Üretici deney](../research/p01-2-review-probe.py) yalnız encoding/standart HMAC vektörünü sabitler; target normalizer veya ürün registry'sini uygulamaz. Ürün testleri aynı vektörleri bağımsız olarak tüketmeli; hedef örnekleri, alan eksikliği ve boundary negatiflerini de doğrulamalıdır.

## Kalıcı gözlem API'si

`api.observe_credential(service_id, *, config=None, profile=None, project=None, state_dir=None)` ve `context identity --service evren-platform|evren-llm [--state-dir PATH]` seçili env değerini bir kez çözüp yerel kimliği kaydeder. JSON `identity` altında `credential_id`, `credential_revision`, `identity_epoch`, `observed_at` taşır. Reference adı, secret ve karşılaştırma tag'i public sonuca girmez. `context credential` kalıcı kayıt açmadan yalnız değerin varlığını denetlemeyi sürdürür.

Aynı altı alan/değer tekrarında kimlik, nesil ve zaman değişmez. Gözlenen değer değişiminde aynı kimliğin nesli transaction içinde bir artar; A→B→A 1→2→3'tür. Eşzamanlı bağımsız env snapshot'ları kilit edinme sırasıyla kaydedilir; süreçlerin başlama zamanı veya uzak sunucunun o andaki durumu hakkında sıra garantisi yoktur. Hiç gözlenmeyen değişimler ve aynı değerin uzak izin değişimleri saptanamaz. Nesil 2^63−1 iken farklı değer `credential_revision_exhausted` verir; otomatik reset olmaz.

Hesap/proje public context'te kalır, binding anahtarının yerine geçmez. Bu gözlem eski offline Plan'a kimlik eklemez veya yürütme yetkisi vermez. Açık reset/restore/recover [state sözleşmesinde](local-state.md) tanımlıdır.
