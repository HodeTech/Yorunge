# ADR-0020: Hizmete bağlı salt okunur context keşfi

**Durum:** Proposed — kullanıcı onayı bekleniyor; bağımlı ürün kodu başlamadı. **Tarih:** 2026-10-31. **İş:** P02-0 / P02-0b. [Araştırma](../research/p02-contract-sdk-pilot.md), [kart](../roadmap/tasks/p02-0b-context-discovery.md), [paket planı](../roadmap/p02-0-delivery-plan.md).

## Bağlam

P01 yerel context/credential kimliğini ve güvenli taşıma sınırını uyguladı. Mevcut `Context` v1 `remote_verified=false` taşır; account_id/project_id seçilmiş tercihtir. Platform ve LLM aynı profil içinde olsa da aynı uzak principal/izin alanı oldukları kanıtlanmış değildir. Mevcut capability cache’in kendi kaydı güncel izin kaynağı olamaz; [ADR-0013](0013-scoped-capability-cache.md) tam kapsam/bağımsız otorite kuralı korunur.

Güncel resmî kaynaklar Platform API key için X-API-Key gösteriyor; browser’ın me/org/project uçlarını yalnız Bearer oturumunda gördük. LLM’de terms/models/quota vardır, hesap/org/project introspection endpoint’i yoktur. Bu boşlukta model owner, key hash’i, profil adı veya Platform hesap ID’sinden LLM hesabı üretilemez. SDK 0.11.0 bu keşfi sunmuyor ve ağ davranışı [ADR-0017](0017-bounded-http-transport.md) ile uyumlu değil.

Bu karar, gözlenebilen veriyi dürüstçe sunan **ayrı bir discovery sonucu** önerir. Doğrulanmamış bir uç/kimlik için başarı uydurmaz; P02-0b’nin tam kabulünü araştırma çıktısına indirmez. Eksik API key sözleşmesi ve gerçek hesap kabulü ayrı açılma kapısıdır.

## Önerilen karar

### Hizmet ayrımı ve uyumluluk

1. P02’de seçilen endpoint’ler mevcut ortak HTTP/session üstünde bağımsız, strict normalizasyonla uygulanır. EVREN SDK dependency/import/kod kopyası eklenmez. Bu, ADR-0017’nin endpoint bazlı araştırmasını bu tüketici için sonuçlandırır; gelecekte farklı bir SDK adaptörü ayrı kanıt/kararla değerlendirilebilir.
2. Eski config, `Context` v1, offline Plan, capability scope v2, Result v1 ve doctor varsayılanı değişmez. Bir profile global `remote_verified=true` yazılmaz. Yeni `ContextDiscovery` v1 yalnız açık `context discover --service evren-platform|evren-llm` / `api.discover_context(service_id, *, config=None, profile=None, project=None, state_dir=None)` çağrısının tipli `Result` verisidir. Bu adlar Proposed’dır, bugün çalışan komut değildir.
3. Her çağrı yalnız seçilen hizmetin credential’ını, env’den **bir kez** alır. Hedef/credential_id/revision/store/epoch bağını P01 registry’siyle kurar; başka hizmete, SDK env varsayılanına veya browser JWT’sine fallback yoktur. Ham key/env adı/tag/K public sonuçta bulunmaz. Registry gözlemi yerel yazı olabilir; “salt okunur” uzak hizmet etkisini tanımlar.
4. Bu paket discovery sonucunu yeni DB tablosuna veya capability cache’e yazmaz; şema 6/migration/restore/reset kuralı değişmez. Yetkiyi kalıcı cache’ten yeniden kuran bağımsız bir resolver eklenmez. Gözlem gelecekteki yan etki için izin değildir; o tüketici güncel credential, hedef, hesap/proje ve gerekli izinleri kendi final kapısında tekrar doğrular.

### Gözlem, kimlik ve seçim farklı iddialardır

Yeni kapalı referans, uygulamadan önce şu alan gruplarını kesin tür/sınır/nullability ile tanımlar: sürüm/hizmet/hedef/profil; yerel credential kimliği/nesli ve store/epoch bağı; UTC gözlem zamanı; **seçilmiş** account/project; **provider’dan doğrulanmış** principal/account/organization/project; liste tamlığı; context doğrulama sonucu ve kapalı neden kataloğu. Public sonuç auth header, email/full_name/avatar, ham role/admin_permissions veya sağlayıcı açıklaması taşımaz. UI isimleri gerekli değilse toplanmaz; principal kaydı salt gösterim verisinden türetilmez.

| İddia | Gerekli kanıt | Kanıt yoksa |
|---|---|---|
| Endpoint erişimi | Bu hizmet/key bağında auth isteyen endpoint’in strict geçerli cevabı ve doğrulanmış auth sözleşmesi | 2xx tek başına `verified` değil; endpoint/auth bağı `unknown` |
| Provider principal/account | O endpoint’in tanımlı principal/account alanı ve anlamı | null + `not_exposed` veya `unverified`; model owner veya seçilen ID kopyalanmaz |
| Organizasyon/proje listesi | Kapalı endpoint şeması ve açık pagination/tamlık | Eksik/overflow listeyi tam gösterme yok; ilk öğe varsayılan değil |
| Seçili proje eşliği | Açık çağrı → profil tercihi; aynı hizmette tam liste veya doğrudan detail ile ID/parent eşliği | `selection_required`, `unverified` veya `mismatch`; yanlış hedefe sessiz geçiş yok |
| Yazma/çıkarım izni | Göreve özgü güncel permission/endpoint kabulü | Bu keşif izin üretmez; authorization_scope=null |

Platform’da account_id’nin user ID mi organization ID mi olduğu varsayılmaz. Raw sözleşme anlamı ayrı principal/account/organization alanına kayıpsız eşlenmeden seçilmiş account_id doğrulanamaz. Herhangi bir dönen org seçilmiş hesabın yerine otomatik geçirilmez. Çok/boş proje açık durumdur; yalnız bir proje olsa bile otomatik seçilmez. Seçili ID bulunamazsa, sayfalama tamam değilken “erişim yok/silinmiş” denmez. Geçerli seçim ID’si config’e kendiliğinden yazılmaz.

LLM’de provider account/project introspection yokken bu alanlar null/`not_exposed` kalır; seçilmiş eski profil tercihleri ayrı gösterilir ve `unverified` olur. Terms cevabı key sahibi için şart durumudur; accepted=true kullanıcı kimliği, tüm model erişimi veya inference onayı değildir. Bu sınırlı kolun teslimi Platform kimlik kabulünü veya P02-0 bütününü kendiliğinden verified yapmaz. Yeni introspection sözleşmesi bulunursa kapalı parser/kabul ayrıca genişletilir.

### Endpoint ve güven sınırı

- Platform aday GET’leri: `auth/me`, `organizations`, `projects`, açık seçilmiş `projects/{id}`. API key header’ı X-API-Key; kabulü **henüz kanıtlanmadı**. Bunlar önerilen keşif whitelist’idir, doğrulanmış backend iddiası değil. Uygulama kartı ready olmadan raw minimum alanlar/envelope/pagination ve key kabulü sağlayıcı sözleşmesi veya ayrı yetkili bounded read pilotuyla kapatılır. Browser token okuma/token exchange eklenmez.
- LLM ilk aday GET’i `terms/status`; tek header `Authorization: Bearer <seçilen LLM key>`. Bu biçim resmî istemci örneği/S kaynağıyla desteklidir; `accepted=false` otomatik şart kabulü üretmez. doc_path, URL veya terms text başka hedeften otomatik takip edilmez.
- GET model/kota keşfi P02-4a/P02-6b’nin işidir; yalnız kimlik doğruluyor görünmek için toplu endpoint taraması yapılmaz. Inference, export hazırlama, upload, terms accept, key üretme, silme veya kaynak rezervasyonu whitelist’e girmez.
- Hedef binding v1, HTTPS/443, TLS, redirectsiz istek, cookie/env/log/secret izolasyonu aynen kalır. P02 storage/signed URL sınırı bu kararla açılmaz. Endpoint ID’leri alan sözdizimiyle doğrulanır; path/authority/query parçası olarak key veya ham provider URL’si kullanılmaz.

### Deadline, kaynak ve yarışlar

Bir discovery invocation config/env/registry/network/normalizasyon/final denetim dahil **30 s cooperative toplam deadline** kullanır. İstekler seri aynı owned session’da yürür; retry sahibi P01 politikasıdır: yalnız açık read-only GET en çok 2 attempt, bütün backoff’lar aynı kalan bütçeden. Response başına ≤1 MiB; toplam response gövdesi invocation başına ≤4 MiB; en çok **4 mantıksal GET / 8 attempt**. Liste başına ≤128 satır, birleşik output ≤256 KiB; mevcut portun strict JSON derinlik/node/secret sınırları ayrıca geçerlidir. Limit dolunca sessiz kırpma yok; kapalı hata veya açık incomplete/unverified sonucu referansta tek biçimde tanımlanır. Tamlığı bilinmeyen API’de bu bütçe tam tarama garantisi değildir; hazır kart gerçek pagination kararını kapatır.

State işlemi başına mevcut en çok 5 s bütçe ve 1 s lock/busy sınırı, invocation’ın daha dar kalan süresiyle birlikte uygulanır; network transaction dışında kalır. Son kısa transaction ve publish öncesinde store/epoch/clock generation, kullanılan credential ID/revision ve çağrı deadline’ı tekrar karşılaştırılır. Arada credential/epoch değişmişse `state_changed`; ikinci env çözümleme, otomatik observe/retry veya eski snapshot’la verified sonuç yoktur. Çıktı tek gözlem anına aittir; TTL veya sonraki işlem için yetki garantisi verilmez. Bloke sistem I/O’suna katı duvar saati garantisi yoktur.

Owned Runner preflight aktif loop/thread/PID/reentrancy’yi env/DB/ağ öncesi reddeder. Yerel help/context/doctor yoluna ağ/import yükü taşınmaz. İptal, UTF-8/NDJSON/BrokenPipe ve kalıcı yerel yazı belirsizliği ADR-0018’in mevcut önceliğini korur; sırf discovery iptal edildi diye registry geçmişi geri alınmış denmez.

### Hata ve public referans kapısı

Mevcut transport/credential/state/invalid_response hataları ve exit anlamları korunur. 401/403 `remote_access_denied`, 429 `remote_rate_limited`; ham server mesajı/status-body public sonuca eklenmez. Bunlar global unsupported veya otomatik `requires_access` kanıtı değildir. 2xx logical failure/yanlış alan/duplicate/oversize `invalid_response`; known context uyuşmazlığı/eksik seçim normal observation’ın kapalı doğrulama durumunda açık gösterilir, yürütme yetkisi verilmez. `Result.status=completed` yalnız keşif çağrısının tamamlanmasıdır; context doğrulanmışlığının yerine kullanılamaz.

Kesin discovery wire, her validation durumu/nedeni ve CLI text/JSON/NDJSON eşliği yeni referansla **ürün kodundan önce** kapatılır. Bilinmeyen wire alanını generic dict olarak dışarı verme, mevcut Context’i genişletme veya her yeni duruma keyfi ErrorCode ekleme yolu seçilmez. Referansın raw endpoint parser’ı kanıtsız kalırsa bağımlı adapter draft kalır; araştırma veya fake fixture ile kapatılmaz.

## Kabul

1. Önce/sonra CLI/Python/JSON uyumu; eski Context/config/Plan byte/digest ve local-only lazy davranış korunur. Yeni alanlar yalnız ayrı typed discovery verisinde bulunur.
2. Platform ve LLM bağımsız gerçek TLS fixture’ında seçili key/header/hedefle sınanır. Cross-service key, redirect, proxy/env/cookie, reflected secret ve malformed/2xx logical failure kontrollü reddedilir. Kısa secret P01 literal kuralıyla sınanır.
3. İki süreçli credential rotation/identity reset yarışı: ağ gözleminden sonra başka süreç güncel nesli değiştirir; eski çağrı finalde state_changed verir, doğrulanmış context yayımlamaz, env bir kez okunur.
4. Çok/boş/duplicate/eksik/bounded proje, eksik principal, yanlış parent ve pagination/incomplete sınırları; LLM account alanı yokluğu ve accepted=false ayrı oracle’larla sınanır. Özel role/visible model permission listesine çevrilmez.
5. CLI/Python aynı kullanım senaryosunu çağırır; normal JSON/tek-result NDJSON/UTF-8/SIGINT/output hataları, timeout/retry çağrı sayısı ve resource cleanup gerçek süreç/taşıma sınırında doğrulanır.
6. Son kaynakta tam statik/test/kurulum, kaynak bağlı startup/jobs kabulü ve bağımsız iki review turu tamamlanır. Gerçek hesap kabulü scoped pilotla ayrı kaydedilir; Platform key kimlik sözleşmesi belirsizken veya canlı kabul yokken P02-0b/P02-0 verified olmaz.

## Alternatifler

- SDK client’ını doğrudan kullanmak: discovery sağlamıyor; retry/env/parse sınırlarını yeniden sahiplenmek gerekir. Seçilmedi.
- Eski Context v1’i yerinde doğrulanmış yapmak veya Platform ID’sini LLM’ye kopyalamak: eski tüketici ve güven anlamını bozar. Seçilmedi.
- Model/kota başarılı diye hesap/izin üretmek ya da browser JWT fallback’i: kanıtın kapsamını aşar. Seçilmedi.
- Eksik introspection nedeniyle LLM hakkında hiç bilgi sunmamak: erişim/terms gözlemi bağımsız değer sağlayabilir; ancak gözlemin sınırı ayrı ve açık tutulur.
- Bu ilk tüketicide yeni kalıcı remote-context tablosu/cache şeması: güncel otorite gereksinimini çözmeden ek state yaratır. Seçilmedi; gerçek tüketici ihtiyacı olursa ayrı karar gerekir.

## Sonuçlar ve onay kapsamı

Onay; bağımsız ortak taşıma adaptörü, ayrı hizmet bağlı discovery sonucu ve doğrulanamayan kimlik/izinleri açık tutma yaklaşımını benimser. Yeni endpoint’lerin çalıştığını, bir pilotun yetkili olduğunu veya P02-0b’nin tamamlandığını ilan etmez. Ürün geliştirmesinden önce gereken raw endpoint/reference kapısı korunur. P02-0b kartı bu karar ve gerçek sözleşme açılma koşulu yüzünden draft’tır. Yeni transfer/SSE/yan etki kararları kendi tüketicisinde ele alınır; bu ADR onları önceden onaylamaz.
